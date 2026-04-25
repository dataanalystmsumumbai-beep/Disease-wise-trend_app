import streamlit as st
import pandas as pd

st.set_page_config(page_title="Disease Trend App", layout="wide")

st.title("Disease-wise Trend Analysis")

# Default Google Sheet link provided by you
DEFAULT_GSHEET_URL = "https://docs.google.com/spreadsheets/d/11-ZeoBvixvY_ujLO8_9Vlze2jmGC4CooTWjvd2INX-4/edit?gid=1214285155#gid=1214285155"

# Function to convert sharing link to export link
def get_export_url(url):
    if "/edit" in url:
        return url.replace("/edit", "/export?format=csv")
    return url

# Step 1: User Selection for Data Source
st.subheader("Select Data Source")
source_option = st.radio(
    "Choose how you want to load the data:",
    ("Use Default Google Sheet", "Paste a New Google Sheet Link")
)

target_url = ""

if source_option == "Use Default Google Sheet":
    target_url = get_export_url(DEFAULT_GSHEET_URL)
    st.info("Using the predefined Google Sheet link.")
else:
    user_url = st.text_input("Paste your Google Sheet link here:", "")
    if user_url:
        target_url = get_export_url(user_url)

# Step 2: Read and Display Data
if target_url:
    try:
        # Reading the CSV data from Google Sheets
        df = pd.read_csv(target_url)
        
        st.success("Data loaded successfully!")
        st.subheader("Data Preview")
        st.dataframe(df)
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.info("Make sure the Google Sheet is shared as 'Anyone with the link can view'.")
