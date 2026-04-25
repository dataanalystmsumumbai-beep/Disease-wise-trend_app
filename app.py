import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="IHIP Dashboard", layout="wide")

st.title("📊 IHIP Smart Dashboard")

# ---------------- INPUT ----------------
st.sidebar.header("🔗 Google Sheet Setup")

sheet_id = st.sidebar.text_input("Enter Google Sheet ID")

gid_input = st.sidebar.text_area(
    "Enter GIDs (one per line)",
    placeholder="Example:\n0\n123456789\n987654321"
)

uploaded_file = st.sidebar.file_uploader("Or Upload Excel", type=["xlsx"])

# ---------------- LOAD FUNCTIONS ----------------
@st.cache_data
def load_google_tabs(sheet_id, gids):
    data = {}

    for gid in gids:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        try:
            df = pd.read_csv(url)
            data[f"Sheet_{gid}"] = df
        except:
            continue

    return data

@st.cache_data
def load_excel(file):
    xls = pd.ExcelFile(file)
    data = {}
    for sheet in xls.sheet_names:
        data[sheet] = pd.read_excel(file, sheet_name=sheet)
    return data

# ---------------- PROCESS ----------------
def process_data(df):
    df = df.copy()

    if "Ward" not in df.columns:
        return df

    df_melt = df.melt(id_vars=["Ward"], var_name="Month_Week", value_name="Value")

    df_melt["Month"] = df_melt["Month_Week"].str.extract(r'([A-Za-z]+)')
    df_melt["Week"] = df_melt["Month_Week"].str.extract(r'(Week\s*\d+)')

    return df_melt

# ---------------- EXPORT ----------------
def create_excel(data_dict):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, df in data_dict.items():
            df.to_excel(writer, sheet_name=name, index=False)
    return output.getvalue()

# ---------------- LOAD ----------------
data_dict = {}

if sheet_id and gid_input:
    gids = [g.strip() for g in gid_input.split("\n") if g.strip()]
    data_dict = load_google_tabs(sheet_id, gids)

if uploaded_file:
    data_dict = load_excel(uploaded_file)

# ---------------- MAIN ----------------
if data_dict:

    tabs = st.tabs(list(data_dict.keys()))
    final_export = {}

    for i, tab in enumerate(tabs):
        with tab:
            name = list(data_dict.keys())[i]
            df = data_dict[name]

            st.subheader(name)
            st.dataframe(df, use_container_width=True)

            df_proc = process_data(df)

            if "Ward" in df_proc.columns:

                wards = df_proc["Ward"].unique()
                months = df_proc["Month"].dropna().unique()

                col1, col2 = st.columns(2)

                with col1:
                    sel_ward = st.multiselect("Ward", wards, default=wards)

                with col2:
                    sel_month = st.multiselect("Month", months, default=months)

                df_f = df_proc[
                    (df_proc["Ward"].isin(sel_ward)) &
                    (df_proc["Month"].isin(sel_month))
                ]

                # ---------------- MONTH COMP ----------------
                pivot = df_f.pivot_table(index="Ward", columns="Month", values="Value", aggfunc="sum").fillna(0)

                if len(pivot.columns) >= 2:
                    m1, m2 = pivot.columns[-2], pivot.columns[-1]

                    comp = pivot[[m1, m2]].reset_index()

                    st.markdown("### 📊 Month Comparison")
                    st.plotly_chart(
                        px.bar(comp, x="Ward", y=[m1, m2], barmode="group"),
                        use_container_width=True
                    )

                    comp["% Change"] = ((comp[m2] - comp[m1]) / comp[m1].replace(0,1)) * 100

                    st.markdown("### 📈 % Change")
                    st.plotly_chart(
                        px.bar(comp, x="Ward", y="% Change"),
                        use_container_width=True
                    )

                    final_export[name] = comp

                # ---------------- WEEK COMP ----------------
                week_pivot = df_f.pivot_table(index="Ward", columns="Week", values="Value", aggfunc="sum").fillna(0)

                if len(week_pivot.columns) >= 2:
                    w1, w2 = week_pivot.columns[-2], week_pivot.columns[-1]

                    wk = week_pivot[[w1, w2]].reset_index()

                    st.markdown("### 📅 Week Comparison")
                    st.plotly_chart(
                        px.bar(wk, x="Ward", y=[w1, w2], barmode="group"),
                        use_container_width=True
                    )

            else:
                final_export[name] = df

    # ---------------- DOWNLOAD ----------------
    st.markdown("## 📥 Download")

    st.download_button(
        "Download Excel",
        data=create_excel(final_export),
        file_name="IHIP_Report.xlsx"
    )

else:
    st.info("Enter Sheet ID + GIDs OR upload Excel")
