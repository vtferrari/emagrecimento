---
name: emagrecimento-workflows
description: Guides implementation of common workflows in the emagrecimento cutting dashboard. Use when adding PDF metrics, new use cases, UI blocks, or modifying the Withings/MyFitnessPal data pipeline. Follows TDD and Clean Architecture.
---

# Emagrecimento Workflows

## TDD First

Always write the test before implementing. Red → Green → Refactor.

## Add PDF Metric (Withings Report)

1. **Test first** in `test_pdf_metrics_parser.py` – failing test for the new metric.
2. **Parser** (`src/emagrecimento/infrastructure/pdf_metrics_parser.py`):
   - Add regex to `PATTERNS` dict: `"key_name": r"regex capturing group"`.
   - For alternate formats, add to `FALLBACK_PATTERNS`.
   - If value is numeric, ensure key is in the parse block (ends with `_kg`, `_pct`, `_bpm`, `_sec`, `_min`, or in `("visceral_fat", "nights", "pwv_m_per_s")`).

3. **Transformer** (`build_report.py`, `_build_pdf_report_v2`):
   - Map flat key to block: `activity`, `body`, `sleep`, or `cardio`.
   - For derived values (e.g. `derived_fat_mass_pct`), compute from other metrics.

4. **Frontend** (`static/js/app.js`):
   - Add Portuguese label to `pdfV2Labels` (v2 blocks) and/or `labels` (flat pdf_report).

## Add New Use Case (TDD)

1. **Test first** – write failing test for the use case behavior.
2. Create `application/use_cases/your_use_case.py`.
3. Add port in `interfaces.py` if needed.
4. Add factory in `container.py`.
5. Wire in `app.py` or script that needs it.

## Project Structure Reference

```
src/emagrecimento/
├── domain/          # entities, value_objects
├── application/     # interfaces, use_cases (build_report, extract_pdf, extract_zip)
├── infrastructure/  # zip_reader, pdf_reader, pdf_metrics_parser
└── container.py     # composition root
```
