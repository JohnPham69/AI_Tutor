import streamlit as st
from streamlit_javascript import st_javascript
from streamlit_cookies_controller import CookieController
from Prac_AI import generate_quiz_data, evaluate_user_answer_clarity
import streamlit.components.v1 as components

# --- Constants ---
QUIZ_STATE_INITIAL = "initial"
QUIZ_STATE_CONFIG = "config"
QUIZ_STATE_QUESTIONING = "questioning"
QUIZ_STATE_GRADING_FEEDBACK = "grading_feedback"
FEEDBACK_STATUS_CORRECT = "correct"
FEEDBACK_STATUS_INCORRECT = "incorrect"
FEEDBACK_STATUS_ERROR = "error"

# --- Session state init ---
def ensure_session():
    default_values = {
        "quiz_step": QUIZ_STATE_INITIAL,
        "num_questions_to_ask": 0,
        "current_question_idx": 0,
        "user_answers": {},
        "feedback": {},
        "generated_quiz_data": [],
        "quiz_error_message": None,
        "time_for_each": 60,
    }
    for key, val in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = val

ensure_session()
controller = CookieController()
st.title("Practice Quiz")

# --- Reset function ---
def reset_quiz_state(set_step_to_initial=True):
    if set_step_to_initial:
        st.session_state.quiz_step = QUIZ_STATE_INITIAL
    st.session_state.num_questions_to_ask = 0
    st.session_state.current_question_idx = 0
    st.session_state.user_answers = {}
    st.session_state.feedback = {}
    st.session_state.generated_quiz_data = []
    st.session_state.quiz_error_message = None

# --- INITIAL STATE ---
if st.session_state.quiz_step == QUIZ_STATE_INITIAL:
    st.markdown("### Bắt đầu một phiên luyện tập mới")
    if st.session_state.quiz_error_message:
        st.error(st.session_state.quiz_error_message)
        st.session_state.quiz_error_message = None

    if st.button("Bắt đầu bài quiz"):
        st.session_state.quiz_step = QUIZ_STATE_CONFIG
        st.rerun()
    st.caption("Dựa trên môn học và bài học đã chọn ở thanh bên (nếu có).")

# --- CONFIG STATE ---
elif st.session_state.quiz_step == QUIZ_STATE_CONFIG:
    st.markdown("### Cấu hình Bài Quiz của Bạn")
    selected_subject = st.session_state.get("sb_subject_tester")
    selected_lesson_id = st.session_state.get("sb_lesson_tester")

    num_q = st.number_input("Bạn muốn trả lời bao nhiêu câu?", 1, 20, value=5, step=1)
    num_time = st.number_input("Bạn muốn trả lời trong bao lâu (phút)?", 1, 30, value=10, step=1)

    st.session_state.time_for_each = num_time * 60 / num_q
    st.markdown(f"**Thời gian cho mỗi câu hỏi:** {st.session_state.time_for_each:.0f} giây")

    if st.button("Tạo Quiz và Bắt đầu"):
        user_api_key = controller.get("user_api")
        if not user_api_key:
            st.error("Vui lòng nhập API key ở mục Config hoặc thanh bên.")
        else:
            with st.spinner("Đang tạo quiz..."):
                data = generate_quiz_data(num_q, user_api_key, selected_subject, selected_lesson_id)
            if data and len(data) == num_q:
                st.session_state.generated_quiz_data = data
                st.session_state.num_questions_to_ask = num_q
                st.session_state.quiz_step = QUIZ_STATE_QUESTIONING
                st.rerun()
            else:
                st.error("Không thể tạo đủ câu hỏi. Kiểm tra API hoặc kết nối mạng.")
                st.session_state.generated_quiz_data = []

    if st.button("Quay lại"):
        reset_quiz_state()
        st.rerun()

# --- QUESTIONING or FEEDBACK ---
elif st.session_state.quiz_step in [QUIZ_STATE_QUESTIONING, QUIZ_STATE_GRADING_FEEDBACK]:
    idx = st.session_state.current_question_idx
    total = st.session_state.num_questions_to_ask
    data = st.session_state.generated_quiz_data

    if not data or idx >= total or idx >= len(data):
        st.balloons()
        st.success("Bạn đã hoàn thành bài quiz!")
        correct = sum(1 for i in range(total) if st.session_state.feedback.get(i, {}).get("status") == FEEDBACK_STATUS_CORRECT)
        st.markdown(f"**Kết quả:** {correct}/{total} đúng")
        if st.button("Làm bài khác"):
            reset_quiz_state()
            st.rerun()
    else:
        st.markdown(f"### Câu hỏi {idx + 1} / {total}")
        current = data[idx]
        st.markdown(f"**{current['question']}**")

        if st.session_state.quiz_step == QUIZ_STATE_QUESTIONING:
            answer = st.text_area("Câu trả lời của bạn:", key=f"answer_{idx}", value=st.session_state.user_answers.get(idx, ""))

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Kiểm tra", key=f"check_{idx}"):
                    st.session_state.user_answers[idx] = answer
                    key = controller.get("user_api")
                    if not key:
                        st.error("Thiếu API key.")
                        reset_quiz_state()
                        st.rerun()
                    with st.spinner("Đang chấm điểm..."):
                        result = evaluate_user_answer_clarity(answer, current['answer'], current['question'], key)
                    if result == "CORRECT":
                        st.session_state.feedback[idx] = {"message": "Đúng rồi! ✅", "status": FEEDBACK_STATUS_CORRECT}
                    elif result == "INCORRECT":
                        st.session_state.feedback[idx] = {"message": f"Sai rồi! ❌ Đáp án đúng là: {current['answer']}", "status": FEEDBACK_STATUS_INCORRECT}
                    else:
                        st.session_state.feedback[idx] = {"message": f"Lỗi khi chấm điểm. Đáp án đúng là: {current['answer']}", "status": FEEDBACK_STATUS_ERROR}
                    st.session_state.quiz_step = QUIZ_STATE_GRADING_FEEDBACK
                    st.rerun()

            with col2:
                if st.button("Thoát Quiz", key=f"exit_{idx}_q"):
                    reset_quiz_state()
                    st.rerun()

            # --- Countdown UI with HTML ---
            timeout = int(st.session_state.time_for_each)
            components.html(f"""
                <div id='timer' style='font-size:24px; font-weight:bold; color:red;'>Thời gian còn lại: {timeout} giây</div>
                <script>
                    let t = {timeout};
                    const el = document.getElementById('timer');
                    const iv = setInterval(() => {{
                        t--;
                        el.innerText = "Thời gian còn lại: " + t + " giây";
                        if (t <= 0) {{
                            clearInterval(iv);
                            alert("Hết thời gian! Bạn sẽ tự động chuyển sang câu tiếp theo.");
                        }}
                    }}, 1000);
                </script>
            """, height=40)

            # --- JS control via return value ---
            result = st_javascript(f"""
                const sleep = ms => new Promise(r => setTimeout(r, ms));
                await sleep({timeout} * 1000);
                return 'time_up';
            """, key=f"js_timer_{idx}")

            if result == "time_up":
                st.session_state.current_question_idx += 1
                st.rerun()

        elif st.session_state.quiz_step == QUIZ_STATE_GRADING_FEEDBACK:
            feedback = st.session_state.feedback.get(idx, {})
            if feedback.get("status") == FEEDBACK_STATUS_CORRECT:
                st.success(feedback.get("message"))
            else:
                st.error(feedback.get("message"))

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Tiếp tục", key=f"next_{idx}"):
                    st.session_state.current_question_idx += 1
                    st.session_state.quiz_step = QUIZ_STATE_QUESTIONING
                    st.rerun()
            with col2:
                if st.button("Thoát Quiz", key=f"exit_{idx}_fb"):
                    reset_quiz_state()
                    st.rerun()
