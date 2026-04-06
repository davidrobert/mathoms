#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E0-unlock — Descriptografa PDFs protegidos por senha no inbox.

Usage:
  python scripts/e0_unlock.py                    # Processa todos os PDFs do inbox
  python scripts/e0_unlock.py --file X.pdf       # Processa um arquivo específico
  python scripts/e0_unlock.py --dry-run          # Mostra quais estão protegidos, sem alterar
  python scripts/e0_unlock.py --check-destinations  # Varre data/ e members/ por PDFs encriptados
                                                    # e desbloqueia in-place

Tenta as senhas configuradas em config/passwords.txt (uma por linha).
PDFs já abertos são ignorados. O original protegido é substituído pela
versão desbloqueada (o pipeline nunca deve processar PDFs com senha).

IMPORTANTE: Rodar ANTES do roteamento E0.A (para inbox/) e DEPOIS
(com --check-destinations) para garantir que nenhum PDF encriptado
chegou aos destinos — especialmente arquivos com nomes originais que
foram renomeados e roteados sem passar pelo unlock.

Author: Claude Opus 4.6
Date: 2026-04-05 (atualizado 2026-04-06: --check-destinations)
"""

import argparse
import sys
from datetime import date
from pathlib import Path

try:
    import pikepdf
except ImportError:
    print("ERRO: pikepdf não instalado. Rode: pip install pikepdf")
    sys.exit(1)

# ---------- paths ----------
BASE = Path(__file__).resolve().parent.parent
INBOX = BASE / "inbox"
PASSWORDS_FILE = BASE / "config" / "passwords.txt"
QA_LOG = BASE / "logs" / "qa_log.md"
DEST_DIRS = [
    BASE / "data" / "financial_statements",
    BASE / "data" / "income_tax_br",
    BASE / "data" / "real_estate",
    BASE / "data" / "vehicles",
    BASE / "members",
]


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
            print(f"  ✓ Desbloqueado com sucesso")
            return True
        except pikepdf.PasswordError:
            continue
        except Exception as e:
            print(f"  ERRO ao salvar {pdf_path.name}: {e}")
            return False
    print(f"  ✗ Nenhuma senha funcionou")
    return False


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
        print(f"Registrado em logs/qa_log.md")

    return failed


def main():
    parser = argparse.ArgumentParser(description="Desbloqueia PDFs protegidos por senha no inbox")
    parser.add_argument("--file", type=str, help="Processar apenas este arquivo (nome no inbox)")
    parser.add_argument("--dry-run", action="store_true", help="Apenas mostra status, sem alterar")
    parser.add_argument("--check-destinations", action="store_true",
                        help="Varre data/ e members/ por PDFs encriptados e desbloqueia in-place")
    args = parser.parse_args()

    passwords = load_passwords()
    print(f"Senhas carregadas: {len(passwords)}")
    print()

    # Modo --check-destinations: varrer destinos em vez do inbox
    if args.check_destinations:
        failed = check_destinations(passwords, dry_run=args.dry_run)
        sys.exit(2 if failed > 0 else 0)

    # Determinar arquivos a verificar
    if args.file:
        target = INBOX / args.file
        if not target.exists():
            print(f"ERRO: Arquivo não encontrado: {target}")
            sys.exit(1)
        pdf_files = [target]
    else:
        pdf_files = sorted(list(INBOX.glob("*.pdf")) + list(INBOX.glob("*.PDF")))

    if not pdf_files:
        print("Nenhum PDF encontrado no inbox.")
        return

    encrypted = []
    skipped = []

    for pdf_path in pdf_files:
        if is_encrypted(pdf_path):
            encrypted.append(pdf_path)
        else:
            skipped.append(pdf_path)

    print(f"PDFs no inbox: {len(pdf_files)}")
    print(f"  Protegidos: {len(encrypted)}")
    print(f"  Abertos:    {len(skipped)}")
    print()

    if not encrypted:
        print("Nenhum PDF protegido por senha. Nada a fazer.")
        return

    # Tentar desbloquear
    success = 0
    failed = 0
    failed_files: list[str] = []
    for pdf_path in encrypted:
        print(f"→ {pdf_path.name}")
        if try_unlock(pdf_path, passwords, dry_run=args.dry_run):
            success += 1
        else:
            failed += 1
            failed_files.append(pdf_path.name)

    print()
    action = "Identificados" if args.dry_run else "Desbloqueados"
    print(f"{action}: {success} | Falha: {failed}")

    if failed > 0:
        # --- Alerta no console ---
        print()
        print("=" * 60)
        print("  ⚠️  ALERTA: PDFs PROTEGIDOS SEM SENHA VÁLIDA")
        print("=" * 60)
        print()
        print(f"  {failed} arquivo(s) não puderam ser desbloqueados.")
        print(f"  Nenhuma das {len(passwords)} senhas em config/passwords.txt funcionou.")
        print()
        for name in failed_files:
            print(f"    • {name}")
        print()
        print("  Ação necessária:")
        print("    1. Obtenha a senha correta do banco/instituição")
        print("    2. Adicione a nova senha em config/passwords.txt")
        print("    3. Rode novamente: python scripts/e0_unlock.py")
        print()
        print("  Estes arquivos NÃO serão processados pelo pipeline até")
        print("  serem desbloqueados — E2 falhará ao tentar extrair dados.")
        print("=" * 60)

        # --- Registrar no qa_log.md ---
        if not args.dry_run:
            qa_entries = []
            for name in failed_files:
                qa_entries.append(
                    f"`[WARN]` E0-unlock | Arquivo `{name}` protegido por senha — "
                    f"nenhuma das {len(passwords)} senhas configuradas funcionou. "
                    f"Pipeline não conseguirá extrair dados deste PDF."
                )
            append_qa_log(qa_entries)
            print(f"\n  Registrado em logs/qa_log.md")

        # Exit code 2 = parcialmente bem-sucedido (diferente de 1 = erro fatal)
        sys.exit(2)


if __name__ == "__main__":
    main()
