import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Function to add a new result to Google Sheets
# This function is designed to be called from the Test_practice_page.py
def AddNewResult(user_nickname: str, user_school: str, user_class: str, user_id: str, total_questions_str: str, correct_answers_str: str, subject_name: str):
    try:
        # Google Sheets scope and credentials
        # These are already defined globally in this file, but for robustness
        # if this function were moved, it's good practice to re-establish or pass them.
        # For this specific request, we'll re-initialize for clarity and independence.
        gs_scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        gs_creds_json = st.secrets["gcp_service_account"]
        gs_creds = ServiceAccountCredentials.from_json_keyfile_dict(gs_creds_json, gs_scope)
        gs_client = gspread.authorize(gs_creds)

        spreadsheet_key = "1xyKL_KQktxVjLfPh0eKCMc1ZyxMMdyiSZLk_p1nGafA" # Same as used above
        worksheet_name = "Students" # Same as used above
        gs_sheet = gs_client.open_by_key(spreadsheet_key).worksheet(worksheet_name)

        # Convert total_questions and correct_answers to int
        total_q_int = int(total_questions_str) if total_questions_str else 0
        correct_a_int = int(correct_answers_str) if correct_answers_str else 0

        # Prepare the row data according to the expected columns:
        # "Rank", "User Name", "Total Attempted", "Correct Answer", "Subject",
        # "Performance Ratio", "School", "Class", "Student ID"
        new_row = [
            user_nickname,
            total_q_int,
            correct_a_int,
            subject_name,
            user_school,
            user_class,
            user_id
        ]
        gs_sheet.append_row(new_row, value_input_option='USER_ENTERED')
        # st.success("New result added to Google Sheets successfully!") # Optional: for direct feedback if called from UI
        return True
    except Exception as e:
        st.error(f"Lỗi khi lưu kết quả mới vào Google Sheets: {e}")
        print(f"Error in AddNewResult (Test_leader_page.py): {e}")
        return False