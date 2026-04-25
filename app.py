import streamlit as st
import pandas as pd

st.set_page_config(page_title="Health Analysis Dashboard", layout="wide")

# --- 1. DATA LOADING (Google Sheet) ---
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
        months = df_raw.iloc[0, 2:].ffill().tolist()
        weeks = df_raw.iloc[1, 2:].tolist()
        cols = ['Ward', 'Total'] + [f"{m}_{w}" for m, w in zip(months, weeks)]
        data = df_raw.iloc[2:].copy()
        data.columns = cols[:len(data.columns)]
        
        ward_a_indices = data[data['Ward'] == 'A'].index.tolist()
        if len(ward_a_indices) >= 2:
            df_25 = data.loc[ward_a_indices[0]:ward_a_indices[1]-2].copy()
            df_26 = data.loc[ward_a_indices[1]-1:].copy()
        else:
            df_25, df_26 = data.iloc[:56], data.iloc[56:]
        
        for c in data.columns[1:]:
            df_25[c] = pd.to_numeric(df_25[c], errors='coerce').fillna(0)
            df_26[c] = pd.to_numeric(df_26[c], errors='coerce').fillna(0)
        
        all_data[sheet] = {'25': df_25, '26': df_26}
    return all_data

# --- 2. LOGIC FOR "UP TO WEEK" SUM ---
def get_sum_up_to_week(df, ward, month, week_str, all_months, all_weeks):
    # Mahinyachya suruvati pasun tya week paryantche columns shodhane
    target_cols = []
    week_idx = all_weeks.index(week_str)
    for i in range(week_idx + 1):
        col_name = f"{month}_{all_weeks[i]}"
        if col_name in df.columns:
            target_cols.append(col_name)
    
    val = df[df['Ward'] == ward][target_cols].values.sum()
    return val

def get_cumulative_sum(df, ward, end_month, end_week, all_months, all_weeks):
    target_cols = []
    m_idx = all_months.index(end_month)
    for m in all_months[:m_idx+1]:
        for w in all_weeks:
            col_name = f"{m}_{w}"
            if col_name in df.columns:
                target_cols.append(col_name)
            if m == end_month and w == end_week:
                break
        if m == end_month: break
    
    val = df[df['Ward'] == ward][target_cols].values.sum()
    return val

# --- 3. MAIN UI ---
try:
    data_dict = load_all_sheets(DEFAULT_GSHEET_URL)
    tabs = st.tabs(list(data_dict.keys()))
    
    months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    weeks_list = ["WEEK 1", "WEEK 2", "WEEK 3", "WEEK 4"]

    for i, sheet_name in enumerate(data_dict.keys()):
        with tabs[i]:
            df_25 = data_dict[sheet_name]['25']
            df_26 = data_dict[sheet_name]['26']
            wards = [w for w in df_26['Ward'].dropna().unique() if w not in ['Ward', 'Total', 'YEAR 2026', 'YEAR 2025']]

            row1_col1, row1_col2 = st.columns(2)
            row2_col1, row2_col2 = st.columns(2)

            # --- TABLE 1: Monthly (Up to Week) ---
            with row1_col1:
                st.subheader("1. Monthly (2026)")
                c1, c2, c3 = st.columns(3)
                m1 = c1.selectbox("Month 1", months_list, index=2, key=f"t1m1_{sheet_name}")
                m2 = c2.selectbox("Month 2", months_list, index=3, key=f"t1m2_{sheet_name}")
                w_sel = c3.selectbox("Up to Week", weeks_list, index=0, key=f"t1w_{sheet_name}")
                
                t1_res = []
                for w in wards:
                    v1 = get_sum_up_to_week(df_26, w, m1, w_sel, months_list, weeks_list)
                    v2 = get_sum_up_to_week(df_26, w, m2, w_sel, months_list, weeks_list)
                    diff = ((v2 - v1) / v1) if v1 > 0 else 0
                    t1_res.append({'Ward': w, f"{m1} (up to {w_sel})": v1, f"{m2} (up to {w_sel})": v2, '% Change': f"{diff:.1%}"})
                st.table(pd.DataFrame(t1_res))

            # --- TABLE 2: Yearly (Up to Week) ---
            with row1_col2:
                st.subheader("2. Yearly (Same Week Sum)")
                c1, c2, c3 = st.columns(3)
                y25m = c1.selectbox("2025 Month", months_list, index=3, key=f"t2m25_{sheet_name}")
                y26m = c2.selectbox("2026 Month", months_list, index=3, key=f"t2m26_{sheet_name}")
                w_sel_y = c3.selectbox("Up to Week", weeks_list, index=0, key=f"t2w_{sheet_name}")
                
                t2_res = []
                for w in wards:
                    v25 = get_sum_up_to_week(df_25, w, y25m, w_sel_y, months_list, weeks_list)
                    v26 = get_sum_up_to_week(df_26, w, y26m, w_sel_y, months_list, weeks_list)
                    diff = ((v26 - v25) / v25) if v25 > 0 else 0
                    t2_res.append({'Ward': w, '2025': v25, '2026': v26, '% Change': f"{diff:.1%}"})
                st.table(pd.DataFrame(t2_res))

            # --- TABLE 3: Cumulative (Jan to Selected Month-Week) ---
            with row2_col1:
                st.subheader("3. Cumulative")
                c1, c2 = st.columns(2)
                cum_m = c1.selectbox("End Month", months_list, index=3, key=f"t3m_{sheet_name}")
                cum_w = c2.selectbox("End Week", weeks_list, index=0, key=f"t3w_{sheet_name}")
                
                t3_res = []
                for w in wards:
                    v25c = get_cumulative_sum(df_25, w, cum_m, cum_w, months_list, weeks_list)
                    v26c = get_cumulative_sum(df_26, w, cum_m, cum_w, months_list, weeks_list)
                    diff = ((v26c - v25c) / v25c) if v25c > 0 else 0
                    t3_res.append({'Ward': w, '2025 Cum': v25c, '2026 Cum': v26c, '% Change': f"{diff:.1%}"})
                st.table(pd.DataFrame(t3_res))

            # --- TABLE 4: Summary ---
            with row2_col2:
                st.subheader("4. Summary")
                summary_data = []
                for i_w, w in enumerate(wards):
                    summary_data.append({
                        'Ward': w,
                        'Monthly %': t1_res[i_w]['% Change'],
                        'Yearly %': t2_res[i_w]['% Change'],
                        'Cum %': t3_res[i_w]['% Change']
                    })
                st.table(pd.DataFrame(summary_data))

except Exception as e:
    st.error(f"Logic Error: {e}")
