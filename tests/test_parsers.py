import pytest
import os
import pandas as pd
from App_STDR_OCR_PDF_Extract import parse_santander_pdf, parse_hsbc_pdf

SAMPLE_PDF_DIR = "/home/marianoduran/Documents/TeamIT-Proyectos/00 - EstudioDM-01-OCRExtractPDF/PDFs"

@pytest.mark.parametrize("filename", [
    "03_Santander_Dic24.pdf",
    "04_Santander ago-25_NEW.pdf"
])
def test_parse_santander_pdf(filename):
    pdf_path = os.path.join(SAMPLE_PDF_DIR, filename)
    if not os.path.exists(pdf_path):
        pytest.skip(f"Sample PDF {filename} not found.")
    
    with open(pdf_path, "rb") as f:
        df = parse_santander_pdf(f)
    
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert all(col in df.columns for col in ["Fecha", "Referencia", "Importe", "Saldo"])
    
    # Check if Saldo Inicial is the first row
    assert df.iloc[0]["Referencia"] == "Saldo Inicial"

def test_parse_hsbc_pdf():
    filename = "02_HSBC_Extracto.pdf"
    pdf_path = os.path.join(SAMPLE_PDF_DIR, filename)
    if not os.path.exists(pdf_path):
        pytest.skip(f"Sample PDF {filename} not found.")
    
    with open(pdf_path, "rb") as f:
        df = parse_hsbc_pdf(f)
    
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert all(col in df.columns for col in ["Fecha", "Referencia", "Importe", "Saldo"])
    
    # Check if SALDO ANTERIOR is the first row (based on hsbc_parser logic)
    assert df.iloc[0]["Referencia"] == "SALDO ANTERIOR"
