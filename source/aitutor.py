import streamlit as st
import tempfile
import os
from StAI import genRes
from markitdown import MarkItDown
from app_translations import get_translator
from app_utils import get_cookie_controller

controller = get_cookie_controller()
_ = get_translator()
#
# Initialize chat history if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

if "uploaded_file_content" not in st.session_state:
    st.session_state.uploaded_file_content = ""

# Display chat messages from history.
if "messages" in st.session_state:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

starting_mess = _("Shall we start?")
start_api_miss = _("API Key Missing Error Config")
if not st.session_state.get('user_api'):
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": start_api_miss})
else:
    st.session_state.messages = []
    st.session_state['first_mess_set'] = False
    st.session_state.messages.append({"role": "assistant", "content": starting_mess})

# Accept chat input and file
prompt = st.chat_input(
    _("Type your message here (/x to clear, attach TXT/PPTX/PDF/DOCX if needed)"),
    accept_file=True,
    file_type=['txt', 'pptx', 'pdf', 'docx'],
)

uploaded_content = ""

user_api = st.session_state.get('user_api')
user_model = st.session_state.get('user_model')

if not st.session_state.first_mess_set:
    first_mess_fake = "Ok, chúng ta có thể bắt đầu."
    selected_grade_from_tester = st.session_state.get('sb_grade_tester')
    selected_subject_from_tester = st.session_state.get('sb_subject_tester')
    selected_lesson_details_for_ai = st.session_state.get('selected_lesson_contexts', [])
    
    with st.chat_message("assistant"):
        with st.spinner(_("AI is thinking...")):
            ai_response = genRes(
                first_mess_fake,
                st.session_state.messages,
                user_api,
                user_model,
                selected_grade=selected_grade_from_tester,
                selected_subject_name=selected_subject_from_tester,
                selected_lesson_data_list=selected_lesson_details_for_ai,
                uploaded_file_text=None,
                translator=_
            )
            if ai_response is not None:
                st.markdown(ai_response)
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                st.session_state.first_mess_set = True
            else:
                st.markdown("Error: No response from AI.")
                st.session_state.first_mess_set = True
else:
    pass

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
                    st.markdown(ai_response)
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})
                else:
                    st.markdown("Error: No response from AI.")
