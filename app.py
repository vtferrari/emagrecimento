#!/usr/bin/env python3
"""
Cutting Report Dashboard - Web application for weight loss metrics.
"""

import io
import math
import sys
from pathlib import Path

# Add src to path for development (without pip install -e)
sys.path.insert(0, str(Path(__file__).parent / "src"))

from flask import Flask, jsonify, render_template, request

from emagrecimento.container import (
    create_build_report_use_case,
    create_extract_pdf_use_case,
    create_extract_zip_use_case,
)
from emagrecimento.domain.export_filename import build_export_filename

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB


def _extract_user_info_from_files(zip_data, pdf_metrics):
    """
    Extract user info (weight, height, age, sex) from ZIP and PDF data.
    Used to auto-fill form when user does not provide these values.
    - Peso: from measures (last row) or PDF latest_weight_kg
    - Altura: derived from PDF BMI + weight (height_cm = 100 * sqrt(weight/bmi))
    - Idade: from PDF "30yo" pattern
    - Sexo: from PDF "Biological Sex: Female/Male"
    """
    result = {}
    weight_kg = None
    if pdf_metrics and pdf_metrics.get("latest_weight_kg") is not None:
        weight_kg = float(pdf_metrics["latest_weight_kg"])
    if weight_kg is None and zip_data and not zip_data.measures.empty:
        last = zip_data.measures.iloc[-1]
        w = last.get("weight")
        if w is not None and not math.isnan(w):
            weight_kg = float(w)
    if weight_kg is not None:
        result["weight_kg"] = round(weight_kg, 1)

    # Derive height from BMI when we have both weight and bmi
    bmi = pdf_metrics.get("bmi_avg") if pdf_metrics else None
    if bmi is not None and weight_kg is not None and float(bmi) > 0:
        try:
            height_cm = 100 * math.sqrt(float(weight_kg) / float(bmi))
            if 100 <= height_cm <= 250:
                result["height_cm"] = int(round(height_cm))
        except (ValueError, TypeError):
            pass

    if pdf_metrics:
        if pdf_metrics.get("age_years") is not None:
            result["age"] = int(pdf_metrics["age_years"])
        if pdf_metrics.get("biological_sex") is not None:
            result["sex"] = pdf_metrics["biological_sex"]

    return result


def _sanitize_for_json(obj):
    """Replace NaN/Inf with None so JSON is valid."""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    return obj


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
        zip_data = extract_zip.execute(io.BytesIO(zip_file.read()))
        pdf_metrics = extract_pdf.execute(io.BytesIO(pdf_file.read()))
        extracted = _extract_user_info_from_files(zip_data, pdf_metrics)
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
        extracted = _extract_user_info_from_files(zip_data, pdf_metrics)
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
        summary = _sanitize_for_json(summary)

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

        return jsonify(summary)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Erro ao processar: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
