import streamlit as st
import pdfplumber
import pandas as pd
import re
import io
from datetime import datetime

# -------------------------
# Logic adapted from your script (no global side-effects)
# -------------------------

saldo_anterior_regex = re.compile(r"Saldo\s+Inicial\s+(-?\$\s*[\d\.\,]+)")

linea_movimiento = re.compile(
    r"""^
    (?P<fecha>\d{2}/\d{2}/\d{2})?     # Fecha opcional
    \s*
    (?:\d+\s+)?                       # Comprobante opcional (número), ignorado
    (?P<movimiento>.*?)               # Movimiento (texto)
    \s+
    (?:
        (?P<debito>-?\$\s*[\d\.\,]+)   # Débito
        \s+
        (?P<saldo>-?\$\s*[\d\.\,]+)    # Saldo si no hay crédito
      |
        (?P<credito>-?\$\s*[\d\.\,]+)  # Crédito
        \s+
        (?P<saldo2>-?\$\s*[\d\.\,]+)   # Saldo si no hay débito
    )
    $""",
    re.VERBOSE
)

linea_transferencia = re.compile(
    r'^(?:De|A)(?:\s+[A-Za-zÁÉÍÓÚÑáéíóúñ\s,.]+)?\s*/\s*(?:transf|varios)\s*-\s*var\s*/.*$',
    re.IGNORECASE
)

def _clean_money(raw: str) -> float:
    return float(
        raw.replace("$", "").replace(".", "").replace(",", ".").replace(" ", "").strip()
    )

def parse_pdf_to_movimientos(file_like) -> pd.DataFrame:
    """Replicates the core parsing logic, returning the movimientos DataFrame."""
    movimientos = []
    fecha_actual = None
    previous_saldo = None
    saldo_anterior_registrado = False
    row_transferencia = False

    with pdfplumber.open(file_like) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in (l.strip() for l in text.splitlines()):
                # 1) Saldo Inicial
                if not saldo_anterior_registrado:
                    m_saldo = saldo_anterior_regex.search(line)
                    if m_saldo:
                        saldo_inicial = _clean_money(m_saldo.group(1))
                        movimientos.append({
                            "Fecha": "",
                            "Referencia": "Saldo Inicial",
                            "Importe": "",
                            "Saldo": saldo_inicial
                        })
                        previous_saldo = saldo_inicial
                        saldo_anterior_registrado = True
                        continue

                # 2) Línea de movimiento (fecha opcional)
                m = linea_movimiento.match(line)
                if m:
                    fecha = m.group("fecha")
                    if fecha:
                        fecha_actual = fecha
                        fecha_anterior = fecha
                    else:
                        # hereda última fecha válida
                        fecha_actual = locals().get("fecha_anterior", None)

                    referencia = (m.group("movimiento") or "").strip()

                    raw_imp = m.group("debito") or m.group("credito")
                    importe = _clean_money(raw_imp)
                    # Si es débito, importe negativo
                    if m.group("debito"):
                        importe = -1.0 * importe

                    raw_saldo = m.group("saldo") or m.group("saldo2")
                    saldo = _clean_money(raw_saldo)

                    # Ajuste según diferencia de saldo (tu control de integridad)
                    if previous_saldo is not None and (saldo - previous_saldo) > 0:
                        importe = -importe  # invierte signo si sube el saldo
                        # (Se omite logging detallado en UI)

                    # Si es encabezado de transferencia, marcar bandera para esperar detalle
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

                # 3) Línea de detalle de transferencia (si corresponde)
                if linea_transferencia.match(line):
                    if row_transferencia and previous_saldo is not None and current_row is not None:
                        movimientos.append({
                            "Fecha": current_row["Fecha"],
                            "Referencia": current_row["Referencia"] + " - " + line,
                            "Importe": current_row["Importe"],
                            "Saldo": current_row["Saldo"]
                        })
                        row_transferencia = False

    return pd.DataFrame(movimientos)

def build_summary(df_movs: pd.DataFrame) -> pd.DataFrame:
    """Creates the resumen por referencia, with totals row, like your script."""
    if df_movs.empty:
        return pd.DataFrame(columns=["Referencia", "Sum_Importe", "Cantidad", "Pct_Importe", "Pct_Cantidad"])

    # ignorar primera fila (Saldo Inicial)
    df_work = df_movs.iloc[1:].copy()
    df_work["Importe"] = pd.to_numeric(df_work["Importe"], errors="coerce")

    summary = df_work.groupby("Referencia").agg(
        Sum_Importe=("Importe", "sum"),
        Cantidad=("Referencia", "count")
    ).reset_index()

    if summary["Sum_Importe"].abs().sum() == 0:
        summary["Pct_Importe"] = 0.0
    else:
        summary["Pct_Importe"] = ((summary["Sum_Importe"].abs() / summary["Sum_Importe"].abs().sum()) * 100).round(4)

    summary["Pct_Cantidad"] = ((summary["Cantidad"] / summary["Cantidad"].sum()) * 100).round(4)

    total_row = {
        "Referencia": "TOTAL",
        "Sum_Importe": summary["Sum_Importe"].sum(),
        "Cantidad": summary["Cantidad"].sum(),
        "Pct_Importe": summary["Pct_Importe"].sum(),
        "Pct_Cantidad": summary["Pct_Cantidad"].sum()
    }
    summary = pd.concat([summary, pd.DataFrame([total_row])], ignore_index=True)
    return summary

def to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False, encoding="utf-8")
    return buf.getvalue().encode("utf-8")


# -------------------------
# Streamlit UI
# -------------------------

st.set_page_config(page_title="Extractor de Movimientos PDF", page_icon="📄")
st.title("📄 Extractor de Movimientos desde PDF (Santander / similar)")

st.write("Subí tu archivo PDF, lo procesamos y podés descargar:")
st.markdown("- **Detalle de movimientos**")
st.markdown("- **Resumen por referencia**")

uploaded = st.file_uploader("Elegí un extracto bancario en PDF", type=["pdf"])

if uploaded is not None:
    base_name = uploaded.name.rsplit(".pdf", 1)[0]
    ts = datetime.now().strftime("%Y%m%d_%H%M")

    with st.spinner("Procesando PDF..."):
        df_movs = parse_pdf_to_movimientos(uploaded)
        if df_movs.empty:
            st.error("No se detectaron movimientos en el PDF.")
        else:
            # Mostrar previews
            st.subheader("Vista previa: Detalle de Movimientos")
            st.dataframe(df_movs.head(30), use_container_width=True)

            df_summary = build_summary(df_movs)
            st.subheader("Vista previa: Resumen por Referencia")
            st.dataframe(df_summary, use_container_width=True)

            # Botones de descarga (mismos nombres que tu script, con timestamp)
            detalle_filename = f"{base_name}_Detalle_Movimientos_{ts}.csv"
            resumen_filename = f"{base_name}_Resumen_Referencias_{ts}.csv"

            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="⬇️ Descargar Detalle de Movimientos (CSV)",
                    data=to_csv_bytes(df_movs),
                    file_name=detalle_filename,
                    mime="text/csv"
                )
            with col2:
                st.download_button(
                    label="⬇️ Descargar Resumen por Referencia (CSV)",
                    data=to_csv_bytes(df_summary),
                    file_name=resumen_filename,
                    mime="text/csv"
                )

            # (Opcional) KPIs rápidos (como tu resumen de consola)
            try:
                saldo_inicial = float(df_movs["Saldo"].iloc[0])
                total_movs = pd.to_numeric(df_movs.iloc[1:]["Importe"], errors="coerce").sum()
                saldo_final = float(df_movs["Saldo"].iloc[-1])

                st.markdown("### Resumen")
                st.metric("Saldo Inicial", f"{saldo_inicial:,.2f}")
                st.metric("Total Movimientos", f"{total_movs:,.2f}")
                st.metric("Saldo Final", f"{saldo_final:,.2f}")
            except Exception:
                pass
