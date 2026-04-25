import io

# --- New Function to Create Formatted Excel ---
def create_formatted_excel(data_dict):
    output = io.BytesIO()
    # Use xlsxwriter engine for styling
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Define Formats
        header_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#D7E4BC', 'border': 1, 'align': 'center'
        })
        cell_fmt = workbook.add_format({'border': 1, 'align': 'center'})
        title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'font_color': '#1F4E78'})
        
        for sheet_name, data in data_dict.items():
            # Get dataframes for this sheet (Logic to regenerate df1, df2, df3, df4)
            # For brevity, this assumes you pass the processed dataframes to this function
            # Or you can combine them here.
            
            worksheet = workbook.add_worksheet(sheet_name[:31]) # Max 31 chars
            curr_row = 0
            
            # Helper to write table
            def write_styled_table(ws, df, start_row, title):
                ws.write(start_row, 0, title, title_fmt)
                # Write Header
                for col_num, value in enumerate(df.columns.values):
                    ws.write(start_row + 2, col_num, value, header_fmt)
                # Write Data
                for row_num, row_data in enumerate(df.values):
                    for col_num, value in enumerate(row_data):
                        ws.write(row_num + start_row + 3, col_num, value, cell_fmt)
                return start_row + len(df) + 6 # Return next start row with gap

            # Example of writing sections with space
            # (Assuming df1, df2, df3, df4 are generated for the sheet)
            # curr_row = write_styled_table(worksheet, df1, curr_row, "1. Monthly Comparison")
            # curr_row = write_styled_table(worksheet, df2, curr_row, "2. Yearly Comparison")
            # ... and so on
            
    output.seek(0)
    return output

# --- Update your Download Button UI section ---
# Inside your 'for sheet_name in data_dict.keys():' loop:
# After creating df1, df2, df3, df4

formatted_report = io.BytesIO()
with pd.ExcelWriter(formatted_report, engine='xlsxwriter') as writer:
    workbook = writer.book
    header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1, 'align': 'center'})
    cell_fmt = workbook.add_format({'border': 1, 'align': 'center'})
    title_fmt = workbook.add_format({'bold': True, 'font_size': 14})
    
    ws = workbook.add_worksheet(sheet_name[:31])
    
    def write_df(df, start_row, title):
        ws.write(start_row, 0, title, title_fmt)
        for c, col in enumerate(df.columns):
            ws.write(start_row+1, c, col, header_fmt)
        for r, row in enumerate(df.values):
            for c, val in enumerate(row):
                ws.write(r+start_row+2, c, val, cell_fmt)
        return start_row + len(df) + 4

    next_r = write_df(df1, 0, "1. Monthly Comparison")
    next_r = write_df(df2, next_r, "2. Yearly Comparison")
    next_r = write_df(df3, next_r, "3. Cumulative Comparison")
    write_df(df4, next_r, "4. Summary Trends")

st.download_button(
    label=f"📥 Download {sheet_name} Formatted Report",
    data=formatted_report,
    file_name=f"{sheet_name}_Analysis.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    key=f"dl_new_{sheet_name}"
)
