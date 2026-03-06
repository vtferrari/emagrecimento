"""Unit tests for serialization utilities."""

from emagrecimento.application.serialization import sanitize_for_json


class TestSanitizeForJson:
    """Tests for sanitize_for_json function."""

    def test_replaces_nan_with_none(self) -> None:
        """NaN floats become None."""
        assert sanitize_for_json(float("nan")) is None

    def test_replaces_inf_with_none(self) -> None:
        """Inf floats become None."""
        assert sanitize_for_json(float("inf")) is None
        assert sanitize_for_json(float("-inf")) is None

    def test_preserves_valid_floats(self) -> None:
        """Valid floats are preserved."""
        assert sanitize_for_json(3.14) == 3.14
        assert sanitize_for_json(0.0) == 0.0

    def test_recursively_sanitizes_dict(self) -> None:
        """Dict values are recursively sanitized."""
        obj = {"a": 1.0, "b": float("nan"), "c": {"nested": float("inf")}}
        result = sanitize_for_json(obj)
        assert result["a"] == 1.0
        assert result["b"] is None
        assert result["c"]["nested"] is None

    def test_recursively_sanitizes_list(self) -> None:
        """List elements are recursively sanitized."""
        obj = [1.0, float("nan"), [float("inf")]]
        result = sanitize_for_json(obj)
        assert result[0] == 1.0
        assert result[1] is None
        assert result[2][0] is None

    def test_preserves_other_types(self) -> None:
        """Strings, ints, bools, None are preserved."""
        obj = {"s": "hello", "i": 42, "b": True, "n": None}
        result = sanitize_for_json(obj)
        assert result == obj

    def test_handles_empty_structures(self) -> None:
        """Empty dict and list are preserved."""
        assert sanitize_for_json({}) == {}
        assert sanitize_for_json([]) == []
