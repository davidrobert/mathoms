#!/usr/bin/env python3
"""
Bank Statement Extraction - Hybrid Version
Combines table-based and text-based extraction
"""

import pdfplumber
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

FILE_MAPPINGS = {
    'bankofamerica_extratoconta_202602_202603-0_original.pdf':
        'bankofamerica_extratoconta_202602_202603-2_extract.json',
    'bradesco_extratoconta_202501_202512-0_original.pdf':
        'bradesco_extratoconta_202501_202512-2_extract.json',
    'bradesco_extratoconta_202601_202603-0_original.pdf':
        'bradesco_extratoconta_202601_202603-2_extract.json',
    'btgpactual_extratoconta_202602_202603-0_original.pdf':
        'btgpactual_extratoconta_202602_202603-2_extract.json',
    'c6bank_extratoconta_202504_202604-0_original.pdf':
        'c6bank_extratoconta_202504_202604-2_extract.json',
    'c6bank_extratoconta_202603-0_original.pdf':
        'c6bank_extratoconta_202603-2_extract.json',
    'c6bank_extratocontapj_202503_202603-0_original.pdf':
        'c6bank_extratocontapj_202503_202603-2_extract.json',
    'c6bank_extratocontapj_202504_202604-0_original.pdf':
        'c6bank_extratocontapj_202504_202604-2_extract.json',
    'itau_extratoconta_202507-0_original.pdf':
        'itau_extratoconta_202507-2_extract.json',
    'itau_extratoconta_202601-0_original.pdf':
        'itau_extratoconta_202601-2_extract.json',
    'itau_extratocontapersonnalite_202505_202603-0_original.pdf':
        'itau_extratocontapersonnalite_202505_202603-2_extract.json',
    'picpay_extratoconta_202512_202603-0_original.pdf':
        'picpay_extratoconta_202512_202603-2_extract.json',
    'rico_extratoconta_202510_202603-0_original.pdf':
        'rico_extratoconta_202510_202603-2_extract.json',
    'santander_extratoconta_202511_202512-0_original.pdf':
        'santander_extratoconta_202511_202512-2_extract.json',
    'santander_extratoconta_202601_202603-0_original.pdf':
        'santander_extratoconta_202601_202603-2_extract.json',
    'wise_extratocontabrl_202501_202603-0_original.pdf':
        'wise_extratocontabrl_202501_202603-2_extract.json',
    'wise_extratocontausd_202501_202603-0_original.pdf':
        'wise_extratocontausd_202501_202603-2_extract.json',
}

class BankStatementExtractor:
    def __init__(self, input_dir: Path, output_dir: Path):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def normalize_currency(self, value_str: str) -> Optional[float]:
        if not value_str:
            return None
        value_str = str(value_str).strip()
        if not value_str:
            return None
        value_str = re.sub(r'[R$\s]', '', value_str)
        dot_count = value_str.count('.')
        comma_count = value_str.count(',')
        try:
            if dot_count > 0 and comma_count > 0:
                if value_str.rindex('.') > value_str.rindex(','):
                    value_str = value_str.replace(',', '')
                else:
                    value_str = value_str.replace('.', '').replace(',', '.')
            elif comma_count > 0:
                value_str = value_str.replace(',', '.')
            return float(value_str)
        except (ValueError, AttributeError):
            return None

    def parse_date(self, date_str: str) -> Optional[str]:
        if not date_str:
            return None
        date_str = str(date_str).strip()
        formats = ['%d/%m/%Y', '%d/%m/%y', '%d.%m.%Y', '%d.%m.%y', '%d-%m-%Y', '%Y-%m-%d']
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        return None

    def extract_from_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        logger.info(f"Processing: {pdf_path.name}")
        result = {
            'banco': self._extract_bank_name(pdf_path.name),
            'tipo': 'extratoconta',
            'moeda': 'BRL',
            'numero_conta': None,
            'periodo': {'inicio': None, 'fim': None},
            'saldo_inicial': None,
            'saldo_final': None,
            'transacoes': [],
            'notas': []
        }
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ''
                tables = []
                for page_num, page in enumerate(pdf.pages):
                    full_text += page.extract_text() or ''
                    page_tables = page.extract_tables()
                    if page_tables:
                        for table in page_tables:
                            tables.append((page_num, table))
                self._extract_period(full_text, result)
                self._extract_balances(full_text, result)
                self._extract_account_number(full_text, result)

                # Try tables first, then text
                if tables:
                    self._extract_from_tables(tables, result)
                    # If no transactions found, try text
                    if not result['transacoes']:
                        self._extract_from_text(full_text, result)
                else:
                    self._extract_from_text(full_text, result)
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            result['notas'].append(f"Error: {str(e)}")
        return result

    def _extract_bank_name(self, filename: str) -> str:
        parts = filename.split('_')
        return parts[0] if parts else 'unknown'

    def _extract_period(self, text: str, result: Dict):
        patterns = [
            r'Período de (\d{1,2}/\d{1,2}/\d{4}) a (\d{1,2}/\d{1,2}/\d{4})',
            r'entre (\d{2}/\d{2}/\d{4}) e (\d{2}/\d{2}/\d{4})',
            r'período de visualização: (\d{2}/\d{2}/\d{4}) até (\d{2}/\d{2}/\d{4})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                inicio = self.parse_date(match.group(1))
                fim = self.parse_date(match.group(2))
                if inicio:
                    result['periodo']['inicio'] = inicio
                if fim:
                    result['periodo']['fim'] = fim
                break

    def _extract_balances(self, text: str, result: Dict):
        patterns = [
            (r'[Ss]aldo\s+[Ii]nicial[:\s]+[R$]*\s*([-\d.,]+)', 'inicial'),
            (r'[Ss]aldo\s+[Aa]nterior[:\s]+[R$]*\s*([-\d.,]+)', 'inicial'),
            (r'[Ss]aldo\s+[Ff]inal[:\s]+[R$]*\s*([-\d.,]+)', 'final'),
            (r'[Ss]aldo\s+[Aa]tual[:\s]+[R$]*\s*([-\d.,]+)', 'final'),
        ]
        for pattern, saldo_type in patterns:
            match = re.search(pattern, text)
            if match:
                val = self.normalize_currency(match.group(1))
                if val is not None:
                    if saldo_type == 'inicial':
                        result['saldo_inicial'] = val
                    elif saldo_type == 'final':
                        result['saldo_final'] = val

    def _extract_account_number(self, text: str, result: Dict):
        patterns = [r'[Cc]onta[:\s]*(\d{6,15})', r'conta:\s*(\d+)']
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                result['numero_conta'] = match.group(1)
                break

    def _extract_from_tables(self, tables: List[Tuple], result: Dict):
        transactions = []
        for page_num, table in tables:
            if not table or len(table) < 2:
                continue
            header = table[0]
            data_col, descricao_col = 0, 1
            valor_col, debito_col, credito_col, saldo_col = None, None, None, None

            for i, h in enumerate(header):
                h_lower = str(h or '').lower()
                if 'descr' in h_lower or 'histórico' in h_lower:
                    descricao_col = i
                elif 'deb' in h_lower:
                    debito_col = i
                elif 'cred' in h_lower:
                    credito_col = i
                elif 'saldo' in h_lower:
                    saldo_col = i
                elif 'valor' in h_lower and valor_col is None:
                    valor_col = i

            for row in table[1:]:
                if not row or not any(row):
                    continue
                try:
                    data_str = str(row[data_col] or '').strip() if data_col < len(row) else ''
                    data = self.parse_date(data_str)
                    if not data:
                        continue
                    descricao = str(row[descricao_col] or '').strip() if descricao_col < len(row) else ''

                    valor = None
                    if valor_col is not None and valor_col < len(row):
                        valor = self.normalize_currency(str(row[valor_col] or ''))
                    if valor is None and credito_col is not None and credito_col < len(row):
                        cred = self.normalize_currency(str(row[credito_col] or ''))
                        if cred and cred != 0:
                            valor = cred
                    if valor is None and debito_col is not None and debito_col < len(row):
                        deb = self.normalize_currency(str(row[debito_col] or ''))
                        if deb and deb != 0:
                            valor = -deb

                    if valor is None:
                        continue

                    saldo_apos = None
                    if saldo_col is not None and saldo_col < len(row):
                        saldo_apos = self.normalize_currency(str(row[saldo_col] or ''))

                    transactions.append({
                        'data': data,
                        'descricao': descricao,
                        'valor': valor,
                        'saldo_apos': saldo_apos
                    })
                except Exception as e:
                    logger.debug(f"Row error: {e}")
                    continue

        result['transacoes'] = transactions

    def _extract_from_text(self, text: str, result: Dict):
        transactions = []
        lines = text.split('\n')
        for line in lines:
            match = re.match(r'(\d{1,2}/\d{1,2}/\d{4})\s+(.+?)\s+([-\d.,]+)\s*$', line)
            if match:
                data = self.parse_date(match.group(1))
                descricao = match.group(2).strip()
                valor = self.normalize_currency(match.group(3))
                if data and descricao and valor is not None:
                    transactions.append({
                        'data': data,
                        'descricao': descricao,
                        'valor': valor,
                        'saldo_apos': None
                    })
        result['transacoes'] = transactions

    def process_all_files(self):
        results = {}
        for input_file, output_file in FILE_MAPPINGS.items():
            input_path = self.input_dir / input_file
            output_path = self.output_dir / output_file
            if not input_path.exists():
                logger.warning(f"Not found: {input_path}")
                continue
            try:
                data = self.extract_from_pdf(input_path)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                logger.info(f"Saved: {output_file}")
                results[output_file] = {
                    'status': 'success',
                    'transacoes': len(data.get('transacoes', []))
                }
            except Exception as e:
                logger.error(f"Failed: {input_file}: {str(e)}")
                results[input_file] = {'status': 'error', 'error': str(e)}
        return results


def main():
    base_dir = Path('/sessions/magical-elegant-mendel/mnt/Financas Familia/financas-familia')
    extractor = BankStatementExtractor(base_dir / 'data' / 'financial_statements',
                                      base_dir / 'processed' / 'E2_extracts')
    results = extractor.process_all_files()
    logger.info("\n=== SUMMARY ===")
    total = 0
    for file, info in results.items():
        if info['status'] == 'success':
            logger.info(f"✓ {file}: {info['transacoes']} transactions")
            total += info['transacoes']
    logger.info(f"Total: {total} transactions")

if __name__ == '__main__':
    main()
