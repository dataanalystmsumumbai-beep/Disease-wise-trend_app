import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Google Sheet Dynamic App", layout="wide")

st.title("📊 Google Sheet Dynamic Dashboard")

# ---------------- INPUT ----------------
sheet_url = st.text_input(
    "Enter Google Sheet URL",
    value="https://docs.google.com/spreadsheets/d/11-ZeoBvixvY_ujLO8_9Vlze2jmGC4CooTWjvd2INX-4/edit#gid=0"
)

# ---------------- CONNECTION ----------------
@st.cache_resource
def connect_gsheet():
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]

    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "credentials.json", scope
    )
    client = gspread.authorize(creds)
    return client

# ---------------- READ DATA ----------------
def load_all_sheets(url):
    client = connect_gsheet()
    sh = client.open_by_url(url)

    worksheets = sh.worksheets()

    data_dict = {}

    for ws in worksheets:
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        data_dict[ws.title] = df

    return data_dict

# ---------------- MAIN ----------------
if sheet_url:
    try:
        data_dict = load_all_sheets(sheet_url)

        tab_names = list(data_dict.keys())
        tabs = st.tabs(tab_names)

        for i, tab in enumerate(tabs):
            with tab:
                st.subheader(f"📄 {tab_names[i]}")

                df = data_dict[tab_names[i]]

                if df.empty:
                    st.warning("No data available")
                else:
                    st.dataframe(df, use_container_width=True)

                    # Basic Summary
                    st.markdown("### Summary")
                    st.write(df.describe())

    except Exception as e:
        st.error(f"Error: {e}")
