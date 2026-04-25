import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="Disease Trend App", layout="wide")

st.title("Disease-wise Trend Analysis")

# ---------------- GOOGLE SHEET ----------------
DEFAULT_GSHEET_URL = "https://docs.google.com/spreadsheets/d/11-ZeoBvixvY_ujLO8_9Vlze2jmGC4CooTWjvd2INX-4/edit"

def get_xlsx_url(url):
    if "/edit" in url:
        return url.split('/edit')[0] + "/export?format=xlsx"
    return url

# ---------------- INPUT ----------------
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

# ---------------- PROCESS FUNCTION ----------------
def process(df):
    if "Ward" not in df.columns:
        return None

    df_melt = df.melt(id_vars=["Ward"], var_name="Month_Week", value_name="Value")
    df_melt["Month"] = df_melt["Month_Week"].str.extract(r'([A-Za-z]+)')
    df_melt["Week"] = df_melt["Month_Week"].str.extract(r'(Week\s*\d+)')

    return df_melt

# ---------------- EXPORT ----------------
def export_excel(data_dict):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, df in data_dict.items():
            df.to_excel(writer, sheet_name=name, index=False)
    return output.getvalue()

# ---------------- MAIN ----------------
if target_url:
    try:
        with st.spinner('Reading all sheets and creating tabs...'):
            excel_file = pd.ExcelFile(target_url, engine='openpyxl')
            sheet_names = excel_file.sheet_names

        final_export = {}

        if sheet_names:
            tabs = st.tabs(sheet_names)

            for i, sheet_name in enumerate(sheet_names):
                with tabs[i]:
                    st.subheader(f"📄 {sheet_name}")

                    df = pd.read_excel(target_url, sheet_name=sheet_name)
                    st.dataframe(df, use_container_width=True)

                    df_proc = process(df)

                    # 👉 If proper format (Ward exists)
                    if df_proc is not None:

                        # ---------------- MONTH COMPARISON ----------------
                        pivot = df_proc.pivot_table(
                            index="Ward",
                            columns="Month",
                            values="Value",
                            aggfunc="sum"
                        ).fillna(0)

                        months = list(pivot.columns)

                        if len(months) >= 2:
                            m1, m2 = months[-2], months[-1]

                            comp = pivot[[m1, m2]].reset_index()
                            comp["Change"] = comp[m2] - comp[m1]
                            comp["% Change"] = (comp["Change"] / comp[m1].replace(0,1)) * 100

                            st.markdown("### 📊 Month Comparison")
                            st.dataframe(comp, use_container_width=True)

                            st.plotly_chart(
                                px.bar(comp, x="Ward", y=[m1, m2], barmode="group"),
                                use_container_width=True
                            )

                            # ---------------- % CHANGE ----------------
                            st.markdown("### 📈 % Change")

                            st.plotly_chart(
                                px.bar(
                                    comp,
                                    x="Ward",
                                    y="% Change",
                                    color="% Change",
                                    color_continuous_scale=["red", "green"]
                                ),
                                use_container_width=True
                            )

                            # ---------------- TOP / BOTTOM ----------------
                            col1, col2 = st.columns(2)

                            col1.markdown("#### 🔝 Top 5")
                            col1.dataframe(comp.sort_values("% Change", ascending=False).head(5))

                            col2.markdown("#### 🔻 Bottom 5")
                            col2.dataframe(comp.sort_values("% Change").head(5))

                            final_export[sheet_name] = comp

                        # ---------------- WEEK COMPARISON ----------------
                        week_pivot = df_proc.pivot_table(
                            index="Ward",
                            columns="Week",
                            values="Value",
                            aggfunc="sum"
                        ).fillna(0)

                        weeks = list(week_pivot.columns)

                        if len(weeks) >= 2:
                            w1, w2 = weeks[-2], weeks[-1]

                            wk = week_pivot[[w1, w2]].reset_index()

                            st.markdown("### 📅 Week Comparison")

                            st.plotly_chart(
                                px.bar(wk, x="Ward", y=[w1, w2], barmode="group"),
                                use_container_width=True
                            )

                    else:
                        st.info("⚠️ 'Ward' column नाही → analysis skip")

        # ---------------- DOWNLOAD ----------------
        st.markdown("---")
        st.subheader("📥 Download Report")

        st.download_button(
            "Download Excel",
            data=export_excel(final_export),
            file_name="IHIP_Report.xlsx"
        )

    except Exception as e:
        st.error(f"Error: {e}")
        st.info("Ensure Google Sheet is public (Anyone with link can view)")

else:
    st.info("Provide Google Sheet link")
