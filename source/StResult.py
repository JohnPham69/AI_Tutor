import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
#
# Add nâng cao into bảng xếp hạng
# Function to add or update a result in Google Sheets.
# It checks for an existing entry with the same Student ID and Subject.
# If found, it updates the scores. Otherwise, it adds a new row.
def AddNewResult(user_nickname: str, user_school: str, user_class: str, user_id: str, current_quiz_questions: int, current_quiz_correct: int, subject_name: str, difficulty: str):
    # Check for secrets before proceeding
    if "gcp_service_account" not in st.secrets:
        st.error(_("Lỗi cấu hình: Google Sheets credentials không được thiết lập trong Streamlit secrets."))
        print(_("Error in AddNewResult: 'gcp_service_account' not found in st.secrets."))
        return False

    try:
        # Google Sheets scope and credentials
        gs_scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        gs_creds_json = st.secrets["gcp_service_account"]
        gs_creds = ServiceAccountCredentials.from_json_keyfile_dict(gs_creds_json, gs_scope)
        gs_client = gspread.authorize(gs_creds)

        spreadsheet_key = "1xyKL_KQktxVjLfPh0eKCMc1ZyxMMdyiSZLk_p1nGafA"
        worksheet_name = "Students"
        gs_sheet = gs_client.open_by_key(spreadsheet_key).worksheet(worksheet_name)

        # Fetch all data to check for existing records
        all_records = gs_sheet.get_all_values()

        # Column indices based on the structure in Test_leader_page.py
        # "User Name", "Total Attempted", "Correct Answer", "Subject", "School", "Class", "Student ID"
        TOTAL_ATTEMPTED_COL = 1
        CORRECT_ANSWER_COL = 2
        SUBJECT_COL = 3
        STUDENT_ID_COL = 6

        match_found = False
        # gspread rows are 1-indexed, list is 0-indexed.
        for i, row in enumerate(all_records):
            # Check if row has enough columns to avoid IndexError
            if len(row) > max(STUDENT_ID_COL, SUBJECT_COL):
                existing_student_id = row[STUDENT_ID_COL]
                existing_subject = row[SUBJECT_COL]

                if existing_student_id == user_id and existing_subject == subject_name:
                    # Match found, update the row
                    try:
                        # Get existing scores, handle potential non-numeric values (like headers)
                        existing_total_q = int(row[TOTAL_ATTEMPTED_COL])
                        existing_correct_a = int(row[CORRECT_ANSWER_COL])
                    except (ValueError, TypeError):
                        existing_total_q = 0
                        existing_correct_a = 0

                    # Calculate new totals by adding the results from the current quiz
                    updated_total_q = existing_total_q + current_quiz_questions
                    updated_correct_a = existing_correct_a + current_quiz_correct

                    # Prepare the full updated row. Also update user info in case it changed.
                    updated_row_data = [user_nickname, updated_total_q, updated_correct_a, subject_name, user_school, user_class, user_id]
                    
                    row_to_update_idx = i + 1
                    # Update the row in the sheet. The range is from column A to G for the specific row.
                    gs_sheet.update(f'A{row_to_update_idx}:G{row_to_update_idx}', [updated_row_data])
                    
                    match_found = True
                    break # Exit loop once the match is found and updated

        if not match_found:
            # No match found, append a new row with the initial results
            new_row_data = [user_nickname, current_quiz_questions, current_quiz_correct, subject_name, user_school, user_class, user_id]
            gs_sheet.append_row(new_row_data, value_input_option='USER_ENTERED')
        
        return True
    except Exception as e:
        st.error(f"Lỗi khi lưu kết quả mới vào Google Sheets: {e}")
        print(f"Error in AddNewResult: {e}")
        return False


