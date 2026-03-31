import pytest
from streamlit.testing.v1 import AppTest

def test_ui_basic_load():
    at = AppTest.from_file("App_STDR_OCR_PDF_Extract.py")
    at.run()
    assert not at.exception
    assert "Extractor de Movimientos" in at.title[0].value

def test_ui_system_info():
    at = AppTest.from_file("App_STDR_OCR_PDF_Extract.py")
    at.run()
    
    # Change to System Info
    at.sidebar.radio[0].set_value("System Info").run()
    
    assert not at.exception
    assert "Librerías Instaladas" in at.subheader[0].value
