"""Domain layer - entities and value objects."""

from emagrecimento.domain.entities import ZipData
from emagrecimento.domain.value_objects import find_column, normalize_text, parse_number

__all__ = ["ZipData", "normalize_text", "find_column", "parse_number"]
