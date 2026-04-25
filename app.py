import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Disease Trend Dashboard", layout="wide")

st.title("Ward-wise Disease Trend Analysis")

# --- DATA LOADING ---
DEFAULT_GSHEET_URL = "https://docs.google.com/spreadsheets/d/11-ZeoBvixvY_ujLO8_9Vlze2jmGC4CooTWjvd2INX-4/edit?gid=1214285155#gid=1214285155"

def get_csv_url(url):
    if "/edit" in url:
        # Extract base URL and gid
        base_url = url.split('/edit')[0]
        if 'gid=' in url:
            gid = url.split('gid=')[1].split('#')[0]
            return f"{base_url}/export?format=csv&gid={gid}"
        return f"{base_url}/export?format=csv"
    return url

@st.cache_data
def load_and_clean_data(url):
    csv_url = get_csv_url(url)
    df_raw = pd.read_csv(csv_url, header=None)
    
    # Cleaning headers: Using .ffill() instead of fillna(method='ffill')
    months_row = df_raw.iloc[0, 2:].ffill().tolist()
    weeks_row = df_raw.iloc[1, 2:].tolist()
    
    # Create unique column names
    columns = ['Ward', 'Total'] + [f"{m}_{w}" for m, w in zip(months_row, weeks_row)]
    
    data_only = df_raw.iloc[2:].copy()
    data_only.columns = columns
    
    # Split into 2025 and 2026 
    # Logic: Find where Ward 'A' repeats
    ward_a_indices = data_only[data_only['Ward'] == 'A'].index.tolist()
    
    if len(ward_a_indices) >= 2:
        df_2025 = data_only.loc[ward_a_indices[0]:ward_a_indices[1]-2].copy()
        df_2026 = data_only.loc[ward_a_indices[1]-1:].copy()
    else:
        # Fallback if split logic fails
        df_2025 = data_only.iloc[:56].copy() 
        df_2026 = data_only.iloc[56:].copy()

    # Convert to numeric
    for col in data_only.columns[1:]:
        df_2025[col] = pd.to_numeric(df_2025[col], errors='coerce').fillna(0)
        df_2026[col] = pd.to_numeric(df_2026[col], errors='coerce').fillna(0)
        
    return df_2025, df_2026

try:
    df_2025, df_2026 = load_and_clean_data(DEFAULT_GSHEET_URL)
    
    # --- UI FILTERS ---
    month_options = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    week_options = ["WEEK 1", "WEEK 2", "WEEK 3", "WEEK 4"]
    
    col_f1, col_f2 = st.columns(2)
    selected_month = col_f1.selectbox("Select Month", month_options, index=3) # Default April
    selected_week = col_f2.selectbox("Select Week", week_options, index=2)   # Default Week 3

    tab1, tab2, tab3 = st.tabs(["Monthly Comparison", "Yearly Week Comparison", "Cumulative Analysis"])

    # Month Calculation Logic
    m_idx = month_options.index(selected_month)
    prev_month = month_options[m_idx-1] if m_idx > 0 else "Jan"

    # --- TAB 1: Monthly Comparison (Current vs Previous Month in 2026) ---
    with tab1:
        st.subheader(f"Ward Trends: {selected_month} vs {prev_month} (2026)")
        curr_cols = [c for c in df_2026.columns if c.startswith(selected_month)]
        prev_cols = [c for c in df_2026.columns if c.startswith(prev_month)]
        
        for ward in df_2026['Ward'].unique():
            if ward in ['Ward', 'Total', 'YEAR 2026', 'YEAR 2025'] or pd.isna(ward): continue
            
            val_curr = df_2026[df_2026['Ward'] == ward][curr_cols].values.sum()
            val_prev = df_2026[df_2026['Ward'] == ward][prev_cols].values.sum()
            
            c1, c2 = st.columns([1, 4])
            c1.write(f"**Ward {ward}**")
            
            chart_df = pd.DataFrame({
                'Month': [prev_month, selected_month],
                'Cases': [val_prev, val_curr]
            })
            
            bar = alt.Chart(chart_df).mark_bar().encode(
                x=alt.X('Cases:Q', title=None),
                y=alt.Y('Month:N', sort=None, title=None),
                color=alt.Color('Month:N', scale=alt.Scale(range=['#CDE0F7', '#1F77B4']), legend=None)
            ).properties(height=60)
            c2.altair_chart(bar, use_container_width=True)

    # --- TAB 2: Yearly Week Comparison (2025 Week X vs 2026 Week X) ---
    with tab2:
        st.subheader(f"{selected_month} {selected_week}: 2025 vs 2026")
        target_col = f"{selected_month}_{selected_week}"
        
        for ward in df_2026['Ward'].unique():
            if ward in ['Ward', 'Total', 'YEAR 2026', 'YEAR 2025'] or pd.isna(ward): continue
            
            # Get values for the specific week
            val_25 = df_2025[df_2025['Ward'] == ward][target_col].values[0] if target_col in df_2025.columns else 0
            val_26 =
