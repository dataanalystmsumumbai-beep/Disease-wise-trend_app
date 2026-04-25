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
            # Header logic
            months_row = df_raw.iloc[0, 2:].ffill().tolist()
            weeks_row = df_raw.iloc[1, 2:].tolist()
            cols = ['Ward', 'Total'] + [f"{m}_{w}" for m, w in zip(months_row, weeks_row)]
            
            data_only = df_raw.iloc[2:].copy()
            data_only.columns = cols[:len(data_only.columns)]
            
            # Split 2025 and 2026 data
            ward_a_idx = data_only[data_only['Ward'] == 'A'].index.tolist()
            if len(ward_a_idx) >= 2:
                df_25 = data_only.loc[ward_a_idx[0]:ward_a_idx[1]-2].copy()
                df_26 = data_only.loc[ward_a_idx[1]-1:].copy()
            else:
                df_25 = data_only.iloc[:56].copy()
                df_26 = data_only.iloc[56:].copy()
                
            for c in data_only.columns[1:]:
                df_25[c] = pd.to_numeric(df_25[c], errors='coerce').fillna(0)
                df_26[c] = pd.to_numeric(df_26[c], errors='coerce').fillna(0)
                
            sheets_dict[sheet_name] = {'df_25': df_25, 'df_26': df_26}
        except:
            continue
    return sheets_dict

# --- MINIMAL GRAPH FUNCTION ---
def draw_bar_chart(data, x_col, y_col, colors):
    chart = alt.Chart(data).mark_bar(height=18, cornerRadiusEnd=2).encode(
        x=alt.X(f'{x_col}:Q', axis=None),
        y=alt.Y(f'{y_col}:N', axis=alt.Axis(title=None, domain=False, ticks=False, labelFontWeight='bold')),
        color=alt.Color(f'{y_col}:N', scale=alt.Scale(range=colors), legend=None),
        tooltip=[y_col, x_col]
    ).properties(height=70).configure_view(strokeWidth=0)
    return chart

# --- MAIN APP ---
try:
    with st.spinner("डेटा लोड होत आहे..."):
        all_data = load_all_sheets(DEFAULT_GSHEET_URL)
    
    if all_data:
        sheet_names = list(all_data.keys())
        tabs = st.tabs(sheet_names)
        
        month_opts = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        week_opts = ["WEEK 1", "WEEK 2", "WEEK 3", "WEEK 4"]

        for i, sheet in enumerate(sheet_names):
            with tabs[i]:
                # --- Filters INSIDE each tab ---
                f1, f2, _ = st.columns([2, 2, 6])
                sel_month = f1.selectbox(f"Select Month ({sheet})", month_opts, index=3, key=f"m_{sheet}")
                sel_week = f2.selectbox(f"Select Week ({sheet})", week_opts, index=2, key=f"w_{sheet}")
                
                st.markdown("---")
                
                df_25 = all_data[sheet]['df_25']
                df_26 = all_data[sheet]['df_26']
                
                m_idx = month_opts.index(sel_month)
                prev_month = month_opts[m_idx-1] if m_idx > 0 else "Jan"
                target_col = f"{sel_month}_{sel_week}"
                months_upto = month_opts[:m_idx+1]

                # Headers
                h1, h2, h3, h4 = st.columns([1, 2.5, 2.5, 2.5])
                h1.write("**Ward**")
                h2.write(f"**Monthly** ({prev_month} vs {sel_month} '26)")
                h3.write(f"**Yearly** ({sel_month} {sel_week}: '25 vs '26)")
                h4.write(f"**Cumulative** (Jan to {sel_month})")
                st.divider()

                wards = df_26['Ward'].dropna().unique()
                for ward in wards:
                    if ward in ['Ward', 'Total', 'YEAR 2026', 'YEAR 2025']: continue
                    
                    # 1. Monthly Logic
                    curr_m_cols = [c for c in df_26.columns if c.startswith(sel_month)]
                    prev_m_cols = [c for c in df_26.columns if c.startswith(prev_month)]
                    v_curr_m = df_26[df_26['Ward'] == ward][curr_m_cols].values.sum()
                    v_prev_m = df_26[df_26['Ward'] == ward][prev_m_cols].values.sum()
                    
                    # 2. Yearly Logic
                    v_25_wk = df_25[df_25['Ward'] == ward][target_col].values[0] if target_col in df_25.columns else 0
                    v_26_wk = df_26[df_26['Ward'] == ward][target_col].values[0] if target_col in df_26.columns else 0
                    
                    # 3. Cumulative Logic
                    cum_cols = [c for c in df_26.columns if any(c.startswith(m) for m in months_upto)]
                    v_25_cum = df_25[df_25['Ward'] == ward][cum_cols].values.sum()
                    v_26_cum = df_26[df_26['Ward'] == ward][cum_cols].values.sum()

                    # Row Layout
                    c_ward, c_m, c_y, c_c = st.columns([1, 2.5, 2.5, 2.5])
                    
                    c_ward.subheader(ward)
                    
                    # Monthly Graph
                    df_m = pd.DataFrame({'Month': [prev_month, sel_month], 'Cases': [v_prev_m, v_curr_m]})
                    c_m.altair_chart(draw_bar_chart(df_m, 'Cases', 'Month', ['#CDE0F7', '#1F77B4']), use_container_width=True)
                    
                    # Yearly Graph
                    df_y = pd.DataFrame({'Year': ['2025', '2026'], 'Cases': [v_25_wk, v_26_wk]})
                    c_y.altair_chart(draw_bar_chart(df_y, 'Cases', 'Year', ['#FFD8B1', '#FF7F0E']), use_container_width=True)
                    
                    # Cumulative Graph
                    df_c = pd.DataFrame({'Period': [''25 Total', ''26 Total'], 'Cases': [v_25_cum, v_26_cum]})
                    c_c.altair_chart(draw_bar_chart(df_c, 'Cases', 'Period', ['#B2E0B2', '#2CA02C']), use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
