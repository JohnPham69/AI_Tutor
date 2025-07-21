import streamlit as st
from StLearn import genRes
from markitdown import MarkItDown
from app_translations import get_translator # Import the translator
from app_utils import get_cookie_controller, get_cookies_manager # Import the singleton controller
import tempfile
import os
from streamlit_cookies_manager import CookieManager

# Global variable
follow_up = [] # an array that stores follow_up quesiotns

_ = get_translator() # Initialize translator for this page, assumes session_state lang is set by Tester.py

# Initialize chat history if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

if "uploaded_file_content" not in st.session_state:
    st.session_state.uploaded_file_content = ""

st.session_state.messages.append({"role": "assistant", "content": _("Shall we start?")})


# These will now render in Streamlit's main flow, below the sticky title.
if "messages" in st.session_state:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


# Accept chat input and file
prompt = st.chat_input(
    _("Type your message here (/x to clear, attach TXT/PPTX/PDF/DOCX if needed)"),
    accept_file=True,
    file_type=['txt', 'pptx', 'pdf', 'docx'],
)

uploaded_content = ""
# Xử lý follow_up cho mỗi lần assistant trả lời

# Instead, fetch from st.session_state
user_api = st.session_state.get('user_api')
user_model = st.session_state.get('user_model')

def extract_response_and_followup(ai_response):
    if "///Follow_up///" in ai_response:
        response = ai_response.split("///Follow_up///")[0].strip()
        follow_up_raw = ai_response.split("///Follow_up///")[1]
        follow_up = [q.strip() for q in follow_up_raw.split("-") if q.strip()]
    else:
        response = ai_response.strip()
        follow_up = []
    return response, follow_up

if prompt:
    # Handle file upload
    if prompt.get("files"):
        uploaded_file = prompt["files"][0]
        st.write(f"Processing: {uploaded_file.name} ({uploaded_file.size} bytes)")
        try:
            file_bytes = uploaded_file.getvalue()
            file_extension = os.path.splitext(uploaded_file.name)[1].lower()
            if file_extension == ".pdf":
                md_converter = MarkItDown()
            elif file_extension in [".xlsx", ".xls"]:
                md_converter = MarkItDown(enable_plugins=False)
            else:
                md_converter = MarkItDown()
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension, mode='wb') as tmp_file:
                tmp_file.write(file_bytes)
                temp_file_path = tmp_file.name
            try:
                result = md_converter.convert(temp_file_path)
                uploaded_content = result.text_content
                st.session_state.uploaded_file_content = uploaded_content
            except Exception as e:
                st.error(f"MarkItDown error for {uploaded_file.name}: {e}")
            finally:
                os.unlink(temp_file_path)
        except Exception as e:
            st.error(f"Error processing file: {e}")
    # Handle chat clear
    if prompt.get("text", "").strip() == "/x":
        st.session_state.messages = []
        st.session_state.uploaded_file_content = ""
        st.rerun()
    elif prompt.get("text"):
        user_text = prompt["text"]
        with st.chat_message("user"):
            st.markdown(user_text)
        st.session_state.messages.append({"role": "user", "content": user_text})

        
        selected_grade_from_tester = st.session_state.get('sb_grade_tester')
        selected_subject_from_tester = st.session_state.get('sb_subject_tester')
        selected_lesson_details_for_ai = st.session_state.get('selected_lesson_contexts', [])
        uploaded_content_for_prompt = st.session_state.get("uploaded_file_content", "")

        with st.chat_message("assistant"):
            with st.spinner(_("AI is thinking...")):
                ai_response = genRes(
                    user_text,
                    st.session_state.messages,
                    user_api,
                    user_model,
                    selected_grade=selected_grade_from_tester,
                    selected_subject_name=selected_subject_from_tester,
                    selected_lesson_data_list=selected_lesson_details_for_ai,
                    uploaded_file_text=uploaded_content_for_prompt,
                    translator=_
                )
                if ai_response is not None:
                    response, follow_up = extract_response_and_followup(ai_response)
                    st.session_state["last_follow_up"] = follow_up  # Lưu follow_up vào session_state
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                else:
                    st.markdown("Error: No response from AI.")
                    st.session_state["last_follow_up"] = []
# Only show suggestion buttons if there are messages and there are follow up questions
follow_up = st.session_state.get("last_follow_up", [])
if st.session_state.messages and len(follow_up) != 0:
    for idx, question in enumerate(follow_up):
        if st.button(question, key=f"followup_{idx}"):
            st.session_state.messages.append({"role": "user", "content": question})

            selected_grade_from_tester = st.session_state.get('sb_grade_tester')
            selected_subject_from_tester = st.session_state.get('sb_subject_tester')
            selected_lesson_details_for_ai = st.session_state.get('selected_lesson_contexts', [])
            uploaded_content_for_prompt = st.session_state.get("uploaded_file_content", "")

            with st.chat_message("assistant"):
                with st.spinner(_("AI is thinking...")):
                    ai_response = genRes(
                        question,
                        st.session_state.messages,
                        user_api,
                        user_model,
                        selected_grade=selected_grade_from_tester,
                        selected_subject_name=selected_subject_from_tester,
                        selected_lesson_data_list=selected_lesson_details_for_ai,
                        uploaded_file_text=uploaded_content_for_prompt,
                        translator=_
                    )
                    if ai_response is not None:
                        response, follow_up = extract_response_and_followup(ai_response)
                        st.session_state["last_follow_up"] = follow_up
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    else:
                        st.markdown("Error: No response from AI.")
                        st.session_state["last_follow_up"] = []
            st.rerun()
