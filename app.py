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

# --- 2. Data Loading & Processing ---
# (तुमचे जुने process_excel_data, load_from_url, इ. फंक्शन्स इथे राहतील)
# ... (जसा आधीचा कोड होता तसाच ठेवा)

# --- 4. Table Display UI ---
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

# --- 5. Main UI Logic ---
# ... (Data Source selection logic)

try:
    # ... (Data loading logic)
    
    if data_dict:
        st.title("📊 Disease-wise Trend Analysis")
        tabs = st.tabs(list(data_dict.keys()))
        
        months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        weeks_list = ["WEEK 1", "WEEK 2", "WEEK 3", "WEEK 4"]

        for i, sheet_name in enumerate(data_dict.keys()):
            with tabs[i]:
                df_25, df_26 = data_dict[sheet_name]['25'], data_dict[sheet_name]['26']
                wards = [w for w in df_26['Ward'].dropna().unique() if w not in ['Ward', 'Total', 'YEAR 2026', 'YEAR 2025']]

                # Row 1 (Tables 1 & 2)
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("1. Monthly Comparison")
                    # ... (Selectbox logic)
                    t1_data = [] # (Data calculation logic as before)
                    df1 = display_table(t1_data, [m1, m2], '% Inc/Dec')

                with col2:
                    st.subheader("2. Yearly Comparison")
                    # ... (Selectbox logic)
                    t2_data = [] # (Data calculation logic as before)
                    df2 = display_table(t2_data, ['2025', '2026'], '% Inc/Dec')

                # Row 2 (Tables 3 & 4)
                col3, col4 = st.columns(2)
                with col3:
                    st.subheader("3. Cumulative Comparison")
                    # ... (Selectbox logic)
                    t3_data = [] # (Data calculation logic as before)
                    df3 = display_table(t3_data, ['2025 Cum', '2026 Cum'], '% Inc/Dec')

                with col4:
                    st.subheader("4. Summary Trends (%)")
                    t4_data = []
                    for idx, w in enumerate(wards):
                        t4_data.append({
                            'Ward': w, 
                            'Monthly %': t1_data[idx]['% Inc/Dec'], 
                            'Yearly %': t2_data[idx]['% Inc/Dec'], 
                            'Cum %': t3_data[idx]['% Inc/Dec']
                        })
                    
                    # Fix: Get Total percentages from df1, df2, df3
                    t1_total_pct = df1.iloc[-1]['% Inc/Dec']
                    t2_total_pct = df2.iloc[-1]['% Inc/Dec']
                    t3_total_pct = df3.iloc[-1]['% Inc/Dec']
                    
                    df4 = pd.DataFrame(t4_data)
                    total_row_4 = {
                        'Ward': 'Total', 
                        'Monthly %': t1_total_pct, 
                        'Yearly %': t2_total_pct, 
                        'Cum %': t3_total_pct
                    }
                    df4_final = pd.concat([df4, pd.DataFrame([total_row_4])], ignore_index=True)
                    st.table(df4_final)

                # --- Download Section (Side-by-Side Layout) ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter', engine_kwargs={'options': {'nan_inf_to_errors': True}}) as writer:
                    wb = writer.book
                    ws = wb.add_worksheet("Analysis_Report")
                    
                    h_fmt = wb.add_format({'bold':True, 'bg_color':'#D7E4BC', 'border':1, 'align':'center'})
                    c_fmt = wb.add_format({'border':1, 'align':'center'})
                    t_fmt = wb.add_format({'bold':True, 'font_size':12, 'font_color':'#1F4E78'})
                    
                    def write_table_side(df, start_col, title):
                        df_clean = df.replace([np.inf, -np.inf], 0).fillna(0)
                        ws.write(0, start_col, title, t_fmt)
                        # Headers
                        for c, col in enumerate(df_clean.columns):
                            ws.write(2, start_col + c, col, h_fmt)
                        # Data
                        for r, row in enumerate(df_clean.values):
                            for c, val in enumerate(row):
                                ws.write(r + 3, start_col + c, val, c_fmt)
                        # Return next start column (+1 for blank space)
                        return start_col + len(df_clean.columns) + 1

                    # Write tables side-by-side
                    curr_col = write_table_side(df1, 0, "1. Monthly Comparison")
                    curr_col = write_table_side(df2, curr_col, "2. Yearly Comparison")
                    curr_col = write_table_side(df3, curr_col, "3. Cumulative Comparison")
                    write_table_side(df4_final, curr_col, "4. Summary Trends")
                
                st.download_button(
                    label=f"📥 Download Side-by-Side Report ({sheet_name})", 
                    data=output.getvalue(),
                    file_name=f"{sheet_name}_SideBySide_Report.xlsx", 
                    key=f"dl_side_{sheet_name}"
                )

except Exception as e:
    st.error(f"Error: {e}")
