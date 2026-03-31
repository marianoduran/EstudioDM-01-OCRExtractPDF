# 🏦 OCRExtractPDF (Santander / HSBC)

This project extracs movements from bank statements in PDF format (Santander and HSBC), calculates transaction amounts based on balance differences, and provides a summary.

## 🚀 Usage

The application is built with Streamlit. To run it:

```bash
streamlit run App_STDR_OCR_PDF_Extract.py
```

## 🧪 Testing

We use `pytest` for unit and integration tests.

To run all tests:
```bash
.venv/bin/python -m pytest
```

See [tests/README.md](tests/README.md) for more details.

## 🛠 Project Structure

- `App_STDR_OCR_PDF_Extract.py`: Main Streamlit application and parsing logic.
- `tests/`: Project tests directory.
- `PDFs/`: Sample PDFs used for testing and validation.
- `requirements.txt`: Project dependencies.
