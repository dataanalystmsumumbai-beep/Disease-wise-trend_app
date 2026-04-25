import streamlit as st
import pandas as pd

st.set_page_config(page_title="Disease Trend App", layout="wide")

st.title("Disease-wise Trend Analysis")

# Your Google Sheet base link
DEFAULT_GSHEET_URL = "https://docs.google.com/spreadsheets/d/11-ZeoBvixvY_ujLO8_9Vlze2jmGC4CooTWjvd2INX-4/edit"

def get_xlsx_url(url):
    if "/edit" in url:
        return url.split('/edit')[0] + "/export?format=xlsx"
    return url

st.subheader("Select Data Source")
source_option = st.radio(
    "Choose how you want to load the data:",
    ("Use Default Google Sheet", "Paste a New Google Sheet Link")
)

target_url = ""
if source_option == "Use Default Google Sheet":
    target_url = get_xlsx_url(DEFAULT_GSHEET_URL)
else:
    user_url = st.text_input("Paste your Google Sheet link here:", "")
    if user_url:
        target_url = get_xlsx_url(user_url)

if target_url:
    try:
        with st.spinner('Reading all sheets and creating tabs...'):
            # Load the entire Excel file
            excel_file = pd.ExcelFile(target_url, engine='openpyxl')
            sheet_names = excel_file.sheet_names
            
            if sheet_names:
                # Creating dynamic tabs based on sheet names
                tabs = st.tabs(sheet_names)
                
                for i, sheet_name in enumerate(sheet_names):
                    with tabs[i]:
                        st.subheader(f"Data from Sheet: {sheet_name}")
                        # Reading individual sheet data
                        df = pd.read_excel(target_url, sheet_name=sheet_name)
                        st.dataframe(df, use_container_width=True)
            else:
                st.warning("No sheets found in the linked Google Sheet.")
                
    except Exception as e:
        st.error(f"Error: {e}")
        st.info("Ensure the Google Sheet is shared as 'Anyone with the link can view'.")
