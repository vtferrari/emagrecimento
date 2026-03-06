"""Unit tests for export filename builder."""

from datetime import datetime

from emagrecimento.domain.export_filename import build_export_filename


class TestBuildExportFilename:
    """Tests for build_export_filename."""

    def test_with_name_and_fixed_date(self) -> None:
        """Filename includes name and timestamp."""
        when = datetime(2026, 3, 6, 21, 30, 45)
        result = build_export_filename("Vinicius", when=when)
        assert result == "Vinicius_2026-03-06_21-30-45.json"

    def test_with_full_name_spaces_to_underscore(self) -> None:
        """Spaces in name become underscores."""
        when = datetime(2026, 3, 6, 10, 0, 0)
        result = build_export_filename("Sibele Schuantes", when=when)
        assert result == "Sibele_Schuantes_2026-03-06_10-00-00.json"

    def test_with_none_name_uses_relatorio(self) -> None:
        """None or empty name uses 'relatorio' fallback."""
        when = datetime(2026, 3, 6, 12, 0, 0)
        assert build_export_filename(None, when=when) == "relatorio_2026-03-06_12-00-00.json"
        assert build_export_filename("", when=when) == "relatorio_2026-03-06_12-00-00.json"
        assert build_export_filename("   ", when=when) == "relatorio_2026-03-06_12-00-00.json"

    def test_removes_invalid_filename_chars(self) -> None:
        """Invalid chars / \\ : * ? \" < > | are removed."""
        when = datetime(2026, 3, 6, 1, 2, 3)
        result = build_export_filename("João/Test:file", when=when)
        assert result == "JoãoTestfile_2026-03-06_01-02-03.json"
        assert "/" not in result
        assert ":" not in result

    def test_date_format_padded(self) -> None:
        """Month, day, hour, minute, second are zero-padded."""
        when = datetime(2026, 1, 5, 9, 5, 3)
        result = build_export_filename("User", when=when)
        assert result == "User_2026-01-05_09-05-03.json"

    def test_uses_now_when_when_not_provided(self) -> None:
        """When when is None, uses current datetime."""
        result = build_export_filename("Test")
        assert result.endswith(".json")
        assert "Test_" in result
        # Format: Test_YYYY-MM-DD_HH-mm-ss.json
        parts = result.replace(".json", "").split("_")
        assert len(parts) >= 3
        assert len(parts[1]) == 10  # YYYY-MM-DD
        assert len(parts[2]) == 8   # HH-mm-ss
