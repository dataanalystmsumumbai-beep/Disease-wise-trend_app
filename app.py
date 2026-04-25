import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Disease Dashboard", layout="wide")

# --- DATA LOADING FROM GOOGLE SHEET ---
DEFAULT_GSHEET_URL = "https://docs.google.com/spreadsheets/d/11-ZeoBvixvY_ujLO8_9Vlze2jmGC4CooTWjvd2INX-4/edit"

def get_xlsx_url(url):
    if "/edit" in url:
        return url.split('/edit')[0] + "/export?format=xlsx"
    return url

@st.cache_data
def load_all_sheets(url):
    xlsx_url = get_xlsx_url(url)
    xls = pd.ExcelFile(xlsx_url, engine='openpyxl')
    sheets_dict = {}
    
    for sheet_name in xls.sheet_names:
        df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        try:
            # Header Cleaning (Months & Weeks)
            months_row = df_raw.iloc[0, 2:].ffill().tolist()
            weeks_row = df_raw.iloc[1, 2:].tolist()
            cols = ['Ward', 'Total'] + [f"{m}_{w}" for m, w in zip(months_row, weeks_row)]
            
            data_only = df_raw.iloc[2:].copy()
            data_only.columns = cols[:len(data_only.columns)]
            
            # Split 2025 and 2026 data based on 'A' Ward row
            ward_a_idx = data_only[data_only['Ward'] == 'A'].index.tolist()
            if len(ward_a_idx) >= 2:
                df_25 = data_only.loc[ward_a_idx[0]:ward_a_idx[1]-2].copy()
                df_26 = data_only.loc[ward_a_idx[1]-1:].copy()
            else:
                df_25, df_26 = data_only.iloc[:56], data_only.iloc[56:]
                
            for c in data_only.columns[1:]:
                df_25[c] = pd.to_numeric(df_25[c], errors='coerce').fillna(0)
                df_26[c] = pd.to_numeric(df_26[c], errors='coerce').fillna(0)
                
            sheets_dict[sheet_name] = {'25': df_25, '26': df_26}
        except: continue
    return sheets_dict

# --- MINIMAL CHART FUNCTION ---
def create_chart(v1, v2, label1, label2, colors):
    data = pd.DataFrame({'Category': [label1, label2], 'Value': [v1, v2]})
    return alt.Chart(data).mark_bar(height=16, cornerRadiusEnd=2).encode(
        x=alt.X('Value:Q', axis=None),
        y=alt.Y('Category:N', axis=alt.Axis(title=None, ticks=False, domain=False), sort=None),
        color=alt.Color('Category:N', scale=alt.Scale(range=colors), legend=None),
        tooltip=['Category', 'Value']
    ).properties(height=65).configure_view(strokeWidth=0)

# --- MAIN UI ---
st.title("Ward-wise Disease Dashboard")

try:
    with st.spinner("डेटा लोड होत आहे..."):
        all_data = load_all_sheets(DEFAULT_GSHEET_URL)
    
    if all_data:
        tabs = st.tabs(list(all_data.keys()))
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        weeks = ["WEEK 1", "WEEK 2", "WEEK 3", "WEEK 4"]

        for i, sheet in enumerate(all_data.keys()):
            with tabs[i]:
                # 1. INDEPENDENT FILTERS
                f1, f2 = st.columns(2)
                sel_m = f1.selectbox("Month", months, index=3, key=f"m_{sheet}")
                sel_w = f2.selectbox("Week", weeks, index=2, key=f"w_{sheet}")
                
                df_25 = all_data[sheet]['25']
                df_26 = all_data[sheet]['26']
                
                m_idx = months.index(sel_m)
                prev_m = months[m_idx-1] if m_idx > 0 else "Jan"
                target_col = f"{sel_m}_{sel_w}"
                cum_months = months[:m_idx+1]

                # 2. TABLE HEADERS
                st.markdown("---")
                h_ward, h_mon, h_year, h_cum = st.columns([1, 2.5, 2.5, 2.5])
                h_ward.write("**Ward**")
                h_mon.write(f"**Monthly** ({prev_m} vs {sel_m} '26)")
                h_year.write(f"**Yearly** ({sel_m} {sel_w} '25 vs '26)")
                h_cum.write(f"**Cumulative** (Jan-{sel_m} '25 vs '26)")
                st.divider()

                # 3. ROWS
                wards = df_26['Ward'].dropna().unique()
                for ward in wards:
                    if ward in ['Ward', 'Total', 'YEAR 2026', 'YEAR 2025']: continue
                    
                    # Calculations
                    # Monthly Comparison
                    c_curr = [c for c in df_26.columns if c.startswith(sel_m)]
                    c_prev = [c for c in df_26.columns if c.startswith(prev_m)]
                    v_curr_m = df_26[df_26['Ward'] == ward][c_curr].values.sum()
                    v_prev_m = df_26[df_26['Ward'] == ward][c_prev].values.sum()
                    
                    # Yearly Week Comparison
                    v_25_w = df_25[df_25['Ward'] == ward][target_col].values[0] if target_col in df_25.columns else 0
                    v_26_w = df_26[df_26['Ward'] == ward][target_col].values[0] if target_col in df_26.columns else 0
                    
                    # Cumulative Comparison
                    c_cum = [c for c in df_26.columns if any(c.startswith(m) for m in cum_months)]
                    v_25_c = df_25[df_25['Ward'] == ward][c_cum].values.sum()
                    v_26_c = df_26[df_26['Ward'] == ward][c_cum].values.sum()

                    # Layout
                    r_ward, r_mon, r_year, r_cum = st.columns([1, 2.5, 2.5, 2.5])
                    r_ward.subheader(ward)
                    
                    r_mon.altair_chart(create_chart(v_prev_m, v_curr_m, prev_m, sel_m, ['#AEC7E8', '#1F77B4']), use_container_width=True)
                    r_year.altair_chart(create_chart(v_25_w, v_26_w, "2025", "2026", ['#FFBB78', '#FF7F0E']), use_container_width=True)
                    r_cum.altair_chart(create_chart(v_25_c, v_26_c, "2025", "2026", ['#98DF8A', '#2CA02C']), use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
