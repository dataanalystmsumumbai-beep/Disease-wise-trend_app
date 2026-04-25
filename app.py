import streamlit as st
import pandas as pd

st.set_page_config(page_title="Disease Trend App", layout="wide")

st.title("Disease-wise Trend Analysis")

# Your Google Sheet base link
DEFAULT_GSHEET_URL = "https://docs.google.com/spreadsheets/d/11-ZeoBvixvY_ujLO8_9Vlze2jmGC4CooTWjvd2INX-4/edit"

def get_xlsx_url(url):
    # Convert edit link to xlsx export link to read all sheets
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
        with st.spinner('Reading all sheets from Google Sheet...'):
            # Load the entire Excel file (all sheets)
            excel_file = pd.ExcelFile(target_url, engine='openpyxl')
            sheet_names = excel_file.sheet_names
            
            st.success(f"Successfully loaded {len(sheet_names)} sheets!")
            
            # Dropdown to select a specific sheet
            selected_sheet = st.selectbox("Select a sheet to view:", sheet_names)
            
            if selected_sheet:
                df = pd.read_excel(target_url, sheet_name=selected_sheet)
                st.subheader(f"Data Preview: {selected_sheet}")
                st.dataframe(df)
                
    except Exception as e:
        st.error(f"Error: {e}")
        st.info("Ensure the Google Sheet is shared as 'Anyone with the link can view'.")
