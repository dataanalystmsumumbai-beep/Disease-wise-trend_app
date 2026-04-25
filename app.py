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

# --- Create Formatted Excel Report ---
        formatted_report = io.BytesIO()
        
        # Using xlsxwriter for borders and highlights
        with pd.ExcelWriter(formatted_report, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            # --- Styles/Formats ---
            header_fmt = workbook.add_format({
                'bold': True,
                'bg_color': '#D7E4BC',  # Light Green highlight
                'border': 1,            # Thin border
                'align': 'center',
                'valign': 'vcenter'
            })
            
            cell_fmt = workbook.add_format({
                'border': 1,            # Border for all data cells
                'align': 'center'
            })
            
            title_fmt = workbook.add_format({
                'bold': True,
                'font_size': 14,
                'font_color': '#1F4E78'  # Dark Blue title
            })

            ws = workbook.add_worksheet(sheet_name[:31])
            
            # Function to write tables with borders and spacing
            def write_styled_df(df, start_row, title):
                # Write Title
                ws.write(start_row, 0, title, title_fmt)
                
                # Write Header Row
                for col_num, col_name in enumerate(df.columns):
                    ws.write(start_row + 1, col_num, col_name, header_fmt)
                
                # Write Data Rows
                for row_num, row_values in enumerate(df.values):
                    for col_num, value in enumerate(row_values):
                        ws.write(row_num + start_row + 2, col_num, value, cell_fmt)
                
                # Return next start row (Table length + Title + Header + 3 blank rows for space)
                return start_row + len(df) + 5

            # Write all 4 tables with spacing
            current_r = write_styled_df(df1, 0, "1. Monthly Comparison (2026)")
            current_r = write_styled_df(df2, current_r, "2. Yearly Comparison (2025 vs 2026)")
            current_r = write_styled_df(df3, current_r, "3. Cumulative Comparison")
            write_styled_df(df4, current_r, "4. Summary Trends (%)")

        # --- Download Button UI ---
        st.download_button(
            label=f"📥 Download {sheet_name} Formatted Report",
            data=formatted_report.getvalue(),
            file_name=f"{sheet_name}_Analysis_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"dl_btn_{sheet_name}"
        )
