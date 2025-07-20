import streamlit as st
import tempfile
import os
from StAI import genRes
from markitdown import MarkItDown
from app_translations import get_translator
from app_utils import get_cookie_controller

controller = get_cookie_controller()
_ = get_translator()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "uploaded_file_content" not in st.session_state:
    st.session_state.uploaded_file_content = ""

st.session_state.messages = []
st.session_state.uploaded_file_content = ""

if "first_question_sent" not in st.session_state:
    st.session_state.first_question_sent = False


# Accept chat input and file
prompt = st.chat_input(
    _("Type your message here (/x to clear, attach TXT/PPTX/PDF/DOCX if needed)"),
    accept_file=True,
    file_type=['txt', 'pptx', 'pdf', 'docx'],
)

uploaded_content = ""

user_api = st.session_state.get('user_api')
user_model = st.session_state.get('user_model')
selected_grade_from_tester = st.session_state.get('sb_grade_tester')
selected_subject_from_tester = st.session_state.get('sb_subject_tester')
selected_lesson_details_for_ai = st.session_state.get('selected_lesson_contexts', [])
uploaded_content_for_prompt = st.session_state.get("uploaded_file_content", "")

if not st.session_state.first_question_sent:
    prompt = "Bắt đầu thôi!"
    st.session_state.first_question_sent = True

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
        st.session_state.first_question_sent = False # Reset to send first question again
    elif prompt.get("text"):
        user_text = prompt["text"]
        with st.chat_message("user"):
            st.markdown(user_text)
        st.session_state.messages.append({"role": "user", "content": user_text})

        with st.chat_message("assistant"):
            with st.spinner("AI is thinking..."):
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
                # Ensure ai_response is not None before attempting to markdown.
                if ai_response is not None:
                    st.markdown(ai_response)
                else:
                    st.markdown("Error: No response from AI.")
        # Add assistant response to chat history
        if ai_response is not None:
            st.session_state.messages.append({"role": "assistant", "content": ai_response})

# Display chat messages from history.
# These will now render in Streamlit's main flow, below the sticky title.
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
