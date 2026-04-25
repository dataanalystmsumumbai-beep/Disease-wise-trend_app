import streamlit as st
import pandas as pd

st.set_page_config(page_title="Disease Trend App", layout="wide")

st.title("Disease-wise Trend Analysis")

# Your specific Google Sheet link
DEFAULT_GSHEET_URL = "https://docs.google.com/spreadsheets/d/11-ZeoBvixvY_ujLO8_9Vlze2jmGC4CooTWjvd2INX-4/edit?gid=1214285155#gid=1214285155"

def get_export_url(url):
    try:
        # Handling the gid for specific sheets
        base_url = url.split('/edit')[0]
        if 'gid=' in url:
            gid = url.split('gid=')[1].split('#')[0]
            return f"{base_url}/export?format=csv&gid={gid}"
        return f"{base_url}/export?format=csv"
    except:
        return url

st.subheader("Select Data Source")
source_option = st.radio(
    "Choose how you want to load the data:",
    ("Use Default Google Sheet", "Paste a New Google Sheet Link")
)

target_url = ""
if source_option == "Use Default Google Sheet":
    target_url = get_export_url(DEFAULT_GSHEET_URL)
else:
    user_url = st.text_input("Paste your Google Sheet link here:", "")
    if user_url:
        target_url = get_export_url(user_url)

if target_url:
    try:
        # Adding a loading spinner
        with st.spinner('Loading data from Google Sheets...'):
            df = pd.read_csv(target_url)
            
            st.success("Data loaded successfully!")
            st.subheader("Data Preview")
            # Displaying the file name/info if needed
            st.write(f"Displaying data from selected sheet.")
            st.dataframe(df)
            
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.warning("Please ensure the Google Sheet is shared as 'Anyone with the link can view'.")
        st.info("Check if the link is correct and contains /edit or gid.")
