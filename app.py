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

data_dict = None
DEFAULT_URL = "https://docs.google.com/spreadsheets/d/11-ZeoBvixvY_ujLO8_9Vlze2jmGC4CooTWjvd2INX-4/edit"

try:
    if data_source_type == "Use Google Sheet Link":
        user_url = st.sidebar.text_input("Google Sheet URL:", value=DEFAULT_URL)
        if user_url: data_dict = load_from_url(user_url)
    else:
        uploaded_file = st.sidebar.file_uploader("Upload .xlsx file", type=['xlsx'])
        if uploaded_file: data_dict = load_from_file(uploaded_file)

    if data_dict is not None:
        st.title("📊 Disease-wise Trend Analysis")
        tabs = st.tabs(list(data_dict.keys()))
        months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        weeks_list = ["WEEK 1", "WEEK 2", "WEEK 3", "WEEK 4"]

        for i, sheet_name in enumerate(data_dict.keys()):
            with tabs[i]:
                df_25, df_26 = data_dict[sheet_name]['25'], data_dict[sheet_name]['26']
                wards = [w for w in df_26['Ward'].dropna().unique() if w not in ['Ward', 'Total', 'YEAR 2026', 'YEAR 2025']]

                # Tables Logic
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("1. Monthly Comparison")
                    f1, f2, f3 = st.columns(3)
                    m1, m2, wt1 = f1.selectbox("Month 1", months_list, index=2, key=f"m1_{sheet_name}"), f2.selectbox("Month 2", months_list, index=3, key=f"m2_{sheet_name}"), f3.selectbox("Up to", weeks_list, key=f"wt1_{sheet_name}")
                    t1_res = []
                    for w in wards:
                        v1 = get_sum_up_to_week(df_26, w, m1, wt1, months_list, weeks_list); v2 = get_sum_up_to_week(df_26, w, m2, wt1, months_list, weeks_list)
                        diff = ((v2-v1)/v1) if v1 > 0 else 0
                        t1_res.append({'Ward':w, m1:v1, m2:v2, '% Inc/Dec':format_pct(diff), '_raw_diff': diff})
                    df1 = display_table(t1_res, [m1, m2], '% Inc/Dec')

                with c2:
                    st.subheader("2. Yearly Comparison")
                    f1, f2, f3, f4 = st.columns(4)
                    m25, w25, m26, w26 = f1.selectbox("25 Month", months_list, index=3, key=f"m25_{sheet_name}"), f2.selectbox("25 Week", weeks_list, key=f"w25_{sheet_name}"), f3.selectbox("26 Month", months_list, index=3, key=f"m26_{sheet_name}"), f4.selectbox("26 Week", weeks_list, key=f"w26_{sheet_name}")
                    t2_res = []
                    for w in wards:
                        v25 = get_sum_up_to_week(df_25, w, m25, w25, months_list, weeks_list); v26 = get_sum_up_to_week(df_26, w, m26, w26, months_list, weeks_list)
                        diff = ((v26-v25)/v25) if v25 > 0 else 0
                        t2_res.append({'Ward':w, '2025':v25, '2026':v26, '% Inc/Dec':format_pct(diff), '_raw_diff': diff})
                    df2 = display_table(t2_res, ['2025', '2026'], '% Inc/Dec')

                c3, c4 = st.columns(2)
                with c3:
                    st.subheader("3. Cumulative Comparison")
                    f1, f2 = st.columns(2)
                    cm, cw = f1.selectbox("End Month", months_list, index=3, key=f"cm_{sheet_name}"), f2.selectbox("End Week", weeks_list, key=f"cw_{sheet_name}")
                    t3_res = []
                    for w in wards:
                        v25c = get_cumulative_sum(df_25, w, cm, cw, months_list, weeks_list); v26c = get_cumulative_sum(df_26, w, cm, cw, months_list, weeks_list)
                        diff = ((v26c-v25c)/v25c) if v25c > 0 else 0
                        t3_res.append({'Ward':w, '2025 Cum':v25c, '2026 Cum':v26c, '% Inc/Dec':format_pct(diff), '_raw_diff': diff})
                    df3 = display_table(t3_res, ['2025 Cum', '2026 Cum'], '% Inc/Dec')

                with c4:
                    st.subheader("4. Summary Trends (%)")
                    t4_res = [{'Ward': w, 'Monthly %': t1_res[idx]['% Inc/Dec'], 'Yearly %': t2_res[idx]['% Inc/Dec'], 'Cum %': t3_res[idx]['% Inc/Dec']} for idx, w in enumerate(wards)]
                    t4_total = {'Ward':'Total', 'Monthly %': df1.iloc[-1]['% Inc/Dec'], 'Yearly %': df2.iloc[-1]['% Inc/Dec'], 'Cum %': df3.iloc[-1]['% Inc/Dec']}
                    df4_final = pd.concat([pd.DataFrame(t4_res), pd.DataFrame([t4_total])], ignore_index=True)
                    st.table(df4_final)

                # Sorting and Top/Bottom 5
                top5_m = sorted(t1_res, key=lambda x: x['_raw_diff'], reverse=True)[:5]
                bot5_m = sorted(t1_res, key=lambda x: x['_raw_diff'], reverse=False)[:5]
                df_top_m = pd.DataFrame([{'Ward': x['Ward'], 'Increase': format_pct(x['_raw_diff'])} for x in top5_m])
                df_bot_m = pd.DataFrame([{'Ward': x['Ward'], 'Decrease': format_pct(x['_raw_diff'])} for x in bot5_m])

                st.markdown("---")
                st.subheader("🏆 Top & Bottom 5 (Monthly)")
                top_c1, top_c2 = st.columns(2)
                with top_c1: st.write("Top 5 Increase"); st.table(df_top_m)
                with top_c2: st.write("Bottom 5 Increase/Decrease"); st.table(df_bot_m)

                # Plotly Chart (For Dashboard)
                df_chart = pd.DataFrame(t4_res)
                for col in ['Monthly %', 'Yearly %', 'Cum %']: df_chart[col] = df_chart[col].str.replace(' %', '').astype(float)
                df_melted = df_chart.melt(id_vars='Ward', var_name='Metric', value_name='Percentage')
                fig = px.line(df_melted, x='Ward', y='Percentage', color='Metric', markers=True)
                st.plotly_chart(fig, use_container_width=True)

                # --- EXCEL DOWNLOAD (NO KALEIDO / NO CHROME) ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    wb = writer.book
                    ws = wb.add_worksheet("Analysis")
                    
                    # Formatting
                    h_fmt = wb.add_format({'bold':True, 'bg_color':'#D7E4BC', 'border':1})
                    num_fmt = wb.add_format({'border':1})
                    
                    # 1. Write Summary Data for Chart
                    ws.write(0, 0, "Summary Trend Data (Source for Chart)", hb_fmt := wb.add_format({'bold':True}))
                    headers = ["Ward", "Monthly %", "Yearly %", "Cum %"]
                    for c, h in enumerate(headers): ws.write(1, c, h, h_fmt)
                    
                    for r, row in enumerate(t4_res):
                        ws.write(r+2, 0, row['Ward'], num_fmt)
                        ws.write(r+2, 1, float(row['Monthly %'].replace(' %','')), num_fmt)
                        ws.write(r+2, 2, float(row['Yearly %'].replace(' %','')), num_fmt)
                        ws.write(r+2, 3, float(row['Cum %'].replace(' %','')), num_fmt)
                    
                    # 2. CREATE NATIVE EXCEL CHART
                    chart = wb.add_chart({'type': 'line'})
                    last_row = len(t4_res) + 1
                    
                    for i in range(1, 4):
                        chart.add_series({
                            'name':       ['Analysis', 1, i],
                            'categories': ['Analysis', 2, 0, last_row, 0],
                            'values':     ['Analysis', 2, i, last_row, i],
                            'marker':     {'type': 'circle'}
                        })
                    
                    chart.set_title({'name': 'Trend Visualization'})
                    chart.set_x_axis({'name': 'Wards'})
                    chart.set_y_axis({'name': 'Percentage (%)'})
                    chart.set_size({'width': 800, 'height': 400})
                    
                    # Insert Chart into Sheet
                    ws.insert_chart('F2', chart)

                    # 3. Write other tables below
                    start_r = last_row + 25
                    df1.to_excel(writer, sheet_name="Analysis", startrow=start_r, index=False)
                    ws.write(start_r-1, 0, "Monthly Comparison Table", hb_fmt)

                st.download_button(label="📥 Download Report (No System Requirements)", data=output.getvalue(),
                                   file_name=f"{sheet_name}_Report.xlsx", key=f"dl_{sheet_name}")

except Exception as e:
    st.error(f"Error: {e}")
