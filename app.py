import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="IHIP Report", layout="wide")

st.title("📊 IHIP Report (Stable Version)")

# ---------------- INPUT ----------------
sheet_url = st.text_input(
    "Paste Google Sheet Link",
    "https://docs.google.com/spreadsheets/d/11-ZeoBvixvY_ujLO8_9Vlze2jmGC4CooTWjvd2INX-4/edit"
)

gid_input = st.text_area(
    "Enter Sheet GIDs (one per line)",
    help="Open each tab → copy gid from URL"
)

# ---------------- GET SHEET ID ----------------
def get_sheet_id(url):
    return url.split("/d/")[1].split("/")[0]

# ---------------- LOAD CSV ----------------
@st.cache_data
def load_sheet(sheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return pd.read_csv(url)

# ---------------- PROCESS ----------------
def process(df):
    if "Ward" not in df.columns:
        return df

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
if sheet_url and gid_input:

    sheet_id = get_sheet_id(sheet_url)
    gids = [g.strip() for g in gid_input.split("\n") if g.strip()]

    tabs = st.tabs([f"Sheet {g}" for g in gids])
    final_export = {}

    for i, tab in enumerate(tabs):
        with tab:
            gid = gids[i]

            try:
                df = load_sheet(sheet_id, gid)
            except:
                st.error(f"Failed to load GID: {gid}")
                continue

            st.header(f"📄 Sheet {gid}")

            if df.empty:
                st.warning("No data")
                continue

            df_proc = process(df)

            if "Ward" in df_proc.columns:

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

                    st.subheader(f"📊 {m1} vs {m2}")
                    st.dataframe(comp)

                    st.plotly_chart(
                        px.bar(comp, x="Ward", y=[m1, m2], barmode="group"),
                        use_container_width=True
                    )

                    st.subheader("📈 % Change")
                    st.plotly_chart(
                        px.bar(comp, x="Ward", y="% Change", color="% Change",
                               color_continuous_scale=["red", "green"]),
                        use_container_width=True
                    )

                    # Top Bottom
                    col1, col2 = st.columns(2)

                    col1.write("🔝 Top 5")
                    col1.dataframe(comp.sort_values("% Change", ascending=False).head(5))

                    col2.write("🔻 Bottom 5")
                    col2.dataframe(comp.sort_values("% Change").head(5))

                    final_export[f"Sheet_{gid}"] = comp

                # WEEK
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

                    st.subheader(f"📅 {w1} vs {w2}")
                    st.plotly_chart(
                        px.bar(wk, x="Ward", y=[w1, w2], barmode="group"),
                        use_container_width=True
                    )

            else:
                st.dataframe(df)
                final_export[f"Sheet_{gid}"] = df

    # DOWNLOAD
    st.markdown("---")
    st.subheader("📥 Download Report")

    st.download_button(
        "Download Excel",
        data=export_excel(final_export),
        file_name="IHIP_Report.xlsx"
    )

else:
    st.info("Paste Sheet link + GIDs")
