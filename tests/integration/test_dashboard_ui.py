"""Integration tests for dashboard UI elements."""

from app import app


class TestDashboardUI:
    """Verify dashboard HTML contains required elements for new features."""

    def test_weight_card_has_total_loss_and_rate_elements(self) -> None:
        """Weight card has id totalLoss and id lossRate."""
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert 'id="totalLoss"' in html or "id='totalLoss'" in html
        assert 'id="lossRate"' in html or "id='lossRate'" in html

    def test_nutrition_card_has_carbs_fat_and_chart(self) -> None:
        """Nutrition card has avgCarbs, avgFat, nutritionChart."""
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert 'id="avgCarbs"' in html or "id='avgCarbs'" in html
        assert 'id="avgFat"' in html or "id='avgFat'" in html
        assert 'id="nutritionChart"' in html or "id='nutritionChart'" in html

    def test_exercise_card_has_session_counts_and_chart(self) -> None:
        """Exercise card has sessionTypeCounts and exerciseChart."""
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert 'id="sessionTypeCounts"' in html or "id='sessionTypeCounts'" in html
        assert 'id="exerciseChart"' in html or "id='exerciseChart'" in html

    def test_comparison_card_exists(self) -> None:
        """Comparison card exists with id comparisonCard or class comparison-card."""
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert 'id="comparisonCard"' in html or "comparison-card" in html

    def test_export_json_button_exists(self) -> None:
        """Dashboard has export JSON button with id exportJsonBtn."""
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert 'id="exportJsonBtn"' in html or "id='exportJsonBtn'" in html

    def test_last_days_input_removed(self) -> None:
        """Upload section does not have 'Últimos dias' or lastDays input."""
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "Últimos dias" not in html
        assert 'id="lastDays"' not in html

    def test_weight_card_has_body_fat_element(self) -> None:
        """Weight card has body fat stat element for new format data."""
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert 'id="bodyFatStat"' in html or "id='bodyFatStat'" in html
        assert 'id="latestBodyFat"' in html or "id='latestBodyFat'" in html

    def test_weekly_summary_card_exists(self) -> None:
        """Weekly summary card exists with id weeklySummary."""
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert 'id="weeklyCard"' in html or "id='weeklyCard'" in html
        assert 'id="weeklySummary"' in html or "id='weeklySummary'" in html

    def test_alerts_card_exists(self) -> None:
        """Alerts/insights card exists with id alertsList."""
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert 'id="alertsCard"' in html or "id='alertsCard'" in html
        assert 'id="alertsList"' in html or "id='alertsList'" in html

    def test_summary_cards_exist(self) -> None:
        """Dashboard has 4 summary cards at top: gordura, calorias, insights, alertas."""
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert 'id="summaryCards"' in html or "id='summaryCards'" in html
        assert 'id="summaryFat"' in html
        assert 'id="summaryCalories"' in html
        assert 'id="summaryInsights"' in html
        assert 'id="summaryAlerts"' in html

    def test_pdf_card_removed_in_favor_of_v2(self) -> None:
        """Legacy pdf-card (Relatório Withings PDF) is removed; use pdf-report-v2-card instead."""
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert 'class="card pdf-card"' not in html and "pdf-card" not in html
        assert 'id="pdfMetrics"' not in html

    def test_pdf_report_v2_card_has_four_blocks(self) -> None:
        """PDF report v2 card exists with activity, body, sleep, cardio block containers."""
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert 'id="pdfReportV2Card"' in html or "id='pdfReportV2Card'" in html
        assert 'id="pdfV2Activity"' in html or "id='pdfV2Activity'" in html
        assert 'id="pdfV2Body"' in html or "id='pdfV2Body'" in html
        assert 'id="pdfV2Sleep"' in html or "id='pdfV2Sleep'" in html
        assert 'id="pdfV2Cardio"' in html or "id='pdfV2Cardio'" in html

    def test_metas_form_has_fat_and_carbs_fields(self) -> None:
        """Metas override section has fat_g (Gordura) and carbs_g (Carboidratos) inputs."""
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert 'id="fatG"' in html or "id='fatG'" in html
        assert 'id="carbsG"' in html or "id='carbsG'" in html
        assert "Gordura" in html
        assert "Carboidratos" in html

    def test_dashboard_header_has_sticky_class(self) -> None:
        """Dashboard header has sticky class for fixed positioning when scrolling."""
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "dashboard-header--sticky" in html

    def test_clear_storage_button_exists(self) -> None:
        """Dashboard has clear storage button for removing persisted session data."""
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert 'id="btnClearStorage"' in html or "id='btnClearStorage'" in html
        assert "Limpar dados salvos" in html

    def test_storage_script_loaded(self) -> None:
        """Page loads storage.js for IndexedDB persistence."""
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "storage.js" in html
