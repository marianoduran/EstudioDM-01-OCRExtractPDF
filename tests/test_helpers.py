import pytest
import pandas as pd
import io
from App_STDR_OCR_PDF_Extract import (
    _to_float_money_arg,
    _to_float_money_us,
    build_summary,
    to_csv_bytes,
    get_kpis,
    generate_filenames
)

def test_to_float_money_arg():
    assert _to_float_money_arg("$ 1.234,56") == 1234.56
    assert _to_float_money_arg("-$ 1.234,56") == -1234.56
    assert _to_float_money_arg("–$ 1.234,56") == -1234.56  # Unicode dash
    assert _to_float_money_arg("1.000,00") == 1000.00
    assert _to_float_money_arg("70.833,71") == 70833.71

def test_to_float_money_us():
    assert _to_float_money_us("1,234.56") == 1234.56
    assert _to_float_money_us("-1,234.56") == -1234.56
    assert _to_float_money_us("–1,234.56") == -1234.56  # Unicode dash
    assert _to_float_money_us("1000.00") == 1000.00

def test_build_summary_empty():
    df = pd.DataFrame(columns=["Fecha", "Referencia", "Importe", "Saldo"])
    summary = build_summary(df)
    assert "TOTAL" not in summary["Referencia"].values
    assert len(summary) == 0

def test_build_summary_with_data():
    data = [
        {"Fecha": "", "Referencia": "Saldo Inicial", "Importe": "", "Saldo": 1000.0},
        {"Fecha": "01/01/24", "Referencia": "Compra A", "Importe": -100.0, "Saldo": 900.0},
        {"Fecha": "01/01/24", "Referencia": "Compra A", "Importe": -50.0, "Saldo": 850.0},
        {"Fecha": "02/01/24", "Referencia": "Venta B", "Importe": 200.0, "Saldo": 1050.0},
    ]
    df = pd.DataFrame(data)
    summary = build_summary(df)
    
    # Check if "Saldo Inicial" is ignored
    assert "Saldo Inicial" not in summary["Referencia"].values
    
    # Check groupings
    summary_a = summary[summary["Referencia"] == "Compra A"].iloc[0]
    assert summary_a["Sum_Importe"] == -150.0
    assert summary_a["Cantidad"] == 2
    
    summary_b = summary[summary["Referencia"] == "Venta B"].iloc[0]
    assert summary_b["Sum_Importe"] == 200.0
    assert summary_b["Cantidad"] == 1
    
    # Check TOTAL row
    total_row = summary[summary["Referencia"] == "TOTAL"].iloc[0]
    assert total_row["Sum_Importe"] == 50.0
    assert total_row["Cantidad"] == 3

def test_to_csv_bytes():
    df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    csv_bytes = to_csv_bytes(df)
    assert isinstance(csv_bytes, bytes)
    content = csv_bytes.decode("utf-8")
    assert "A,B" in content
    assert "1,3" in content

def test_get_kpis():
    data = [
        {"Fecha": "", "Referencia": "Saldo Inicial", "Importe": "", "Saldo": 1000.0},
        {"Fecha": "01/01/24", "Referencia": "A", "Importe": -100.0, "Saldo": 900.0},
        {"Fecha": "02/01/24", "Referencia": "B", "Importe": 200.0, "Saldo": 1100.0},
    ]
    df = pd.DataFrame(data)
    s_inc, tot, s_fin = get_kpis(df)
    assert s_inc == 1000.0
    assert tot == 100.0  # -100 + 200
    assert s_fin == 1100.0

def test_get_kpis_empty():
    assert get_kpis(pd.DataFrame()) == (0.0, 0.0, 0.0)

def test_generate_filenames():
    det, res = generate_filenames("test_file", "Santander OCR Extract")
    assert "test_file_STDR_Detalle_Movimientos_" in det
    assert "test_file_STDR_Resumen_Referencias_" in res
    assert det.endswith(".csv")
    
    det_h, res_h = generate_filenames("test_file", "HSBC OCR Extract")
    assert "test_file_HSBC_Detalle_Movimientos_" in det_h
