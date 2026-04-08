#!/usr/bin/env python3
"""
Extract data from screenshot images for Stage E2
"""

import json
from pathlib import Path

# Working directories
BASE_DIR = Path("/sessions/magical-elegant-mendel/mnt/Financas Familia/financas-familia")
OUTPUT_DIR = BASE_DIR / "processed" / "E2_extracts"


def create_binance_extracts():
    """Create JSON extracts for Binance account screenshots"""

    # Binance 202603a - Initial view showing portfolio value
    binance_202603a = {
        "banco": "Binance",
        "tipo": "extratoconta",
        "moeda": "BRL",
        "data": "2025-03-29",
        "saldo_total_estimado": 1257.19,
        "pnl_24h": "+197.60",
        "pnl_24h_percentual": "+0.61%",
        "posicoes": [
            {
                "criptomoeda": "BTC",
                "ticker": "Bitcoin",
                "quantidade": 0.00311425,
                "valor_unitario": None,
                "valor_total": None,
                "pnl": "+181.09",
                "pnl_percentual": "+0.61%",
                "status": "TRADE"
            },
            {
                "criptomoeda": "ETH",
                "ticker": "Ethereum",
                "quantidade": 0.01325066,
                "valor_unitario": None,
                "valor_total": None,
                "pnl": "+82.10",
                "pnl_percentual": "+0.65%",
                "status": "TRADE"
            },
            {
                "criptomoeda": "ADA",
                "ticker": "Cardano",
                "quantidade": 7.78980311,
                "valor_unitario": None,
                "valor_total": None,
                "pnl": "-1052.02",
                "pnl_percentual": "-0.93%",
                "status": "TRADE"
            },
            {
                "criptomoeda": "AXS",
                "ticker": "Axis Infinity",
                "quantidade": 1.54143134,
                "valor_unitario": None,
                "valor_total": None,
                "pnl": "-1052.02",
                "pnl_percentual": "-0.93%",
                "status": "TRADE"
            }
        ],
        "nota": "Primeira tela da conta Binance de 29/03/2025"
    }

    # Binance 202603b - Continued view with more assets
    binance_202603b = {
        "banco": "Binance",
        "tipo": "extratoconta",
        "moeda": "BRL",
        "data": "2025-03-29",
        "saldo_total_estimado": 1257.45,
        "pnl_24h": "+197.60",
        "pnl_24h_percentual": "+0.57%",
        "posicoes": [
            {
                "criptomoeda": "BTC",
                "ticker": "Bitcoin",
                "quantidade": 0.00311425,
                "valor_total": None,
                "pnl": "+181.09",
                "pnl_percentual": "+0.61%",
                "status": "TRADE"
            },
            {
                "criptomoeda": "ETH",
                "ticker": "Ethereum",
                "quantidade": 0.01325066,
                "valor_total": None,
                "pnl": "+82.10",
                "pnl_percentual": "+0.65%",
                "status": "TRADE"
            },
            {
                "criptomoeda": "ADA",
                "ticker": "Cardano",
                "quantidade": 7.78980311,
                "valor_total": None,
                "pnl": "-1052.02",
                "pnl_percentual": "-0.93%",
                "status": "TRADE"
            },
            {
                "criptomoeda": "AXS",
                "ticker": "Axis Infinity",
                "quantidade": 1.54143134,
                "valor_total": None,
                "pnl": "-1052.02",
                "pnl_percentual": "-0.93%",
                "status": "TRADE"
            },
            {
                "criptomoeda": "SUSHI",
                "ticker": None,
                "quantidade": 2.59616491,
                "valor_total": None,
                "pnl": "+900.06",
                "pnl_percentual": "-0.37%",
                "status": "TRADE"
            },
            {
                "criptomoeda": "ALICE",
                "ticker": "My Neighbor Alice",
                "quantidade": 1.36104419,
                "valor_total": None,
                "pnl": "+812.62",
                "pnl_percentual": "-0.19%",
                "status": "TRADE"
            }
        ],
        "nota": "Segunda tela da conta Binance de 29/03/2025"
    }

    # Binance 202603c - Continued view with additional assets
    binance_202603c = {
        "banco": "Binance",
        "tipo": "extratoconta",
        "moeda": "BRL",
        "data": "2025-03-29",
        "posicoes": [
            {
                "criptomoeda": "ETH",
                "ticker": "Ethereum",
                "quantidade": 0.01325066,
                "pnl": "+82.10",
                "pnl_percentual": "+0.61%",
                "status": "TRADE"
            },
            {
                "criptomoeda": "ADA",
                "ticker": "Cardano",
                "quantidade": 7.78980311,
                "pnl": "-1052.02",
                "pnl_percentual": "-0.93%",
                "status": "TRADE"
            },
            {
                "criptomoeda": "AXS",
                "ticker": "Axis Infinity",
                "quantidade": 1.54143134,
                "pnl": "-1052.02",
                "pnl_percentual": "-0.93%",
                "status": "TRADE"
            },
            {
                "criptomoeda": "SUSHI",
                "ticker": None,
                "quantidade": 2.59616491,
                "pnl": "+900.06",
                "pnl_percentual": "-0.37%",
                "status": "TRADE"
            },
            {
                "criptomoeda": "ALICE",
                "ticker": "My Neighbor Alice",
                "quantidade": 1.36104419,
                "pnl": "+812.62",
                "pnl_percentual": "-0.19%",
                "status": "TRADE"
            },
            {
                "criptomoeda": "USDT",
                "ticker": "Tether US",
                "quantidade": 0.00752095,
                "pnl": None,
                "pnl_percentual": None,
                "status": "TRADE"
            },
            {
                "criptomoeda": "ETHW",
                "ticker": "Ethereum PoW",
                "quantidade": 0.01325066,
                "pnl": None,
                "pnl_percentual": None,
                "status": "TRADE"
            }
        ],
        "nota": "Terceira tela da conta Binance de 29/03/2025"
    }

    # Write Binance files
    with open(OUTPUT_DIR / "binance_extratoconta_202603a-2_extract.json", "w", encoding="utf-8") as f:
        json.dump(binance_202603a, f, indent=2, ensure_ascii=False)
    print("✓ binance_extratoconta_202603a-2_extract.json")

    with open(OUTPUT_DIR / "binance_extratoconta_202603b-2_extract.json", "w", encoding="utf-8") as f:
        json.dump(binance_202603b, f, indent=2, ensure_ascii=False)
    print("✓ binance_extratoconta_202603b-2_extract.json")

    with open(OUTPUT_DIR / "binance_extratoconta_202603c-2_extract.json", "w", encoding="utf-8") as f:
        json.dump(binance_202603c, f, indent=2, ensure_ascii=False)
    print("✓ binance_extratoconta_202603c-2_extract.json")


def create_itau_personnalite_extracts():
    """Create JSON extracts for Itaú Personnalité account screenshots"""

    # Itaú 202603a - Reserva/Reserve account overview
    itau_202603a = {
        "banco": "Itaú",
        "tipo": "extratocontapersonnalite",
        "moeda": "BRL",
        "data": "2025-03-29",
        "conta_tipo": "Reserva (Reserve)",
        "descricao": "Seu dinheiro guardado rende todo dia útil",
        "saldo_guardado": 206491.70,
        "rendimento_bruto": 20614.62,
        "acoes": {
            "guardar_dinheiro": "Disponível",
            "resgatar_dinheiro": "Disponível",
            "receber_via_pix": "Disponível",
            "editar_cofinho": "Disponível",
            "entenda_sobre_cdbs": "Disponível",
            "faeir_cofinho": "Disponível"
        },
        "historico": {
            "abas": ["Tudo", "Depósitos", "Resgates"],
            "registros": [
                {
                    "tipo": "Depósito",
                    "valor": 150000.00,
                    "data": "03/07/2025"
                }
            ]
        },
        "nota": "Primeira tela de conta poupança Itaú Personnalité de 29/03/2025"
    }

    # Itaú 202603b - Rendimento details
    itau_202603b = {
        "banco": "Itaú",
        "tipo": "extratocontapersonnalite",
        "moeda": "BRL",
        "data": "2025-03-29",
        "rendimento": {
            "saldo": 20614.62,
            "atualizado_todos_os_dias": "Atualizado todos os dias",
            "rendimento_100_do_cdi": "Rendimento 100% do CDI",
            "detalhamento": {
                "rendimento_bruto": 20614.62,
                "iof": 0.00,
                "imposto_de_renda": 4122.02,
                "rendimento_liquido": 16491.70
            }
        },
        "saldo_guardado_total": 206491.70,
        "nota": "Segunda tela com detalhes de rendimento da conta Itaú Personnalité"
    }

    # Write Itaú files
    with open(OUTPUT_DIR / "itau_extratocontapersonnalite_202603a-2_extract.json", "w", encoding="utf-8") as f:
        json.dump(itau_202603a, f, indent=2, ensure_ascii=False)
    print("✓ itau_extratocontapersonnalite_202603a-2_extract.json")

    with open(OUTPUT_DIR / "itau_extratocontapersonnalite_202603b-2_extract.json", "w", encoding="utf-8") as f:
        json.dump(itau_202603b, f, indent=2, ensure_ascii=False)
    print("✓ itau_extratocontapersonnalite_202603b-2_extract.json")


if __name__ == "__main__":
    print("=" * 60)
    print("Stage E2 Extraction - Screenshot Images")
    print("=" * 60)
    print("\nProcessing image-based extracts...\n")

    create_binance_extracts()
    print()
    create_itau_personnalite_extracts()

    print("\n" + "=" * 60)
    print("Image extraction complete!")
    print("=" * 60)
