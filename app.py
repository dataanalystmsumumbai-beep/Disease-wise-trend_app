import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="IHIP Smart Dashboard", layout="wide")

st.title("📊 IHIP Dynamic Dashboard")

# ---------------- INPUT ----------------
st.sidebar.header("🔗 Data Source")

sheet_url = st.sidebar.text_input("Google Sheet URL")

uploaded_file = st.sidebar.file_uploader("Or Upload Excel", type=["xlsx"])

# ---------------- LOAD DATA ----------------
@st.cache_data
def load_gsheet(url):
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=url)
    return {"Sheet1": df}

@st.cache_data
def load_excel(file):
    xls = pd.ExcelFile(file)
    data = {}
    for sheet in xls.sheet_names:
        data[sheet] = pd.read_excel(file, sheet_name=sheet)
    return data

data_dict = {}

if sheet_url:
    try:
        data_dict = load_gsheet(sheet_url)
    except:
        st.error("Google Sheet load failed")

if uploaded_file:
    data_dict = load_excel(uploaded_file)

# ---------------- FUNCTION ----------------
def process_data(df):
    df = df.copy()

    numeric_cols = df.select_dtypes(include="number").columns
    df[numeric_cols] = df[numeric_cols].fillna(0)

    # Melt for easier analysis
    if "Ward" in df.columns:
        df_melt = df.melt(id_vars=["Ward"], var_name="Month_Week", value_name="Value")

        df_melt["Month"] = df_melt["Month_Week"].str.extract(r'([A-Za-z]+)')
        df_melt["Week"] = df_melt["Month_Week"].str.extract(r'(Week\s*\d+)')

        return df_melt

    return df

def create_excel(data_dict):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, df in data_dict.items():
            df.to_excel(writer, sheet_name=name, index=False)

    return output.getvalue()

# ---------------- MAIN ----------------
if data_dict:

    tab_names = list(data_dict.keys())
    tabs = st.tabs(tab_names)

    final_export = {}

    for i, tab in enumerate(tabs):
        with tab:
            st.subheader(f"📄 {tab_names[i]}")

            df = data_dict[tab_names[i]]

            if df.empty:
                st.warning("No data")
                continue

            st.dataframe(df, use_container_width=True)

            # ---------------- PROCESS ----------------
            df_proc = process_data(df)

            if "Ward" in df_proc.columns:
                # FILTERS
                wards = df_proc["Ward"].unique()
                months = df_proc["Month"].dropna().unique()

                col1, col2 = st.columns(2)

                with col1:
                    selected_ward = st.multiselect("Select Ward", wards, default=wards)

                with col2:
                    selected_month = st.multiselect("Select Month", months, default=months)

                df_filt = df_proc[
                    (df_proc["Ward"].isin(selected_ward)) &
                    (df_proc["Month"].isin(selected_month))
                ]

                # ---------------- CHART ----------------
                st.markdown("### 📊 Trend Chart")
                fig = px.line(df_filt, x="Month", y="Value", color="Ward", markers=True)
                st.plotly_chart(fig, use_container_width=True)

                # ---------------- ANALYSIS ----------------
                st.markdown("### 📈 Month Comparison")

                pivot = df_filt.pivot_table(index="Ward", columns="Month", values="Value", aggfunc="sum")

                if len(pivot.columns) >= 2:
                    last_two = pivot.columns[-2:]

                    pivot["Change"] = pivot[last_two[1]] - pivot[last_two[0]]
                    pivot["% Change"] = (pivot["Change"] / pivot[last_two[0]].replace(0,1)) * 100

                st.dataframe(pivot, use_container_width=True)

                final_export[tab_names[i]] = pivot

            else:
                final_export[tab_names[i]] = df

    # ---------------- DOWNLOAD ----------------
    st.markdown("---")
    st.markdown("## 📥 Download")

    excel_file = create_excel(final_export)

    st.download_button(
        label="⬇ Download Full Excel Report",
        data=excel_file,
        file_name="IHIP_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("Enter Google Sheet link OR upload file")
