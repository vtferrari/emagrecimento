"""Integration tests for /api/process endpoint."""

import io
import zipfile

import pytest
from pypdf import PdfWriter

from app import app


def _create_minimal_withings_zip() -> bytes:
    """Create minimal valid Withings export ZIP."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        measures = (
            "Date,Time,Value,Unit,Recorded by,Measure type\n"
            "2026-01-20,08:00,95.4,kg,Scale,Weight\n"
            "2026-01-20,08:00,23.5,kg,Scale,Fat Mass Weight\n"
            "2026-01-20,08:00,68.4,kg,Scale,Muscle Mass\n"
            "2026-01-20,08:00,3.5,,Scale,Visceral Fat\n"
            "2026-01-20,08:00,38,years,Scale,Metabolic Age\n"
        )
        zf.writestr("Measures | [2026-01-01] - [2026-01-31].csv", measures)
        steps = "Date,Measure type,Value\n2026-01-20,Steps,15000\n"
        zf.writestr("Steps | [2026-01-01] - [2026-01-31].csv", steps)
    return buf.getvalue()


def _create_minimal_zip() -> bytes:
    """Create minimal valid ZIP with required CSVs."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        measures_csv = (
            "Data,Peso\n"
            "2026-02-01,85.0\n2026-02-02,84.8\n2026-02-03,84.5\n"
            "2026-02-04,84.3\n2026-02-05,84.0\n2026-02-06,83.8\n"
            "2026-02-07,83.5\n2026-02-08,83.3\n"
        )
        zf.writestr("medidas.csv", measures_csv)

        nutrition_csv = (
            "Data,Calorias,Proteínas (g),Carboidratos (g),Gorduras (g),Fibra,Sódio (mg)\n"
            "2026-02-01,1900,180,200,60,25,2000\n"
            "2026-02-02,1850,175,190,55,22,1900\n"
        )
        zf.writestr("alimentacao.csv", nutrition_csv)

        exercise_csv = (
            "Data,Calorias de exercícios,Minutos de exercício,Passos,Exercício\n"
            "2026-02-01,350,45,8000,Esteira\n"
            "2026-02-02,0,0,5000,\n"
        )
        zf.writestr("exercicios.csv", exercise_csv)

    buffer.seek(0)
    return buffer.getvalue()


def _create_minimal_pdf() -> bytes:
    """Create minimal valid PDF (blank page - no Withings metrics extracted)."""
    buffer = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(100, 100)
    writer.write(buffer)
    buffer.seek(0)
    return buffer.getvalue()


class TestApiProcess:
    """Integration tests for POST /api/process."""

    def test_api_response_has_agent_and_report_structure(self) -> None:
        """API response includes agent.prompt, agent.context and report with full data."""
        client = app.test_client()
        zip_bytes = _create_minimal_zip()
        pdf_bytes = _create_minimal_pdf()

        response = client.post(
            "/api/process",
            data={
                "zip_file": (io.BytesIO(zip_bytes), "export.zip"),
                "pdf_file": (io.BytesIO(pdf_bytes), "report.pdf"),
                "target_date": "2026-06-01",
            },
        )

        assert response.status_code == 200
        data = response.get_json()

        assert "agent" in data
        assert "prompt" in data["agent"]
        assert "context" in data["agent"]
        assert len(data["agent"]["prompt"]) > 0
        assert len(data["agent"]["context"]) > 0

        assert "report" in data
        report = data["report"]
        assert "weight" in report
        assert "nutrition" in report
        assert "exercise" in report
        assert "comparison" in report

    def test_api_process_returns_new_structure(self) -> None:
        """API response includes weight.total_loss_kg, nutrition.nutrition_history, exercise.exercise_history, comparison."""
        client = app.test_client()
        zip_bytes = _create_minimal_zip()
        pdf_bytes = _create_minimal_pdf()

        response = client.post(
            "/api/process",
            data={
                "zip_file": (io.BytesIO(zip_bytes), "export.zip"),
                "pdf_file": (io.BytesIO(pdf_bytes), "report.pdf"),
                "target_date": "2026-06-01",
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        report = data["report"]

        assert "weight" in report
        assert "total_loss_kg" in report["weight"]
        assert "loss_rate_kg_per_week" in report["weight"]
        assert "first_weight_kg" in report["weight"]
        assert "latest_weight_kg" in report["weight"]

        assert "nutrition" in report
        assert "nutrition_history" in report["nutrition"]
        assert isinstance(report["nutrition"]["nutrition_history"], list)
        assert "avg_carbs_g" in report["nutrition"]
        assert "avg_fat_g" in report["nutrition"]

        assert "exercise" in report
        assert "exercise_history" in report["exercise"]
        assert isinstance(report["exercise"]["exercise_history"], list)
        assert "session_type_counts" in report["exercise"]

        assert "comparison" in report
        assert "weight_mfp_kg" in report["comparison"]
        assert "weight_withings_kg" in report["comparison"]
        assert "steps_mfp" in report["comparison"]
        assert "steps_withings" in report["comparison"]

        assert "target_date" in report
        assert report["target_date"] == "2026-06-01"
        assert "user" in report
        # When form does not send user info, weight is extracted from measures (last row = 83.3)
        assert report["user"]["name"] is None
        assert report["user"]["sex"] is None
        assert report["user"]["height_cm"] is None
        assert report["user"]["age"] is None
        assert report["user"]["weight_kg"] == 83.3  # extracted from measures

        assert "suggested_export_filename" in report
        assert report["suggested_export_filename"].endswith(".json")
        assert "relatorio_" in report["suggested_export_filename"]  # no name -> relatorio

    def test_suggested_export_filename_includes_user_name(self) -> None:
        """suggested_export_filename includes user name when provided."""
        client = app.test_client()
        zip_bytes = _create_minimal_zip()
        pdf_bytes = _create_minimal_pdf()

        response = client.post(
            "/api/process",
            data={
                "zip_file": (io.BytesIO(zip_bytes), "export.zip"),
                "pdf_file": (io.BytesIO(pdf_bytes), "report.pdf"),
                "target_date": "2026-06-01",
                "name": "Vinicius",
            },
        )
        assert response.status_code == 200
        data = response.get_json()
        fn = data["report"]["suggested_export_filename"]
        assert fn.startswith("Vinicius_")
        assert fn.endswith(".json")
        # Format: Vinicius_YYYY-MM-DD_HH-mm-ss.json
        parts = fn.replace(".json", "").split("_")
        assert len(parts) >= 3

    def test_extract_preview_returns_extracted_user_info(self) -> None:
        """POST /api/extract-preview returns weight from measures when PDF has no metrics."""
        client = app.test_client()
        zip_bytes = _create_minimal_zip()
        pdf_bytes = _create_minimal_pdf()

        response = client.post(
            "/api/extract-preview",
            data={
                "zip_file": (io.BytesIO(zip_bytes), "export.zip"),
                "pdf_file": (io.BytesIO(pdf_bytes), "report.pdf"),
            },
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "extracted" in data
        # Weight from measures (last row)
        assert data["extracted"]["weight_kg"] == 83.3

    def test_api_process_accepts_fat_and_carbs_overrides(self) -> None:
        """API accepts fat_g and carbs_g in user_info and passes to adherence targets."""
        client = app.test_client()
        zip_bytes = _create_minimal_zip()
        pdf_bytes = _create_minimal_pdf()

        response = client.post(
            "/api/process",
            data={
                "zip_file": (io.BytesIO(zip_bytes), "export.zip"),
                "pdf_file": (io.BytesIO(pdf_bytes), "report.pdf"),
                "target_date": "2026-06-01",
                "fat_g": "65",
                "carbs_g": "150",
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        report = data["report"]
        targets = report.get("meta", {}).get("adherence_targets") or report.get("nutrition", {}).get("adherence_targets")
        assert targets is not None
        assert targets.get("fat_g") == 65
        assert targets.get("carbs_g") == 150

    def test_api_process_accepts_optional_withings_zip(self) -> None:
        """API accepts optional withings_zip_file and returns withings_zip in report."""
        client = app.test_client()
        zip_bytes = _create_minimal_zip()
        pdf_bytes = _create_minimal_pdf()
        withings_zip_bytes = _create_minimal_withings_zip()

        response = client.post(
            "/api/process",
            data={
                "zip_file": (io.BytesIO(zip_bytes), "export.zip"),
                "pdf_file": (io.BytesIO(pdf_bytes), "report.pdf"),
                "withings_zip_file": (io.BytesIO(withings_zip_bytes), "withings_export.zip"),
                "target_date": "2026-06-01",
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        report = data["report"]
        assert "withings_zip" in report
        wz = report["withings_zip"]
        assert wz is not None
        assert "body_composition" in wz
        assert "activity" in wz
        assert len(wz["body_composition"].get("history", [])) >= 1
        assert wz["activity"]["summary"]["avg_daily_steps"] == 15000

    def test_api_process_works_without_withings_zip(self) -> None:
        """API works when withings_zip_file is not sent; withings_zip is None."""
        client = app.test_client()
        zip_bytes = _create_minimal_zip()
        pdf_bytes = _create_minimal_pdf()

        response = client.post(
            "/api/process",
            data={
                "zip_file": (io.BytesIO(zip_bytes), "export.zip"),
                "pdf_file": (io.BytesIO(pdf_bytes), "report.pdf"),
                "target_date": "2026-06-01",
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        report = data["report"]
        assert report.get("withings_zip") is None
