# Add New PDF Metric

Add a new metric extracted from the Withings medical report PDF. **TDD: write the test first.**

## Steps (TDD order)

1. **Test first** (`tests/unit/test_pdf_metrics_parser.py`):
   - Write a failing test that asserts the new metric is extracted from sample text.

2. **Parser** (`src/emagrecimento/infrastructure/pdf_metrics_parser.py`):
   - Add regex to `PATTERNS` or `FALLBACK_PATTERNS`
   - Add key to numeric parsing if needed (`_kg`, `_pct`, `_bpm`, `_sec`, `_min`, etc.)
   - Run pytest until the test passes.

3. **Transformer** (`src/emagrecimento/application/use_cases/build_report.py`):
   - Map the flat key to the appropriate block in `_build_pdf_report_v2` (activity, body, sleep, cardio)

4. **Frontend** (`static/js/app.js`):
   - Add Portuguese label to `pdfV2Labels` and/or `labels` (flat pdf_report)

5. Run `pytest` to ensure all tests pass.
