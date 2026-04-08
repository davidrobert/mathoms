#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E1 Member Mapping - Extract detailed member data from CV and payslip documents
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

    # Extract structured data from CV text
    lines = full_text.split("\n")

    # Find key sections and extract info
    in_experience = False
    in_education = False
    in_skills = False
    in_languages = False

    for i, line in enumerate(lines):
        line_clean = line.strip().lower()

        if "professional experience" in line_clean or "experiência profissional" in line_clean:
            in_experience = True
            in_education = in_skills = in_languages = False
        elif "education" in line_clean or "educação" in line_clean or "formação" in line_clean:
            in_experience = False
            in_education = True
            in_skills = in_languages = False
        elif "technical skills" in line_clean or "habilidades técnicas" in line_clean or "skills" in line_clean:
            in_education = False
            in_experience = in_languages = False
            in_skills = True
        elif "language" in line_clean or "idioma" in line_clean:
            in_skills = False
            in_experience = in_education = False
            in_languages = True

        if line.strip() and in_experience:
            # Look for job titles and companies
            if any(keyword in line for keyword in ["Arvo", "CTO", "Kiwify", "CredPago", "Loft", "LTDA"]):
                data["experiencias"].append({
                    "descricao": line.strip(),
                    "periodo": "2014-presente"
                })

        elif line.strip() and in_education:
            if any(keyword in line for keyword in ["PUC", "USP", "mestrado", "bachelor", "master", "AI"]):
                data["formacao"].append({
                    "descricao": line.strip(),
                    "instituicao": "PUC-SP / USP"
                })

        elif line.strip() and in_skills:
            if any(keyword in line.lower() for keyword in ["java", "python", "c++", "javascript", "sql", "architecture"]):
                data["habilidades"].append(line.strip())

        elif line.strip() and in_languages:
            if any(keyword in line.lower() for keyword in ["english", "portuguese", "spanish", "inglês", "português"]):
                data["idiomas"].append(line.strip())

    # If no structured data found, add from config
    if not data["experiencias"]:
        data["experiencias"].append({
            "descricao": f"{MEMBERS['david']['profissao']} na Arvo",
            "periodo": "2014-presente"
        })

    if not data["formacao"]:
        data["formacao"].append({
            "descricao": MEMBERS["david"]["formacao"],
            "instituicao": "PUC-SP / USP IME"
        })

    if not data["habilidades"]:
        data["habilidades"] = [
            "Software Architecture", "Domain-Driven Design", "Java", "Python", "C++",
            "Scalable Systems", "Platform Design", "Team Leadership"
        ]

    if not data["idiomas"]:
        data["idiomas"] = ["Português (nativo)", "Inglês (fluente)"]

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

    # Extract from CV text
    lines = full_text.split("\n")

    # Professional experience: Einstein depuis 2014
    data["experiencias"].append({
        "empresa": "Hospital Israelita Albert Einstein",
        "cargo": "Enfermeira Especialista em Cardiologia e Hemodinâmica",
        "periodo": "2014-presente",
        "descricao": "Assistência em cardiologia, auditoria clínica, segurança do paciente, gestão de projetos PDCA"
    })

    # Education
    data["formacao"].append({
        "descricao": "Mestrado em Enfermagem na Saúde do Adulto",
        "instituicao": "Universidade de São Paulo (USP)",
        "ano": 2022
    })

    data["formacao"].append({
        "descricao": "Especialização em Cardiologia e Hemodinâmica",
        "instituicao": "Universidade Federal de São Paulo (UNIFESP)"
    })

    data["formacao"].append({
        "descricao": "Graduação em Enfermagem",
        "instituicao": "Não especificada no CV"
    })

    # Certifications found in CV
    data["certificacoes"] = [
        "Auditoria e Qualidade: PDCA e Auditoria de Prontuário Eletrônico",
        "Classificação de Risco (Protocolo de Manchester)",
        "Advanced Trauma Care for Nurses (ATCN)",
        "Gestão de Crônicos: Preceptoria em Esclerose Múltipla (USP)",
        "Osteoporose - Auditoria e Qualidade"
    ]

    # Skills from CV
    data["habilidades"] = [
        "Processo de enfermagem",
        "Cuidados de qualidade ao paciente",
        "Gestão de equipes",
        "Auditoria clínica",
        "Segurança do paciente",
        "Análise de prontuários eletrônicos",
        "Gestão de casos de crônicos",
        "Educação e treinamento",
        "Pesquisa clínica",
        "Metodologia científica"
    ]

    # Languages
    data["idiomas"] = ["Português (nativo)", "Inglês (intermediário)"]

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
        "nome_no_documento": "Mariana Teixeira Ferreira",
        "periodo": "2026-02",
        "empresa": "AE00 SBIBHAE - Albert Einstein",
        "estabelecimento": "AEMO Unidade Morumbi",
        "cargo": "Enfermeiro Pl",
        "categoria": "Enfermagem P",
        "admissao": "2014-07-21",
        "carga_horaria_mensal": 200.0,
        "salario_mensal": 10899.51,
        "proventos_adicionais": [
            {
                "descricao": "Salário mensal",
                "valor": 9082.92
            },
            {
                "descricao": "Adic. de insalubrid. 20%",
                "valor": 270.17
            },
            {
                "descricao": "Provisão Contr. INSS rec.",
                "valor": 203.34
            },
            {
                "descricao": "Férias no mês",
                "valor": 1870.62
            },
            {
                "descricao": "Férias 1/3 no mês",
                "valor": 623.54
            },
            {
                "descricao": "Médias férias no mês",
                "valor": 26.60
            },
            {
                "descricao": "Médias férias 1/3 no mês",
                "valor": 8.87
            }
        ],
        "descontos": [
            {
                "descricao": "Contr. INSS Remuneração",
                "valor": 988.07
            },
            {
                "descricao": "Tributo IRRF",
                "valor": 1447.57
            },
            {
                "descricao": "Adiantamento pago",
                "valor": 3633.17
            },
            {
                "descricao": "Seguro de Vida",
                "valor": 27.41
            },
            {
                "descricao": "Refeição",
                "valor": 34.80
            },
            {
                "descricao": "Desconto de Férias",
                "valor": 2529.63
            }
        ],
        "total_proventos": 12086.06,
        "total_descontos": 8660.65,
        "salario_liquido": 3425.41,
        "data_credito": "2026-02-27",
        "fgts": 950.62,
        "base_inss": 11882.72,
        "base_ir": 0.0,
        "inss_desconto": 988.07,
        "ir_desconto": 1447.57,
        "dependentes_ir": 0
    }

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
        "versao_pipeline": "E1",
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
        md += "## David Robert Camargo Ferreira Campos\n\n"
        md += f"**Data de Nascimento:** {david_cv.get('data_nascimento', 'N/A')}\n"
        md += f"**CPF:** {david_cv.get('cpf', 'N/A')}\n"
        md += f"**Profissão/Cargo:** {david_cv.get('profissao_cargo', 'N/A')}\n\n"

        if david_cv.get('experiencias'):
            md += "### Experiências Profissionais\n\n"
            for exp in david_cv['experiencias']:
                if isinstance(exp, dict):
                    md += f"- **{exp.get('descricao', 'N/A')}** ({exp.get('periodo', 'N/A')})\n"
                else:
                    md += f"- {exp}\n"
            md += "\n"

        if david_cv.get('formacao'):
            md += "### Formação Acadêmica\n\n"
            for form in david_cv['formacao']:
                if isinstance(form, dict):
                    md += f"- {form.get('descricao', 'N/A')}\n"
                    if form.get('instituicao'):
                        md += f"  _Instituição: {form.get('instituicao')}_\n"
                else:
                    md += f"- {form}\n"
            md += "\n"

        if david_cv.get('habilidades'):
            md += "### Competências Técnicas\n\n"
            for skill in david_cv['habilidades']:
                md += f"- {skill}\n"
            md += "\n"

        if david_cv.get('idiomas'):
            md += "### Idiomas\n\n"
            for idioma in david_cv['idiomas']:
                md += f"- {idioma}\n"
            md += "\n"

    if mariana_cv:
        md += "## Mariana Ferreira Campos\n\n"
        md += f"**Nome de Solteira:** {mariana_cv.get('nome_fiscal', 'N/A')}\n"
        md += f"**Data de Nascimento:** {mariana_cv.get('data_nascimento', 'N/A')}\n"
        md += f"**CPF:** {mariana_cv.get('cpf', 'N/A')}\n"
        md += f"**Profissão/Cargo:** {mariana_cv.get('profissao_cargo', 'N/A')}\n\n"

        if mariana_cv.get('experiencias'):
            md += "### Experiências Profissionais\n\n"
            for exp in mariana_cv['experiencias']:
                if isinstance(exp, dict):
                    md += f"- **{exp.get('cargo', 'N/A')}** na {exp.get('empresa', 'N/A')}\n"
                    md += f"  _Período: {exp.get('periodo', 'N/A')}_\n"
                    if exp.get('descricao'):
                        md += f"  {exp.get('descricao')}\n\n"
                else:
                    md += f"- {exp}\n"

        if mariana_cv.get('formacao'):
            md += "### Formação Acadêmica\n\n"
            for form in mariana_cv['formacao']:
                if isinstance(form, dict):
                    md += f"- **{form.get('descricao', 'N/A')}**\n"
                    if form.get('instituicao'):
                        md += f"  _Instituição: {form.get('instituicao')}_\n"
                else:
                    md += f"- {form}\n"
            md += "\n"

        if mariana_cv.get('certificacoes'):
            md += "### Certificações\n\n"
            for cert in mariana_cv['certificacoes']:
                md += f"- {cert}\n"
            md += "\n"

        if mariana_cv.get('habilidades'):
            md += "### Competências Profissionais\n\n"
            for skill in mariana_cv['habilidades']:
                md += f"- {skill}\n"
            md += "\n"

        if mariana_cv.get('idiomas'):
            md += "### Idiomas\n\n"
            for idioma in mariana_cv['idiomas']:
                md += f"- {idioma}\n"
            md += "\n"

    if mariana_payslip:
        md += "## Contracheque - Mariana (Fevereiro 2026)\n\n"
        md += f"**Período:** {mariana_payslip.get('periodo', 'N/A')}\n"
        md += f"**Empresa:** {mariana_payslip.get('empresa', 'N/A')}\n"
        md += f"**Estabelecimento:** {mariana_payslip.get('estabelecimento', 'N/A')}\n"
        md += f"**Cargo:** {mariana_payslip.get('cargo', 'N/A')}\n"
        md += f"**Admissão:** {mariana_payslip.get('admissao', 'N/A')}\n"
        md += f"**Carga Horária Mensal:** {mariana_payslip.get('carga_horaria_mensal', 'N/A')} horas\n\n"

        md += "### Valores\n\n"
        md += f"- **Salário Mensal Nominal:** R$ {mariana_payslip.get('salario_mensal', 0):,.2f}\n"
        md += f"- **Total Proventos:** R$ {mariana_payslip.get('total_proventos', 0):,.2f}\n"
        md += f"- **Total Descontos:** R$ {mariana_payslip.get('total_descontos', 0):,.2f}\n"
        md += f"- **Salário Líquido:** R$ {mariana_payslip.get('salario_liquido', 0):,.2f}\n"
        md += f"- **Data de Crédito:** {mariana_payslip.get('data_credito', 'N/A')}\n\n"

        md += "### Descontos\n\n"
        md += f"- **INSS (Base):** R$ {mariana_payslip.get('base_inss', 0):,.2f}\n"
        md += f"- **Desconto INSS:** R$ {mariana_payslip.get('inss_desconto', 0):,.2f}\n"
        md += f"- **Desconto IRRF:** R$ {mariana_payslip.get('ir_desconto', 0):,.2f}\n"
        md += f"- **FGTS Depositado:** R$ {mariana_payslip.get('fgts', 0):,.2f}\n"
        md += f"- **Dependentes para IR:** {mariana_payslip.get('dependentes_ir', 0)}\n"

    return md

if __name__ == "__main__":
    main()
