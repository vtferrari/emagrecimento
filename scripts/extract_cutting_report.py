#!/usr/bin/env python3
"""
Extract cutting report from MyFitnessPal ZIP and Withings PDF.

Generates a JSON report with weight metrics (MA5, MA7), nutrition summary,
exercise stats, and Withings PDF metrics (body composition, sleep, steps).

Usage:
    python scripts/extract_cutting_report.py <zip_file> <pdf_file> [options]

Examples:
    python scripts/extract_cutting_report.py export.zip report.pdf
    python scripts/extract_cutting_report.py export.zip report.pdf --output meu_relatorio.json
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root src to path
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root / "src"))

from emagrecimento.container import (
    create_build_report_use_case,
    create_extract_pdf_use_case,
    create_extract_zip_use_case,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extrai métricas de cutting a partir do ZIP do MyFitnessPal e do PDF da Withings.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  %(prog)s export.zip report.pdf
  %(prog)s export.zip report.pdf --output relatorio.json
        """,
    )
    parser.add_argument(
        "zip_file",
        help="Caminho para o ZIP exportado do MyFitnessPal (com CSVs de medidas, alimentação e exercícios)",
    )
    parser.add_argument(
        "pdf_file",
        help="Caminho para o PDF do relatório médico da Withings",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="cutting_report.json",
        metavar="FILE",
        help="Arquivo JSON de saída (padrão: cutting_report.json)",
    )
    args = parser.parse_args()

    extract_zip = create_extract_zip_use_case()
    extract_pdf = create_extract_pdf_use_case()
    build_report = create_build_report_use_case()

    zip_data = extract_zip.execute(args.zip_file)
    pdf_metrics = extract_pdf.execute(args.pdf_file)
    summary = build_report.execute(zip_data, pdf_metrics)

    output_path = Path(args.output)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Relatório salvo em: {output_path.resolve()}")
    print()
    print("Resumo rápido:")
    print(f"  Peso atual: {summary['weight']['latest_weight_kg']} kg")
    print(f"  MA5: {summary['weight']['latest_ma5_kg']} kg | MA7: {summary['weight']['latest_ma7_kg']} kg")
    print(f"  Calorias: {summary['nutrition']['avg_calories']} kcal/dia")
    print(f"  Proteína: {summary['nutrition']['avg_protein_g']} g/dia")
    print(f"  Fibra: {summary['nutrition']['avg_fiber_g']} g/dia | Sódio: {summary['nutrition']['avg_sodium_mg']} mg/dia")
    if summary["pdf_report"].get("latest_weight_kg"):
        print(f"  Withings peso: {summary['pdf_report']['latest_weight_kg']} kg")
    if summary["pdf_report"].get("daily_steps_avg"):
        print(f"  Withings passos: {summary['pdf_report']['daily_steps_avg']}/dia")


if __name__ == "__main__":
    main()
