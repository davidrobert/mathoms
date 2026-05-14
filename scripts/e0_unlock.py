#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
E0-unlock — Descriptografa PDFs protegidos por senha e descompacta ZIPs
com senha no inbox.

Usage:
  python scripts/e0_unlock.py                    # Processa todos os PDFs e ZIPs do inbox
  python scripts/e0_unlock.py --file X.pdf       # Processa um arquivo específico
  python scripts/e0_unlock.py --file X.zip       # Descompacta ZIP específico com senha
  python scripts/e0_unlock.py --dry-run          # Mostra quais estão protegidos, sem alterar
  python scripts/e0_unlock.py --check-destinations  # Varre data/ e members/ por PDFs encriptados
                                                    # e desbloqueia in-place

Tenta as senhas configuradas em config/passwords.txt (uma por linha).
PDFs já abertos são ignorados. O original protegido é substituído pela
versão desbloqueada (o pipeline nunca deve processar PDFs com senha).

ZIPs protegidos são descompactados no inbox/ e o arquivo .zip é movido
para inbox_processed/ após extração bem-sucedida. ZIPs sem senha são
descompactados diretamente. Conteúdo extraído fica no inbox/ para
roteamento normal no E0.A.

IMPORTANTE: Rodar ANTES do roteamento E0.A (para inbox/) e DEPOIS
(com --check-destinations) para garantir que nenhum PDF encriptado
chegou aos destinos — especialmente arquivos com nomes originais que
foram renomeados e roteados sem passar pelo unlock.

Author: Claude Opus 4.6
Date: 2026-04-05 (atualizado 2026-04-06: --check-destinations)
       (atualizado 2026-04-07: suporte a ZIP com senha)
"""

import argparse
import sys
import zipfile
from datetime import date
from pathlib import Path

try:
    import pikepdf
except ImportError:
    print("ERRO: pikepdf não instalado. Rode: pip install pikepdf")
    sys.exit(1)

import scripts.pipeline_common as _pc

_DEFAULT_BASE_DIR = _pc._DEFAULT_BASE_DIR

# ---------- paths — script-specific extras ----------


def _init_config(base_dir: Path) -> None:
    """(Re-)inicializa paths globais a partir de base_dir."""
    global BASE, INBOX, INBOX_PROCESSED, PASSWORDS_FILE, QA_LOG, DEST_DIRS
    _pc._init_config(base_dir)
    BASE = _pc.PROJECT_DIR
    INBOX = _pc.INBOX_DIR
    INBOX_PROCESSED = _pc.INBOX_PROCESSED_DIR
    PASSWORDS_FILE = _pc.CONFIG_DIR / "passwords.txt"
    QA_LOG = _pc.LOGS_DIR / "qa_log.md"
    DEST_DIRS = [
        _pc.DATA_DIR / "financial_statements",
        _pc.DATA_DIR / "income_tax_br",
        _pc.DATA_DIR / "real_estate",
        _pc.DATA_DIR / "vehicles",
        _pc.MEMBERS_DIR,
    ]


_init_config(_pc.PROJECT_DIR)


def _discover_dest_dirs() -> list:
    """Descobre todos os subdiretórios de data/ + members/."""
    dirs = list(DEST_DIRS)  # Base list
    data_dir = BASE / "data"
    if data_dir.exists():
        for d in sorted(data_dir.iterdir()):
            if d.is_dir() and d not in dirs:
                dirs.append(d)
    return dirs


def append_qa_log(entries: list[str]) -> None:
    """Appenda alertas ao qa_log.md."""
    if not entries:
        return
    QA_LOG.parent.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    lines = [f"\n## E0-unlock — {today}\n"]
    for entry in entries:
        lines.append(f"- {entry}\n")
    with open(QA_LOG, "a", encoding="utf-8") as f:
        f.writelines(lines)


def load_passwords() -> list[str]:
    """Carrega senhas de config/passwords.txt (uma por linha, ignora vazias e #)."""
    if not PASSWORDS_FILE.exists():
        print(f"ERRO: Arquivo de senhas não encontrado: {PASSWORDS_FILE}")
        print("Crie o arquivo com uma senha por linha.")
        sys.exit(1)
    passwords = []
    for line in PASSWORDS_FILE.read_text().strip().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            passwords.append(line)
    if not passwords:
        print(f"ERRO: Nenhuma senha encontrada em {PASSWORDS_FILE}")
        sys.exit(1)
    return passwords


def is_encrypted(pdf_path: Path) -> bool:
    """Verifica se o PDF está protegido por senha."""
    try:
        with pikepdf.open(pdf_path) as _:
            return False
    except pikepdf.PasswordError:
        return True
    except Exception as e:
        print(f"  WARN: PDF possivelmente corrompido {pdf_path.name}: {e}")
        return False  # Não é encriptado, mas pode estar corrompido — E2 lidará


def try_unlock(pdf_path: Path, passwords: list[str], dry_run: bool = False) -> bool:
    """Tenta desbloquear o PDF com cada senha. Retorna True se desbloqueou."""
    for pw in passwords:
        try:
            with pikepdf.open(pdf_path, password=pw) as pdf:
                if dry_run:
                    print(f"  ✓ Senha encontrada (senha: {'*' * len(pw)})")
                    return True
                # Salva versão desbloqueada
                tmp = pdf_path.with_suffix(".tmp.pdf")
                pdf.save(tmp)
            # Cria backup antes de substituir
            bak = pdf_path.with_suffix(".bak.pdf")
            try:
                pdf_path.rename(bak)
                tmp.rename(pdf_path)
                # Verifica que o novo arquivo é legível
                with pikepdf.open(pdf_path) as _check:
                    pass
                bak.unlink()  # Backup OK, remove
            except Exception as e_replace:
                # Rollback: restaura original
                if bak.exists():
                    if pdf_path.exists():
                        pdf_path.unlink()
                    bak.rename(pdf_path)
                if tmp.exists():
                    tmp.unlink()
                print(f"  ERRO ao substituir {pdf_path.name}: {e_replace}")
                return False
            print("  ✓ Desbloqueado com sucesso")
            return True
        except pikepdf.PasswordError:
            continue
        except Exception as e:
            print(f"  ERRO ao salvar {pdf_path.name}: {e}")
            return False
    print("  ✗ Nenhuma senha funcionou")
    return False


# ---------- ZIP functions ----------

MAX_EXTRACT_FILE_SIZE = 500 * 1024 * 1024  # 500 MB per member
MAX_EXTRACT_TOTAL_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB total


def _safe_extractall(zf: zipfile.ZipFile, dest_dir: Path, pwd: bytes | None = None) -> None:
    """Extract ZIP members with path traversal validation (zip slip) and size limits."""
    dest_resolved = dest_dir.resolve()
    total_size = 0
    members_to_extract = []

    for member in zf.infolist():
        # Zip slip check
        member_path = (dest_dir / member.filename).resolve()
        if not str(member_path).startswith(str(dest_resolved)):
            raise ValueError(
                f"ZIP member '{member.filename}' resolves outside destination "
                f"directory — possible zip slip attack. Aborting extraction."
            )
        # Size limit per file
        if member.file_size > MAX_EXTRACT_FILE_SIZE:
            print(
                f"  WARN: ZIP member '{member.filename}' "
                f"({member.file_size / (1024*1024):.0f}MB) excede limite de "
                f"{MAX_EXTRACT_FILE_SIZE // (1024*1024)}MB — pulando"
            )
            continue
        # Cumulative size limit
        total_size += member.file_size
        if total_size > MAX_EXTRACT_TOTAL_SIZE:
            raise ValueError(
                f"ZIP total extraction size ({total_size / (1024**3):.1f}GB) "
                f"excede limite de {MAX_EXTRACT_TOTAL_SIZE // (1024**3)}GB — "
                f"abortando extração."
            )
        members_to_extract.append(member)

    for member in members_to_extract:
        zf.extract(member, dest_dir, pwd=pwd)


def is_zip_encrypted(zip_path: Path) -> bool:
    """Verifica se o ZIP está protegido por senha."""
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            # Tenta ler o primeiro arquivo sem senha
            for info in zf.infolist():
                if not info.is_dir():
                    try:
                        zf.read(info.filename)
                        return False  # Conseguiu ler sem senha
                    except RuntimeError:
                        return True  # Precisa de senha
            return False  # ZIP vazio ou só diretórios
    except zipfile.BadZipFile:
        print(f"  WARN: Arquivo ZIP possivelmente corrompido: {zip_path.name}")
        return False
    except Exception as e:
        print(f"  WARN: Erro ao verificar ZIP {zip_path.name}: {e}")
        return False


def try_extract_zip(zip_path: Path, passwords: list[str], dry_run: bool = False) -> bool:
    """Tenta descompactar o ZIP (com ou sem senha) no diretório pai.

    Retorna True se extraiu com sucesso.
    Após extração, move o .zip para inbox_processed/.
    """
    dest_dir = zip_path.parent

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            file_list = [i for i in zf.infolist() if not i.is_dir()]
            if not file_list:
                print(f"  WARN: ZIP vazio (sem arquivos): {zip_path.name}")
                return False

            # Tenta sem senha primeiro
            try:
                zf.read(file_list[0].filename)
                # ZIP sem senha
                if dry_run:
                    print(f"  ✓ ZIP sem senha — {len(file_list)} arquivo(s)")
                    for info in file_list:
                        print(f"      → {info.filename}")
                    return True
                _safe_extractall(zf, dest_dir)
                print(f"  ✓ Extraído (sem senha) — {len(file_list)} arquivo(s)")
                for info in file_list:
                    print(f"      → {info.filename}")
                _move_zip_to_processed(zip_path)
                return True
            except RuntimeError:
                pass  # Precisa de senha, continua abaixo

            # Tenta cada senha
            for pw in passwords:
                try:
                    pw_bytes = pw.encode("utf-8")
                    zf.read(file_list[0].filename, pwd=pw_bytes)
                    # Senha funciona
                    if dry_run:
                        print(
                            f"  ✓ Senha encontrada (senha: {'*' * len(pw)}) — {len(file_list)} arquivo(s)"
                        )
                        for info in file_list:
                            print(f"      → {info.filename}")
                        return True
                    _safe_extractall(zf, dest_dir, pwd=pw_bytes)
                    print(f"  ✓ Extraído com senha — {len(file_list)} arquivo(s)")
                    for info in file_list:
                        print(f"      → {info.filename}")
                    _move_zip_to_processed(zip_path)
                    return True
                except RuntimeError:
                    continue

            print("  ✗ Nenhuma senha funcionou para o ZIP")
            return False

    except zipfile.BadZipFile:
        print(f"  ERRO: Arquivo ZIP corrompido: {zip_path.name}")
        return False
    except Exception as e:
        print(f"  ERRO ao extrair ZIP {zip_path.name}: {e}")
        return False


def _move_zip_to_processed(zip_path: Path) -> None:
    """Move o .zip para inbox_processed/ após extração."""
    INBOX_PROCESSED.mkdir(parents=True, exist_ok=True)
    dest = INBOX_PROCESSED / zip_path.name
    if dest.exists():
        # Evita colisão: adiciona sufixo
        stem = zip_path.stem
        suffix = zip_path.suffix
        i = 1
        while dest.exists():
            dest = INBOX_PROCESSED / f"{stem}_{i}{suffix}"
            i += 1
    zip_path.rename(dest)
    print(f"  → ZIP movido para inbox_processed/{dest.name}")


# ---------- check-destinations ----------


def check_destinations(passwords: list[str], dry_run: bool = False) -> int:
    """Varre diretórios de destino por PDFs encriptados e desbloqueia in-place.

    Retorna o número de PDFs que não puderam ser desbloqueados.
    """
    print("=" * 60)
    print("  CHECK-DESTINATIONS: Varrendo PDFs nos destinos")
    print("=" * 60)
    print()

    all_pdfs = []
    for d in _discover_dest_dirs():
        if d.exists():
            all_pdfs.extend(sorted(list(d.glob("*.pdf")) + list(d.glob("*.PDF"))))

    encrypted = []
    for pdf_path in all_pdfs:
        if is_encrypted(pdf_path):
            encrypted.append(pdf_path)

    print(f"PDFs nos destinos: {len(all_pdfs)}")
    print(f"  Encriptados: {len(encrypted)}")
    print()

    if not encrypted:
        print("✅ Nenhum PDF encriptado nos destinos.")
        return 0

    success = 0
    failed = 0
    failed_files: list[str] = []
    qa_entries = []

    for pdf_path in encrypted:
        rel = pdf_path.relative_to(BASE)
        print(f"→ {rel}")
        if try_unlock(pdf_path, passwords, dry_run=dry_run):
            success += 1
            if not dry_run:
                qa_entries.append(
                    f"`[FIX]` E0-unlock --check-destinations | `{rel}` estava encriptado "
                    f"no destino — desbloqueado in-place."
                )
        else:
            failed += 1
            failed_files.append(str(rel))
            qa_entries.append(
                f"`[WARN]` E0-unlock --check-destinations | `{rel}` encriptado no destino "
                f"— nenhuma senha funcionou. E2 falhará neste arquivo."
            )

    print()
    action = "Identificados" if dry_run else "Corrigidos"
    print(f"{action}: {success} | Falha: {failed}")

    if not dry_run and qa_entries:
        append_qa_log(qa_entries)
        print("Registrado em logs/qa_log.md")

    return failed


def main(root_dir: Path = None):
    if root_dir:
        _init_config(root_dir)
    parser = argparse.ArgumentParser(
        description="Desbloqueia PDFs protegidos por senha e descompacta ZIPs com senha no inbox"
    )
    parser.add_argument("--file", type=str, help="Processar apenas este arquivo (nome no inbox)")
    parser.add_argument("--dry-run", action="store_true", help="Apenas mostra status, sem alterar")
    parser.add_argument(
        "--check-destinations",
        action="store_true",
        help="Varre data/ e members/ por PDFs encriptados e desbloqueia in-place",
    )
    args = parser.parse_args([] if root_dir else None)

    passwords = load_passwords()
    print(f"Senhas carregadas: {len(passwords)}")
    print()

    # Modo --check-destinations: varrer destinos em vez do inbox
    if args.check_destinations:
        failed = check_destinations(passwords, dry_run=args.dry_run)
        sys.exit(2 if failed > 0 else 0)

    # ==================== ZIPs ====================
    if args.file and args.file.lower().endswith(".zip"):
        target = (INBOX / args.file).resolve()
        if not str(target).startswith(str(INBOX.resolve())):
            print(f"ERRO: Caminho inválido (fora do inbox): {args.file}")
            sys.exit(1)
        zip_files = [target]
        if not zip_files[0].exists():
            print(f"ERRO: Arquivo não encontrado: {zip_files[0]}")
            sys.exit(1)
    elif not args.file:
        zip_files = sorted(list(INBOX.glob("*.zip")) + list(INBOX.glob("*.ZIP")))
    else:
        zip_files = []

    zip_success = 0
    zip_failed = 0
    zip_failed_files: list[str] = []

    if zip_files:
        print(f"ZIPs no inbox: {len(zip_files)}")
        print()

        for zip_path in zip_files:
            print(f"→ {zip_path.name}")
            if try_extract_zip(zip_path, passwords, dry_run=args.dry_run):
                zip_success += 1
            else:
                if is_zip_encrypted(zip_path):
                    zip_failed += 1
                    zip_failed_files.append(zip_path.name)
                else:
                    zip_failed += 1
                    zip_failed_files.append(zip_path.name)

        print()
        action = "Identificados" if args.dry_run else "Extraídos"
        print(f"ZIPs — {action}: {zip_success} | Falha: {zip_failed}")
        print()

    # ==================== PDFs ====================
    if args.file and not args.file.lower().endswith(".zip"):
        target = (INBOX / args.file).resolve()
        if not str(target).startswith(str(INBOX.resolve())):
            print(f"ERRO: Caminho inválido (fora do inbox): {args.file}")
            sys.exit(1)
        if not target.exists():
            print(f"ERRO: Arquivo não encontrado: {target}")
            sys.exit(1)
        pdf_files = [target]
    elif not args.file:
        pdf_files = sorted(list(INBOX.glob("*.pdf")) + list(INBOX.glob("*.PDF")))
    else:
        pdf_files = []

    encrypted = []
    skipped = []

    for pdf_path in pdf_files:
        if is_encrypted(pdf_path):
            encrypted.append(pdf_path)
        else:
            skipped.append(pdf_path)

    if pdf_files:
        print(f"PDFs no inbox: {len(pdf_files)}")
        print(f"  Protegidos: {len(encrypted)}")
        print(f"  Abertos:    {len(skipped)}")
        print()

    pdf_success = 0
    pdf_failed = 0
    pdf_failed_files: list[str] = []

    if encrypted:
        for pdf_path in encrypted:
            print(f"→ {pdf_path.name}")
            if try_unlock(pdf_path, passwords, dry_run=args.dry_run):
                pdf_success += 1
            else:
                pdf_failed += 1
                pdf_failed_files.append(pdf_path.name)

        print()
        action = "Identificados" if args.dry_run else "Desbloqueados"
        print(f"PDFs — {action}: {pdf_success} | Falha: {pdf_failed}")

    if not pdf_files and not zip_files:
        print("Nenhum PDF ou ZIP encontrado no inbox.")
        return

    if not encrypted and not zip_files:
        print("Nenhum PDF protegido por senha. Nada a fazer.")
        return

    # ==================== Resumo de falhas ====================
    all_failed_files = pdf_failed_files + zip_failed_files
    total_failed = pdf_failed + zip_failed

    if total_failed > 0:
        # --- Alerta no console ---
        print()
        print("=" * 60)
        print("  ALERTA: ARQUIVOS PROTEGIDOS SEM SENHA VÁLIDA")
        print("=" * 60)
        print()
        print(f"  {total_failed} arquivo(s) não puderam ser processados.")
        print(f"  Nenhuma das {len(passwords)} senhas em config/passwords.txt funcionou.")
        print()
        for name in all_failed_files:
            print(f"    - {name}")
        print()
        print("  Ação necessária:")
        print("    1. Obtenha a senha correta do banco/instituição")
        print("    2. Adicione a nova senha em config/passwords.txt")
        print("    3. Rode novamente: python scripts/e0_unlock.py")
        print()
        if pdf_failed_files:
            print("  PDFs protegidos NÃO serão processados pelo pipeline até")
            print("  serem desbloqueados — E2 falhará ao tentar extrair dados.")
        if zip_failed_files:
            print("  ZIPs protegidos NÃO serão descompactados até que a senha")
            print("  correta seja adicionada em config/passwords.txt.")
        print("=" * 60)

        # --- Registrar no qa_log.md ---
        if not args.dry_run:
            qa_entries = []
            for name in pdf_failed_files:
                qa_entries.append(
                    f"`[WARN]` E0-unlock | Arquivo `{name}` protegido por senha — "
                    f"nenhuma das {len(passwords)} senhas configuradas funcionou. "
                    f"Pipeline não conseguirá extrair dados deste PDF."
                )
            for name in zip_failed_files:
                qa_entries.append(
                    f"`[WARN]` E0-unlock | ZIP `{name}` protegido por senha — "
                    f"nenhuma das {len(passwords)} senhas configuradas funcionou. "
                    f"Conteúdo não foi extraído para o inbox."
                )
            append_qa_log(qa_entries)
            print("\n  Registrado em logs/qa_log.md")

        # Exit code 2 = parcialmente bem-sucedido (diferente de 1 = erro fatal)
        sys.exit(2)
