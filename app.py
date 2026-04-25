import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Health Analysis Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- 1. Formatting Functions ---
def format_pct(val):
    if val == 0: return "0 %"
    val = val * 100
    if abs(val - round(val)) < 1e-9:
        return f"{int(val)} %"
    else:
        return f"{val:.2f} %"

def get_xlsx_url(url):
    if "/edit" in url:
        return url.split('/edit')[0] + "/export?format=xlsx"
    return url

# --- 2. Data Processing Logic (Common for URL and File) ---
@st.cache_data
def process_excel_data(_xls):  # Added '_' to fix the hashing error
    all_data = {}
    for sheet in _xls.sheet_names:
        df_raw = pd.read_excel(_xls, sheet_name=sheet, header=None)
        
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
            df_25[c] = pd.to_numeric(df_25[c], errors='coerce').fillna(0).astype(int)
            df_26[c] = pd.to_numeric(df_26[c], errors='coerce').fillna(0).astype(int)
        
        all_data[sheet] = {'25': df_25, '26': df_26}
    return all_data

@st.cache_data
def load_from_url(url):
    xlsx_url = get_xlsx_url(url)
    xls = pd.ExcelFile(xlsx_url, engine='openpyxl')
    return process_excel_data(xls)

@st.cache_data
def load_from_file(file):
    xls = pd.ExcelFile(file, engine='openpyxl')
    return process_excel_data(xls)

# --- 3. Calculation Logic ---
def get_sum_up_to_week(df, ward, month, week_str, all_months, all_weeks):
    target_cols = []
    if week_str not in all_weeks: return 0
    w_idx = all_weeks.index(week_str)
    for i in range(w_idx + 1):
        c_name = f"{month}_{all_weeks[i]}"
        if c_name in df.columns: target_cols.append(c_name)
    val = df[df['Ward'] == ward][target_cols].values.sum()
    return int(val)

def get_cumulative_sum(df, ward, end_month, end_week, all_months, all_weeks):
    target_cols = []
    m_idx = all_months.index(end_month)
    for m in all_months[:m_idx+1]:
        for w in all_weeks:
            c_name = f"{m}_{w}"
            if c_name in df.columns: target_cols.append(c_name)
            if m == end_month and w == end_week: break
        if m == end_month: break
    return int(df[df['Ward'] == ward][target_cols].values.sum())

# --- 4. Table Display with Total Row ---
def display_table(data_list, numeric_cols, pct_col_name=None):
    df = pd.DataFrame(data_list)
    total_row = {'Ward': 'Total'}
    for col in numeric_cols:
        total_row[col] = int(df[col].sum())
    
    if pct_col_name and len(numeric_cols) >= 2:
        v1 = total_row[numeric_cols[0]]
        v2 = total_row[numeric_cols[1]]
        diff = ((v2 - v1) / v1) if v1 > 0 else 0
        total_row[pct_col_name] = format_pct(diff)
    
    df_final = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)
    st.table(df_final)
    return df_final

# --- 5. Main UI and Data Source Input ---
st.sidebar.header("📁 Data Source")
data_source_type = st.sidebar.radio("Choose Input Method:", ("Use Google Sheet Link", "Upload Excel File"))

data_dict = None
DEFAULT_GSHEET_URL = "https://docs.google.com/spreadsheets/d/11-ZeoBvixvY_ujLO8_9Vlze2jmGC4CooTWjvd2INX-4/edit"

try:
    if data_source_type == "Use Google Sheet Link":
        user_url = st.sidebar.text_input("Google Sheet URL:", value=DEFAULT_GSHEET_URL)
        if user_url:
            with st.spinner("Loading data from URL..."):
                data_dict = load_from_url(user_url)
    else:
        uploaded_file = st.sidebar.file_uploader("Upload your Excel file (.xlsx)", type=['xlsx'])
        if uploaded_file:
            with st.spinner("Processing uploaded file..."):
                data_dict = load_from_file(uploaded_file)

    if data_dict:
        st.title("📊 Disease-wise Trend Analysis")
        tabs = st.tabs(list(data_dict.keys()))
        
        months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        weeks_list = ["WEEK 1", "WEEK 2", "WEEK 3", "WEEK 4"]

        for i, sheet_name in enumerate(data_dict.keys()):
            with tabs[i]:
                df_25 = data_dict[sheet_name]['25']
                df_26 = data_dict[sheet_name]['26']
                wards = [w for w in df_26['Ward'].dropna().unique() if w not in ['Ward', 'Total', 'YEAR 2026', 'YEAR 2025']]

                # --- Row 1: Filters ---
                r1c1, r1c2 = st.columns(2)
                
                with r1c1:
                    st.subheader("1. Monthly Comparison (2026)")
                    f1, f2, f3 = st.columns(3)
                    m1_t1 = f1.selectbox("Month 1", months_list, index=2, key=f"t1m1_{sheet_name}")
                    m2_t1 = f2.selectbox("Month 2", months_list, index=3, key=f"t1m2_{sheet_name}")
                    w_t1 = f3.selectbox("Up to Week", weeks_list, key=f"t1w_{sheet_name}")
                    
                    t1_res = []
                    for w in wards:
                        v1 = get_sum_up_to_week(df_26, w, m1_t1, w_t1, months_list, weeks_list)
                        v2 = get_sum_up_to_week(df_26, w, m2_t1, w_t1, months_list, weeks_list)
                        diff = ((v2 - v1) / v1) if v1 > 0 else 0
                        t1_res.append({'Ward': w, f"{m1_t1}": v1, f"{m2_t1}": v2, '% Inc/Dec': format_pct(diff)})
                    df1 = display_table(t1_res, [m1_t1, m2_t1], '% Inc/Dec')

                with r1c2:
                    st.subheader("2. Yearly Comparison")
                    f1, f2, f3, f4 = st.columns(4)
                    m_25 = f1.selectbox("2025 Month", months_list, index=3, key=f"t2m25_{sheet_name}")
                    w_25 = f2.selectbox("2025 Week", weeks_list, key=f"t2w25_{sheet_name}")
                    m_26 = f3.selectbox("2026 Month", months_list, index=3, key=f"t2m26_{sheet_name}")
                    w_26 = f4.selectbox("2026 Week", weeks_list, key=f"t2w26_{sheet_name}")
                    
                    t2_res = []
                    for w in wards:
                        v25 = get_sum_up_to_week(df_25, w, m_25, w_25, months_list, weeks_list)
                        v26 = get_sum_up_to_week(df_26, w, m_26, w_26, months_list, weeks_list)
                        diff = ((v26 - v25) / v25) if v25 > 0 else 0
                        t2_res.append({'Ward': w, '2025': v25, '2026': v26, '% Inc/Dec': format_pct(diff)})
                    df2 = display_table(t2_res, ['2025', '2026'], '% Inc/Dec')

                # --- Row 2: Cumulative & Summary ---
                r2c1, r2c2 = st.columns(2)
                
                with r2c1:
                    st.subheader("3. Cumulative Comparison")
                    f1, f2 = st.columns(2)
                    cum_m = f1.selectbox("End Month", months_list, index=3, key=f"t3m_{sheet_name}")
                    cum_w = f2.selectbox("End Week", weeks_list, key=f"t3w_{sheet_name}")
                    
                    t3_res = []
                    for w in wards:
                        v25c = get_cumulative_sum(df_25, w, cum_m, cum_w, months_list, weeks_list)
                        v26c = get_cumulative_sum(df_26, w, cum_m, cum_w, months_list, weeks_list)
                        diff = ((v26c - v25c) / v25c) if v25c > 0 else 0
                        t3_res.append({'Ward': w, '2025 Cum': v25c, '2026 Cum': v26c, '% Inc/Dec': format_pct(diff)})
                    df3 = display_table(t3_res, ['2025 Cum', '2026 Cum'], '% Inc/Dec')

                with r2c2:
                    st.subheader("4. Summary Trends (%)")
                    st.write("") 
                    summary_res = []
                    for i_w, w in enumerate(wards):
                        summary_res.append({
                            'Ward': w,
                            'Monthly %': t1_res[i_w]['% Inc/Dec'],
                            'Yearly %': t2_res[i_w]['% Inc/Dec'],
                            'Cum %': t3_res[i_w]['% Inc/Dec']
                        })
                    df4 = display_table(summary_res, [])

                # --- Download Button ---
                csv_buffer = io.StringIO()
                final_report = pd.concat([df1, df2, df3, df4], axis=1)
                final_report.to_csv(csv_buffer, index=False)
                st.download_button(
                    label=f"📥 Download {sheet_name} Report",
                    data=csv_buffer.getvalue(),
                    file_name=f"{sheet_name}_Analysis.csv",
                    mime="text/csv",
                    key=f"dl_{sheet_name}"
                )
    else:
        st.info("👈 Please select a data source from the sidebar or upload a file.")

except Exception as e:
    st.error(f"Error: {e}")
