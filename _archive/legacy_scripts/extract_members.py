#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E1 Member Mapping - Extract member data from CV and payslip documents
"""
import json
import re
from datetime import datetime
from pathlib import Path
from docx import Document
import pdfplumber

# Base directory
BASE_DIR = Path(__file__).parent
MEMBERS_DIR = BASE_DIR / "members"
CONFIG_DIR = BASE_DIR / "config"

# Load family members config
with open(CONFIG_DIR / "family_members.json", "r", encoding="utf-8") as f:
    FAMILY_CONFIG = json.load(f)

MEMBERS = FAMILY_CONFIG.get("membros", {})

def parse_date(date_str):
    """Parse various date formats to YYYY-MM or YYYY-MM-DD"""
    if not date_str or date_str.lower() in ["atual", "present", "presente", "atualmente"]:
        return "presente"

    date_str = date_str.strip().lower()

    # Handle month names in Portuguese
    months = {
        "janeiro": "01", "jan": "01",
        "fevereiro": "02", "fev": "02",
        "março": "03", "mar": "03",
        "abril": "04", "abr": "04",
        "maio": "05", "mai": "05",
        "junho": "06", "jun": "06",
        "julho": "07", "jul": "07",
        "agosto": "08", "ago": "08",
        "setembro": "09", "set": "09",
        "outubro": "10", "out": "10",
        "novembro": "11", "nov": "11",
        "dezembro": "12", "dez": "12",
    }

    # Try "mês ano" format: "junho 2019"
    for month_pt, month_num in months.items():
        if month_pt in date_str:
            # Extract year
            year_match = re.search(r"(\d{4})", date_str)
            if year_match:
                year = year_match.group(1)
                return f"{year}-{month_num}"

    # Try YYYY-MM or DD/MM/YYYY
    if len(date_str) == 7 and "-" in date_str:
        return date_str

    return date_str

def extract_david_cv():
    """Extract David's CV from DOCX"""
    docx_path = MEMBERS_DIR / "david_curriculo-0_original.docx"

    if not docx_path.exists():
        return None

    doc = Document(docx_path)
    full_text = "\n".join([p.text for p in doc.paragraphs])

    # Parse CV data
    data = {
        "tipo": "curriculo",
        "membro": "david",
        "nome_completo": MEMBERS["david"]["nome_completo"],
        "nome_atual": MEMBERS["david"]["nome_completo"],
        "nome_solteiro": MEMBERS["david"]["nome_solteiro"],
        "profissao_cargo": MEMBERS["david"]["profissao"],
        "data_nascimento": MEMBERS["david"]["data_nascimento"],
        "cpf": MEMBERS["david"]["cpf"],
        "experiencias": [],
        "formacao": [],
        "certificacoes": [],
        "habilidades": [],
        "idiomas": []
    }

    # Extract from text - simplified extraction
    # Look for common patterns in CV
    lines = full_text.split("\n")

    current_section = None
    for i, line in enumerate(lines):
        line_clean = line.strip().lower()

        if "experiência" in line_clean or "experience" in line_clean:
            current_section = "experiencias"
        elif "educação" in line_clean or "education" in line_clean or "formação" in line_clean:
            current_section = "formacao"
        elif "certificação" in line_clean or "certification" in line_clean:
            current_section = "certificacoes"
        elif "habilidade" in line_clean or "skills" in line_clean or "competência" in line_clean:
            current_section = "habilidades"
        elif "idioma" in line_clean or "languages" in line_clean:
            current_section = "idiomas"
        elif line.strip() and current_section:
            # Add content to current section
            if current_section == "experiencias":
                # Try to extract job info
                if any(keyword in line for keyword in ["Arvo", "CTO", "LTDA", "Kiwify"]):
                    data["experiencias"].append({"descricao": line.strip()})
            elif current_section == "formacao":
                if any(keyword in line for keyword in ["PUC", "USP", "mestrado", "Ciência"]):
                    data["formacao"].append({"descricao": line.strip()})

    return data

def extract_mariana_cv():
    """Extract Mariana's CV from PDF"""
    pdf_path = MEMBERS_DIR / "mariana_curriculo-0_original.pdf"

    if not pdf_path.exists():
        return None

    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            full_text += page.extract_text() or ""

    data = {
        "tipo": "curriculo",
        "membro": "mariana",
        "nome_completo": MEMBERS["mariana"]["nome_completo"],
        "nome_atual": MEMBERS["mariana"]["nome_completo"],
        "nome_solteira": MEMBERS["mariana"]["nome_solteira"],
        "nome_fiscal": MEMBERS["mariana"]["nome_fiscal"],
        "profissao_cargo": MEMBERS["mariana"]["profissao"],
        "data_nascimento": MEMBERS["mariana"]["data_nascimento"],
        "cpf": MEMBERS["mariana"]["cpf"],
        "experiencias": [],
        "formacao": [],
        "certificacoes": [],
        "habilidades": [],
        "idiomas": []
    }

    lines = full_text.split("\n")
    current_section = None

    for line in lines:
        line_clean = line.strip().lower()

        if "experiência" in line_clean or "experience" in line_clean:
            current_section = "experiencias"
        elif "educação" in line_clean or "education" in line_clean or "formação" in line_clean:
            current_section = "formacao"
        elif "certificação" in line_clean or "certification" in line_clean:
            current_section = "certificacoes"
        elif "habilidade" in line_clean or "skills" in line_clean:
            current_section = "habilidades"
        elif "idioma" in line_clean or "languages" in line_clean:
            current_section = "idiomas"
        elif line.strip() and current_section:
            if current_section == "experiencias":
                if any(keyword in line for keyword in ["Einstein", "Hospital", "Enfermeira", "Cardiologia"]):
                    data["experiencias"].append({"descricao": line.strip()})
            elif current_section == "formacao":
                if any(keyword in line for keyword in ["Enfermagem", "UNIFESP", "USP", "especialização"]):
                    data["formacao"].append({"descricao": line.strip()})

    return data

def extract_mariana_payslip():
    """Extract Mariana's payslip from PDF"""
    pdf_path = MEMBERS_DIR / "mariana_holerite_202602-0_original.pdf"

    if not pdf_path.exists():
        return None

    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            full_text += page.extract_text() or ""

    data = {
        "tipo": "holerite",
        "membro": "mariana",
        "nome_no_documento": MEMBERS["mariana"]["nome_fiscal"],
        "periodo": "2026-02",
        "empresa": "Sociedade Beneficente Israelita Albert Einstein",
        "estabelecimento": "Hospital Israelita Albert Einstein",
        "cargo": "Enfermeira",
        "salario_bruto": None,
        "proventos_adicionais": [],
        "descontos": [],
        "total_descontos": None,
        "salario_liquido": None,
        "data_credito": None,
        "fgts": None,
        "inss_base": None,
        "dependentes_ir": None
    }

    # Extract numerical values from PDF text
    lines = full_text.split("\n")

    for i, line in enumerate(lines):
        # Look for salary-related keywords
        if "salário" in line.lower() or "vencimento" in line.lower():
            # Try to extract number from this or next line
            numbers = re.findall(r"[\d.,]+", line)
            if numbers:
                # Use the first substantial number
                val = numbers[-1].replace(".", "").replace(",", ".")
                try:
                    data["salario_bruto"] = float(val)
                except:
                    pass

        elif "líquido" in line.lower():
            numbers = re.findall(r"[\d.,]+", line)
            if numbers:
                val = numbers[-1].replace(".", "").replace(",", ".")
                try:
                    data["salario_liquido"] = float(val)
                except:
                    pass

        elif "inss" in line.lower() and "desconto" not in line.lower():
            numbers = re.findall(r"[\d.,]+", line)
            if numbers:
                val = numbers[-1].replace(".", "").replace(",", ".")
                try:
                    data["inss_base"] = float(val)
                except:
                    pass

        elif "fgts" in line.lower():
            numbers = re.findall(r"[\d.,]+", line)
            if numbers:
                val = numbers[-1].replace(".", "").replace(",", ".")
                try:
                    data["fgts"] = float(val)
                except:
                    pass

        elif "desconto" in line.lower() or "ir" in line.lower():
            numbers = re.findall(r"[\d.,]+", line)
            if numbers and not any(kw in line.lower() for kw in ["nota", "obs"]):
                data["descontos"].append(line.strip())

    return data

def main():
    """Main extraction pipeline"""
    results = {}

    # Extract David's CV
    print("Extracting David's CV...")
    david_cv = extract_david_cv()
    if david_cv:
        output_path = MEMBERS_DIR / "david_curriculo-1a_extract.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(david_cv, f, ensure_ascii=False, indent=2)
        print(f"  ✓ Saved to {output_path}")
        results["david_cv"] = david_cv
    else:
        print("  ✗ Failed to extract David's CV")

    # Extract Mariana's CV
    print("Extracting Mariana's CV...")
    mariana_cv = extract_mariana_cv()
    if mariana_cv:
        output_path = MEMBERS_DIR / "mariana_curriculo-1a_extract.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(mariana_cv, f, ensure_ascii=False, indent=2)
        print(f"  ✓ Saved to {output_path}")
        results["mariana_cv"] = mariana_cv
    else:
        print("  ✗ Failed to extract Mariana's CV")

    # Extract Mariana's Payslip
    print("Extracting Mariana's payslip...")
    mariana_payslip = extract_mariana_payslip()
    if mariana_payslip:
        output_path = MEMBERS_DIR / "mariana_holerite_202602-1a_extract.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(mariana_payslip, f, ensure_ascii=False, indent=2)
        print(f"  ✓ Saved to {output_path}")
        results["mariana_payslip"] = mariana_payslip
    else:
        print("  ✗ Failed to extract Mariana's payslip")

    # Create unified member data
    print("Creating unified member data...")
    unified = {
        "data_extracao": datetime.now().isoformat(),
        "membros": {
            "david": david_cv,
            "mariana": mariana_cv
        },
        "holerites": {
            "mariana_202602": mariana_payslip
        }
    }

    unified_path = MEMBERS_DIR / "members-1b_unified.json"
    with open(unified_path, "w", encoding="utf-8") as f:
        json.dump(unified, f, ensure_ascii=False, indent=2)
    print(f"  ✓ Saved to {unified_path}")

    # Create enriched markdown profiles
    print("Creating enriched markdown profiles...")
    enriched_md = create_enriched_markdown(david_cv, mariana_cv, mariana_payslip)
    enriched_path = MEMBERS_DIR / "members-1c_enriched.md"
    with open(enriched_path, "w", encoding="utf-8") as f:
        f.write(enriched_md)
    print(f"  ✓ Saved to {enriched_path}")

    print("\n✓ E1 extraction complete!")

def create_enriched_markdown(david_cv, mariana_cv, mariana_payslip):
    """Create enriched markdown profiles"""
    md = "# Perfis dos Membros da Família\n\n"
    md += f"_Extraído em {datetime.now().strftime('%d/%m/%Y às %H:%M')}._\n\n"

    if david_cv:
        md += "## David\n\n"
        md += f"**Nome Completo:** {david_cv.get('nome_completo', 'N/A')}\n"
        md += f"**Data de Nascimento:** {david_cv.get('data_nascimento', 'N/A')}\n"
        md += f"**CPF:** {david_cv.get('cpf', 'N/A')}\n"
        md += f"**Profissão/Cargo:** {david_cv.get('profissao_cargo', 'N/A')}\n"

        if david_cv.get('experiencias'):
            md += "\n### Experiências Profissionais\n"
            for exp in david_cv['experiencias']:
                md += f"- {exp.get('descricao', 'N/A')}\n"

        if david_cv.get('formacao'):
            md += "\n### Formação Acadêmica\n"
            for form in david_cv['formacao']:
                md += f"- {form.get('descricao', 'N/A')}\n"

        md += "\n"

    if mariana_cv:
        md += "## Mariana\n\n"
        md += f"**Nome Completo:** {mariana_cv.get('nome_completo', 'N/A')}\n"
        md += f"**Nome de Solteira:** {mariana_cv.get('nome_fiscal', 'N/A')}\n"
        md += f"**Data de Nascimento:** {mariana_cv.get('data_nascimento', 'N/A')}\n"
        md += f"**CPF:** {mariana_cv.get('cpf', 'N/A')}\n"
        md += f"**Profissão/Cargo:** {mariana_cv.get('profissao_cargo', 'N/A')}\n"

        if mariana_cv.get('experiencias'):
            md += "\n### Experiências Profissionais\n"
            for exp in mariana_cv['experiencias']:
                md += f"- {exp.get('descricao', 'N/A')}\n"

        if mariana_cv.get('formacao'):
            md += "\n### Formação Acadêmica\n"
            for form in mariana_cv['formacao']:
                md += f"- {form.get('descricao', 'N/A')}\n"

        md += "\n"

    if mariana_payslip:
        md += "## Contracheque - Mariana\n\n"
        md += f"**Período:** {mariana_payslip.get('periodo', 'N/A')}\n"
        md += f"**Empresa:** {mariana_payslip.get('empresa', 'N/A')}\n"
        md += f"**Cargo:** {mariana_payslip.get('cargo', 'N/A')}\n"

        if mariana_payslip.get('salario_bruto'):
            md += f"**Salário Bruto:** R$ {mariana_payslip['salario_bruto']:,.2f}\n"
        if mariana_payslip.get('salario_liquido'):
            md += f"**Salário Líquido:** R$ {mariana_payslip['salario_liquido']:,.2f}\n"
        if mariana_payslip.get('inss_base'):
            md += f"**Base INSS:** R$ {mariana_payslip['inss_base']:,.2f}\n"
        if mariana_payslip.get('fgts'):
            md += f"**FGTS:** R$ {mariana_payslip['fgts']:,.2f}\n"

    return md

if __name__ == "__main__":
    main()
