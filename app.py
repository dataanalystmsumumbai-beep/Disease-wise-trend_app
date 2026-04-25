import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Disease Trend Dashboard", layout="wide")

st.title("Ward-wise Disease Trend Analysis")

# --- DATA LOADING ---
DEFAULT_GSHEET_URL = "https://docs.google.com/spreadsheets/d/11-ZeoBvixvY_ujLO8_9Vlze2jmGC4CooTWjvd2INX-4/edit?gid=1214285155#gid=1214285155"

def get_csv_url(url):
    if "/edit" in url:
        return url.split('/edit')[0] + "/export?format=csv&gid=" + url.split('gid=')[1].split('#')[0]
    return url

@st.cache_data
def load_and_clean_data(url):
    df_raw = pd.read_csv(get_csv_url(url), header=None)
    
    # Identify Year 2025 and 2026 rows
    # Assuming 2025 starts at top and 2026 starts after a certain row
    # In your data, 2026 starts where the 'Ward' column repeats 'A' again
    
    # Simple cleaning: header is in rows 0 and 1
    months = df_raw.iloc[0, 2:].fillna(method='ffill').tolist()
    weeks = df_raw.iloc[1, 2:].tolist()
    columns = ['Ward', 'Total'] + [f"{m}_{w}" for m, w in zip(months, weeks)]
    
    # Split into 2025 and 2026 (Logic based on ward 'A' appearing twice)
    data_only = df_raw.iloc[2:].copy()
    data_only.columns = columns
    
    # Finding the break point where 2026 starts
    indices = data_only[data_only['Ward'] == 'A'].index.tolist()
    df_2025 = data_only.loc[indices[0]:indices[1]-2].copy()
    df_2026 = data_only.loc[indices[1]-1:].copy() # Adjusting for Year title row
    
    # Convert numeric columns
    for col in columns[1:]:
        df_2025[col] = pd.to_numeric(df_2025[col], errors='coerce').fillna(0)
        df_2026[col] = pd.to_numeric(df_2026[col], errors='coerce').fillna(0)
        
    return df_2025, df_2026, list(set(months))

try:
    df_2025, df_2026, month_list = load_and_clean_data(DEFAULT_GSHEET_URL)
    
    # --- UI FILTERS ---
    col_f1, col_f2 = st.columns(2)
    selected_month = col_f1.selectbox("Select Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], index=3)
    selected_week = col_f2.selectbox("Select Week", ["WEEK 1", "WEEK 2", "WEEK 3", "WEEK 4"])

    tab1, tab2, tab3 = st.tabs(["Monthly Comparison (2026)", "Yearly Week Comparison (25 vs 26)", "Cumulative Analysis"])

    # Helper to get previous month
    month_idx = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    prev_month = month_idx[month_idx.index(selected_month)-1] if month_idx.index(selected_month) > 0 else "Jan"

    # --- TAB 1: CURRENT VS PREVIOUS MONTH (2026) ---
    with tab1:
        st.subheader(f"Comparison: {selected_month} 2026 vs {prev_month} 2026")
        
        # Calculate sum for months
        cols_curr = [c for c in df_2026.columns if c.startswith(selected_month)]
        cols_prev = [c for c in df_2026.columns if c.startswith(prev_month)]
        
        for index, row in df_2026.iterrows():
            ward = row['Ward']
            if ward == 'Total': continue
            
            val_curr = row[cols_curr].sum()
            val_prev = row[cols_prev].sum()
            
            # Displaying each ward with a small bar chart
            c1, c2 = st.columns([1, 5])
            c1.write(f"**Ward {ward}**")
            
            chart_data = pd.DataFrame({
                'Period': [prev_month, selected_month],
                'Cases': [val_prev, val_curr]
            })
            
            chart = alt.Chart(chart_data).mark_bar().encode(
                x=alt.X('Cases:Q', title=None),
                y=alt.Y('Period:N', sort='-x', title=None),
                color=alt.Color('Period:N', legend=None, scale=alt.Scale(range=['#aec7e8', '#1f77b4']))
            ).properties(height=70)
            
            c2.altair_chart(chart, use_container_width=True)

    # --- TAB 2: YEARLY WEEK COMPARISON ---
    with tab2:
        st.subheader(f"Comparison: {selected_month} {selected_week} (2025 vs 2026)")
        target_col = f"{selected_month}_{selected_week}"
        
        # Merge data for comparison
        comp_df = pd.merge(df_2025[['Ward', target_col]], df_2026[['Ward', target_col]], on='Ward', suffixes=('_25', '_26'))
        
        for index, row in comp_df.iterrows():
            ward = row['Ward']
            if ward == 'Total': continue
            
            c1, c2 = st.columns([1, 5])
            c1.write(f"**Ward {ward}**")
            
            chart_data = pd.DataFrame({
                'Year': ['2025', '2026'],
                'Cases': [row[target_col+'_25'], row[target_col+'_26']]
            })
            
            chart = alt.Chart(chart_data).mark_bar().encode(
                x=alt.X('Cases:Q', title=None),
                y=alt.Y('Year:N', title=None),
                color=alt.Color('Year:N', legend=None, scale=alt.Scale(range=['#ffbb78', '#ff7f0e']))
            ).properties(height=70)
            
            c2.altair_chart(chart, use_container_width=True)

    # --- TAB 3: CUMULATIVE ---
    with tab3:
        st.subheader(f"Cumulative: Jan to {selected_month} (2025 vs 2026)")
        
        # Find all columns up to current month
        limit_idx = month_idx.index(selected_month) + 1
        months_to_sum = month_idx[:limit_idx]
        
        all_cols_to_sum = [c for c in df_2025.columns if any(c.startswith(m) for m in months_to_sum)]
        
        for ward in df_2025['Ward'].unique():
            if ward == 'Total': continue
            
            val_25 = df_2025[df_2025['Ward'] == ward][all_cols_to_sum].values.sum()
            val_26 = df_2026[df_2026['Ward'] == ward][all_cols_to_sum].values.sum()
            
            c1, c2 = st.columns([1, 5])
            c1.write(f"**Ward {ward}**")
            
            chart_data = pd.DataFrame({
                'Year': ['2025 Total', '2026 Total'],
                'Total Cases': [val_25, val_26]
            })
            
            chart = alt.Chart(chart_data).mark_bar().encode(
                x=alt.X('Total Cases:Q', title=None),
                y=alt.Y('Year:N', title=None),
                color=alt.Color('Year:N', legend=None, scale=alt.Scale(range=['#98df8a', '#2ca02c']))
            ).properties(height=70)
            
            c2.altair_chart(chart, use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
    st.info("Please check if the Google Sheet link and structure are correct.")
