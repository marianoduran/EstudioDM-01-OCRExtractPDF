# Unit and Integration Tests

This project uses `pytest` for testing.

## Prerequisites

Ensure you have the virtual environment activated and `pytest` installed.
If not, you can install it via:
```bash
.venv/bin/pip install pytest
```

## Running Tests

To run all tests:
```bash
.venv/bin/python -m pytest
```

## Test Structure

- `tests/test_helpers.py`: Unit tests for helper functions like `_to_float_money_arg`, `_to_float_money_us`, `build_summary`, and `to_csv_bytes`.
- `tests/test_parsers.py`: Integration tests that run the Santander and HSBC parsers on sample PDFs located in the `PDFs` directory.

## Coverage

The tests cover:
- Parsing of Argentine and US formatted money strings.
- DataFrame summary aggregation logic (including total calculations and ignoring "Saldo Inicial" rows).
- PDF parsing logic for both Santander and HSBC formats using real (sample) files.
- Refactored `App_STDR_OCR_PDF_Extract.py` to allow imports without starting the Streamlit server.
