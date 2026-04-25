import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Disease Dashboard", layout="wide")

st.title("Ward-wise Comparison Dashboard (Data 2 Style)")

# --- १. फाईल अपलोडर (कोणतीही डिफॉल्ट लिंक नाही) ---
uploaded_file = st.file_uploader("तुमची एक्सेल फाईल (data for app.xlsx) इथे अपलोड करा", type=["xlsx"])

def load_data(file):
    xls = pd.ExcelFile(file, engine='openpyxl')
    sheets_dict = {}
    for sheet_name in xls.sheet_names:
        df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        
        # Header processing
        months_row = df_raw.iloc[0, 2:].ffill().tolist()
        weeks_row = df_raw.iloc[1, 2:].tolist()
        cols = ['Ward', 'Total'] + [f"{m}_{w}" for m, w in zip(months_row, weeks_row)]
        
        data_only = df_raw.iloc[2:].copy()
        data_only.columns = cols[:len(data_only.columns)]
        
        # Split 2025 and 2026 data based on 'A' ward position
        ward_a_indices = data_only[data_only['Ward'] == 'A'].index.tolist()
        if len(ward_a_indices) >= 2:
            df_25 = data_only.loc[ward_a_indices[0]:ward_a_indices[1]-2].copy()
            df_26 = data_only.loc[ward_a_indices[1]-1:].copy()
        else:
            df_25 = data_only.iloc[:56].copy()
            df_26 = data_only.iloc[56:].copy()
            
        for c in data_only.columns[1:]:
            df_25[c] = pd.to_numeric(df_25[c], errors='coerce').fillna(0)
            df_26[c] = pd.to_numeric(df_26[c], errors='coerce').fillna(0)
            
        sheets_dict[sheet_name] = {'25': df_25, '26': df_26}
    return sheets_dict

# --- २. ग्राफ फंक्शन (Data 2 फोटोप्रमाणे दोन बार्सची तुलना) ---
def create_comparison_chart(val_1, val_2, label_1, label_2, colors):
    chart_data = pd.DataFrame({
        'Category': [label_1, label_2],
        'Value': [val_1, val_2]
    })
    
    chart = alt.Chart(chart_data).mark_bar(height=15).encode(
        x=alt.X('Value:Q', axis=None), # No numbers on axis
        y=alt.Y('Category:N', axis=alt.Axis(title=None, labelFontWeight='bold'), sort=None),
        color=alt.Color('Category:N', scale=alt.Scale(range=colors), legend=None),
        tooltip=['Category', 'Value']
    ).properties(height=60)
    
    return chart.configure_view(strokeWidth=0)

# --- ३. मुख्य डिस्प्ले लॉजिक ---
if uploaded_file:
    data_all = load_data(uploaded_file)
    sheet_names = list(data_all.keys())
    
    # टॅब्स तयार करणे (Malaria, Dengue etc.)
    tabs = st.tabs(sheet_names)
    
    month_opts = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    week_opts = ["WEEK 1", "WEEK 2", "WEEK 3", "WEEK 4"]

    for i, name in enumerate(sheet_names):
        with tabs[i]:
            # --- स्वतंत्र फिल्टर्स (Independent for each tab) ---
            col_f1, col_f2 = st.columns(2)
            sel_m = col_f1.selectbox(f"Month Select", month_opts, index=3, key=f"m_{name}")
            sel_w = col_f2.selectbox(f"Week Select", week_opts, index=2, key=f"w_{name}")
            
            st.markdown("---")
            
            df_25 = data_all[name]['25']
            df_26 = data_all[name]['26']
            
            # कालखंड ठरवणे
            m_idx = month_opts.index(sel_m)
            prev_m = month_opts[m_idx-1] if m_idx > 0 else "Jan"
            target_col = f"{sel_m}_{sel_w}"
            cum_months = month_opts[:m_idx+1]
            
            # Headers (Data 2 लेआउटप्रमाणे)
            h_ward, h_1, h_2, h_3 = st.columns([1, 3, 3, 3])
            h_ward.write("**Ward**")
            h_1.write(f"**Monthly Comparison** ({prev_m} vs {sel_m} '26)")
            h_2.write(f"**Yearly Comparison** ({sel_m} {sel_w} '25 vs '26)")
            h_3.write(f"**Cumulative** (Jan to {sel_m} '25 vs '26)")
            st.divider()

            # प्रत्येक वॉर्डसाठी रो (Row) तयार करणे
            wards = df_26['Ward'].dropna().unique()
            for ward in wards:
                if ward in ['Ward', 'Total', 'YEAR 2026', 'YEAR 2025']: continue
                
                # १. Monthly (Current Year only)
                curr_m_cols = [c for c in df_26.columns if c.startswith(sel_m)]
                prev_m_cols = [c for c in df_26.columns if c.startswith(prev_m)]
                v_curr_m = df_26[df_26['Ward'] == ward][curr_m_cols].values.sum()
                v_prev_m = df_26[df_26['Ward'] == ward][prev_m_cols].values.sum()
                
                # २. Yearly Week (2025 vs 2026)
                v_25_wk = df_25[df_25['Ward'] == ward][target_col].values[0] if target_col in df_25.columns else 0
                v_26_wk = df_26[df_26['Ward'] == ward][target_col].values[0] if target_col in df_26.columns else 0
                
                # ३. Cumulative (2025 vs 2026)
                cum_cols = [c for c in df_26.columns if any(c.startswith(m) for m in cum_months)]
                v_25_cum = df_25[df_25['Ward'] == ward][cum_cols].values.sum()
                v_26_cum = df_26[df_26['Ward'] == ward][cum_cols].values.sum()

                # डिस्प्ले रो
                c_ward, c_1, c_2, c_3 = st.columns([1, 3, 3, 3])
                c_ward.subheader(ward)
                
                # तिन्ही ग्राफ्स एका ओळीत
                c_1.altair_chart
