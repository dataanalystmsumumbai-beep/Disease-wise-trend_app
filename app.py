import streamlit as st
import pandas as pd
import io
import numpy as np
import plotly.express as px

# Page Configuration
st.set_page_config(page_title="Health Analysis Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- 1. Helper Functions ---
def format_pct(val):
    """Formats numeric values into clean percentage strings."""
    if pd.isna(val) or np.isinf(val): return "0 %"
    if val == 0: return "0 %"
    val = val * 100
    if abs(val - round(val)) < 1e-9:
        return f"{int(val)} %"
    else:
        return f"{val:.2f} %"

def get_xlsx_url(url):
    """Converts a Google Sheet 'edit' URL to an 'export' URL."""
    if "/edit" in url:
        return url.split('/edit')[0] + "/export?format=xlsx"
    return url

# --- 2. Data Processing (Dynamic Refresh Enabled) ---
@st.cache_data(ttl=600) # Clears cache every 10 minutes to fetch fresh data
def process_excel_data(_xls):
    all_data = {}
    for sheet in _xls.sheet_names:
        df_raw = pd.read_excel(_xls, sheet_name=sheet, header=None)
        # Extract Month and Week headers
        months = df_raw.iloc[0, 2:].ffill().tolist()
        weeks = df_raw.iloc[1, 2:].tolist()
        cols = ['Ward', 'Total'] + [f"{m}_{w}" for m, w in zip(months, weeks)]
        
        data = df_raw.iloc[2:].copy()
        data.columns = cols[:len(data.columns)]
        
        # Split data for 2025 and 2026 based on Ward 'A' occurrences
        ward_a_indices = data[data['Ward'] == 'A'].index.tolist()
        if len(ward_a_indices) >= 2:
            df_25 = data.loc[ward_a_indices[0]:ward_a_indices[1]-2].copy()
            df_26 = data.loc[ward_a_indices[1]-1:].copy()
        else:
            df_25, df_26 = data.iloc[:56], data.iloc[56:]
        
        # Convert numeric columns
        for c in data.columns[1:]:
            df_25[c] = pd.to_numeric(df_25[c], errors='coerce').fillna(0).astype(int)
            df_26[c] = pd.to_numeric(df_26[c], errors='coerce').fillna(0).astype(int)
        
        all_data[sheet] = {'25': df_25, '26': df_26}
    return all_data

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

def calculate_table(data_list, numeric_cols, pct_col_name=None):
    df = pd.DataFrame([{k:v for k,v in d.items() if k != '_raw_diff'} for d in data_list])
    total_row = {'Ward': 'Total'}
    for col in numeric_cols:
        total_row[col] = int(df[col].sum())
    if pct_col_name and len(numeric_cols) >= 2:
        v1, v2 = total_row[numeric_cols[0]], total_row[numeric_cols[1]]
        diff = ((v2 - v1) / v1) if v1 > 0 else 0
        total_row[pct_col_name] = format_pct(diff)
    return pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)

# --- 3. UI Logic ---
st.sidebar.header("📁 Configuration")
data_source_type = st.sidebar.radio("Select Data Source:", ("Google Sheet Link", "Local Excel File"))
DEFAULT_URL = "https://docs.google.com/spreadsheets/d/11-ZeoBvixvY_ujLO8_9Vlze2jmGC4CooTWjvd2INX-4/edit"

try:
    if data_source_type == "Google Sheet Link":
        user_url = st.sidebar.text_input("Enter Google Sheet URL:", value=DEFAULT_URL)
        if user_url:
            xls = pd.ExcelFile(get_xlsx_url(user_url), engine='openpyxl')
            data_dict = process_excel_data(xls)
    else:
        uploaded_file = st.sidebar.file_uploader("Upload Excel (.xlsx) file", type=['xlsx'])
        if uploaded_file:
            xls = pd.ExcelFile(uploaded_file, engine='openpyxl')
            data_dict = process_excel_data(xls)

    if data_dict:
        st.title("📊 Health Infrastructure & Trend Analysis")
        tabs = st.tabs(list(data_dict.keys()))
        months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        weeks_list = ["WEEK 1", "WEEK 2", "WEEK 3", "WEEK 4"]

        for i, sheet_name in enumerate(data_dict.keys()):
            with tabs[i]:
                df_25, df_26 = data_dict[sheet_name]['25'], data_dict[sheet_name]['26']
                wards = [w for w in df_26['Ward'].dropna().unique() if w not in ['Ward', 'Total', 'YEAR 2026', 'YEAR 2025']]

                # --- DYNAMIC DATA DETECTION ---
                # Automatically find the last column with data (> 0)
                all_metric_cols = [c for c in df_26.columns if '_' in c]
                active_col = all_metric_cols[0] 
                for col in all_metric_cols:
                    if df_26[col].sum() > 0:
                        active_col = col 

                active_m, active_w = active_col.split('_')
                m_idx = months_list.index(active_m) if active_m in months_list else 0
                w_idx = weeks_list.index(active_w) if active_w in weeks_list else 0
                prev_m_idx = max(0, m_idx - 1)

                # Section 1: Monthly Comparison
                st.subheader("1. Monthly Comparison")
                c1, c2, c3 = st.columns(3)
                m1 = c1.selectbox("Start Month", months_list, index=prev_m_idx, key=f"m1_{i}")
                m2 = c2.selectbox("End Month", months_list, index=m_idx, key=f"m2_{i}")
                wt1 = c3.selectbox("Comparison Week", weeks_list, index=w_idx, key=f"wt1_{i}")
                
                t1_res = [{'Ward':w, m1: (v1:=get_sum_up_to_week(df_26, w, m1, wt1, months_list, weeks_list)), m2: (v2:=get_sum_up_to_week(df_26, w, m2, wt1, months_list, weeks_list)), '% Inc/Dec':format_pct(((v2-v1)/v1) if v1 > 0 else 0), '_raw_diff': ((v2-v1)/v1) if v1 > 0 else 0} for w in wards]
                df1 = calculate_table(t1_res, [m1, m2], '% Inc/Dec')
                st.table(df1)

                # Section 2: Yearly Comparison
                st.subheader("2. Yearly Comparison")
                y1, y2, y3, y4 = st.columns(4)
                m25 = y1.selectbox("2025 Reference Month", months_list, index=m_idx, key=f"m25_{i}")
                w25 = y2.selectbox("2025 Reference Week", weeks_list, index=w_idx, key=f"w25_{i}")
                m26 = y3.selectbox("2026 Target Month", months_list, index=m_idx, key=f"m26_{i}")
                w26 = y4.selectbox("2026 Target Week", weeks_list, index=w_idx, key=f"w26_{i}")
                
                t2_res = [{'Ward':w, '2025': (v25:=get_sum_up_to_week(df_25, w, m25, w25, months_list, weeks_list)), '2026': (v26:=get_sum_up_to_week(df_26, w, m26, w26, months_list, weeks_list)), '% Inc/Dec':format_pct(((v26-v25)/v25) if v25 > 0 else 0), '_raw_diff': ((v26-v25)/v25) if v25 > 0 else 0} for w in wards]
                df2 = calculate_table(t2_res, ['2025', '2026'], '% Inc/Dec')
                st.table(df2)

                # Section 3: Cumulative Comparison
                st.subheader("3. Cumulative Comparison")
                cu1, cu2 = st.columns(2)
                cm = cu1.selectbox("Analysis Month", months_list, index=m_idx, key=f"cm_{i}")
                cw = cu2.selectbox("Analysis Week", weeks_list, index=w_idx, key=f"cw_{i}")
                
                t3_res = [{'Ward':w, '2025 Cum': (v25c:=get_cumulative_sum(df_25, w, cm, cw, months_list, weeks_list)), '2026 Cum': (v26c:=get_cumulative_sum(df_26, w, cm, cw, months_list, weeks_list)), '% Inc/Dec':format_pct(((v26c-v25c)/v25c) if v25c > 0 else 0), '_raw_diff': ((v26c-v25c)/v25c) if v25c > 0 else 0} for w in wards]
                df3 = calculate_table(t3_res, ['2025 Cum', '2026 Cum'], '% Inc/Dec')
                st.table(df3)

                # Section 4: Summary Trends
                st.subheader("4. Summary Trends Overview (%)")
                t4_res = [{'Ward': w, 'Monthly %': t1_res[idx]['% Inc/Dec'], 'Yearly %': t2_res[idx]['% Inc/Dec'], 'Cum %': t3_res[idx]['% Inc/Dec']} for idx, w in enumerate(wards)]
                df4 = pd.concat([pd.DataFrame(t4_res), pd.DataFrame([{'Ward':'Total', 'Monthly %': df1.iloc[-1]['% Inc/Dec'], 'Yearly %': df2.iloc[-1]['% Inc/Dec'], 'Cum %': df3.iloc[-1]['% Inc/Dec']}])], ignore_index=True)
                st.table(df4)

                # --- DASHBOARD VISUALIZATION ---
                st.markdown("---")
                st.subheader("📈 Summary Trends Visualization")
                df_graph = pd.DataFrame(t4_res)
                for col in ['Monthly %', 'Yearly %', 'Cum %']:
                    df_graph[col] = df_graph[col].str.replace(' %', '').astype(float)
                df_melted = df_graph.melt(id_vars='Ward', var_name='Metric', value_name='Percentage')
                fig = px.line(df_melted, x='Ward', y='Percentage', color='Metric', markers=True)
                # Removed data labels as requested
                st.plotly_chart(fig, use_container_width=True)

                # --- RANKINGS SECTION ---
                def get_rank_dfs(res_list, col_name):
                    top = pd.DataFrame([{'Ward': x['Ward'], col_name: x['% Inc/Dec']} for x in sorted(res_list, key=lambda x: x['_raw_diff'], reverse=True)[:5]])
                    bot = pd.DataFrame([{'Ward': x['Ward'], col_name: x['% Inc/Dec']} for x in sorted(res_list, key=lambda x: x['_raw_diff'], reverse=False)[:5]])
                    return top, bot

                dt_m, db_m = get_rank_dfs(t1_res, "Monthly %")
                dt_y, db_y = get_rank_dfs(t2_res, "Yearly %")
                dt_c, db_c = get_rank_dfs(t3_res, "Cum %")

                st.subheader("🏆 Top 5 Increase Performance")
                r_top1, r_top2, r_top3 = st.columns(3)
                r_top1.table(dt_m); r_top2.table(dt_y); r_top3.table(dt_c)

                st.subheader("📉 Bottom 5 Performance (Decrease)")
                r_bot1, r_bot2, r_bot3 = st.columns(3)
                r_bot1.table(db_m); r_bot2.table(db_y); r_bot3.table(db_c)

                # --- EXCEL REPORT EXPORT ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df1.to_excel(writer, sheet_name='Summary_Report', startrow=1)
                    # Note: You can add full Excel styling logic here as per previous versions
                st.download_button(label="📥 Download Professional Report", data=output.getvalue(), file_name=f"{sheet_name}_Analysis.xlsx")

except Exception as e:
    st.error(f"Application Error: {e}")
