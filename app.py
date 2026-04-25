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
            months_row = df_raw.iloc[0, 2:].ffill().tolist()
            weeks_row = df_raw.iloc[1, 2:].tolist()
            cols = ['Ward', 'Total'] + [f"{m}_{w}" for m, w in zip(months_row, weeks_row)]
            
            data_only = df_raw.iloc[2:].copy()
            if len(data_only.columns) > len(cols):
                cols += [f"Un_{i}" for i in range(len(data_only.columns) - len(cols))]
            data_only.columns = cols[:len(data_only.columns)]
            
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
        except Exception:
            continue
            
    return sheets_dict

# --- CLEAN SPARKLINE GRAPH FUNCTION ---
def create_sparkline(df, category_col, value_col, color_range):
    # Create a very clean, minimal horizontal bar chart
    chart = alt.Chart(df).mark_bar(height=15, cornerRadiusEnd=2).encode(
        x=alt.X(f'{value_col}:Q', axis=None), # Hide X axis completely
        y=alt.Y(f'{category_col}:N', axis=alt.Axis(title=None, domain=False, ticks=False, labelAngle=0, labelPadding=5)),
        color=alt.Color(f'{category_col}:N', scale=alt.Scale(range=color_range), legend=None),
        tooltip=[category_col, value_col]
    ).properties(height=60) # Make it small
    
    # Remove background grid and borders
    return chart.configure_view(strokeWidth=0).configure_axis(grid=False)

# --- MAIN APP ---
try:
    with st.spinner("Loading data..."):
        all_data = load_all_sheets(DEFAULT_GSHEET_URL)
    
    if all_data:
        month_opts = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        week_opts = ["WEEK 1", "WEEK 2", "WEEK 3", "WEEK 4"]
        
        st.subheader("Select Timeline")
        col1, col2, _ = st.columns([2, 2, 6])
        sel_month = col1.selectbox("Month", month_opts, index=3)
        sel_week = col2.selectbox("Week", week_opts, index=2)
        
        m_idx = month_opts.index(sel_month)
        prev_month = month_opts[m_idx-1] if m_idx > 0 else "Jan"
        target_col = f"{sel_month}_{sel_week}"
        months_upto = month_opts[:m_idx+1]
        
        sheet_names = list(all_data.keys())
        tabs = st.tabs(sheet_names)
        
        for i, sheet in enumerate(sheet_names):
            with tabs[i]:
                df_25 = all_data[sheet]['df_25']
                df_26 = all_data[sheet]['df_26']
                
                # Clean Headers matching your image layout
                h1, h2, h3, h4 = st.columns([1, 2, 2, 2])
                h1.markdown("**Ward**")
                h2.markdown(f"**Monthly**<br>({prev_month} vs {sel_month} '26)", unsafe_allow_html=True)
                h3.markdown(f"**Yearly**<br>({sel_month} Wk: '25 vs '26)", unsafe_allow_html=True)
                h4.markdown(f"**Cumulative**<br>(Jan-{sel_month})", unsafe_allow_html=True)
                st.divider()
                
                curr_m_cols = [c for c in df_26.columns if c.startswith(sel_month)]
                prev_m_cols = [c for c in df_26.columns if c.startswith(prev_month)]
                cum_cols = [c for c in df_26.columns if any(c.startswith(m) for m in months_upto)]
                
                wards = df_26['Ward'].dropna().unique()
                for ward in wards:
                    if ward in ['Ward', 'Total', 'YEAR 2026', 'YEAR 2025']: continue
                    
                    val_curr_m = df_26[df_26['Ward'] == ward][curr_m_cols].values.sum()
                    val_prev_m = df_26[df_26['Ward'] == ward][prev_m_cols].values.sum()
                    val_25_wk = df_25[df_25['Ward'] == ward][target_col].values[0] if target_col in df_25.columns else 0
                    val_26_wk = df_26[df_26['Ward'] == ward][target_col].values[0] if target_col in df_26.columns else 0
                    val_25_cum = df_25[df_25['Ward'] == ward][cum_cols].values.sum()
                    val_26_cum = df_26[df_26['Ward'] == ward][cum_cols].values.sum()
                    
                    # Columns layout exactly like the photo
                    c_ward, c_graph1, c_graph2, c_graph3 = st.columns([1, 2, 2, 2])
                    
                    # 1. Ward Name
                    c_ward.write(f"### {ward}")
                    
                    # 2. Graph 1 (Monthly) - Blue theme
                    df_g1 = pd.DataFrame({'Period': [prev_month, sel_month], 'Cases': [val_prev_m, val_curr_m]})
                    c_graph1.altair_chart(create_sparkline(df_g1, 'Period', 'Cases', ['#aec7e8', '#1f77b4']), use_container_width=True)
                    
                    # 3. Graph 2 (Yearly) - Orange theme
                    df_g2 = pd.DataFrame({'Year': ['2025', '2026'], 'Cases': [val_25_wk, val_26_wk]})
                    c_graph2.altair_chart(create_sparkline(df_g2, 'Year', 'Cases', ['#ffbb78', '#ff7f0e']), use_container_width=True)
                    
                    # 4. Graph 3 (Cumulative) - Green theme
                    df_g3 = pd.DataFrame({'Year': ['25 Total', '26 Total'], 'Cases': [val_25_cum, val_26_cum]})
                    c_graph3.altair_chart(create_sparkline(df_g3, 'Year', 'Cases', ['#98df8a', '#2ca02c']), use_container_width=True)

except Exception as e:
    st.error(f"Error processing data: {e}")
