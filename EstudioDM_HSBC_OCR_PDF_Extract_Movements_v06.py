# ===============================================================================
#  Script Name:        EstudioDM_HSBC_OCR_PDF_Extract_Movements_v05.py
#  Author:             Mariano Duran
#  Created Date:       01-08-2025
#  Last Modified:      01-08-2025
#  Python Version:     0.06
# ===============================================================================
#  Description:
#   This script parses a bank statement PDF, detects "SALDO ANTERIOR", extracts 
#   movements, calculates importes based on saldo differences, and exports results 
#   to a CSV file.
#
#  Usage:
#   python extract_movements_from_pdf.py --input Extracto.pdf --output movimientos.csv
#
#  Parameters:
#   --input     Path to the input PDF file
#   --output    Path to save the extracted CSV file
#
#  Dependencies:
#   - pdfplumber
#   - pandas
#   - re (Python built-in)
#
#  Notes:
#   Assumes that the PDF layout follows a specific bank format where "SALDO ANTERIOR" 
#   is present and transactions are listed with prefixes and saldo at line end.
#
#  Que hace?
#   📄 Lee un extracto bancario PDF (02_Extracto_PDF.pdf) usando pdfplumber
#   🔍 Detecta explícitamente la línea que contiene "SALDO ANTERIOR" y extrae su valor real
#   🧮 Calcula el campo Importe como la diferencia entre el saldo actual y el anterior
#   ✅ Procesa correctamente:
#       Líneas con fecha
#       Líneas sin fecha (heredando la última fecha válida)
#   📤 Exporta a 05_movimientos_con_saldo_anterior_detectado.csv
#
#  Change control history:
#     - 01-08-2025:  v0.05 Initial creation of script
#     - 02-08-2025:  v0.06 Addes summary table
# ===============================================================================

import pdfplumber
import re
import pandas as pd
import logging
import os
import platform, psutil
import sys
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("process.log"),
        logging.StreamHandler()
    ]
)

# Inicialización
pdf_path = "02_Extracto_PDF.pdf"  # asegurate de que el archivo esté en la misma carpeta


movimientos = []
fecha_actual = None
previous_saldo = None
saldo_anterior_registrado = False

def summary(df):
    # Supongamos que ya tienes tu DataFrame cargado en "df" con las columnas:
    # 'Fecha', 'Referencia', 'Importe', 'Saldo'

    # Ignorar la primera línea (SALDO ANTERIOR o primera fila siempre)
    df_work = df.iloc[1:].copy()

    # Asegurar que Importe es tipo float
    df_work['Importe'] = pd.to_numeric(df_work['Importe'], errors='coerce')

    # Agrupar por Referencia
    summary = df_work.groupby('Referencia').agg(
        Sum_Importe=('Importe', 'sum'),
        Cantidad=('Referencia', 'count')
    ).reset_index()

    # Calcular porcentajes sobre valores absolutos de Sum_Importe
    summary['Pct_Importe'] = ((summary['Sum_Importe'].abs() / summary['Sum_Importe'].abs().sum()) * 100).round(2)

    # Calcular porcentaje de cantidad de ocurrencias
    summary['Pct_Cantidad'] = ((summary['Cantidad'] / summary['Cantidad'].sum()) * 100).round(2)

    # Mostrar el resultado
    total_row = {
    'Referencia': 'TOTAL',
    'Sum_Importe': summary['Sum_Importe'].sum(),
    'Cantidad': summary['Cantidad'].sum(),
    'Pct_Importe': summary['Pct_Importe'].sum(),
    'Pct_Cantidad': summary['Pct_Cantidad'].sum()
    }
    # Append total row to the DataFrame
    summary = pd.concat([summary, pd.DataFrame([total_row])], ignore_index=True)
    # Print summary with totals
    print(summary)

    # Calculate summary values
    saldo_inicial = df['Saldo'].iloc[0]
    total_movimientos = (df_work['Importe'].sum()).round(2)
    saldo_final = df_work['Saldo'].iloc[-1]
    
    fsaldo_inicial = f"{saldo_inicial:>18.2f}"
    ftotal_movimientos = f"{total_movimientos:>18.2f}"
    fsaldo_final = f"{saldo_final:>18.2f}"

    # Print summary
    print("="*96)
    print("Saldo Inicial     :", fsaldo_inicial)
    print("Total Movimientos :", ftotal_movimientos)
    print("Saldo Final       :", fsaldo_final)
    print("="*96)
    
    #Opcional: exportar a CSV
    summary.to_csv("05_Resumen_Referencias.csv", index=False)

####################################################
# Inicio programa
####################################################
# Iniciar timer
logging.info(f"---------------------------------------")
start_time = datetime.now()

print("="*30, "Evaluation Environment Information", "="*30)
print(f'Platform       : {platform.system()}')
print(f'Architecture   : {platform.machine()}')
print(f'Processor      : {platform.processor()}')
print(f'CPU            : {psutil.cpu_count()}')
print(f'Python Version : {sys.version}')
print("="*96)


# Regex para línea explícita de SALDO ANTERIOR
saldo_anterior_regex = re.compile(
    r"(?i)SALDO\s+ANTERIOR.*?((?:\d{1,3}(?:,\d{3})*|\d*)\.\d{2})$"
)

# Regex para línea con fecha + movimiento
linea_con_fecha = re.compile(
    r"""^(?P<fecha>\d{2}-[A-Z]{3})\s+-\s+
        (?P<referencia>.+?)\s+
        \d{5}\s+
        (?P<debito>(?:\d{1,3}(?:,\d{3})*|\d*)?\.\d{2})?\s*
        (?P<credito>(?:\d{1,3}(?:,\d{3})*|\d*)?\.\d{2})?\s+
        (?P<saldo>(?:\d{1,3}(?:,\d{3})*|\d*)?\.\d{2})
    """, re.VERBOSE
)

# Regex para línea sin fecha
linea_sin_fecha = re.compile(
    r"""^\s*-\s+
        (?P<referencia>.+?)\s+
        \d{5}\s+
        (?P<debito>(?:\d{1,3}(?:,\d{3})*|\d*)?\.\d{2})?\s*
        (?P<credito>(?:\d{1,3}(?:,\d{3})*|\d*)?\.\d{2})?\s+
        (?P<saldo>(?:\d{1,3}(?:,\d{3})*|\d*)?\.\d{2})
    """, re.VERBOSE
)

# Procesamiento del PDF
with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        lines = page.extract_text().splitlines()
        for line in lines:
            line = line.strip()

            # 1. Detectar línea SALDO ANTERIOR
            if not saldo_anterior_registrado:
                match_saldo = saldo_anterior_regex.search(line)
                if match_saldo:
                    saldo_inicial = float(match_saldo.group(1).replace(",", ""))
                    movimientos.append({
                        "Fecha": "",
                        "Referencia": "SALDO ANTERIOR",
                        "Importe": "",
                        "Saldo": saldo_inicial
                    })
                    previous_saldo = saldo_inicial
                    saldo_anterior_registrado = True
                    continue  # no procesar esta línea como movimiento

            # 2. Línea con fecha
            match_con_fecha = linea_con_fecha.match(line)
            if match_con_fecha:
                fecha_actual = match_con_fecha.group("fecha")
                referencia = match_con_fecha.group("referencia").strip()
                saldo = float(match_con_fecha.group("saldo").replace(",", ""))
                importe = round(saldo - previous_saldo, 2)

                movimientos.append({
                    "Fecha": fecha_actual,
                    "Referencia": referencia,
                    "Importe": importe,
                    "Saldo": saldo
                })
                previous_saldo = saldo
                continue

            # 3. Línea sin fecha
            match_sin_fecha = linea_sin_fecha.match(line)
            if match_sin_fecha and fecha_actual:
                referencia = match_sin_fecha.group("referencia").strip()
                saldo = float(match_sin_fecha.group("saldo").replace(",", ""))
                importe = round(saldo - previous_saldo, 2)

                movimientos.append({
                    "Fecha": fecha_actual,
                    "Referencia": referencia,
                    "Importe": importe,
                    "Saldo": saldo
                })
                previous_saldo = saldo

# Exportar a CSV
df = pd.DataFrame(movimientos)
summary (df)
output_path = "05_Detalle_movimientos.csv"
df.to_csv(output_path, index=False, encoding="utf-8")
print(f"✅ Archivo generado: {output_path}")

end_time = datetime.now()
elapsed = end_time - start_time

logging.info(f"---------------------------------------")
logging.info(f"Process finished")
logging.info(f"Start Time  : {start_time}")
logging.info(f"End Time    : {end_time}")
logging.info(f"Elapsed Time: {elapsed}")
logging.info(f"---------------------------------------")
