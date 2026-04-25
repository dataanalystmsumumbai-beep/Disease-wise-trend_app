import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Disease Dashboard", layout="wide")

# --- DATA LOADING (Direct from your file structure) ---
@st.cache_data
def load_all_data(file):
    xls = pd.ExcelFile(file, engine='openpyxl')
    sheets_dict = {}
    
    for sheet_name in xls.sheet_names:
        df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        # Header processing for 'data for app' style
        months_row = df_raw.iloc[0, 2:].ffill().tolist()
        weeks_row = df_raw.iloc[1, 2:].tolist()
        cols = ['Ward', 'Total'] + [f"{m}_{w}" for m, w in zip(months_row, weeks_row)]
        
        data_only = df_raw.iloc[2:].copy()
        data_only.columns = cols[:len(data_only.columns)]
        
        # Logic to split 2025 and 2026 data
        ward_a_idx = data_only[data_only['Ward'] == 'A'].index.tolist()
        if len(ward_a_idx) >= 2:
            df_25 = data_only.loc[ward_a_idx[0]:ward_a_idx[1]-2].copy()
            df_26 = data_only.loc[ward_a_idx[1]-1:].copy()
        else:
            df_25, df_26 = data_only.iloc[:56], data_only.iloc[56:]
            
        # Convert to numeric
        for c in data_only.columns[1:]:
            df_25[c] = pd.to_numeric(df_25[c], errors='coerce').fillna(0)
            df_26[c] = pd.to_numeric(df_26[c], errors='coerce').fillna(0)
            
        sheets_dict[sheet_name] = {'25': df_25, '26': df_26}
    return sheets_dict

# --- MINIMAL COMPARISON CHART (Photo Style) ---
def create_chart(v1, v2, label1, label2, colors):
    source = pd.DataFrame({
        'Category': [label1, label2],
        'Value': [v1, v2]
    })
    chart = alt.Chart(source).mark_bar(height=15).encode(
        x=alt.X('Value:Q', axis=None),
        y=alt.Y('Category:N', axis=alt.Axis(title=None, ticks=False, domain=False), sort=None),
        color=alt.Color('Category:N', scale=alt.Scale(range=colors), legend=None),
        tooltip=['Category', 'Value']
    ).properties(height=60)
    return chart.configure_view(strokeWidth=0)

# --- MAIN UI ---
st.title("Ward-wise Disease Trends")
uploaded_file = st.file_uploader("Upload 'data for app.xlsx' here", type="xlsx")

if uploaded_file:
    data_store = load_all_data(uploaded_file)
    tabs = st.tabs(list(data_store.keys()))
    
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    weeks = ["WEEK 1", "WEEK 2", "WEEK 3", "WEEK 4"]

    for i, sheet in enumerate(data_store.keys()):
        with tabs[i]:
            # --- 1. INDEPENDENT FILTERS PER TAB ---
            col_f1, col_f2 = st.columns(2)
            sel_m = col_f1.selectbox("Select Month", months, index=3, key=f"m_{sheet}")
            sel_w = col_f2.selectbox("Select Week", weeks, index=2, key=f"w_{sheet}")
            
            df_25 = data_store[sheet]['25']
            df_26 = data_store[sheet]['26']
            
            # Logic: Determine Columns
            m_idx = months.index(sel_m)
            prev_m = months[m_idx-1] if m_idx > 0 else "Jan"
            target_col = f"{sel_m}_{sel_w}"
            cum_months = months[:m_idx+1]

            # --- 2. HEADER ROW (Data 2 Style) ---
            st.markdown("---")
            h_ward, h_mon, h_year, h_cum = st.columns([1, 2.5, 2.5, 2.5])
            h_ward.markdown("**Ward**")
            h_mon.markdown(f"**Monthly**<br>{prev_m} vs {sel_m} ('26)", unsafe_allow_html=True)
            h_year.markdown(f"**Yearly**<br>{sel_m} {sel_w} ('25 vs '26)", unsafe_allow_html=True)
            h_cum.markdown(f"**Cumulative**<br>Jan to {sel_m} ('25 vs '26)", unsafe_allow_html=True)
            st.divider()

            # --- 3. DATA ROWS ---
            wards = df_26['Ward'].dropna().unique()
            for ward in wards:
                if ward in ['Ward', 'Total', 'YEAR 2026', 'YEAR 2025']: continue
                
                # Logic: Calculations
                # Monthly Comparison (2026 data only)
                c_curr = [c for c in df_26.columns if c.startswith(sel_m)]
                c_prev = [c for c in df_26.columns if c.startswith(prev_m)]
                v_curr_m = df_26[df_26['Ward'] == ward][c_curr].values.sum()
                v_prev_m = df_26[df_26['Ward'] == ward][c_prev].values.sum()
                
                # Yearly Comparison (Week vs Week)
                v_25_w = df_25[df_25['Ward'] == ward][target_col].values[0] if target_col in df_25.columns else 0
                v_26_w = df_26[df_26['Ward'] == ward][target_col].values[0] if target_col in df_26.columns else 0
                
                # Cumulative (Sum of all weeks up to sel_m)
                c_cum = [c for c in df_26.columns if any(c.startswith(m) for m in cum_months)]
                v_25_c = df_25[df_25['Ward'] == ward][c_cum].values.sum()
                v_26_c = df_26[df_26['Ward'] == ward][c_cum].values.sum()

                # Display Row
                r_ward, r_mon, r_year, r_cum = st.columns([1, 2.5, 2.5, 2.5])
                r_ward.subheader(ward)
                
                # Graph 1: Monthly (Blue)
                r_mon.altair_chart(create_chart(v_prev_m, v_curr_m, prev_m, sel_m, ['#AEC7E8', '#1F77B4']), use_container_width=True)
                
                # Graph 2: Yearly (Orange)
                r_year.altair_chart(create_chart(v_25_w, v_26_w, "2025", "2026", ['#FFBB78', '#FF7F0E']), use_container_width=True)
                
                # Graph 3: Cumulative (Green)
                r_cum.altair_chart(create_chart(v_25_c, v_26_c, "2025", "2026", ['#98DF8A', '#2CA02C']), use_container_width=True)

else:
    st.info("Please upload your Excel file to begin.")
