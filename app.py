import streamlit as st
import pandas as pd
import io
import numpy as np
import plotly.express as px

# Page Configuration
st.set_page_config(page_title="Health Analysis Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- 1. Helper Functions ---
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

# --- 2. Data Processing ---
@st.cache_data
def process_excel_data(_xls):
    all_data = {}
    for sheet in _xls.sheet_names:
        df_raw = pd.read_excel(_xls, sheet_name=sheet, header=None)
        
        # --- ROBUST HEADER EXTRACTION (Fix for future months like May, Jun) ---
        # Automatically clean and format months to strictly 3 letters (e.g., "MAY", "May ", "April" -> "May", "Apr")
        raw_months = df_raw.iloc[0, 2:].ffill().astype(str).str.strip().tolist()
        months = [m[:3].capitalize() if m.lower() != 'nan' else 'Unknown' for m in raw_months]
        
        # Clean and format weeks (e.g., "WEEK 1", "week 1", "WEEK  1" -> "WEEK 1")
        raw_weeks = df_raw.iloc[1, 2:].astype(str).str.strip().str.upper().tolist()
        weeks = [w.replace("  ", " ") if w.lower() != 'nan' else 'Unknown' for w in raw_weeks]
        
        cols = ['Ward', 'Total'] + [f"{m}_{w}" for m, w in zip(months, weeks)]
        data = df_raw.iloc[2:].copy()
        data.columns = cols[:len(data.columns)]
        
        # Ensure column renaming if the source uses "Zone/Administrative Ward Name"
        if 'Zone/Administrative Ward Name' in data.columns:
            data.rename(columns={'Zone/Administrative Ward Name': 'Ward'}, inplace=True)
        
        ward_a_indices = data[data['Ward'] == 'A'].index.tolist()
        if len(ward_a_indices) >= 2:
            df_25 = data.loc[ward_a_indices[0]:ward_a_indices[1]-2].copy()
            df_26 = data.loc[ward_a_indices[1]-1:].copy()
        else:
            # Safe Fallback just in case rows shift
            half = len(data) // 2
            df_25, df_26 = data.iloc[:half].copy(), data.iloc[half:].copy()
        
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

def get_sum_up_to_week(df, ward, month, week_str, all_months, all_weeks):
    if week_str not in all_weeks: return 0
    w_idx = all_weeks.index(week_str)
    target_cols = [f"{month}_{all_weeks[i]}" for i in range(w_idx + 1) if f"{month}_{all_weeks[i]}" in df.columns]
    if not target_cols: return 0
    val = df[df['Ward'] == ward][target_cols].values.sum()
    return int(val)

def get_cumulative_sum(df, ward, end_month, end_week, all_months, all_weeks):
    if end_month not in all_months: return 0
    m_idx = all_months.index(end_month)
    target_cols = []
    for m in all_months[:m_idx+1]:
        for w in all_weeks:
            c_name = f"{m}_{w}"
            if c_name in df.columns: target_cols.append(c_name)
            if m == end_month and w == end_week: break
        if m == end_month: break
    if not target_cols: return 0
    return int(df[df['Ward'] == ward][target_cols].values.sum())

def calculate_table(data_list, numeric_cols, pct_col_name=None):
    df = pd.DataFrame([{k:v for k,v in d.items() if k != '_raw_diff'} for d in data_list])
    if df.empty: return df
    total_row = {'Ward': 'Total'}
    for col in numeric_cols:
        if col in df.columns:
            total_row[col] = int(df[col].sum())
    if pct_col_name and len(numeric_cols) >= 2:
        v1, v2 = total_row.get(numeric_cols[0], 0), total_row.get(numeric_cols[1], 0)
        diff = ((v2 - v1) / v1) if v1 > 0 else 0
        total_row[pct_col_name] = format_pct(diff)
    return pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)

# --- 3. UI Logic ---
st.sidebar.header("📁 Configuration")
data_source_type = st.sidebar.radio("Data Source:", ("Google Sheet Link", "Local Excel File"))
DEFAULT_URL = "https://docs.google.com/spreadsheets/d/11-ZeoBvixvY_ujLO8_9Vlze2jmGC4CooTWjvd2INX-4/edit"

try:
    if data_source_type == "Google Sheet Link":
        user_url = st.sidebar.text_input("URL:", value=DEFAULT_URL)
        data_dict = load_from_url(user_url) if user_url else None
    else:
        uploaded_file = st.sidebar.file_uploader("Upload .xlsx", type=['xlsx'])
        data_dict = load_from_file(uploaded_file) if uploaded_file else None

    if data_dict:
        st.title("📊 Health Infrastructure & Trend Analysis")
        tabs = st.tabs(list(data_dict.keys()))
        months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        weeks_list = ["WEEK 1", "WEEK 2", "WEEK 3", "WEEK 4", "WEEK 5"] # Safe measure if some months have 5 weeks

        for i, sheet_name in enumerate(data_dict.keys()):
            with tabs[i]:
                df_25, df_26 = data_dict[sheet_name]['25'], data_dict[sheet_name]['26']
                wards = [w for w in df_26['Ward'].dropna().unique() if w not in ['Ward', 'Total', 'YEAR 2026', 'YEAR 2025']]

                # --- DYNAMIC DATA DETECTION (IMPROVED) ---
                active_m, active_w = "Jan", "WEEK 1"
                data_cols = [c for c in df_26.columns if '_' in c]
                for col in data_cols:
                    if df_26[col].sum() > 0: # Check if column has data
                        parts = col.split('_')
                        if len(parts) == 2:
                            c_m, c_w = parts[0], parts[1]
                            # Only set if it matches our standard list
                            if c_m in months_list and c_w in weeks_list:
                                active_m, active_w = c_m, c_w
                
                # Setup default indexes based on actual data
                m_idx = months_list.index(active_m) if active_m in months_list else 0
                w_idx = weeks_list.index(active_w) if active_w in weeks_list else 0
                prev_m_idx = max(0, m_idx - 1)

                # 1. Monthly
                st.subheader("1. Monthly Comparison")
                c1, c2, c3 = st.columns(3)
                m1 = c1.selectbox("Start Month", months_list, index=prev_m_idx, key=f"m1_{i}")
                m2 = c2.selectbox("End Month", months_list, index=m_idx, key=f"m2_{i}")
                wt1 = c3.selectbox("Week", weeks_list, index=w_idx, key=f"wt1_{i}")
                
                t1_res = [{'Ward':w, m1: (v1:=get_sum_up_to_week(df_26, w, m1, wt1, months_list, weeks_list)), m2: (v2:=get_sum_up_to_week(df_26, w, m2, wt1, months_list, weeks_list)), '% Inc/Dec':format_pct(((v2-v1)/v1) if v1 > 0 else 0), '_raw_diff': ((v2-v1)/v1) if v1 > 0 else 0} for w in wards]
                df1 = calculate_table(t1_res, [m1, m2], '% Inc/Dec')
                st.table(df1)

                # 2. Yearly
                st.subheader("2. Yearly Comparison")
                y1, y2, y3, y4 = st.columns(4)
                m25 = y1.selectbox("2025 Month", months_list, index=m_idx, key=f"m25_{i}")
                w25 = y2.selectbox("2025 Week", weeks_list, index=w_idx, key=f"w25_{i}")
                m26 = y3.selectbox("2026 Month", months_list, index=m_idx, key=f"m26_{i}")
                w26 = y4.selectbox("2026 Week", weeks_list, index=w_idx, key=f"w26_{i}")
                
                t2_res = [{'Ward':w, '2025': (v25:=get_sum_up_to_week(df_25, w, m25, w25, months_list, weeks_list)), '2026': (v26:=get_sum_up_to_week(df_26, w, m26, w26, months_list, weeks_list)), '% Inc/Dec':format_pct(((v26-v25)/v25) if v25 > 0 else 0), '_raw_diff': ((v26-v25)/v25) if v25 > 0 else 0} for w in wards]
                df2 = calculate_table(t2_res, ['2025', '2026'], '% Inc/Dec')
                st.table(df2)

                # 3. Cumulative
                st.subheader("3. Cumulative Comparison")
                cu1, cu2 = st.columns(2)
                cm = cu1.selectbox("Month", months_list, index=m_idx, key=f"cm_{i}")
                cw = cu2.selectbox("Week", weeks_list, index=w_idx, key=f"cw_{i}")
                
                t3_res = [{'Ward':w, '2025 Cum': (v25c:=get_cumulative_sum(df_25, w, cm, cw, months_list, weeks_list)), '2026 Cum': (v26c:=get_cumulative_sum(df_26, w, cm, cw, months_list, weeks_list)), '% Inc/Dec':format_pct(((v26c-v25c)/v25c) if v25c > 0 else 0), '_raw_diff': ((v26c-v25c)/v25c) if v25c > 0 else 0} for w in wards]
                df3 = calculate_table(t3_res, ['2025 Cum', '2026 Cum'], '% Inc/Dec')
                st.table(df3)

                # 4. Summary Trend Overview
                st.subheader("4. Summary Trends Overview (%)")
                t4_res = [{'Ward': w, 'Monthly %': t1_res[idx]['% Inc/Dec'], 'Yearly %': t2_res[idx]['% Inc/Dec'], 'Cum %': t3_res[idx]['% Inc/Dec']} for idx, w in enumerate(wards)]
                df4 = pd.concat([pd.DataFrame(t4_res), pd.DataFrame([{'Ward':'Total', 'Monthly %': df1.iloc[-1]['% Inc/Dec'] if not df1.empty else "0 %", 'Yearly %': df2.iloc[-1]['% Inc/Dec'] if not df2.empty else "0 %", 'Cum %': df3.iloc[-1]['% Inc/Dec'] if not df3.empty else "0 %"}])], ignore_index=True)
                st.table(df4)

                # --- DASHBOARD VISUALIZATION ---
                st.markdown("---")
                st.subheader("📈 Summary Trends Visualization")
                df_graph = pd.DataFrame(t4_res)
                for col in ['Monthly %', 'Yearly %', 'Cum %']:
                    df_graph[col] = df_graph[col].str.replace(' %', '').astype(float)
                df_melted = df_graph.melt(id_vars='Ward', var_name='Metric', value_name='Percentage')
                fig = px.line(df_melted, x='Ward', y='Percentage', color='Metric', markers=True)
                st.plotly_chart(fig, use_container_width=True)

                # --- DASHBOARD RANKINGS ---
                def get_rank_dfs(res_list, col_name):
                    top = pd.DataFrame([{'Ward': x['Ward'], col_name: x['% Inc/Dec']} for x in sorted(res_list, key=lambda x: x['_raw_diff'], reverse=True)[:5]])
                    bot = pd.DataFrame([{'Ward': x['Ward'], col_name: x['% Inc/Dec']} for x in sorted(res_list, key=lambda x: x['_raw_diff'], reverse=False)[:5]])
                    return top, bot

                dt_m, db_m = get_rank_dfs(t1_res, "Monthly %")
                dt_y, db_y = get_rank_dfs(t2_res, "Yearly %")
                dt_c, db_c = get_rank_dfs(t3_res, "Cum %")

                st.subheader("🏆 Top 5 Increase Rankings")
                r_top1, r_top2, r_top3 = st.columns(3)
                r_top1.table(dt_m); r_top2.table(dt_y); r_top3.table(dt_c)

                st.subheader("📉 Bottom 5 Decrease Rankings")
                r_bot1, r_bot2, r_bot3 = st.columns(3)
                r_bot1.table(db_m); r_bot2.table(db_y); r_bot3.table(db_c)

                # --- EXCEL EXPORT LOGIC ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    workbook = writer.book
                    header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1, 'align': 'center'})
                    cell_fmt = workbook.add_format({'border': 1, 'align': 'center'})
                    title_fmt = workbook.add_format({'bold': True, 'font_size': 11, 'font_color': '#1F4E78'})
                    
                    ws_t = workbook.add_worksheet('Analysis_Tables')
                    titles = [
                        f"1. Monthly Comparison (2026): {m1} vs {m2} (Up to {wt1})",
                        f"2. Yearly Comparison: 2025 ({m25}-{w25}) vs 2026 ({m26}-{w26})",
                        f"3. Cumulative: Jan to {cm} ({cw})",
                        "4. Summary Trends Overview (%)"
                    ]
                    offsets = [0, 5, 10, 15]
                    table_dfs = [df1, df2, df3, df4]
                    
                    for idx, df_to_write in enumerate(table_dfs):
                        ws_t.merge_range(0, offsets[idx], 0, offsets[idx] + 3, titles[idx], title_fmt)
                        for c_idx, col_name in enumerate(df_to_write.columns):
                            ws_t.write(1, offsets[idx] + c_idx, col_name, header_fmt)
                        for r_idx, row_val in enumerate(df_to_write.values):
                            for c_idx, val in enumerate(row_val):
                                ws_t.write(r_idx + 2, offsets[idx] + c_idx, val, cell_fmt)

                    # Export Rankings to Excel
                    rank_row = len(df1) + 5
                    ws_t.write(rank_row, 0, "🏆 Top 5 Increase", title_fmt)
                    rank_tops = [dt_m, dt_y, dt_c]
                    for idx, rdf in enumerate(rank_tops):
                        for c_idx, col_name in enumerate(rdf.columns): ws_t.write(rank_row+1, (idx*3)+c_idx, col_name, header_fmt)
                        for r_idx, row_val in enumerate(rdf.values):
                            for c_idx, val in enumerate(row_val): ws_t.write(rank_row+2+r_idx, (idx*3)+c_idx, val, cell_fmt)

                    bot_row = rank_row + 8
                    ws_t.write(bot_row, 0, "📉 Bottom 5 Decrease", title_fmt)
                    rank_bots = [db_m, db_y, db_c]
                    for idx, rdf in enumerate(rank_bots):
                        for c_idx, col_name in enumerate(rdf.columns): ws_t.write(bot_row+1, (idx*3)+c_idx, col_name, header_fmt)
                        for r_idx, row_val in enumerate(rdf.values):
                            for c_idx, val in enumerate(row_val): ws_t.write(bot_row+2+r_idx, (idx*3)+c_idx, val, cell_fmt)

                    # Export Chart Sheet
                    ws_c = workbook.add_worksheet('Trend_Chart')
                    for c, h in enumerate(["Ward", "Monthly %", "Yearly %", "Cum %"]): ws_c.write(0, c, h, header_fmt)
                    for r, row in enumerate(t4_res):
                        ws_c.write(r+1, 0, row['Ward'], cell_fmt)
                        ws_c.write(r+1, 1, float(row['Monthly %'].replace(' %','')), cell_fmt)
                        ws_c.write(r+1, 2, float(row['Yearly %'].replace(' %','')), cell_fmt)
                        ws_c.write(r+1, 3, float(row['Cum %'].replace(' %','')), cell_fmt)
                    excel_chart = workbook.add_chart({'type': 'line'})
                    for i in range(1, 4):
                        excel_chart.add_series({'name':['Trend_Chart',0,i],'categories':['Trend_Chart',1,0,len(t4_res),0],'values':['Trend_Chart',1,i,len(t4_res),i],'marker':{'type':'circle'}})
                    ws_c.insert_chart('F2', excel_chart)

                st.download_button(label="📥 Download Professional Report", data=output.getvalue(), file_name=f"{sheet_name}_Analysis.xlsx")

except Exception as e:
    st.error(f"Error occurred: {e}")
