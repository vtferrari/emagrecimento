#!/usr/bin/env python3
"""
Cutting Report Dashboard - Web application for weight loss metrics.
"""

import io
import os
import sys
from pathlib import Path

# Add src to path for development (without pip install -e)
sys.path.insert(0, str(Path(__file__).parent / "src"))

from flask import Flask, jsonify, render_template, request

from emagrecimento.application.presenters.chatgpt_export import wrap_report_for_chatgpt
from emagrecimento.application.serialization import sanitize_for_json
from emagrecimento.container import (
    create_build_report_use_case,
    create_extract_pdf_use_case,
    create_extract_user_info_use_case,
    create_extract_zip_use_case,
)
from emagrecimento.domain.export_filename import build_export_filename

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/extract-preview", methods=["POST"])
def extract_preview():
    """
    Extract user info (weight, height, age, sex) from ZIP and PDF.
    Returns extracted values for form pre-fill - user does not need to type them.
    """
    zip_file = request.files.get("zip_file")
    pdf_file = request.files.get("pdf_file")
    if not zip_file or not zip_file.filename or not zip_file.filename.lower().endswith(".zip"):
        return jsonify({"error": "Arquivo ZIP é obrigatório"}), 400
    if not pdf_file or not pdf_file.filename or not pdf_file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Arquivo PDF é obrigatório"}), 400

    try:
        extract_zip = create_extract_zip_use_case()
        extract_pdf = create_extract_pdf_use_case()
        extract_user_info = create_extract_user_info_use_case()
        zip_data = extract_zip.execute(io.BytesIO(zip_file.read()))
        pdf_metrics = extract_pdf.execute(io.BytesIO(pdf_file.read()))
        extracted = extract_user_info.execute(zip_data, pdf_metrics)
        return jsonify({"extracted": extracted})
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Erro ao extrair: {str(e)}"}), 500


@app.route("/api/process", methods=["POST"])
def process_files():
    zip_file = request.files.get("zip_file")
    pdf_file = request.files.get("pdf_file")
    target_date = request.form.get("target_date", "").strip()
    name = request.form.get("name", "").strip() or None
    sex = request.form.get("sex", "").strip() or None
    height_cm = request.form.get("height_cm", type=int)
    age = request.form.get("age", type=int)
    weight_kg = request.form.get("weight_kg", type=float)
    calorie_min = request.form.get("calorie_min", type=int)
    calorie_max = request.form.get("calorie_max", type=int)
    protein_g = request.form.get("protein_g", type=int)
    fat_g = request.form.get("fat_g", type=int)
    carbs_g = request.form.get("carbs_g", type=int)
    fiber_g = request.form.get("fiber_g", type=int)

    if not zip_file or not zip_file.filename:
        return jsonify({"error": "Arquivo ZIP é obrigatório"}), 400
    if not pdf_file or not pdf_file.filename:
        return jsonify({"error": "Arquivo PDF é obrigatório"}), 400

    if not zip_file.filename.lower().endswith(".zip"):
        return jsonify({"error": "O primeiro arquivo deve ser um ZIP"}), 400
    if not pdf_file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "O segundo arquivo deve ser um PDF"}), 400

    if not target_date:
        return jsonify({"error": "Data alvo é obrigatória"}), 400

    try:
        extract_zip = create_extract_zip_use_case()
        extract_pdf = create_extract_pdf_use_case()
        build_report = create_build_report_use_case()

        zip_data = extract_zip.execute(io.BytesIO(zip_file.read()))
        pdf_metrics = extract_pdf.execute(io.BytesIO(pdf_file.read()))

        # Use extracted values from files when form fields are empty
        extract_user_info = create_extract_user_info_use_case()
        extracted = extract_user_info.execute(zip_data, pdf_metrics)
        user_info = {
            "name": name,
            "sex": sex or extracted.get("sex"),
            "height_cm": height_cm if height_cm is not None else extracted.get("height_cm"),
            "age": age if age is not None else extracted.get("age"),
            "weight_kg": weight_kg if weight_kg is not None else extracted.get("weight_kg"),
        }
        if calorie_min is not None:
            user_info["calorie_min"] = calorie_min
        if calorie_max is not None:
            user_info["calorie_max"] = calorie_max
        if protein_g is not None:
            user_info["protein_g"] = protein_g
        if fat_g is not None:
            user_info["fat_g"] = fat_g
        if carbs_g is not None:
            user_info["carbs_g"] = carbs_g
        if fiber_g is not None:
            user_info["fiber_g"] = fiber_g
        summary = build_report.execute(
            zip_data,
            pdf_metrics,
            target_date=target_date,
            user_info=user_info,
        )
        summary = sanitize_for_json(summary)

        # Add user info and target_date to response for JSON export (use final values including extracted)
        summary["user"] = {
            "name": name,
            "sex": user_info.get("sex"),
            "height_cm": user_info.get("height_cm"),
            "age": user_info.get("age"),
            "weight_kg": user_info.get("weight_kg"),
        }
        summary["target_date"] = target_date
        summary["suggested_export_filename"] = build_export_filename(name)

        output = wrap_report_for_chatgpt(summary)
        return jsonify(output)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Erro ao processar: {str(e)}"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(debug=True, port=port)
