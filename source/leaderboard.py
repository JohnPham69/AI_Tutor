import streamlit as st
import pandas as pd
import numpy as np # Added for array_split
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from app_translations import get_translator # Import translator
_ = get_translator() # Initialize translator for this page
#
# Page title
st.title(_("Leaderboard"))

# Check for secrets before attempting to connect
if "gcp_service_account" not in st.secrets:
    st.error("Lỗi cấu hình: Google Sheets credentials không được thiết lập trong Streamlit secrets.")
    st.info("Để ứng dụng này hoạt động, bạn cần thêm thông tin xác thực vào Streamlit secrets. Vui lòng tham khảo tài liệu của Streamlit về 'Secrets management'.")
    st.stop()

# Google Sheets scope and credentials
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# Open the spreadsheet and worksheet
SHEET_NAME = "QuizMakerAIDB"
WORKSHEET_NAME = "Students"
try:
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1xyKL_KQktxVjLfPh0eKCMc1ZyxMMdyiSZLk_p1nGafA").worksheet(WORKSHEET_NAME)
except Exception as e:
    st.error(f"Lỗi khi kết nối hoặc truy cập Google Sheets: {e}")
    st.info("Vui lòng kiểm tra lại cấu hình secrets và đảm bảo service account email đã được chia sẻ quyền Editor trên Google Sheet.")
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

# translation note
#
# Rank = Hạng
# Performance Ratio = Tỷ lệ đúng
# Total Attempted = Số câu đã làm
# User Name = Tên
# Correct Answer = Số câu đúng
# School = Trường
# Subject = Môn học
# Class = Lớp
# Student ID = Mã học sinh

# Ranking option selection
ranking_option = st.selectbox(
    _("Select Ranking Criteria"),
    [_("Rank by Correct answer"), _("Rank by Total Attempted")],
    index=0  # Default: Correct Answer
)

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

    # Convert 'Total Attempted' and 'Correct Answer' to integers before grouping
    if 'Total Attempted' in df_leaderboard.columns:
        df_leaderboard['Total Attempted'] = pd.to_numeric(df_leaderboard['Total Attempted'], errors='coerce').fillna(0).astype(int)
    if 'Correct Answer' in df_leaderboard.columns:
        df_leaderboard['Correct Answer'] = pd.to_numeric(df_leaderboard['Correct Answer'], errors='coerce').fillna(0).astype(int)

    # Group by 'User Name' and 'Subject', sum 'Total Attempted' and 'Correct Answer'
    if {'User Name', 'Subject', 'Total Attempted', 'Correct Answer'}.issubset(df_leaderboard.columns):
        df_leaderboard = (
            df_leaderboard
            .groupby(['User Name', 'Subject'], as_index=False)
            .agg({
                'Total Attempted': 'sum',
                'Correct Answer': 'sum',
                'School': 'first',
                'Class': 'first',
                'Student ID': 'first'
            })
        )

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

    # 1. Calculate Performance
    df_leaderboard['Performance'] = df_leaderboard.apply(
        lambda row: row['Correct Answer'] / row['Total Attempted']
        if row['Total Attempted'] > 0 else 0.0,
        axis=1
    )
    # Filter out users with less than 2 attempted questions
    df_leaderboard = df_leaderboard[df_leaderboard['Total Attempted'] >= 2]

    if not df_leaderboard.empty: # Proceed only if there are users meeting the criteria
        # 2. Sort the DataFrame
        if ranking_option == _("Rank by Correct answer"):
            sort_by_columns = ["Correct Answer", "Performance"]
            ascending_order = [False, False]
        else:  # Rank by Total Attempted
            sort_by_columns = ["Total Attempted", "Performance"]
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
        desired_cols_order = ["Rank", "User Name", "Correct Answer", "Total Attempted", "Subject",
                              "Performance", "School", "Class", "Student ID"]
        existing_cols_in_order = [col for col in desired_cols_order if col in df_leaderboard.columns]
        other_cols = [col for col in df_leaderboard.columns if col not in existing_cols_in_order]
        final_cols_order = existing_cols_in_order + other_cols
        df_leaderboard = df_leaderboard[final_cols_order]

# Translation dictionary for column headers
column_translation = {
    "Rank": "Hạng",
    "Performance": "Tỷ lệ đúng",
    "Total Attempted": "Số câu đã làm",
    "User Name": "Tên",
    "Correct Answer": "Số câu đúng",
    "School": "Trường",
    "Subject": "Môn học",
    "Class": "Lớp",
    "Student ID": "Mã học sinh"
}

# Determine language from session_state
lang = st.session_state.get("lang", "en")

# Format 'Performance' to 2 decimal places before translation
if not df_leaderboard.empty and 'Performance' in df_leaderboard.columns:
    df_leaderboard['Performance'] = pd.to_numeric(df_leaderboard['Performance'], errors='coerce').fillna(0.0).apply(lambda x: f'{x:.2f}')

# Translate column headers if Vietnamese is selected
if lang == "vi" and not df_leaderboard.empty:
    df_leaderboard = df_leaderboard.rename(columns=column_translation)
elif lang != "vi" and not df_leaderboard.empty:
    reverse_translation = {v: k for k, v in column_translation.items()}
    df_leaderboard = df_leaderboard.rename(columns=reverse_translation)

# Highlight function
def highlight_user(row_series): # Parameter is a pandas Series
    # Ensure 'User Name' column exists and value is comparable
    if 'User Name' in row_series.index and row_series['User Name'] == 'Bob':
        return ['background-color: yellow; font-weight: bold;'] * len(row_series)
    return [''] * len(row_series)

# Display leaderboard
st.subheader(_("Top Performers"))

if not df_leaderboard.empty:
    # Ensure 'Rank' column is treated as string for display due to medals
    if 'Rank' in df_leaderboard.columns:
        df_leaderboard['Rank'] = df_leaderboard['Rank'].astype(str)
    # If 'Performance' exists and was read as string, convert to numeric for potential formatting
    if 'Performance' in df_leaderboard.columns:
        # Convert to numeric and format to 2 decimal places
        df_leaderboard['Performance'] = pd.to_numeric(df_leaderboard['Performance'], errors='coerce').fillna(0.0).apply(lambda x: f'{x:.2f}')

    st.dataframe(df_leaderboard.style.apply(highlight_user, axis=1), hide_index=True, use_container_width=True)
else:
    st.write(_("Leaderboard is currently empty or could not be loaded."))
