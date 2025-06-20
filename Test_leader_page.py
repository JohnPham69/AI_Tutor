import streamlit as st
import pandas as pd
import numpy as np # Added for array_split
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Page title
st.title("🏆 Leaderboard")

# Google Sheets scope and credentials
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"], scope
)
client = gspread.authorize(creds)

# Open or create the spreadsheet
SHEET_NAME = "QuizMakerAIDB"
WORKSHEET_NAME = "Students"
try:
    sheet = client.open_by_key("1xyKL_KQktxVjLfPh0eKCMc1ZyxMMdyiSZLk_p1nGafA").worksheet(WORKSHEET_NAME)
except gspread.exceptions.SpreadsheetNotFound:
    st.error(f"Spreadsheet '{SHEET_NAME}' not found. Make sure it's created and shared with your service account.")
    st.stop()
except gspread.exceptions.WorksheetNotFound:
    st.error(f"Worksheet '{WORKSHEET_NAME}' not found in Spreadsheet '{SHEET_NAME}'.")
    st.stop()

# Sample leaderboard data (kept empty as requested)
data = [] 
# df_sample = pd.DataFrame(data) # This line is not strictly necessary anymore

# Define the column names based on the structure written by AddNewResult
# These names will be assigned to the DataFrame created from sheet values.
RAW_SHEET_COLUMNS = [
    "User Name",
    "Total Attempted",
    "Correct Answer",
    "Subject",
    "School",
    "Class",
    "Student ID"
]

# Read all values from the sheet to bypass gspread's header processing
all_values = sheet.get_all_values()

if not all_values:
    # If the sheet is empty, create an empty DataFrame with the expected raw columns
    df_leaderboard = pd.DataFrame(columns=RAW_SHEET_COLUMNS)
else:
    # Create DataFrame from all_values. Pandas will use default integer column names (0, 1, ...)
    df_leaderboard = pd.DataFrame(all_values)
    # Assign our defined column names, up to the number of columns actually present in the sheet data
    num_actual_cols = df_leaderboard.shape[1]
    df_leaderboard.columns = RAW_SHEET_COLUMNS[:num_actual_cols]

# Process the data fetched from Google Sheets
if not df_leaderboard.empty:
    # Convert 'Total Attempted' and 'Correct Answer' to numeric, fill errors with 0
    if 'Total Attempted' in df_leaderboard.columns:
        df_leaderboard['Total Attempted'] = pd.to_numeric(df_leaderboard['Total Attempted'], errors='coerce').fillna(0)
    else:
        df_leaderboard['Total Attempted'] = 0 # Create column if missing
        st.warning("Cột 'Total Attempted' không tìm thấy trong Google Sheet. Mặc định là 0.")

    if 'Correct Answer' in df_leaderboard.columns:
        df_leaderboard['Correct Answer'] = pd.to_numeric(df_leaderboard['Correct Answer'], errors='coerce').fillna(0)
    else:
        df_leaderboard['Correct Answer'] = 0 # Create column if missing
        st.warning("Cột 'Correct Answer' không tìm thấy trong Google Sheet. Mặc định là 0.")

    # Ensure placeholder columns (if read and named) are handled or ignored if not numeric.
    # The numeric conversion above for 'Total Attempted' and 'Correct Answer' will
    # turn non-numeric data in those columns (like an original bad header row) into NaN,
    # which .fillna(0) handles.
    # 'Rank_Placeholder' and 'Perf_Ratio_Placeholder' are not directly used in calculations
    # before 'Rank' and 'Performance Ratio' are created.
    # If they were accidentally numeric and matched 'Total Attempted', they'd be converted,
    # but their distinct names prevent direct misuse in the logic below.

    # 1. Calculate Performance Ratio
    df_leaderboard['Performance Ratio'] = df_leaderboard.apply(
        lambda row: row['Correct Answer'] / row['Total Attempted']
        if row['Total Attempted'] > 0 else 0.0,
        axis=1
    )
    # Filter out users with less than 2 attempted questions
    df_leaderboard = df_leaderboard[df_leaderboard['Total Attempted'] >= 2]

    if not df_leaderboard.empty: # Proceed only if there are users meeting the criteria
        # 2. Sort the DataFrame
        sort_by_columns = ["Performance Ratio", "Total Attempted"]
        ascending_order = [False, False]
        if 'User Name' in df_leaderboard.columns:
            sort_by_columns.append("User Name")
            ascending_order.append(True)
        else:
            st.warning("Cột 'User Name' không tìm thấy. Việc sắp xếp bảng xếp hạng có thể bị ảnh hưởng.")

        df_leaderboard = df_leaderboard.sort_values(
            by=sort_by_columns,
            ascending=ascending_order
        ).reset_index(drop=True)

        # 3. Add Rank column (numeric first)
        df_leaderboard.insert(0, 'Rank', range(1, 1 + len(df_leaderboard)))

        # 4. Add medals to top 3 (Rank becomes string)
        medals = ["🥇", "🥈", "🥉"]
        for i in range(min(3, len(df_leaderboard))):
            df_leaderboard.loc[i, 'Rank'] = f"{medals[i]} {df_leaderboard.loc[i, 'Rank']}"
        df_leaderboard['Rank'] = df_leaderboard['Rank'].astype(str) # Ensure all ranks are strings

        # 5. Reorder columns to a defined order
        desired_cols_order = ["Rank", "User Name", "Total Attempted", "Correct Answer", "Subject",
                              "Performance Ratio", "School", "Class", "Student ID"]
        existing_cols_in_order = [col for col in desired_cols_order if col in df_leaderboard.columns]
        other_cols = [col for col in df_leaderboard.columns if col not in existing_cols_in_order]
        final_cols_order = existing_cols_in_order + other_cols
        df_leaderboard = df_leaderboard[final_cols_order]

# Highlight function
def highlight_user(row_series): # Parameter is a pandas Series
    # Ensure 'User Name' column exists and value is comparable
    if 'User Name' in row_series.index and row_series['User Name'] == 'Bob':
        return ['background-color: yellow; font-weight: bold;'] * len(row_series)
    return [''] * len(row_series)

# Display leaderboard
st.subheader("Top Performers")

if not df_leaderboard.empty:
    # Ensure 'Rank' column is treated as string for display due to medals
    if 'Rank' in df_leaderboard.columns: # Should already be string after medal processing
        df_leaderboard['Rank'] = df_leaderboard['Rank'].astype(str)
    # If 'Performance Ratio' exists and was read as string, convert to numeric for potential formatting
    if 'Performance Ratio' in df_leaderboard.columns:
        # Convert to numeric and format to 2 decimal places
        df_leaderboard['Performance Ratio'] = pd.to_numeric(df_leaderboard['Performance Ratio'], errors='coerce').fillna(0.0).apply(lambda x: f'{x:.2f}')

    st.dataframe(df_leaderboard.style.apply(highlight_user, axis=1), hide_index=True, use_container_width=True)
else:
    st.write("Leaderboard is currently empty or could not be loaded.")
