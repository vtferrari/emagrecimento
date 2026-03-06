"""Integration tests for /api/process endpoint."""

import io
import zipfile

import pytest
from pypdf import PdfWriter

from app import app


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

        assert "weight" in data
        assert "total_loss_kg" in data["weight"]
        assert "loss_rate_kg_per_week" in data["weight"]
        assert "first_weight_kg" in data["weight"]
        assert "latest_weight_kg" in data["weight"]

        assert "nutrition" in data
        assert "nutrition_history" in data["nutrition"]
        assert isinstance(data["nutrition"]["nutrition_history"], list)
        assert "avg_carbs_g" in data["nutrition"]
        assert "avg_fat_g" in data["nutrition"]

        assert "exercise" in data
        assert "exercise_history" in data["exercise"]
        assert isinstance(data["exercise"]["exercise_history"], list)
        assert "session_type_counts" in data["exercise"]

        assert "comparison" in data
        assert "weight_mfp_kg" in data["comparison"]
        assert "weight_withings_kg" in data["comparison"]
        assert "steps_mfp" in data["comparison"]
        assert "steps_withings" in data["comparison"]

        assert "target_date" in data
        assert data["target_date"] == "2026-06-01"
        assert "user" in data
        assert data["user"] == {"name": None, "sex": None, "height_cm": None, "age": None, "weight_kg": None}
