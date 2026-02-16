import streamlit as st
import pdfplumber
import pandas as pd
import re
import io
from datetime import datetime

# =========================
# Shared helpers
# =========================
def _to_float_money_arg(raw: str) -> float:
    """Money with $ and Argentine thousands '.' and decimal ',' (e.g., -$ 70.833,71)."""
    # Normalize unicode dashes to hyphen
    normalized = raw.replace("–", "-").replace("—", "-").replace("−", "-")
    return float(
        normalized.replace("$", "")
           .replace(".", "")
           .replace(",", ".")
           .replace(" ", "")
           .strip()
    )

def _to_float_money_us(raw: str) -> float:
    """Money with US-style thousands ',' and decimal '.' (e.g., 1,234.56)."""
    # Normalize unicode dashes to hyphen
    normalized = raw.replace("–", "-").replace("—", "-").replace("−", "-")
    return float(normalized.replace(",", "").strip())

# ... (omitted code) ...

# =========================
# Santander parser (based on your previous app logic)
# =========================
saldo_inicial_stdr_re = re.compile(r"Saldo\s+Inicial\s+([-–—−]?\s*\$\s*[\d\.\,]+)")

linea_movimiento_stdr = re.compile(
    r"""^
    (?P<fecha>\d{2}/\d{2}/\d{2})?     # Fecha opcional
    \s*
    (?:\d+\s+)?                       # Comprobante opcional
    (?P<movimiento>.*?)               # Movimiento (texto)
    \s+
    (?:
        (?P<debito>[-–—−]?\s*\$\s*[\d\.\,]+)   # Débito (Standard hyphen + unicode dashes)
        \s+
        (?P<saldo>[-–—−]?\s*\$\s*[\d\.\,]+)    # Saldo si no hay crédito
      |
        (?P<credito>[-–—−]?\s*\$\s*[\d\.\,]+)  # Crédito
        \s+
        (?P<saldo2>[-–—−]?\s*\$\s*[\d\.\,]+)   # Saldo si no hay débito
    )
    $""",
    re.VERBOSE
)

linea_transferencia_stdr = re.compile(
    r'^(?:De|A)(?:\s+[A-Za-zÁÉÍÓÚÑáéíóúñ\s,.]+)?\s*/\s*.*?\s*-\s*.*?\s*/.*$',
    re.IGNORECASE
)

def parse_santander_pdf(file_like) -> pd.DataFrame:
    movimientos = []
    fecha_actual = None
    fecha_anterior = None
    previous_saldo = None
    saldo_anterior_registrado = False
    row_transferencia = False
    current_row = None

    with pdfplumber.open(file_like) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in (l.strip() for l in text.splitlines()):
                # 1) Saldo Inicial
                if not saldo_anterior_registrado:
                    m_saldo = saldo_inicial_stdr_re.search(line)
                    if m_saldo:
                        saldo_inicial = _to_float_money_arg(m_saldo.group(1))
                        movimientos.append({
                            "Fecha": "",
                            "Referencia": "Saldo Inicial",
                            "Importe": "",
                            "Saldo": saldo_inicial
                        })
                        previous_saldo = saldo_inicial
                        saldo_anterior_registrado = True
                        continue

                # 2) Línea de movimiento
                m = linea_movimiento_stdr.match(line)
                if m:
                    fecha = m.group("fecha")
                    if fecha:
                        fecha_actual = fecha
                        fecha_anterior = fecha
                    else:
                        fecha_actual = fecha_anterior

                    referencia = (m.group("movimiento") or "").strip()

                    raw_imp = m.group("debito") or m.group("credito")
                    importe = _to_float_money_arg(raw_imp)
                    if m.group("debito"):
                        importe = -importe

                    raw_saldo = m.group("saldo") or m.group("saldo2")
                    saldo = _to_float_money_arg(raw_saldo)

                    # Ajuste por diferencia de saldo (cuando sube el saldo)
                    if previous_saldo is not None and (saldo - previous_saldo) > 0:
                        importe = -importe

                    if referencia.lower() in ("transferencia recibida", "transferencia realizada"):
                        current_row = {"Fecha": fecha_actual, "Referencia": referencia,
                                       "Importe": importe, "Saldo": saldo}
                        row_transferencia = True
                    else:
                        movimientos.append({
                            "Fecha": fecha_actual,
                            "Referencia": referencia,
                            "Importe": importe,
                            "Saldo": saldo
                        })
                        row_transferencia = False
                        current_row = None

                    previous_saldo = saldo
                    continue

                # 3) Detalle de transferencia
                if linea_transferencia_stdr.match(line):
                    if row_transferencia and current_row is not None:
                        movimientos.append({
                            "Fecha": current_row["Fecha"],
                            "Referencia": current_row["Referencia"] + " - " + line,
                            "Importe": current_row["Importe"],
                            "Saldo": current_row["Saldo"]
                        })
                        row_transferencia = False
                        current_row = None

    return pd.DataFrame(movimientos)

# =========================
# HSBC parser (adapted to work in-memory)
# Based on your provided HSBC script’s regex and flow
# =========================
saldo_anterior_hsbc_re = re.compile(
    r"(?i)SALDO\s+ANTERIOR.*?((?:\d{1,3}(?:,\d{3})*|\d*)\.\d{2})$"
)
linea_con_fecha_hsbc = re.compile(
    r"""^(?P<fecha>\d{2}-[A-Z]{3})\s+-\s+
        (?P<referencia>.+?)\s+
        \d{5}\s+
        (?P<debito>(?:\d{1,3}(?:,\d{3})*|\d*)?\.\d{2})?\s*
        (?P<credito>(?:\d{1,3}(?:,\d{3})*|\d*)?\.\d{2})?\s+
        (?P<saldo>(?:\d{1,3}(?:,\d{3})*|\d*)?\.\d{2})
    """, re.VERBOSE
)
linea_sin_fecha_hsbc = re.compile(
    r"""^\s*-\s+
        (?P<referencia>.+?)\s+
        \d{5}\s+
        (?P<debito>(?:\d{1,3}(?:,\d{3})*|\d*)?\.\d{2})?\s*
        (?P<credito>(?:\d{1,3}(?:,\d{3})*|\d*)?\.\d{2})?\s+
        (?P<saldo>(?:\d{1,3}(?:,\d{3})*|\d*)?\.\d{2})
    """, re.VERBOSE
)

def parse_hsbc_pdf(file_like) -> pd.DataFrame:
    movimientos = []
    fecha_actual = None
    previous_saldo = None
    saldo_anterior_registrado = False

    with pdfplumber.open(file_like) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for raw in text.splitlines():
                line = raw.strip()

                # 1) SALDO ANTERIOR
                if not saldo_anterior_registrado:
                    m_saldo = saldo_anterior_hsbc_re.search(line)
                    if m_saldo:
                        saldo_inicial = _to_float_money_us(m_saldo.group(1))
                        movimientos.append({
                            "Fecha": "",
                            "Referencia": "SALDO ANTERIOR",
                            "Importe": "",
                            "Saldo": saldo_inicial
                        })
                        previous_saldo = saldo_inicial
                        saldo_anterior_registrado = True
                        continue

                # 2) Línea con fecha
                m_fecha = linea_con_fecha_hsbc.match(line)
                if m_fecha:
                    fecha_actual = m_fecha.group("fecha")
                    referencia = (m_fecha.group("referencia") or "").strip()
                    saldo = _to_float_money_us(m_fecha.group("saldo"))
                    # Importe por diferencia de saldos (como en tu script)
                    importe = round(saldo - previous_saldo, 2) if previous_saldo is not None else 0.0

                    movimientos.append({
                        "Fecha": fecha_actual,
                        "Referencia": referencia,
                        "Importe": importe,
                        "Saldo": saldo
                    })
                    previous_saldo = saldo
                    continue

                # 3) Línea sin fecha (hereda fecha_actual)
                m_sf = linea_sin_fecha_hsbc.match(line)
                if m_sf and fecha_actual:
                    referencia = (m_sf.group("referencia") or "").strip()
                    saldo = _to_float_money_us(m_sf.group("saldo"))
                    importe = round(saldo - previous_saldo, 2) if previous_saldo is not None else 0.0

                    movimientos.append({
                        "Fecha": fecha_actual,
                        "Referencia": referencia,
                        "Importe": importe,
                        "Saldo": saldo
                    })
                    previous_saldo = saldo

    return pd.DataFrame(movimientos)

# =========================
# Shared helpers (continued)
# =========================
def build_summary(df_movs: pd.DataFrame) -> pd.DataFrame:
    if df_movs.empty:
        return pd.DataFrame(columns=["Referencia", "Sum_Importe", "Cantidad", "Pct_Importe", "Pct_Cantidad"])

    # ignore "Saldo Inicial" rows explicitly
    df_work = df_movs[df_movs["Referencia"] != "Saldo Inicial"].copy()
    df_work["Importe"] = pd.to_numeric(df_work["Importe"], errors="coerce")

    summary = df_work.groupby("Referencia", dropna=False).agg(
        Sum_Importe=("Importe", "sum"),
        Cantidad=("Referencia", "count")
    ).reset_index()

    total_abs = summary["Sum_Importe"].abs().sum()
    summary["Pct_Importe"] = (summary["Sum_Importe"].abs() / total_abs * 100).round(4) if total_abs else 0.0
    summary["Pct_Cantidad"] = (summary["Cantidad"] / summary["Cantidad"].sum() * 100).round(4)

    total_row = {
        "Referencia": "TOTAL",
        "Sum_Importe": summary["Sum_Importe"].sum(),
        "Cantidad": summary["Cantidad"].sum(),
        "Pct_Importe": summary["Pct_Importe"].sum(),
        "Pct_Cantidad": summary["Pct_Cantidad"].sum(),
    }
    return pd.concat([summary, pd.DataFrame([total_row])], ignore_index=True)

def to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False, encoding="utf-8")
    return buf.getvalue().encode("utf-8")

# =========================
# Streamlit UI
# =========================
st.set_page_config(page_title="OCR Extract PDF (Santander / HSBC)", page_icon="🏦", layout="wide")
st.title("🏦 Extractor de Movimientos desde PDF")

# Sidebar menu
choice = st.sidebar.radio(
    "Elegí el banco",
    ["Santander OCR Extract", "HSBC OCR Extract"],
    index=0
)

st.markdown(
    "Subí tu PDF y descargá los resultados en CSV: **Detalle de movimientos** y **Resumen por referencia**."
)

uploaded = st.file_uploader("Elegí el extracto bancario (PDF)", type=["pdf"])

if uploaded is not None:
    base_name = uploaded.name.rsplit(".pdf", 1)[0]
    ts = datetime.now().strftime("%Y%m%d_%H%M")

    with st.spinner(f"Procesando PDF con {choice}..."):
        if choice == "Santander OCR Extract":
            df_movs = parse_santander_pdf(uploaded)
        else:
            df_movs = parse_hsbc_pdf(uploaded)

        if df_movs.empty:
            st.error("No se detectaron movimientos en el PDF.")
        else:
            df_summary = build_summary(df_movs)

            # Previews
            colA, colB = st.columns(2)
            with colA:
                st.subheader("Detalle de Movimientos (preview)")
                st.dataframe(df_movs.head(30), use_container_width=True)
            with colB:
                st.subheader("Resumen por Referencia")
                st.dataframe(df_summary, use_container_width=True)

            # Downloads
            detalle_filename = f"{base_name}_{'STDR' if choice.startswith('Santander') else 'HSBC'}_Detalle_Movimientos_{ts}.csv"
            resumen_filename = f"{base_name}_{'STDR' if choice.startswith('Santander') else 'HSBC'}_Resumen_Referencias_{ts}.csv"

            dcol1, dcol2 = st.columns(2)
            with dcol1:
                st.download_button(
                    label="⬇️ Descargar Detalle de Movimientos (CSV)",
                    data=to_csv_bytes(df_movs),
                    file_name=detalle_filename,
                    mime="text/csv"
                )
            with dcol2:
                st.download_button(
                    label="⬇️ Descargar Resumen por Referencia (CSV)",
                    data=to_csv_bytes(df_summary),
                    file_name=resumen_filename,
                    mime="text/csv"
                )

            # KPIs
            try:
                saldo_inicial = float(df_movs["Saldo"].iloc[0])
                total_movs = pd.to_numeric(df_movs.iloc[1:]["Importe"], errors="coerce").sum()
                saldo_final = float(df_movs["Saldo"].iloc[-1])

                st.markdown("### Resumen")
                k1, k2, k3 = st.columns(3)
                k1.metric("Saldo Inicial", f"{saldo_inicial:,.2f}")
                k2.metric("Total Movimientos", f"{total_movs:,.2f}")
                k3.metric("Saldo Final", f"{saldo_final:,.2f}")
            except Exception:
                pass
else:
    st.info("Subí un PDF para comenzar.")
