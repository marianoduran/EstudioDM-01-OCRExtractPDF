# ===============================================================================
#  Script Name:        App.py
#  Author:             Mariano Duran
#  Created Date:       01-08-2025
#  Last Modified:      01-08-2025
#  Python Version:     1.00
# ===============================================================================
#  Description:
#   Home Page
#
#
#  Parameters:
#   --input     None
#   --output    None
#
#  Dependencies:
#   - streamlit
#   - pandas
#   - subprocess
#
#  Notes:
#   
#
#  Change control history:
#     - 01-08-2025:  v1.00 Initial creation of script
#     - DD-MM-YYYY:  
# ===============================================================================

import streamlit as st
import pandas as pd
import subprocess
import os

# Menu
st.sidebar.title("Menu")
option = st.sidebar.selectbox("Choose an option", ["Home", "HSBC PDF 2 CSV"])

if option == "HSBC PDF 2 CSV":
    st.title("HSBC PDF to CSV Converter")

    # File uploader
    uploaded_file = st.file_uploader("Upload HSBC PDF", type=["pdf"])

    # Submit button
    if uploaded_file is not None:
        with open("uploaded_hsbc.pdf", "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success("PDF uploaded successfully!")

        if st.button("Convert to CSV"):
            # Execute Python script
            st.info("Processing...")
            result = subprocess.run(["python", "process_hsbc_pdf.py"], capture_output=True, text=True)

            if result.returncode == 0:
                st.success("Conversion completed!")
                # Load and display CSV result
                if os.path.exists("output.csv"):
                    df = pd.read_csv("output.csv")
                    st.dataframe(df)
                else:
                    st.error("Output CSV not found.")
            else:
                st.error("Error occurred during processing.")
                st.text(result.stderr)
else:
    st.title("Welcome to the HSBC PDF Processing Tool")
