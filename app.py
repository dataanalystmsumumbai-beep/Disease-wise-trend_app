import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Health Analysis Dashboard", layout="wide")

# --- १. टक्केवारी फॉरमॅट करण्यासाठी हेल्पर फंक्शन ---
def format_pct(val):
    if val == 0: return "0 %"
    val = val * 100
    if val == int(val):
        return f"{int(val)} %"
    else:
        return f"{val:.2f} %"

# --- २. डेटा लोडिंग ---
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
            df_25[c] = pd.to_numeric(df_25[c], errors='coerce').fillna(0).astype(int)
            df_26[c] = pd.to_numeric(df_26[c], errors='coerce').fillna(0).astype(int)
        
        all_data[sheet] = {'25': df_25, '26': df_26}
    return all_data

# --- ३. कॅल्क्युलेशन फंक्शन्स ---
def get_sum_up_to_week(df, ward, month, week_str, all_months, all_weeks):
    target_cols = []
    week_idx = all_weeks.index(week_str)
    for i in range(week_idx + 1):
        col_name = f"{month}_{all_weeks[i]}"
        if col_name in df.columns: target_cols.append(col_name)
    return int(df[df['Ward'] == ward][target_cols].values.sum())

def get_cumulative_sum(df, ward, end_month, end_week, all_months, all_weeks):
    target_cols = []
    m_idx = all_months.index(end_month)
    for m in all_months[:m_idx+1]:
        for w in all_weeks:
            col_name = f"{m}_{w}"
            if col_name in df.columns: target_cols.append(col_name)
            if m == end_month and w == end_week: break
        if m == end_month: break
    return int(df[df['Ward'] == ward][target_cols].values.sum())

# --- ४. टेबल विथ टोटल ओळ ---
def display_with_total(data_list, numeric_cols, pct_col=None):
    df = pd.DataFrame(data_list)
    # Total calculation
    total_row = {'Ward': 'Total'}
    for col in numeric_cols:
        total_row[col] = df[col].sum()
    
    # Total % calculation if exists
    if pct_col and len(numeric_cols) >= 2:
        v1_total = total_row[numeric_cols[0]]
        v2_total = total_row[numeric_cols[1]]
        diff = ((v2_total - v1_total) / v1_total) if v1_total > 0 else 0
        total_row[pct_col] = format_pct(diff)

    df_final = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)
    st.table(df_final)
    return df_final

# --- ५. UI आणि टॅब्स ---
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

            # फिल्टर विभाग
            c1, c2, c3, c4 = st.columns(4)
            m1 = c1.selectbox("Month 1 (2026)", months_list, index=2, key=f"t1m1_{sheet_name}")
            m2 = c2.selectbox("Month 2 (2026)", months_list, index=3, key=f"t1m2_{sheet_name}")
            y25m = c3.selectbox("2025 Month", months_list, index=3, key=f"t2m25_{sheet_name}")
            w_sel = c4.selectbox("Up to Week", weeks_list, index=0, key=f"wglobal_{sheet_name}")

            st.divider()
            
            row1_col1, row1_col2 = st.columns(2)
            row2_col1, row2_col2 = st.columns(2)

            # Table 1: Monthly
            with row1_col1:
                st.subheader("1. Monthly (2026)")
                t1_list = []
                for w in wards:
                    v1 = get_sum_up_to_week(df_26, w, m1, w_sel, months_list, weeks_list)
                    v2 = get_sum_up_to_week(df_26, w, m2, w_sel, months_list, weeks_list)
                    diff = ((v2 - v1) / v1) if v1 > 0 else 0
                    t1_list.append({'Ward': w, f"{m1}": v1, f"{m2}": v2, '% Change': format_pct(diff)})
                df1 = display_with_total(t1_list, [f"{m1}", f"{m2}"], '% Change')

            # Table 2: Yearly
            with row1_col2:
                st.subheader("2. Yearly Comparison")
                t2_list = []
                for w in wards:
                    v25 = get_sum_up_to_week(df_25, w, y25m, w_sel, months_list, weeks_list)
                    v26 = get_sum_up_to_week(df_26, w, m2, w_sel, months_list, weeks_list) # Using m2 for 2026
                    diff = ((v26 - v25) / v25) if v25 > 0 else 0
                    t2_list.append({'Ward': w, '2025': v25, '2026': v26, '% Change': format_pct(diff)})
                df2 = display_with_total(t2_list, ['2025', '2026'], '% Change')

            # Table 3: Cumulative
            with row2_col1:
                st.subheader("3. Cumulative (Jan to Date)")
                t3_list = []
                for w in wards:
                    v25c = get_cumulative_sum(df_25, w, m2, w_sel, months_list, weeks_list)
                    v26c = get_cumulative_sum(df_26, w, m2, w_sel, months_list, weeks_list)
                    diff = ((v26c - v25c) / v25c) if v25c > 0 else 0
                    t3_list.append({'Ward': w, '2025 Cum': v25c, '2026 Cum': v26c, '% Change': format_pct(diff)})
                df3 = display_with_total(t3_list, ['2025 Cum', '2026 Cum'], '% Change')

            # Table 4: Summary
            with row2_col2:
                st.subheader("4. Summary Trends")
                summary_list = []
                for idx, w in enumerate(wards):
                    summary_list.append({
                        'Ward': w,
                        'Monthly %': t1_list[idx]['% Change'],
                        'Yearly %': t2_list[idx]['% Change'],
                        'Cum %': t3_list[idx]['% Change']
                    })
                df4 = display_with_total(summary_list, [], None)

            # --- Download Button ---
            full_report = pd.concat([df1, df2, df3, df4], axis=1)
            csv = full_report.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"Download {sheet_name} Report",
                data=csv,
                file_name=f"{sheet_name}_report.csv",
                mime="text/csv",
                key=f"dl_{sheet_name}"
            )

except Exception as e:
    st.error(f"Error: {e}")
