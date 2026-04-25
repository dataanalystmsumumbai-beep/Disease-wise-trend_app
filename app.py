import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="IHIP Report", layout="wide")

st.title("📄 IHIP Analytical Report")

# ---------------- INPUT ----------------
st.sidebar.header("🔗 Google Sheet")

sheet_id = st.sidebar.text_input("Sheet ID")

gid_input = st.sidebar.text_area(
    "GIDs (one per line)",
    placeholder="0\n123456789"
)

# ---------------- LOAD ----------------
@st.cache_data
def load_data(sheet_id, gids):
    data = {}
    for gid in gids:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        try:
            df = pd.read_csv(url)
            data[f"Sheet_{gid}"] = df
        except:
            continue
    return data

# ---------------- PROCESS ----------------
def process(df):
    df = df.copy()

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
if sheet_id and gid_input:

    gids = [g.strip() for g in gid_input.split("\n") if g.strip()]
    data_dict = load_data(sheet_id, gids)

    tabs = st.tabs(list(data_dict.keys()))
    final_export = {}

    for i, tab in enumerate(tabs):
        with tab:
            name = list(data_dict.keys())[i]
            df = data_dict[name]

            st.header(f"📄 {name}")

            df_proc = process(df)

            # ---------------- MONTH COMP ----------------
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

                st.subheader(f"📊 {m1} vs {m2} Comparison Table")
                st.dataframe(comp, use_container_width=True)

                fig1 = px.bar(comp, x="Ward", y=[m1, m2], barmode="group")
                st.plotly_chart(fig1, use_container_width=True)

                # ---------------- % CHANGE ----------------
                st.subheader("📈 % Increase / Decrease")

                fig2 = px.bar(
                    comp,
                    x="Ward",
                    y="% Change",
                    color="% Change",
                    color_continuous_scale=["red", "green"]
                )
                st.plotly_chart(fig2, use_container_width=True)

                # ---------------- TOP / BOTTOM ----------------
                st.subheader("🏆 Performance")

                top5 = comp.sort_values("% Change", ascending=False).head(5)
                bottom5 = comp.sort_values("% Change").head(5)

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("### 🔝 Top 5 Wards")
                    st.dataframe(top5)

                with col2:
                    st.markdown("### 🔻 Bottom 5 Wards")
                    st.dataframe(bottom5)

                final_export[name] = comp

            # ---------------- WEEK COMP ----------------
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

                st.subheader(f"📅 {w1} vs {w2} Week Comparison")

                fig3 = px.bar(wk, x="Ward", y=[w1, w2], barmode="group")
                st.plotly_chart(fig3, use_container_width=True)

    # ---------------- DOWNLOAD ----------------
    st.markdown("---")
    st.subheader("📥 Download Report")

    st.download_button(
        "Download Excel",
        data=export_excel(final_export),
        file_name="IHIP_Report.xlsx"
    )

else:
    st.info("Enter Sheet ID and GIDs")
