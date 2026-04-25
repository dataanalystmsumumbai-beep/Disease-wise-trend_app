import streamlit as st
import pandas as pd
import io
import numpy as np
import plotly.express as px

# Set page config
st.set_page_config(page_title="Health Analysis Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- 1. Formatting Functions ---
def format_pct(val):
    if pd.isna(val) or np.isinf(val): return "0 %"
    if val == 0: return "0 %"
    val = val * 100
    return f"{int(val)} %" if abs(val - round(val)) < 1e-9 else f"{val:.2f} %"

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
        
        # Header Cleanup
        months = df_raw.iloc[0, 2:].ffill().tolist()
        weeks = df_raw.iloc[1, 2:].tolist()
        cols = ['Ward', 'Total'] + [f"{m}_{w}" for m, w in zip(months, weeks)]
        data = df_raw.iloc[2:].copy()
        data.columns = cols[:len(data.columns)]
        
        # Split 2025 & 2026 data based on 'Ward A' positioning
        ward_a_indices = data[data['Ward'] == 'A'].index.tolist()
        if len(ward_a_indices) >= 2:
            df_25 = data.loc[ward_a_indices[0]:ward_a_indices[1]-2].copy()
            df_26 = data.loc[ward_a_indices[1]-1:].copy()
        else:
            df_25, df_26 = data.iloc[:56], data.iloc[56:]
        
        # Convert to numeric
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

# --- 4. Main UI ---
st.sidebar.header("📁 Data Source")
data_source_type = st.sidebar.radio("Input Method:", ("Use Google Sheet Link", "Upload Excel File"))

data_dict = None
DEFAULT_URL = "https://docs.google.com/spreadsheets/d/11-ZeoBvixvY_ujLO8_9Vlze2jmGC4CooTWjvd2INX-4/edit"

try:
    if data_source_type == "Use Google Sheet Link":
        user_url = st.sidebar.text_input("Google Sheet URL:", value=DEFAULT_URL)
        if user_url:
            data_dict = load_from_url(user_url)
    else:
        uploaded_file = st.sidebar.file_uploader("Upload .xlsx file", type=['xlsx'])
        if uploaded_file:
            data_dict = load_from_file(uploaded_file)

    if data_dict is not None:
        st.title("📊 Disease-wise Trend Analysis")
        tabs = st.tabs(list(data_dict.keys()))
        months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        weeks_list = ["WEEK 1", "WEEK 2", "WEEK 3", "WEEK 4"]

        for i, sheet_name in enumerate(data_dict.keys()):
            with tabs[i]:
                df_25, df_26 = data_dict[sheet_name]['25'], data_dict[sheet_name]['26']
                wards = [w for w in df_26['Ward'].dropna().unique() if w not in ['Ward', 'Total', 'YEAR 2026', 'YEAR 2025']]

                # Row 1: Tables 1 & 2
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("1. Monthly Comparison")
                    f1, f2, f3 = st.columns(3)
                    m1 = f1.selectbox("Month 1", months_list, index=2, key=f"m1_{i}")
                    m2 = f2.selectbox("Month 2", months_list, index=3, key=f"m2_{i}")
                    wt1 = f3.selectbox("Up to", weeks_list, key=f"wt1_{i}")
                    t1_res = []
                    for w in wards:
                        v1 = get_sum_up_to_week(df_26, w, m1, wt1, months_list, weeks_list)
                        v2 = get_sum_up_to_week(df_26, w, m2, wt1, months_list, weeks_list)
                        t1_res.append({'Ward':w, m1:v1, m2:v2, '% Inc/Dec':format_pct(((v2-v1)/v1) if v1 > 0 else 0)})
                    df1 = display_table(t1_res, [m1, m2], '% Inc/Dec')
                    t1_title = f"1. Monthly Comparison: {m1} vs {m2} (Up to {wt1})"

                with col2:
                    st.subheader("2. Yearly Comparison")
                    f1, f2, f3, f4 = st.columns(4)
                    ym25 = f1.selectbox("2025 Month", months_list, index=3, key=f"ym25_{i}")
                    yw25 = f2.selectbox("2025 Week", weeks_list, key=f"yw25_{i}")
                    ym26 = f3.selectbox("2026 Month", months_list, index=3, key=f"ym26_{i}")
                    yw26 = f4.selectbox("2026 Week", weeks_list, key=f"yw26_{i}")
                    t2_res = []
                    for w in wards:
                        v1 = get_sum_up_to_week(df_25, w, ym25, yw25, months_list, weeks_list)
                        v2 = get_sum_up_to_week(df_26, w, ym26, yw26, months_list, weeks_list)
                        t2_res.append({'Ward':w, '2025':v1, '2026':v2, '% Inc/Dec':format_pct(((v2-v1)/v1) if v1 > 0 else 0)})
                    df2 = display_table(t2_res, ['2025', '2026'], '% Inc/Dec')
                    t2_title = f"2. Yearly Comparison: 2025 vs 2026"

                # Row 2: Tables 3 & 4
                col3, col4 = st.columns(2)
                with col3:
                    st.subheader("3. Cumulative Comparison")
                    f1, f2 = st.columns(2)
                    cm = f1.selectbox("End Month", months_list, index=3, key=f"cm_{i}")
                    cw = f2.selectbox("End Week", weeks_list, key=f"cw_{i}")
                    t3_res = []
                    for w in wards:
                        v1 = get_cumulative_sum(df_25, w, cm, cw, months_list, weeks_list)
                        v2 = get_cumulative_sum(df_26, w, cm, cw, months_list, weeks_list)
                        t3_res.append({'Ward':w, '2025 Cum':v1, '2026 Cum':v2, '% Inc/Dec':format_pct(((v2-v1)/v1) if v1 > 0 else 0)})
                    df3 = display_table(t3_res, ['2025 Cum', '2026 Cum'], '% Inc/Dec')
                    t3_title = f"3. Cumulative Comparison: Jan to {cm} ({cw})"

                with col4:
                    st.subheader("4. Summary Trends (%)")
                    # Prepare Summary Data
                    t4_res = [{'Ward': w, 'Monthly %': t1_res[idx]['% Inc/Dec'], 'Yearly %': t2_res[idx]['% Inc/Dec'], 'Cum %': t3_res[idx]['% Inc/Dec']} for idx, w in enumerate(wards)]
                    t4_total = {'Ward':'Total', 'Monthly %': df1.iloc[-1]['% Inc/Dec'], 'Yearly %': df2.iloc[-1]['% Inc/Dec'], 'Cum %': df3.iloc[-1]['% Inc/Dec']}
                    df4_final = pd.concat([pd.DataFrame(t4_res), pd.DataFrame([t4_total])], ignore_index=True)
                    st.table(df4_final)

                    # --- Line Chart (Clean version without data labels) ---
                    st.write("#### 📈 Trend Visualization (Wards Only)")
                    df_ch = pd.DataFrame(t4_res)
                    for col in ['Monthly %', 'Yearly %', 'Cum %']:
                        df_ch[col] = df_ch[col].str.replace(' %', '').astype(float)
                    
                    df_melted = df_ch.melt(id_vars='Ward', var_name='Metric', value_name='Percentage')
                    fig = px.line(df_melted, x='Ward', y='Percentage', color='Metric', markers=True)
                    fig.update_layout(xaxis_title="Wards", yaxis_title="Percentage (%)", height=450)
                    st.plotly_chart(fig, use_container_width=True)

                # --- Excel Side-by-Side Download Logic ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter', engine_kwargs={'options': {'nan_inf_to_errors': True}}) as writer:
                    wb, ws = writer.book, writer.book.add_worksheet("Analysis_Report")
                    h_fmt = wb.add_format({'bold':True, 'bg_color':'#D7E4BC', 'border':1, 'align':'center'})
                    c_fmt = wb.add_format({'border':1, 'align':'center'})
                    t_fmt = wb.add_format({'bold':True, 'font_size':11, 'font_color':'#1F4E78'})
                    
                    def write_side(df, start_col, title):
                        df_c = df.replace([np.inf, -np.inf], 0).fillna(0)
                        ws.write(0, start_col, title, t_fmt)
                        for c, col in enumerate(df_c.columns): 
                            ws.write(2, start_col+c, col, h_fmt)
                        for r, row in enumerate(df_c.values):
                            for c, val in enumerate(row): 
                                ws.write(r+3, start_col+c, val, c_fmt)
                        return start_col + len(df_c.columns) + 1

                    curr = write_side(df1, 0, t1_title)
                    curr = write_side(df2, curr, t2_title)
                    curr = write_side(df3, curr, t3_title)
                    write_side(df4_final, curr, "4. Summary Trends (%)")
                
                st.download_button(label=f"📥 Download {sheet_name} Report", data=output.getvalue(),
                                   file_name=f"{sheet_name}_Analysis.xlsx", key=f"dl_{i}")
    else:
        st.info("👈 Please select a data source from the sidebar to begin.")

except Exception as e:
    st.error(f"An error occurred: {e}")
