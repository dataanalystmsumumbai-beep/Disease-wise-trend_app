import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Disease Dashboard", layout="wide")
st.title("Ward-wise Disease Dashboard")

# --- DATA LOADING ---
DEFAULT_GSHEET_URL = "https://docs.google.com/spreadsheets/d/11-ZeoBvixvY_ujLO8_9Vlze2jmGC4CooTWjvd2INX-4/edit"

def get_xlsx_url(url):
    if "/edit" in url:
        return url.split('/edit')[0] + "/export?format=xlsx"
    return url

@st.cache_data
def load_all_sheets(url):
    xlsx_url = get_xlsx_url(url)
    xls = pd.ExcelFile(xlsx_url, engine='openpyxl')
    sheets_dict = {}
    
    for sheet_name in xls.sheet_names:
        df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        
        try:
            # Clean Headers
            months_row = df_raw.iloc[0, 2:].ffill().tolist()
            weeks_row = df_raw.iloc[1, 2:].tolist()
            cols = ['Ward', 'Total'] + [f"{m}_{w}" for m, w in zip(months_row, weeks_row)]
            
            data_only = df_raw.iloc[2:].copy()
            # Match columns length
            if len(data_only.columns) > len(cols):
                cols += [f"Un_{i}" for i in range(len(data_only.columns) - len(cols))]
            data_only.columns = cols[:len(data_only.columns)]
            
            # Split into 2025 and 2026
            ward_a_idx = data_only[data_only['Ward'] == 'A'].index.tolist()
            if len(ward_a_idx) >= 2:
                df_25 = data_only.loc[ward_a_idx[0]:ward_a_idx[1]-2].copy()
                df_26 = data_only.loc[ward_a_idx[1]-1:].copy()
            else:
                df_25 = data_only.iloc[:56].copy()
                df_26 = data_only.iloc[56:].copy()
                
            for c in data_only.columns[2:]:
                if c in df_25.columns: df_25[c] = pd.to_numeric(df_25[c], errors='coerce').fillna(0)
                if c in df_26.columns: df_26[c] = pd.to_numeric(df_26[c], errors='coerce').fillna(0)
                
            sheets_dict[sheet_name] = {'df_25': df_25, 'df_26': df_26}
        except Exception as e:
            continue # Skip invalid sheets
            
    return sheets_dict

# Helper function for mini graphs
def create_mini_chart(df_data, x_col, y_col, colors):
    return alt.Chart(df_data).mark_bar().encode(
        x=alt.X(x_col, title=None, axis=alt.Axis(labels=False, ticks=False)), # Hide X numbers for clean look
        y=alt.Y(y_col, title=None, sort=None, axis=alt.Axis(labelFontWeight='bold')),
        color=alt.Color(y_col, scale=alt.Scale(range=colors), legend=None),
        tooltip=[y_col, x_col]
    ).properties(height=60)

# --- MAIN APP ---
try:
    with st.spinner("Loading all sheets..."):
        all_data = load_all_sheets(DEFAULT_GSHEET_URL)
    
    if all_data:
        month_opts = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        week_opts = ["WEEK 1", "WEEK 2", "WEEK 3", "WEEK 4"]
        
        # Global Filters
        st.subheader("Select Timeline")
        col1, col2, _ = st.columns([2, 2, 6])
        sel_month = col1.selectbox("Month", month_opts, index=3)
        sel_week = col2.selectbox("Week", week_opts, index=2)
        
        m_idx = month_opts.index(sel_month)
        prev_month = month_opts[m_idx-1] if m_idx > 0 else "Jan"
        target_col = f"{sel_month}_{sel_week}"
        months_upto = month_opts[:m_idx+1]
        
        # 1. Create Tabs for EACH SHEET (Disease)
        sheet_names = list(all_data.keys())
        tabs = st.tabs(sheet_names)
        
        # 2. Populate each tab
        for i, sheet in enumerate(sheet_names):
            with tabs[i]:
                df_25 = all_data[sheet]['df_25']
                df_26 = all_data[sheet]['df_26']
                
                # Headers for the 3 side-by-side sections
                h1, h2, h3, h4 = st.columns([1, 3, 3, 3])
                h1.write("**Ward**")
                h2.write(f"**1. Monthly ({prev_month} vs {sel_month} '26)**")
                h3.write(f"**2. Yearly ({sel_month} {sel_week}: '25 vs '26)**")
                h4.write(f"**3. Cumulative (Jan-{sel_month})**")
                st.divider()
                
                curr_m_cols = [c for c in df_26.columns if c.startswith(sel_month)]
                prev_m_cols = [c for c in df_26.columns if c.startswith(prev_month)]
                cum_cols = [c for c in df_26.columns if any(c.startswith(m) for m in months_upto)]
                
                wards = df_26['Ward'].dropna().unique()
                for ward in wards:
                    if ward in ['Ward', 'Total', 'YEAR 2026', 'YEAR 2025']: continue
                    
                    # Calculations
                    # Type 1: Monthly (Current vs Prev)
                    val_curr_m = df_26[df_26['Ward'] == ward][curr_m_cols].values.sum()
                    val_prev_m = df_26[df_26['Ward'] == ward][prev_m_cols].values.sum()
                    
                    # Type 2: Yearly Week
                    val_25_wk = df_25[df_25['Ward'] == ward][target_col].values[0] if target_col in df_25.columns else 0
                    val_26_wk = df_26[df_26['Ward'] == ward][target_col].values[0] if target_col in df_26.columns else 0
                    
                    # Type 3: Cumulative
                    val_25_cum = df_25[df_25['Ward'] == ward][cum_cols].values.sum()
                    val_26_cum = df_26[df_26['Ward'] == ward][cum_cols].values.sum()
                    
                    # Display Side-by-Side (Like Data 2)
                    c_ward, c_graph1, c_graph2, c_graph3 = st.columns([1, 3, 3, 3])
                    
                    # Ward Name
                    c_ward.write(f"### {ward}")
                    
                    # Graph 1
                    df_g1 = pd.DataFrame({'Period': [prev_month, sel_month], 'Cases': [val_prev_m, val_curr_m]})
                    c_graph1.altair_chart(create_mini_chart(df_g1, 'Cases', 'Period', ['#aec7e8', '#1f77b4']), use_container_width=True)
                    
                    # Graph 2
                    df_g2 = pd.DataFrame({'Year': ['2025', '2026'], 'Cases': [val_25_wk, val_26_wk]})
                    c_graph2.altair_chart(create_mini_chart(df_g2, 'Cases', 'Year', ['#ffbb78', '#ff7f0e']), use_container_width=True)
                    
                    # Graph 3
                    df_g3 = pd.DataFrame({'Year': ['25 Total', '26 Total'], 'Cases': [val_25_cum, val_26_cum]})
                    c_graph3.altair_chart(create_mini_chart(df_g3, 'Cases', 'Year', ['#98df8a', '#2ca02c']), use_container_width=True)
                    
                st.markdown("---")

except Exception as e:
    st.error(f"Error processing data: {e}")
