import pytest
import io
import pandas as pd
from unittest.mock import MagicMock, patch
from App_STDR_OCR_PDF_Extract import parse_santander_pdf

def test_parse_santander_consistency_error():
    # Mock pdfplumber to return a page with inconsistent data
    # Saldo Inicial: 1000
    # Movimiento: -100
    # Expected Saldo: 900
    # Actual Saldo (fake): 800 -> should trigger ValueError
    
    mock_text = (
        "Saldo Inicial $ 1.000,00\n"
        "01/01/24 Movimiento de Prueba $ 100,00 $ 800,00\n"
    )
    
    mock_page = MagicMock()
    mock_page.extract_text.return_value = mock_text
    
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    mock_pdf.__enter__.return_value = mock_pdf
    
    with patch("pdfplumber.open", return_value=mock_pdf):
        # We need a file-like object even if we mock open
        with pytest.raises(ValueError) as excinfo:
            parse_santander_pdf(io.BytesIO(b"fake pdf"))
        
        assert "Error de consistencia" in str(excinfo.value)
        assert "saldo anterior 1,000.00 + importe -100.00 = 900.00 pero el saldo registrado en el PDF es 800.00" in str(excinfo.value)
