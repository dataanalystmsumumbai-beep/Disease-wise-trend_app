import streamlit as st
import pandas as pd
import io
import numpy as np
import plotly.express as px

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
    clean_list = [{k:v for k,v in d.items() if k != '_raw_diff'} for d in data_list]
    df = pd.DataFrame(clean_list)
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

# --- 4. Main App UI ---
st.sidebar.header("📁 Data Source")
data_source_type = st.sidebar.radio("Choose Input Method:", ("Use Google Sheet Link", "Upload Excel File"))
DEFAULT_URL = "https://docs.google.com/spreadsheets/d/11-ZeoBvixvY_ujLO8_9Vlze2jmGC4CooTWjvd2INX-4/edit"

try:
    if data_source_type == "Use Google Sheet Link":
        user_url = st.sidebar.text_input("Google Sheet URL:", value=DEFAULT_URL)
        data_dict = load_from_url(user_url) if user_url else None
    else:
        uploaded_file = st.sidebar.file_uploader("Upload .xlsx file", type=['xlsx'])
        data_dict = load_from_file(uploaded_file) if uploaded_file else None

    if data_dict:
        st.title("📊 Disease-wise Trend Analysis")
        tabs = st.tabs(list(data_dict.keys()))
        months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        weeks_list = ["WEEK 1", "WEEK 2", "WEEK 3", "WEEK 4"]

        for i, sheet_name in enumerate(data_dict.keys()):
            with tabs[i]:
                df_25, df_26 = data_dict[sheet_name]['25'], data_dict[sheet_name]['26']
                wards = [w for w in df_26['Ward'].dropna().unique() if w not in ['Ward', 'Total', 'YEAR 2026', 'YEAR 2025']]

                # Table 1: Monthly Comparison
                st.subheader("1. Monthly Comparison")
                col1, col2, col3 = st.columns(3)
                m1 = col1.selectbox("Month 1", months_list, index=2, key=f"m1_{sheet_name}")
                m2 = col2.selectbox("Month 2", months_list, index=3, key=f"m2_{sheet_name}")
                wt1 = col3.selectbox("Up to Week", weeks_list, key=f"wt1_{sheet_name}")
                t1_res = []
                for w in wards:
                    v1 = get_sum_up_to_week(df_26, w, m1, wt1, months_list, weeks_list)
                    v2 = get_sum_up_to_week(df_26, w, m2, wt1, months_list, weeks_list)
                    diff = ((v2-v1)/v1) if v1 > 0 else 0
                    t1_res.append({'Ward':w, m1:v1, m2:v2, '% Inc/Dec':format_pct(diff), '_raw_diff': diff})
                df1 = display_table(t1_res, [m1, m2], '% Inc/Dec')

                # Table 2: Yearly Comparison
                st.subheader("2. Yearly Comparison")
                y1, y2, y3, y4 = st.columns(4)
                m25, w25 = y1.selectbox("25 Month", months_list, index=3, key=f"m25_{sheet_name}"), y2.selectbox("25 Week", weeks_list, key=f"w25_{sheet_name}")
                m26, w26 = y3.selectbox("26 Month", months_list, index=3, key=f"m26_{sheet_name}"), y4.selectbox("26 Week", weeks_list, key=f"w26_{sheet_name}")
                t2_res = []
                for w in wards:
                    v25 = get_sum_up_to_week(df_25, w, m25, w25, months_list, weeks_list)
                    v26 = get_sum_up_to_week(df_26, w, m26, w26, months_list, weeks_list)
                    diff = ((v26-v25)/v25) if v25 > 0 else 0
                    t2_res.append({'Ward':w, '2025':v25, '2026':v26, '% Inc/Dec':format_pct(diff), '_raw_diff': diff})
                df2 = display_table(t2_res, ['2025', '2026'], '% Inc/Dec')

                # Table 3: Cumulative
                st.subheader("3. Cumulative Comparison")
                c1, c2 = st.columns(2)
                cm, cw = c1.selectbox("End Month", months_list, index=3, key=f"cm_{sheet_name}"), c2.selectbox("End Week", weeks_list, key=f"cw_{sheet_name}")
                t3_res = []
                for w in wards:
                    v25c = get_cumulative_sum(df_25, w, cm, cw, months_list, weeks_list)
                    v26c = get_cumulative_sum(df_26, w, cm, cw, months_list, weeks_list)
                    diff = ((v26c-v25c)/v25c) if v25c > 0 else 0
                    t3_res.append({'Ward':w, '2025 Cum':v25c, '2026 Cum':v26c, '% Inc/Dec':format_pct(diff), '_raw_diff': diff})
                df3 = display_table(t3_res, ['2025 Cum', '2026 Cum'], '% Inc/Dec')

                # Table 4: Summary Trends
                st.subheader("4. Summary Trends (%)")
                t4_res = [{'Ward': w, 'Monthly %': t1_res[idx]['% Inc/Dec'], 'Yearly %': t2_res[idx]['% Inc/Dec'], 'Cum %': t3_res[idx]['% Inc/Dec']} for idx, w in enumerate(wards)]
                t4_total = {'Ward':'Total', 'Monthly %': df1.iloc[-1]['% Inc/Dec'], 'Yearly %': df2.iloc[-1]['% Inc/Dec'], 'Cum %': df3.iloc[-1]['% Inc/Dec']}
                df4 = pd.concat([pd.DataFrame(t4_res), pd.DataFrame([t4_total])], ignore_index=True)
                st.table(df4)

                # Top/Bottom 5
                st.markdown("---")
                top5 = sorted(t1_res, key=lambda x: x['_raw_diff'], reverse=True)[:5]
                bot5 = sorted(t1_res, key=lambda x: x['_raw_diff'], reverse=False)[:5]
                df_top = pd.DataFrame([{'Ward': x['Ward'], 'Increase': x['% Inc/Dec']} for x in top5])
                df_bot = pd.DataFrame([{'Ward': x['Ward'], 'Decrease': x['% Inc/Dec']} for x in bot5])
                
                col_t, col_b = st.columns(2)
                with col_t: st.subheader("🏆 Top 5 Increase (Monthly)"); st.table(df_top)
                with col_b: st.subheader("📉 Bottom 5 (Monthly)"); st.table(df_bot)

                # Dashboard Chart
                df_chart_ui = pd.DataFrame(t4_res)
                for col in ['Monthly %', 'Yearly %', 'Cum %']: 
                    df_chart_ui[col] = df_chart_ui[col].str.replace(' %', '').astype(float)
                fig = px.line(df_chart_ui.melt(id_vars='Ward'), x='Ward', y='value', color='variable', markers=True)
                st.plotly_chart(fig, use_container_width=True)

                # --- ADVANCED EXCEL EXPORT (2 SHEETS) ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    workbook = writer.book
                    
                    # 1. CHART SHEET
                    ws_chart = workbook.add_worksheet('Trend_Chart')
                    h_fmt = workbook.add_format({'bold':True, 'bg_color':'#D7E4BC', 'border':1})
                    n_fmt = workbook.add_format({'border':1})
                    
                    # Hidden Data for Chart
                    ws_chart.write(0, 0, "Source Data (Used for Chart)", workbook.add_format({'italic': True}))
                    chart_headers = ["Ward", "Monthly %", "Yearly %", "Cum %"]
                    for c, h in enumerate(chart_headers): ws_chart.write(1, c, h, h_fmt)
                    
                    for r, row in enumerate(t4_res):
                        ws_chart.write(r+2, 0, row['Ward'], n_fmt)
                        ws_chart.write(r+2, 1, float(row['Monthly %'].replace(' %','')), n_fmt)
                        ws_chart.write(r+2, 2, float(row['Yearly %'].replace(' %','')), n_fmt)
                        ws_chart.write(r+2, 3, float(row['Cum %'].replace(' %','')), n_fmt)
                    
                    # Create Native Chart
                    excel_chart = workbook.add_chart({'type': 'line'})
                    last_r = len(t4_res) + 1
                    for i in range(1, 4):
                        excel_chart.add_series({
                            'name':       ['Trend_Chart', 1, i],
                            'categories': ['Trend_Chart', 2, 0, last_r, 0],
                            'values':     ['Trend_Chart', 2, i, last_r, i],
                            'marker':     {'type': 'circle'}
                        })
                    excel_chart.set_title({'name': f'Trend Analysis - {sheet_name}'})
                    excel_chart.set_size({'width': 900, 'height': 500})
                    ws_chart.insert_chart('F2', excel_chart)

                    # 2. TABLES SHEET
                    ws_table = workbook.add_worksheet('Analysis_Tables')
                    title_fmt = workbook.add_format({'bold':True, 'font_size':14, 'font_color':'#1F4E78'})
                    
                    def write_table_block(df, row, col, title):
                        ws_table.write(row, col, title, title_fmt)
                        df.to_excel(writer, sheet_name='Analysis_Tables', startrow=row+1, startcol=col, index=False)
                        return row + len(df) + 4

                    curr_r = write_table_block(df1, 0, 0, "1. Monthly Comparison")
                    curr_r = write_table_block(df2, curr_r, 0, "2. Yearly Comparison")
                    curr_r = write_table_block(df3, curr_r, 0, "3. Cumulative Comparison")
                    curr_r = write_table_block(df4, curr_r, 0, "4. Summary Trends (%)")
                    
                    # Top/Bottom side by side
                    ws_table.write(curr_r, 0, "Top 5 Increase", title_fmt)
                    df_top.to_excel(writer, sheet_name='Analysis_Tables', startrow=curr_r+1, startcol=0, index=False)
                    ws_table.write(curr_r, 3, "Bottom 5", title_fmt)
                    df_bot.to_excel(writer, sheet_name='Analysis_Tables', startrow=curr_r+1, startcol=3, index=False)

                st.download_button(label="📥 Download Professional Report", data=output.getvalue(), 
                                   file_name=f"{sheet_name}_Health_Report.xlsx")

except Exception as e:
    st.error(f"Error: {e}")
