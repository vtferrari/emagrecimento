#!/usr/bin/env python3
"""
Extract cutting report from MyFitnessPal ZIP and Withings PDF.

Generates a JSON report with agent prompt/context (for ChatGPT) and full report data.
Structure: { "agent": { "prompt", "context" }, "report": {...} }

Usage:
    python scripts/extract_cutting_report.py <zip_file> <pdf_file> [options]

Examples:
    python scripts/extract_cutting_report.py export.zip report.pdf
    python scripts/extract_cutting_report.py export.zip report.pdf -o meu_relatorio.json
    python scripts/extract_cutting_report.py export.zip report.pdf --name Sibele --target-date 2026-06-04
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root and src to path
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(_project_root / "src"))

from app import _extract_user_info_from_files
from emagrecimento.application.chatgpt_export import wrap_report_for_chatgpt
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
  %(prog)s export.zip report.pdf --name Sibele --target-date 2026-06-04
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
    parser.add_argument(
        "--name",
        "-n",
        metavar="NAME",
        help="Nome do usuário (para context e filename)",
    )
    parser.add_argument(
        "--target-date",
        "-t",
        metavar="YYYY-MM-DD",
        default="2026-06-01",
        help="Data alvo para projeção (padrão: 2026-06-01)",
    )
    args = parser.parse_args()

    extract_zip = create_extract_zip_use_case()
    extract_pdf = create_extract_pdf_use_case()
    build_report = create_build_report_use_case()

    zip_data = extract_zip.execute(args.zip_file)
    pdf_metrics = extract_pdf.execute(args.pdf_file)
    extracted = _extract_user_info_from_files(zip_data, pdf_metrics)
    user_info = dict(extracted)
    if args.name:
        user_info["name"] = args.name

    summary = build_report.execute(
        zip_data,
        pdf_metrics,
        target_date=args.target_date,
        user_info=user_info,
    )
    summary["user"] = user_info
    summary["target_date"] = args.target_date

    output_data = wrap_report_for_chatgpt(summary)
    output_path = Path(args.output)
    output_path.write_text(
        json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Relatório salvo em: {output_path.resolve()}")
    print()
    print("Resumo rápido:")
    report = output_data["report"]
    print(f"  Peso atual: {report['weight']['latest_weight_kg']} kg")
    print(f"  MA5: {report['weight']['latest_ma5_kg']} kg | MA7: {report['weight']['latest_ma7_kg']} kg")
    print(f"  Calorias: {report['nutrition']['avg_calories']} kcal/dia")
    print(f"  Proteína: {report['nutrition']['avg_protein_g']} g/dia")
    print(f"  Fibra: {report['nutrition']['avg_fiber_g']} g/dia | Sódio: {report['nutrition']['avg_sodium_mg']} mg/dia")
    if report["pdf_report"].get("latest_weight_kg"):
        print(f"  Withings peso: {report['pdf_report']['latest_weight_kg']} kg")
    if report["pdf_report"].get("daily_steps_avg"):
        print(f"  Withings passos: {report['pdf_report']['daily_steps_avg']}/dia")


if __name__ == "__main__":
    main()
