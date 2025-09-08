import streamlit as st
import pandas as pd
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from app_translations import get_translator
_ = get_translator()

st.title(_("Leaderboard"))

if "gcp_service_account" not in st.secrets:
    st.error("Lỗi cấu hình: Google Sheets credentials không được thiết lập trong Streamlit secrets.")
    st.info("Để ứng dụng này hoạt động, bạn cần thêm thông tin xác thực vào Streamlit secrets. Vui lòng tham khảo tài liệu của Streamlit về 'Secrets management'.")
    st.stop()

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

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

RAW_SHEET_COLUMNS = [
    "User Name",
    "Total Attempted",
    "Correct Answer",
    "Subject",
    "School",
    "Class",
    "Student ID"
]

all_values = sheet.get_all_values()

if not all_values:
    df_leaderboard = pd.DataFrame(columns=RAW_SHEET_COLUMNS)
else:
    df_leaderboard = pd.DataFrame(all_values)
    num_actual_cols = df_leaderboard.shape[1]
    df_leaderboard.columns = RAW_SHEET_COLUMNS[:num_actual_cols]
    if 'Total Attempted' in df_leaderboard.columns:
        df_leaderboard['Total Attempted'] = pd.to_numeric(df_leaderboard['Total Attempted'], errors='coerce').fillna(0).astype(int)
    if 'Correct Answer' in df_leaderboard.columns:
        df_leaderboard['Correct Answer'] = pd.to_numeric(df_leaderboard['Correct Answer'], errors='coerce').fillna(0).astype(int)
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

if not df_leaderboard.empty:
    if 'Total Attempted' in df_leaderboard.columns:
        df_leaderboard['Total Attempted'] = pd.to_numeric(df_leaderboard['Total Attempted'], errors='coerce').fillna(0)
    else:
        df_leaderboard['Total Attempted'] = 0
        st.warning("Cột 'Total Attempted' không tìm thấy trong Google Sheet. Mặc định là 0.")

    if 'Correct Answer' in df_leaderboard.columns:
        df_leaderboard['Correct Answer'] = pd.to_numeric(df_leaderboard['Correct Answer'], errors='coerce').fillna(0)
    else:
        df_leaderboard['Correct Answer'] = 0
        st.warning("Cột 'Correct Answer' không tìm thấy trong Google Sheet. Mặc định là 0.")

    df_leaderboard['Performance'] = df_leaderboard.apply(
        lambda row: row['Correct Answer'] / row['Total Attempted'] if row['Total Attempted'] > 0 else 0.0,
        axis=1
    )
    df_leaderboard = df_leaderboard[df_leaderboard['Total Attempted'] >= 5] # Total attempted more than 5 is needed in order to join the leaderboard

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

lang = st.session_state.get("lang", "en")

if not df_leaderboard.empty and 'Performance' in df_leaderboard.columns:
    df_leaderboard['Performance'] = pd.to_numeric(df_leaderboard['Performance'], errors='coerce').fillna(0.0)

sort_options = {
    _("Correct Answer"): "Correct Answer",
    _("Total Attempted"): "Total Attempted"
}
sort_choice = st.selectbox(
    _("Sort leaderboard by:"),
    options=list(sort_options.keys()),
    index=0
)
sort_col = sort_options[sort_choice]

# --- Interactive sorting and ranking logic ---

def assign_ranks(df, sort_col):
    df = df.copy()
    # Determine secondary and tertiary columns
    if sort_col == "Correct Answer":
        secondary_col = "Performance"
        tertiary_col = "Total Attempted"
    else:
        secondary_col = "Performance"
        tertiary_col = "Correct Answer"
    # Sort
    df = df.sort_values(
        by=[sort_col, secondary_col, tertiary_col, "User Name"],
        ascending=[False, False, False, True],
        kind="mergesort"
    ).reset_index(drop=True)
    # Assign competition-style ranks
    rank = 1
    prev = None
    ranks = []
    for idx, row in df.iterrows():
        curr = (row[sort_col], row[secondary_col], row[tertiary_col])
        if prev is not None and curr != prev:
            rank = idx + 1
        ranks.append(rank)
        prev = curr
    df['Rank'] = ranks
    # Add medals to top 3 unique ranks only
    medals = ["🥇", "🥈", "🥉"]
    unique_ranks = sorted(set(ranks))
    for medal_rank, medal in zip(unique_ranks[:3], medals):
        df.loc[df['Rank'] == medal_rank, 'Rank'] = f"{medal} {medal_rank}"
    df['Rank'] = df['Rank'].astype(str)
    return df

# Streamlit's interactive dataframe
st.subheader(_("Top Performers"))
if not df_leaderboard.empty:
    df_ranked = assign_ranks(df_leaderboard, sort_col)

    if 'Performance' in df_ranked.columns:
        df_ranked['Performance'] = df_ranked['Performance'].apply(lambda x: f'{x:.2f}')

    if lang == "vi":
        df_ranked = df_ranked.rename(columns=column_translation)
        desired_cols = [
            "Hạng", "Tên", "Số câu đúng", "Số câu đã làm", "Tỷ lệ đúng",
            "Môn học", "Trường", "Lớp", "Mã học sinh"
        ]
    else:
        reverse_translation = {v: k for k, v in column_translation.items()}
        df_ranked = df_ranked.rename(columns=reverse_translation)
        desired_cols = [
            "Rank", "User Name", "Correct Answer", "Total Attempted", "Performance",
            "Subject", "School", "Class", "Student ID"
        ]
    existing_cols = [col for col in desired_cols if col in df_ranked.columns]
    other_cols = [col for col in df_ranked.columns if col not in existing_cols]
    df_ranked = df_ranked[existing_cols + other_cols]

    st.dataframe(df_ranked, hide_index=True, use_container_width=True)
else:

    st.write(_("Leaderboard is currently empty or could not be loaded."))

