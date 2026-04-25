import streamlit as st
import pandas as pd
import io
import numpy as np

# Set page config
st.set_page_config(page_title="Health Analysis Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- 1. Formatting Functions ---
def format_pct(val):
    if pd.isna(val) or np.isinf(val): return "0 %"
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

# --- 2. Data Processing Logic ---
@st.cache_data
def process_excel_data(_xls):
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

# --- 3. Calculation Functions ---
def get_sum_up_to_week(df, ward, month, week_str, all_months, all_weeks):
    if week_str not in all_weeks: return 0
    w_idx = all_weeks.index(week_str)
    target_cols = [f"{month}_{all_weeks[i]}" for i in range(w_idx + 1) if f"{month}_{all_weeks[i]}" in df.columns]
    val = df[df['Ward'] == ward][target_cols].values.sum()
    return int(val)

def get_cumulative_sum(df, ward, end_month, end_week, all_months, all_weeks):
    m_idx = all_months.index(end_month)
    target_cols = []
    for m in all_months[:m_idx+1]:
        for w in all_weeks:
            c_name = f"{m}_{w}"
            if c_name in df.columns: target_cols.append(c_name)
            if m == end_month and w == end_week: break
        if m == end_month: break
    return int(df[df['Ward'] == ward][target_cols].values.sum())

def display_table(data_list, numeric_cols, pct_col_name=None):
    df = pd.DataFrame(data_list)
    total_row = {'Ward': 'Total'}
    for col in numeric_cols:
        total_row[col] = int(df[col].sum())
    if pct_col_name and len(numeric_cols) >= 2:
        v1, v2 = total_row[numeric_cols[0]], total_row[numeric_cols[1]]
        diff = ((v2 - v1) / v1) if v1 > 0 else 0
        total_row[pct_col_name] = format_pct(diff)
    df_final = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)
    st.table(df_final)
    return df_final

# --- 4. Main App Logic ---
st.sidebar.header("📁 Data Source")
data_source_type = st.sidebar.radio("Choose Input Method:", ("Use Google Sheet Link", "Upload Excel File"))

# Important: Initialize data_dict as None at the top level
data_dict = None
DEFAULT_URL = "https://docs.google.com/spreadsheets/d/11-ZeoBvixvY_ujLO8_9Vlze2jmGC4CooTWjvd2INX-4/edit"

try:
    if data_source_type == "Use Google Sheet Link":
        user_url = st.sidebar.text_input("Google Sheet URL:", value=DEFAULT_URL)
        if user_url:
            with st.spinner("Loading from Google Sheets..."):
                data_dict = load_from_url(user_url)
    else:
        uploaded_file = st.sidebar.file_uploader("Upload .xlsx file", type=['xlsx'])
        if uploaded_file:
            with st.spinner("Processing file..."):
                data_dict = load_from_file(uploaded_file)

    # Now check if data_dict is successfully defined
    if data_dict is not None:
        st.title("📊 Disease-wise Trend Analysis")
        tabs = st.tabs(list(data_dict.keys()))
        months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        weeks_list = ["WEEK 1", "WEEK 2", "WEEK 3", "WEEK 4"]

        for i, sheet_name in enumerate(data_dict.keys()):
            with tabs[i]:
                df_25, df_26 = data_dict[sheet_name]['25'], data_dict[sheet_name]['26']
                wards = [w for w in df_26['Ward'].dropna().unique() if w not in ['Ward', 'Total', 'YEAR 2026', 'YEAR 2025']]

                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("1. Monthly Comparison")
                    f1, f2, f3 = st.columns(3)
                    m1 = f1.selectbox("Month 1", months_list, index=2, key=f"m1_{sheet_name}")
                    m2 = f2.selectbox("Month 2", months_list, index=3, key=f"m2_{sheet_name}")
                    wt = f3.selectbox("Up to", weeks_list, key=f"wt1_{sheet_name}")
                    t1_res = []
                    for w in wards:
                        v1 = get_sum_up_to_week(df_26, w, m1, wt, months_list, weeks_list)
                        v2 = get_sum_up_to_week(df_26, w, m2, wt, months_list, weeks_list)
                        diff = ((v2-v1)/v1) if v1 > 0 else 0
                        t1_res.append({'Ward':w, m1:v1, m2:v2, '% Inc/Dec':format_pct(diff)})
                    df1 = display_table(t1_res, [m1, m2], '% Inc/Dec')

                with c2:
                    st.subheader("2. Yearly Comparison")
                    f1, f2, f3, f4 = st.columns(4)
                    m25 = f1.selectbox("25 Month", months_list, index=3, key=f"m25_{sheet_name}")
                    w25 = f2.selectbox("25 Week", weeks_list, key=f"w25_{sheet_name}")
                    m26 = f3.selectbox("26 Month", months_list, index=3, key=f"m26_{sheet_name}")
                    w26 = f4.selectbox("26 Week", weeks_list, key=f"w26_{sheet_name}")
                    t2_res = []
                    for w in wards:
                        v25 = get_sum_up_to_week(df_25, w, m25, w25, months_list, weeks_list)
                        v26 = get_sum_up_to_week(df_26, w, m26, w26, months_list, weeks_list)
                        diff = ((v26-v25)/v25) if v25 > 0 else 0
                        t2_res.append({'Ward':w, '2025':v25, '2026':v26, '% Inc/Dec':format_pct(diff)})
                    df2 = display_table(t2_res, ['2025', '2026'], '% Inc/Dec')

                c3, c4 = st.columns(2)
                with c3:
                    st.subheader("3. Cumulative Comparison")
                    f1, f2 = st.columns(2)
                    cm, cw = f1.selectbox("End Month", months_list, index=3, key=f"cm_{sheet_name}"), f2.selectbox("End Week", weeks_list, key=f"cw_{sheet_name}")
                    t3_res = []
                    for w in wards:
                        v25c = get_cumulative_sum(df_25, w, cm, cw, months_list, weeks_list)
                        v26c = get_cumulative_sum(df_26, w, cm, cw, months_list, weeks_list)
                        diff = ((v26c-v25c)/v25c) if v25c > 0 else 0
                        t3_res.append({'Ward':w, '2025 Cum':v25c, '2026 Cum':v26c, '% Inc/Dec':format_pct(diff)})
                    df3 = display_table(t3_res, ['2025 Cum', '2026 Cum'], '% Inc/Dec')

                with c4:
                    st.subheader("4. Summary Trends (%)")
                    t4_res = [{'Ward': w, 'Monthly %': t1_res[idx]['% Inc/Dec'], 'Yearly %': t2_res[idx]['% Inc/Dec'], 'Cum %': t3_res[idx]['% Inc/Dec']} for idx, w in enumerate(wards)]
                    t4_total = {'Ward':'Total', 'Monthly %': df1.iloc[-1]['% Inc/Dec'], 'Yearly %': df2.iloc[-1]['% Inc/Dec'], 'Cum %': df3.iloc[-1]['% Inc/Dec']}
                    df4_final = pd.concat([pd.DataFrame(t4_res), pd.DataFrame([t4_total])], ignore_index=True)
                    st.table(df4_final)

                # --- Excel Side-by-Side Download ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter', engine_kwargs={'options': {'nan_inf_to_errors': True}}) as writer:
                    wb, ws = writer.book, writer.book.add_worksheet("Analysis")
                    h_fmt = wb.add_format({'bold':True, 'bg_color':'#D7E4BC', 'border':1, 'align':'center'})
                    c_fmt = wb.add_format({'border':1, 'align':'center'})
                    t_fmt = wb.add_format({'bold':True, 'font_size':12, 'font_color':'#1F4E78'})
                    
                    def write_side(df, start_col, title):
                        df_c = df.replace([np.inf, -np.inf], 0).fillna(0)
                        ws.write(0, start_col, title, t_fmt)
                        for c, col in enumerate(df_c.columns): ws.write(2, start_col+c, col, h_fmt)
                        for r, row in enumerate(df_c.values):
                            for c, val in enumerate(row): ws.write(r+3, start_col+c, val, c_fmt)
                        return start_col + len(df_c.columns) + 1

                    curr = write_side(df1, 0, "1. Monthly")
                    curr = write_side(df2, curr, "2. Yearly")
                    curr = write_side(df3, curr, "3. Cumulative")
                    write_side(df4_final, curr, "4. Summary")
                
                st.download_button(label=f"📥 Download {sheet_name} Report", data=output.getvalue(),
                                   file_name=f"{sheet_name}_Report.xlsx", key=f"dl_{sheet_name}")
    else:
        st.info("👈 Please select a data source.")

except Exception as e:
    st.error(f"Something went wrong: {e}")
