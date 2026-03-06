"""Integration tests for ZIP extraction."""

import io
import zipfile

import pandas as pd
import pytest

from emagrecimento.infrastructure.zip_reader import ZipFileZipReader


def _create_minimal_zip() -> bytes:
    """Create minimal valid ZIP with required CSVs."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        # Measures CSV
        measures_csv = "Data,Peso\n2026-02-01,85.0\n2026-02-02,84.8\n2026-02-03,84.5\n"
        zf.writestr("medidas.csv", measures_csv)

        # Nutrition CSV
        nutrition_csv = (
            "Data,Calorias,Proteínas (g),Carboidratos (g),Gorduras (g),Fibra,Sódio (mg)\n"
            "2026-02-01,1900,180,200,60,25,2000\n"
            "2026-02-02,1850,175,190,55,22,1900\n"
        )
        zf.writestr("alimentacao.csv", nutrition_csv)

        # Exercise CSV
        exercise_csv = (
            "Data,Calorias de exercícios,Minutos de exercício,Passos,Exercício\n"
            "2026-02-01,350,45,8000,Caminhada\n"
            "2026-02-02,0,0,5000,\n"
        )
        zf.writestr("exercicios.csv", exercise_csv)

    buffer.seek(0)
    return buffer.getvalue()


class TestZipFileZipReader:
    """Integration tests for ZipFileZipReader."""

    def test_extracts_from_bytesio(self) -> None:
        zip_bytes = _create_minimal_zip()
        reader = ZipFileZipReader()
        result = reader.extract(io.BytesIO(zip_bytes))

        assert result.measures is not None
        assert len(result.measures) >= 3
        assert "weight" in result.measures.columns
        assert "ma5" in result.measures.columns
        assert "ma7" in result.measures.columns

        assert result.nutrition_daily is not None
        assert len(result.nutrition_daily) >= 2
        assert "calories" in result.nutrition_daily.columns

        assert result.exercise_daily is not None
        assert len(result.exercise_daily) >= 2

    def test_exercise_sanity_caps_insane_values(self) -> None:
        """Exercise with impossible values gets capped (sanity check)."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            measures_csv = "Data,Peso\n2026-02-01,85.0\n"
            zf.writestr("medidas.csv", measures_csv)
            nutrition_csv = "Data,Calorias,Proteínas (g),Carboidratos (g),Gorduras (g),Fibra,Sódio (mg)\n2026-02-01,1900,180,200,60,25,2000\n"
            zf.writestr("alimentacao.csv", nutrition_csv)
            # Row with insane values: 26621 min, 133630 cal - should be capped
            exercise_csv = (
                "Data,Calorias de exercícios,Minutos de exercício,Passos,Exercício\n"
                "2026-02-01,133630,26621,8000,Esteira\n"
            )
            zf.writestr("exercicios.csv", exercise_csv)

        buffer.seek(0)
        reader = ZipFileZipReader()
        result = reader.extract(io.BytesIO(buffer.getvalue()))

        row = result.exercise_daily.iloc[0]
        assert row["exercise_minutes"] <= 600
        assert row["exercise_calories"] <= 3000
        assert row["steps"] <= 100000

    def test_raises_when_missing_csv(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            zf.writestr("other.csv", "a,b\n1,2\n")
        buffer.seek(0)

        reader = ZipFileZipReader()
        with pytest.raises(FileNotFoundError, match="Não encontrei todos os CSVs"):
            reader.extract(buffer)

    def test_extracts_from_new_format_filenames(self) -> None:
        """Extract from ZIP with new MFP export filenames (Resumo-da-alimentação, etc.)."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            measures_csv = "Data,Body Fat %,Peso\n2026-01-20,24.61,95.4\n2026-01-21,22.26,95.9\n"
            zf.writestr("Resumo-das-medidas-2026-01-19-a-2026-03-06.csv", measures_csv)

            nutrition_csv = (
                "Data,Refeição,Calorias,Gorduras (g),Gorduras saturadas,Carboidratos (g),Fibra,Açucar,Proteínas (g),Sódio (mg)\n"
                "2026-01-19,Almoço,824.8,13.0,1.0,163.0,2.9,9.1,24.5,134.6\n"
                "2026-01-19,Jantar,805.2,14.9,4.2,154.3,4.0,10.8,24.8,128.7\n"
            )
            zf.writestr("Resumo-da-alimentação-2026-01-19-a-2026-03-06.csv", nutrition_csv)

            exercise_csv = (
                "Data,Exercício,Tipo,Calorias de exercícios,Minutos de exercício,Passos\n"
                "2026-01-19,Corrida esteira,Cardiovascular,235.0,49,\n"
                "2026-01-19,Caminhada,Cardiovascular,52.0,11,\n"
            )
            zf.writestr("Resumo-dos-exercícios-2026-01-19-a-2026-03-06.csv", exercise_csv)

        buffer.seek(0)
        reader = ZipFileZipReader()
        result = reader.extract(io.BytesIO(buffer.getvalue()))

        assert result.measures is not None
        assert len(result.measures) >= 2
        assert "weight" in result.measures.columns

        assert result.nutrition_daily is not None
        assert len(result.nutrition_daily) >= 1
        assert "calories" in result.nutrition_daily.columns

        assert result.exercise_daily is not None
        assert len(result.exercise_daily) >= 1

    def test_exercise_deduplication_same_workout_logged_multiple_times(self) -> None:
        """Duplicate rows of same workout (date+exercise) should be deduplicated: max per group, not sum."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            measures_csv = "Data,Peso\n2026-01-19,95.0\n"
            zf.writestr("medidas.csv", measures_csv)
            nutrition_csv = "Data,Calorias,Proteínas (g),Carboidratos (g),Gorduras (g),Fibra,Sódio (mg)\n2026-01-19,1900,180,200,60,25,2000\n"
            zf.writestr("alimentacao.csv", nutrition_csv)
            # 11 identical rows of "Corrida, esteira" 49 min each - should yield 49 min, not 539
            rows = ["2026-01-19,\"\"\"Corrida, esteira\"\"\",Cardiovascular,235.0,49,,,,\n"] * 11
            exercise_csv = (
                "Data,Exercício,Tipo,Calorias de exercícios,Minutos de exercício,Séries,Repetições por série,Quilogramas,Passos\n"
                + "".join(rows)
            )
            zf.writestr("exercicios.csv", exercise_csv)

        buffer.seek(0)
        reader = ZipFileZipReader()
        result = reader.extract(io.BytesIO(buffer.getvalue()))

        row = result.exercise_daily.iloc[0]
        # Should be 49 min (max of duplicates), not 11*49=539
        assert row["exercise_minutes"] == 49
        # Calories: 235*11=2585, but we take max per (date,exercise) so 235 per group
        assert row["exercise_calories"] == 235

    def test_measures_includes_body_fat_pct_when_present(self) -> None:
        """Measures CSV with Body Fat % column should include body_fat_pct in output."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            measures_csv = "Data,Body Fat %,Peso\n2026-01-20,24.61,95.4\n2026-01-21,22.26,95.9\n2026-01-22,,96.1\n"
            zf.writestr("Resumo-das-medidas.csv", measures_csv)
            nutrition_csv = "Data,Calorias,Proteínas (g),Carboidratos (g),Gorduras (g),Fibra,Sódio (mg)\n2026-01-20,1900,180,200,60,25,2000\n"
            zf.writestr("alimentacao.csv", nutrition_csv)
            exercise_csv = "Data,Calorias de exercícios,Minutos de exercício,Passos\n2026-01-20,200,30,\n"
            zf.writestr("exercicios.csv", exercise_csv)

        buffer.seek(0)
        reader = ZipFileZipReader()
        result = reader.extract(io.BytesIO(buffer.getvalue()))

        assert "body_fat_pct" in result.measures.columns
        assert result.measures.iloc[0]["body_fat_pct"] == pytest.approx(24.61, abs=0.01)
        assert result.measures.iloc[1]["body_fat_pct"] == pytest.approx(22.26, abs=0.01)
        assert pd.isna(result.measures.iloc[2]["body_fat_pct"])

    def test_nutrition_includes_new_columns_and_nutrition_by_meal(self) -> None:
        """Nutrition with Refeição, Açucar, Gorduras saturadas should produce nutrition_by_meal."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            measures_csv = "Data,Peso\n2026-01-19,95.0\n2026-01-20,94.8\n"
            zf.writestr("medidas.csv", measures_csv)
            nutrition_csv = (
                "Data,Refeição,Calorias,Gorduras (g),Gorduras saturadas,Gorduras poliinsaturadas,Gorduras monoinsaturadas,Açucar,Carboidratos (g),Fibra,Proteínas (g),Sódio (mg)\n"
                "2026-01-19,Almoço,824.8,13.0,1.0,0.0,0.0,9.1,163.0,2.9,24.5,134.6\n"
                "2026-01-19,Jantar,805.2,14.9,4.2,0.0,0.0,10.8,154.3,4.0,24.8,128.7\n"
                "2026-01-20,Café da manhã,460.4,8.9,3.2,2.0,3.0,0.3,60.0,10.3,41.4,92.0\n"
            )
            zf.writestr("Resumo-da-alimentação.csv", nutrition_csv)
            exercise_csv = "Data,Calorias de exercícios,Minutos de exercício,Passos\n2026-01-19,200,30,\n2026-01-20,0,0,\n"
            zf.writestr("exercicios.csv", exercise_csv)

        buffer.seek(0)
        reader = ZipFileZipReader()
        result = reader.extract(io.BytesIO(buffer.getvalue()))

        assert "sugar_g" in result.nutrition_daily.columns
        assert "fat_saturated_g" in result.nutrition_daily.columns
        assert result.nutrition_by_meal is not None
        assert len(result.nutrition_by_meal) == 3
        assert "meal" in result.nutrition_by_meal.columns
        assert "calories" in result.nutrition_by_meal.columns
        meals = result.nutrition_by_meal["meal"].tolist()
        assert "Almoço" in meals
        assert "Jantar" in meals
        assert "Café da manhã" in meals
