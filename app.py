import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="IHIP Smart Dashboard", layout="wide")

st.title("📊 IHIP Dynamic Dashboard")

# ---------------- SIDEBAR ----------------
st.sidebar.header("🔗 Data Source")

sheet_url = st.sidebar.text_input("Google Sheet URL")

uploaded_file = st.sidebar.file_uploader("Or Upload Excel", type=["xlsx"])

# ---------------- LOAD FUNCTIONS ----------------
@st.cache_data
def load_gsheet(url):
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=url)
    return {"GoogleSheet": df}

@st.cache_data
def load_excel(file):
    xls = pd.ExcelFile(file)
    data = {}
    for sheet in xls.sheet_names:
        data[sheet] = pd.read_excel(file, sheet_name=sheet)
    return data

# ---------------- PROCESS FUNCTION ----------------
def process_data(df):
    df = df.copy()

    numeric_cols = df.select_dtypes(include="number").columns
    df[numeric_cols] = df[numeric_cols].fillna(0)

    if "Ward" in df.columns:
        df_melt = df.melt(id_vars=["Ward"], var_name="Month_Week", value_name="Value")

        df_melt["Month"] = df_melt["Month_Week"].str.extract(r'([A-Za-z]+)')
        df_melt["Week"] = df_melt["Month_Week"].str.extract(r'(Week\s*\d+)')

        return df_melt

    return df

# ---------------- EXCEL EXPORT ----------------
def create_excel(data_dict):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, df in data_dict.items():
            df.to_excel(writer, sheet_name=name, index=False)

    return output.getvalue()

# ---------------- LOAD DATA ----------------
data_dict = {}

if sheet_url:
    try:
        data_dict = load_gsheet(sheet_url)
    except:
        st.error("❌ Google Sheet load failed")

if uploaded_file:
    data_dict = load_excel(uploaded_file)

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
                st.warning("No data available")
                continue

            st.dataframe(df, use_container_width=True)

            df_proc = process_data(df)

            if "Ward" in df_proc.columns:

                # ---------------- FILTERS ----------------
                wards = df_proc["Ward"].dropna().unique()
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

                # ---------------- MONTH COMPARISON ----------------
                st.markdown("### 📊 Month Comparison")

                pivot = df_filt.pivot_table(
                    index="Ward",
                    columns="Month",
                    values="Value",
                    aggfunc="sum"
                ).fillna(0)

                months_list = list(pivot.columns)

                if len(months_list) >= 2:
                    m1, m2 = months_list[-2], months_list[-1]

                    compare_df = pivot[[m1, m2]].reset_index()

                    fig1 = px.bar(
                        compare_df,
                        x="Ward",
                        y=[m1, m2],
                        barmode="group",
                        title=f"{m1} vs {m2}"
                    )

                    st.plotly_chart(fig1, use_container_width=True)

                    # % Change
                    compare_df["% Change"] = (
                        (compare_df[m2] - compare_df[m1]) /
                        compare_df[m1].replace(0, 1)
                    ) * 100

                    st.markdown("### 📈 % Increase / Decrease")

                    fig2 = px.bar(
                        compare_df,
                        x="Ward",
                        y="% Change",
                        title="% Change"
                    )

                    st.plotly_chart(fig2, use_container_width=True)

                    final_export[tab_names[i]] = compare_df

                # ---------------- WEEK COMPARISON ----------------
                st.markdown("### 📅 Week Comparison")

                week_pivot = df_filt.pivot_table(
                    index="Ward",
                    columns="Week",
                    values="Value",
                    aggfunc="sum"
                ).fillna(0)

                weeks_list = list(week_pivot.columns)

                if len(weeks_list) >= 2:
                    w1, w2 = weeks_list[-2], weeks_list[-1]

                    week_compare = week_pivot[[w1, w2]].reset_index()

                    fig3 = px.bar(
                        week_compare,
                        x="Ward",
                        y=[w1, w2],
                        barmode="group",
                        title=f"{w1} vs {w2}"
                    )

                    st.plotly_chart(fig3, use_container_width=True)

            else:
                final_export[tab_names[i]] = df

    # ---------------- DOWNLOAD ----------------
    st.markdown("---")
    st.markdown("## 📥 Download Report")

    excel_file = create_excel(final_export)

    st.download_button(
        label="⬇ Download Excel Report",
        data=excel_file,
        file_name="IHIP_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("👉 Enter Google Sheet link OR upload Excel file")
