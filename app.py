import streamlit as st
import pandas as pd
import io
import numpy as np
import plotly.express as px

# --- IMPORTANT: kaleido is required for Excel image export ---
# pip install kaleido==0.1.0post1

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

                # --- 1-4 Tables Logic (Same as before) ---
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
                    t1_title = f"1. Monthly Comparison (2026): {m1} vs {m2} (Up to {wt1})"

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
                    t2_title = f"2. Yearly Comparison: 2025 ({m25}-{w25}) vs 2026 ({m26}-{w26})"

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
                    t3_title = f"3. Cumulative: Jan to {cm} ({cw})"

                with c4:
                    st.subheader("4. Summary Trends (%)")
                    t4_res = [{'Ward': w, 'Monthly %': t1_res[idx]['% Inc/Dec'], 'Yearly %': t2_res[idx]['% Inc/Dec'], 'Cum %': t3_res[idx]['% Inc/Dec']} for idx, w in enumerate(wards)]
                    t4_total = {'Ward':'Total', 'Monthly %': df1.iloc[-1]['% Inc/Dec'], 'Yearly %': df2.iloc[-1]['% Inc/Dec'], 'Cum %': df3.iloc[-1]['% Inc/Dec']}
                    df4_final = pd.concat([pd.DataFrame(t4_res), pd.DataFrame([t4_total])], ignore_index=True)
                    st.table(df4_final)
                    t4_title = "4. Summary Trends Overview (%)"

                # --- Top/Bottom 5 Sorting ---
                top5_m = sorted(t1_res, key=lambda x: x['_raw_diff'], reverse=True)[:5]
                top5_y = sorted(t2_res, key=lambda x: x['_raw_diff'], reverse=True)[:5]
                top5_c = sorted(t3_res, key=lambda x: x['_raw_diff'], reverse=True)[:5]

                bot5_m = sorted(t1_res, key=lambda x: x['_raw_diff'], reverse=False)[:5]
                bot5_y = sorted(t2_res, key=lambda x: x['_raw_diff'], reverse=False)[:5]
                bot5_c = sorted(t3_res, key=lambda x: x['_raw_diff'], reverse=False)[:5]

                df_top_m = pd.DataFrame([{'Ward': x['Ward'], 'Increase': format_pct(x['_raw_diff'])} for x in top5_m])
                df_top_y = pd.DataFrame([{'Ward': x['Ward'], 'Increase': format_pct(x['_raw_diff'])} for x in top5_y])
                df_top_c = pd.DataFrame([{'Ward': x['Ward'], 'Increase': format_pct(x['_raw_diff'])} for x in top5_c])

                df_bot_m = pd.DataFrame([{'Ward': x['Ward'], 'Decrease': format_pct(x['_raw_diff'])} for x in bot5_m])
                df_bot_y = pd.DataFrame([{'Ward': x['Ward'], 'Decrease': format_pct(x['_raw_diff'])} for x in bot5_y])
                df_bot_c = pd.DataFrame([{'Ward': x['Ward'], 'Decrease': format_pct(x['_raw_diff'])} for x in bot5_c])

                # --- Top/Bottom UI ---
                st.markdown("---")
                st.subheader("🏆 Top 5 Wards")
                tc1, tc2, tc3 = st.columns(3)
                with tc1: st.write("Monthly"); st.table(df_top_m)
                with tc2: st.write("Yearly"); st.table(df_top_y)
                with tc3: st.write("Cumulative"); st.table(df_top_c)

                st.subheader("📉 Bottom 5 Wards")
                bc1, bc2, bc3 = st.columns(3)
                with bc1: st.write("Monthly"); st.table(df_bot_m)
                with bc2: st.write("Yearly"); st.table(df_bot_y)
                with bc3: st.write("Cumulative"); st.table(df_bot_c)

                # --- Chart ---
                st.markdown("---")
                df_chart = pd.DataFrame(t4_res)
                for col in ['Monthly %', 'Yearly %', 'Cum %']: df_chart[col] = df_chart[col].str.replace(' %', '').astype(float)
                df_melted = df_chart.melt(id_vars='Ward', var_name='Metric', value_name='Percentage')
                fig = px.line(df_melted, x='Ward', y='Percentage', color='Metric', markers=True)
                fig.update_layout(xaxis_title="Wards", yaxis_title="Percentage (%)", height=500)
                st.plotly_chart(fig, use_container_width=True)

                # --- ALL-IN-ONE EXCEL DOWNLOAD ---
                output = io.BytesIO()
                # Important: engine is xlsxwriter
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    wb = writer.book
                    ws = wb.add_worksheet("Analysis_Report")
                    
                    # Formats
                    h_fmt = wb.add_format({'bold':True, 'bg_color':'#D7E4BC', 'border':1, 'align':'center'})
                    c_fmt = wb.add_format({'border':1, 'align':'center'})
                    t_fmt = wb.add_format({'bold':True, 'font_size':12, 'font_color':'#1F4E78'})

                    def write_df(df, r, c, title):
                        if '_raw_diff' in df.columns: df = df.drop(columns=['_raw_diff'])
                        ws.write(r, c, title, t_fmt)
                        # Header
                        for col_num, value in enumerate(df.columns.values):
                            ws.write(r+1, c+col_num, value, h_fmt)
                        # Data
                        for row_num, row_data in enumerate(df.values):
                            for col_num, value in enumerate(row_data):
                                ws.write(r+2+row_num, c+col_num, value, c_fmt)
                        return r + len(df) + 4

                    # Writing blocks
                    next_r = write_df(df1, 0, 0, t1_title)
                    next_r = write_df(df2, next_r, 0, t2_title)
                    next_r = write_df(df3, next_r, 0, t3_title)
                    next_r = write_df(df4_final, next_r, 0, "4. Summary Trends")
                    
                    # Top/Bottom 5
                    ws.write(next_r, 0, "🏆 Top 5 Wards", t_fmt)
                    write_df(df_top_m, next_r+1, 0, "Monthly")
                    write_df(df_top_y, next_r+1, 3, "Yearly")
                    next_r = write_df(df_top_c, next_r+1, 6, "Cumulative")

                    ws.write(next_r, 0, "📉 Bottom 5 Wards", t_fmt)
                    write_df(df_bot_m, next_r+1, 0, "Monthly")
                    write_df(df_bot_y, next_r+1, 3, "Yearly")
                    next_r = write_df(df_bot_c, next_r+1, 6, "Cumulative")

                    # INSERT CHART
                    try:
                        # Try generating image
                        img_data = fig.to_image(format="png", engine="kaleido")
                        chart_img = io.BytesIO(img_data)
                        ws.insert_image(next_r + 2, 0, 'chart.png', {'image_data': chart_img, 'x_scale': 0.8, 'y_scale': 0.8})
                    except Exception as e:
                        st.warning(f"Excel मध्ये चार्ट लोड झाला नाही. कृपया टर्मिनलमध्ये 'pip install kaleido==0.1.0post1' रन करा. Error: {e}")

                st.download_button(
                    label=f"📥 Download Everything as Excel ({sheet_name})",
                    data=output.getvalue(),
                    file_name=f"{sheet_name}_Full_Analysis.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"btn_{sheet_name}"
                )

    else:
        st.info("👈 Please select a data source from the sidebar.")

except Exception as e:
    st.error(f"Error: {e}")
