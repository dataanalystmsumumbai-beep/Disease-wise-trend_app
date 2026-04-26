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
        weeks_list = ["WEEK 1", "WEEK 2", "WEEK 3", "WEEK 4"]

        for i, sheet_name in enumerate(data_dict.keys()):
            with tabs[i]:
                df_25, df_26 = data_dict[sheet_name]['25'], data_dict[sheet_name]['26']
                wards = [w for w in df_26['Ward'].dropna().unique() if w not in ['Ward', 'Total', 'YEAR 2026', 'YEAR 2025']]

                # 1. Monthly
                st.subheader("1. Monthly Comparison")
                c1, c2, c3 = st.columns(3)
                m1, m2 = c1.selectbox("Start Month", months_list, index=2, key=f"m1_{i}"), c2.selectbox("End Month", months_list, index=3, key=f"m2_{i}")
                wt1 = c3.selectbox("Week", weeks_list, key=f"wt1_{i}")
                t1_res = [{'Ward':w, m1: (v1:=get_sum_up_to_week(df_26, w, m1, wt1, months_list, weeks_list)), m2: (v2:=get_sum_up_to_week(df_26, w, m2, wt1, months_list, weeks_list)), '% Inc/Dec':format_pct(((v2-v1)/v1) if v1 > 0 else 0), '_raw_diff': ((v2-v1)/v1) if v1 > 0 else 0} for w in wards]
                df1 = calculate_table(t1_res, [m1, m2], '% Inc/Dec')
                st.table(df1)

                # 2. Yearly
                st.subheader("2. Yearly Comparison")
                y1, y2, y3, y4 = st.columns(4)
                m25, w25 = y1.selectbox("2025 Month", months_list, index=3, key=f"m25_{i}"), y2.selectbox("2025 Week", weeks_list, key=f"w25_{i}")
                m26, w26 = y3.selectbox("2026 Month", months_list, index=3, key=f"m26_{i}"), y4.selectbox("2026 Week", weeks_list, key=f"w26_{i}")
                t2_res = [{'Ward':w, '2025': (v25:=get_sum_up_to_week(df_25, w, m25, w25, months_list, weeks_list)), '2026': (v26:=get_sum_up_to_week(df_26, w, m26, w26, months_list, weeks_list)), '% Inc/Dec':format_pct(((v26-v25)/v25) if v25 > 0 else 0), '_raw_diff': ((v26-v25)/v25) if v25 > 0 else 0} for w in wards]
                df2 = calculate_table(t2_res, ['2025', '2026'], '% Inc/Dec')
                st.table(df2)

                # 3. Cumulative
                st.subheader("3. Cumulative Comparison")
                cu1, cu2 = st.columns(2)
                cm, cw = cu1.selectbox("Month", months_list, index=3, key=f"cm_{i}"), cu2.selectbox("Week", weeks_list, key=f"cw_{i}")
                t3_res = [{'Ward':w, '2025 Cum': (v25c:=get_cumulative_sum(df_25, w, cm, cw, months_list, weeks_list)), '2026 Cum': (v26c:=get_cumulative_sum(df_26, w, cm, cw, months_list, weeks_list)), '% Inc/Dec':format_pct(((v26c-v25c)/v25c) if v25c > 0 else 0), '_raw_diff': ((v26c-v25c)/v25c) if v25c > 0 else 0} for w in wards]
                df3 = calculate_table(t3_res, ['2025 Cum', '2026 Cum'], '% Inc/Dec')
                st.table(df3)

                # 4. Summary Trend
                st.subheader("4. Summary Trend Analysis (%)")
                t4_res = [{'Ward': w, 'Monthly %': t1_res[idx]['% Inc/Dec'], 'Yearly %': t2_res[idx]['% Inc/Dec'], 'Cum %': t3_res[idx]['% Inc/Dec']} for idx, w in enumerate(wards)]
                df4 = pd.concat([pd.DataFrame(t4_res), pd.DataFrame([{'Ward':'Total', 'Monthly %': df1.iloc[-1]['% Inc/Dec'], 'Yearly %': df2.iloc[-1]['% Inc/Dec'], 'Cum %': df3.iloc[-1]['% Inc/Dec']}])], ignore_index=True)
                st.table(df4)

                # --- DASHBOARD GRAPH ---
                st.markdown("---")
                st.subheader("📈 Summary Trends Graph")
                df_graph = pd.DataFrame(t4_res)
                for col in ['Monthly %', 'Yearly %', 'Cum %']:
                    df_graph[col] = df_graph[col].str.replace(' %', '').astype(float)
                df_melted = df_graph.melt(id_vars='Ward', var_name='Metric', value_name='Percentage')
                fig = px.line(df_melted, x='Ward', y='Percentage', color='Metric', markers=True)
                st.plotly_chart(fig, use_container_width=True)

                # Rankings
                def get_rank_dfs(res_list, col_name):
                    top = pd.DataFrame([{'Ward': x['Ward'], col_name: x['% Inc/Dec']} for x in sorted(res_list, key=lambda x: x['_raw_diff'], reverse=True)[:5]])
                    bot = pd.DataFrame([{'Ward': x['Ward'], col_name: x['% Inc/Dec']} for x in sorted(res_list, key=lambda x: x['_raw_diff'], reverse=False)[:5]])
                    return top, bot

                dt_m, db_m = get_rank_dfs(t1_res, "Monthly %")
                dt_y, db_y = get_rank_dfs(t2_res, "Yearly %")
                dt_c, db_c = get_rank_dfs(t3_res, "Cum %")

                r_col1, r_col2, r_col3 = st.columns(3)
                with r_col1: st.write("**Monthly Ranks**"); st.table(dt_m); st.table(db_m)
                with r_col2: st.write("**Yearly Ranks**"); st.table(dt_y); st.table(db_y)
                with r_col3: st.write("**Cumulative Ranks**"); st.table(dt_c); st.table(db_c)

                # --- EXCEL EXPORT WITH HIGHLIGHTS & BORDERS ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    workbook = writer.book
                    header_fmt = workbook.add_format({'bold': True, 'bg_color': '#BDD7EE', 'border': 1, 'align': 'center'})
                    cell_fmt = workbook.add_format({'border': 1, 'align': 'center'})
                    title_fmt = workbook.add_format({'bold': True, 'font_size': 12, 'font_color': '#1F4E78'})
                    
                    # 1. Trend_Chart Sheet
                    ws_c = workbook.add_worksheet('Trend_Chart')
                    for c, h in enumerate(["Ward", "Monthly %", "Yearly %", "Cum %"]): ws_c.write(1, c, h, header_fmt)
                    for r, row in enumerate(t4_res):
                        ws_c.write(r+2, 0, row['Ward'], cell_fmt)
                        ws_c.write(r+2, 1, float(row['Monthly %'].replace(' %','')), cell_fmt)
                        ws_c.write(r+2, 2, float(row['Yearly %'].replace(' %','')), cell_fmt)
                        ws_c.write(r+2, 3, float(row['Cum %'].replace(' %','')), cell_fmt)
                    
                    chart = workbook.add_chart({'type': 'line'})
                    for i in range(1, 4):
                        chart.add_series({'name':['Trend_Chart',1,i],'categories':['Trend_Chart',2,0,len(t4_res)+1,0],'values':['Trend_Chart',2,i,len(t4_res)+1,i],'marker':{'type':'circle'}})
                    ws_c.insert_chart('F2', chart)

                    # 2. Analysis_Tables Sheet
                    ws_t = workbook.add_worksheet('Analysis_Tables')
                    col_pos = [0, 5, 10, 15]
                    table_dfs = [df1, df2, df3, df4]
                    table_titles = ["1. Monthly Comparison", "2. Yearly Comparison", "3. Cumulative Comparison", "4. Summary Trends (%)"]
                    
                    for idx, df_to_write in enumerate(table_dfs):
                        ws_t.write(0, col_pos[idx], table_titles[idx], title_fmt)
                        # Write Headers manually for styling
                        for c_idx, col_name in enumerate(df_to_write.columns):
                            ws_t.write(1, col_pos[idx] + c_idx, col_name, header_fmt)
                        # Write Data
                        for r_idx, row_val in enumerate(df_to_write.values):
                            for c_idx, val in enumerate(row_val):
                                ws_t.write(r_idx + 2, col_pos[idx] + c_idx, val, cell_fmt)

                    # Rankings below main tables
                    rank_row = len(df1) + 5
                    ws_t.write(rank_row, 0, "🏆 Top 5 Increase Rankings", title_fmt)
                    rank_dfs_top = [dt_m, dt_y, dt_c]
                    for idx, rdf in enumerate(rank_dfs_top):
                        for c_idx, col_name in enumerate(rdf.columns): ws_t.write(rank_row+1, (idx*3)+c_idx, col_name, header_fmt)
                        for r_idx, row_val in enumerate(rdf.values):
                            for c_idx, val in enumerate(row_val): ws_t.write(rank_row+2+r_idx, (idx*3)+c_idx, val, cell_fmt)

                    ws_t.write(rank_row+8, 0, "📉 Bottom 5 Decrease Rankings", title_fmt)
                    rank_dfs_bot = [db_m, db_y, db_c]
                    for idx, rdf in enumerate(rank_dfs_bot):
                        for c_idx, col_name in enumerate(rdf.columns): ws_t.write(rank_row+9, (idx*3)+c_idx, col_name, header_fmt)
                        for r_idx, row_val in enumerate(rdf.values):
                            for c_idx, val in enumerate(row_val): ws_t.write(rank_row+10+r_idx, (idx*3)+c_idx, val, cell_fmt)

                st.download_button(label="📥 Download Professional Report", data=output.getvalue(), file_name=f"{sheet_name}_Health_Report.xlsx")

except Exception as e:
    st.error(f"Error occurred: {e}")
