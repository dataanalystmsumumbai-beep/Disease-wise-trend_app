import streamlit as st
import pandas as pd

st.set_page_config(page_title="Health Analysis Dashboard", layout="wide")

# --- १. डेटा लोड करणे (Google Sheet) ---
DEFAULT_GSHEET_URL = "https://docs.google.com/spreadsheets/d/11-ZeoBvixvY_ujLO8_9Vlze2jmGC4CooTWjvd2INX-4/edit"

def get_xlsx_url(url):
    if "/edit" in url:
        return url.split('/edit')[0] + "/export?format=xlsx"
    return url

@st.cache_data
def load_all_sheets(url):
    xlsx_url = get_xlsx_url(url)
    xls = pd.ExcelFile(xlsx_url, engine='openpyxl')
    all_data = {}
    for sheet in xls.sheet_names:
        df_raw = pd.read_excel(xls, sheet_name=sheet, header=None)
        # Header processing
        months = df_raw.iloc[0, 2:].ffill().tolist()
        weeks = df_raw.iloc[1, 2:].tolist()
        cols = ['Ward', 'Total'] + [f"{m}_{w}" for m, w in zip(months, weeks)]
        data = df_raw.iloc[2:].copy()
        data.columns = cols[:len(data.columns)]
        # Split 2025 & 2026
        ward_a_indices = data[data['Ward'] == 'A'].index.tolist()
        if len(ward_a_indices) >= 2:
            df_25 = data.loc[ward_a_indices[0]:ward_a_indices[1]-2].copy()
            df_26 = data.loc[ward_a_indices[1]-1:].copy()
        else:
            df_25, df_26 = data.iloc[:56], data.iloc[56:]
        
        for c in data.columns[1:]:
            df_25[c] = pd.to_numeric(df_25[c], errors='coerce').fillna(0)
            df_26[c] = pd.to_numeric(df_26[c], errors='coerce').fillna(0)
        
        all_data[sheet] = {'25': df_25, '26': df_26, 'raw_cols': cols}
    return all_data

# --- २. मुख्य ॲप लॉजिक ---
try:
    data_dict = load_all_sheets(DEFAULT_GSHEET_URL)
    tabs = st.tabs(list(data_dict.keys()))
    
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    weeks = ["WEEK 1", "WEEK 2", "WEEK 3", "WEEK 4"]

    for i, sheet_name in enumerate(data_dict.keys()):
        with tabs[i]:
            df_25 = data_dict[sheet_name]['25']
            df_26 = data_dict[sheet_name]['26']
            wards = df_26['Ward'].dropna().unique()
            wards = [w for w in wards if w not in ['Ward', 'Total', 'YEAR 2026', 'YEAR 2025']]

            # --- टेबल्सची मांडणी (Layout) ---
            row1_col1, row1_col2 = st.columns(2)
            row2_col1, row2_col2 = st.columns(2)

            # --- TABLE 1: Monthly Comparison (2026 only) ---
            with row1_col1:
                st.subheader("1. Monthly (2026)")
                c1, c2 = st.columns(2)
                m1 = c1.selectbox("Month 1", months, index=2, key=f"t1_m1_{sheet_name}")
                m2 = c2.selectbox("Month 2", months, index=3, key=f"t1_m2_{sheet_name}")
                w_sel = st.selectbox("Select Week", weeks, key=f"t1_w_{sheet_name}")
                
                col_m1, col_m2 = f"{m1}_{w_sel}", f"{m2}_{w_sel}"
                t1_data = []
                for w in wards:
                    v1 = df_26[df_26['Ward'] == w][col_m1].values[0] if col_m1 in df_26.columns else 0
                    v2 = df_26[df_26['Ward'] == w][col_m2].values[0] if col_m2 in df_26.columns else 0
                    diff = ((v2 - v1) / v1 * 100) if v1 > 0 else 0
                    t1_data.append({'Ward': w, m1: v1, m2: v2, '% Increase': f"{diff:.1f}%"})
                st.table(pd.DataFrame(t1_data))

            # --- TABLE 2: Yearly Comparison (Same Week) ---
            with row1_col2:
                st.subheader("2. Yearly (Same Week)")
                c1, c2 = st.columns(2)
                y25_m = c1.selectbox("2025 Month", months, index=3, key=f"t2_m25_{sheet_name}")
                y26_m = c2.selectbox("2026 Month", months, index=3, key=f"t2_m26_{sheet_name}")
                w_sel_y = st.selectbox("Select Week", weeks, key=f"t2_w_{sheet_name}")
                
                col_25, col_26 = f"{y25_m}_{w_sel_y}", f"{y26_m}_{w_sel_y}"
                t2_data = []
                for w in wards:
                    v25 = df_25[df_25['Ward'] == w][col_25].values[0] if col_25 in df_25.columns else 0
                    v26 = df_26[df_26['Ward'] == w][col_26].values[0] if col_26 in df_26.columns else 0
                    diff = ((v26 - v25) / v25 * 100) if v25 > 0 else 0
                    t2_data.append({'Ward': w, '2025': v25, '2026': v26, '% Increase': f"{diff:.1f}%"})
                st.table(pd.DataFrame(t2_data))

            # --- TABLE 3: Cumulative Comparison ---
            with row2_col1:
                st.subheader("3. Cumulative (Jan to Month)")
                cum_m = st.selectbox("Up to Month", months, index=3, key=f"t3_m_{sheet_name}")
                cum_w = st.selectbox("Up to Week", weeks, index=0, key=f"t3_w_{sheet_name}")
                
                selected_months = months[:months.index(cum_m)+1]
                t3_data = []
                for w in wards:
                    # Logic to sum all weeks up to selected month/week
                    v25_cum, v26_cum = 0, 0
                    for m in selected_months:
                        for wk in weeks:
                            c_name = f"{m}_{wk}"
                            v25_cum += df_25[df_25['Ward'] == w][c_name].values[0] if c_name in df_25.columns else 0
                            v26_cum += df_26[df_26['Ward'] == w][c_name].values[0] if c_name in df_26.columns else 0
                            if m == cum_m and wk == cum_w: break
                        if m == cum_m: break
                    
                    diff = ((v26_cum - v25_cum) / v25_cum * 100) if v25_cum > 0 else 0
                    t3_data.append({'Ward': w, '2025 Cum': v25_cum, '2026 Cum': v26_cum, '% Diff': f"{diff:.1f}%"})
                st.table(pd.DataFrame(t3_data))

            # --- TABLE 4: Summary Table ---
            with row2_col2:
                st.subheader("4. Summary Table")
                st.write("Overview of all trends")
                # Summary logic using data from above
                summary_data = []
                for idx, w in enumerate(wards):
                    summary_data.append({
                        'Ward': w,
                        'Monthly %': t1_data[idx]['% Increase'],
                        'Yearly %': t2_data[idx]['% Increase'],
                        'Cum %': t3_data[idx]['% Diff']
                    })
                st.table(pd.DataFrame(summary_data))

except Exception as e:
    st.error(f"Error occurred: {e}")
