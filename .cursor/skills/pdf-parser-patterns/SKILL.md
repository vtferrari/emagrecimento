---
name: pdf-parser-patterns
description: Helps define regex patterns for extracting metrics from Withings medical report PDF text. Use when adding or debugging PDF parser patterns, or when the user provides sample PDF text.
---

# PDF Parser Patterns

## Pattern Format

In `pdf_metrics_parser.py`, patterns use a single capturing group for the value:

```python
"key_name": r"Label or context\s+([0-9]+(?:\.[0-9]+)?)\s*unit"
```

## Common Patterns

- **Integer**: `([0-9]+)`
- **Float**: `([0-9]+(?:\.[0-9]+)?)` or `([0-9,]+(?:\.[0-9]+)?)` for comma decimals
- **Percentage**: `([0-9]+)\s*%`
- **Duration (e.g. 7h09)**: `([0-9]+h[0-9]{2})`

## Numeric Parsing

Keys ending in `_kg`, `_kcal`, `_pct`, `_avg`, `_bpm`, `_sec`, `_min` are parsed with `parse_number()`. Also: `visceral_fat`, `nights`, `pwv_m_per_s`.

## Validating Patterns

If you have sample PDF text, test the regex against it. The parser extracts full text via `PypdfPdfReader`, then applies patterns. Use `re.search(pattern, text)` to verify.
