import streamlit as st
from Prac_AI import generate_quiz_data, evaluate_user_answer_clarity
from streamlit.components.v1 import html
from random import randint
import time
import os
from app_translations import get_translator
from app_utils import get_cookie_controller
from StResult import AddNewResult

# --- Constants ---
QUIZ_STATE_INITIAL = "initial"
QUIZ_STATE_CONFIG = "config"
QUIZ_STATE_QUESTIONING = "questioning"
QUIZ_STATE_GRADING_FEEDBACK = "grading_feedback"
FEEDBACK_STATUS_CORRECT = "correct"
FEEDBACK_STATUS_INCORRECT = "incorrect"
FEEDBACK_STATUS_ERROR = "error"

# --- Session Init ---
def ensure_session():
    defaults = {
        "quiz_step": QUIZ_STATE_INITIAL,
        "num_questions_to_ask": 0,
        "current_question_idx": 0,
        "user_answers": {},
        "feedback": {},
        "generated_quiz_data": [],
        "quiz_error_message": None,
        "time_for_each": 60,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

ensure_session()
_ = get_translator()
controller = get_cookie_controller()
st.title(_("Practice Quiz Title"))

# --- Reset ---
def reset_quiz_state(reset_step=True):
    if reset_step:
        st.session_state.quiz_step = QUIZ_STATE_INITIAL
    for k in ["num_questions_to_ask", "current_question_idx", "user_answers", "feedback", "generated_quiz_data", "quiz_error_message"]:
        st.session_state[k] = {} if isinstance(st.session_state.get(k), dict) else [] if isinstance(st.session_state.get(k), list) else None
    st.session_state.time_for_each = 60

# --- Helper to fetch lesson ---
def get_lesson_from_context(data, grade, set_name, subject, lesson_id):
    for g in data.get("grade", []):
        if g.get("number") == grade:
            for s in g.get("textbook_set", []):
                if s.get("name") == set_name:
                    for subj in s.get("subjects", []):
                        if subj.get("name") == subject:
                            for l in subj.get("link", []):
                                if str(l.get("ID")) == str(lesson_id):
                                    return l
    return None

# --- INITIAL STATE ---
if st.session_state.quiz_step == QUIZ_STATE_INITIAL:
    st.session_state.quiz_step = QUIZ_STATE_CONFIG
    st.rerun()

# --- CONFIG STATE ---
elif st.session_state.quiz_step == QUIZ_STATE_CONFIG:
    st.markdown(_("Configure Your Quiz"))
    selected_grade = st.session_state.get('sb_grade_tester')
    selected_set = st.session_state.get('sb_textbook_set_tester')
    selected_subject = st.session_state.get("sb_subject_tester")
    selected_lesson_ids = st.session_state.get("sb_lesson_tester", [])

    lesson_url = None
    lesson_id = selected_lesson_ids[0] if selected_lesson_ids else None

    data_context = st.session_state.get("subject_lesson_data_for_pages")
    if all([data_context, selected_grade, selected_set, selected_subject, lesson_id]):
        lesson_info = get_lesson_from_context(data_context, selected_grade, selected_set, selected_subject, lesson_id)
        if lesson_info:
            lesson_url = lesson_info.get("link")

    if not selected_subject and not lesson_id:
        st.info(_("No subject or lesson selected from the sidebar. The quiz will cover general knowledge topics."))
    elif not lesson_id:
        st.info(_("No specific lesson selected from the sidebar for subject '{subject_name}'. The quiz will cover general topics for this subject.").format(subject_name=selected_subject))
    elif not selected_subject:
        st.warning(_("A lesson is selected, but the subject is missing. Please check sidebar selections. The quiz may cover general knowledge topics."))

    num_q = st.number_input(_("Number of Questions Prompt"), 1, 20, value=5, step=1)
    num_time = st.number_input(_("Time Limit Prompt (minutes)"), 1, 30, value=10, step=1)
    q_type = st.selectbox(_("Type of Question Prompt"), options=[_("Mixed"), _("Multiple Choice"), _("Long / Short Answer")])
    st.session_state.time_for_each = num_time * 60 / num_q
    st.markdown(_("Time Per Question Info").format(time_per_question=st.session_state.time_for_each))

    if st.button(_("Create Quiz and Start Button")):
        user_key = st.session_state.get('user_api')
        if not user_key:
            st.error(_("API key not configured, please set it in the Config page."))
        else:
            with st.spinner(_("Creating Quiz Spinner")):
                quiz = generate_quiz_data(
                    num_questions=num_q,
                    user_api=user_key,
                    subject_name=selected_subject,
                    lesson_id_str=lesson_id,
                    question_type=q_type
                )
                controller.set('selected_subject_name', selected_subject)
            if quiz and len(quiz) == num_q:
                st.session_state.generated_quiz_data = quiz
                st.session_state.num_questions_to_ask = num_q
                st.session_state.quiz_step = QUIZ_STATE_QUESTIONING
                st.rerun()
            else:
                st.error(_("Not Enough Questions Error"))

    if st.button(_("Go Back Button")):
        reset_quiz_state()
        st.rerun()

# --- QUESTIONING ---
elif st.session_state.quiz_step in [QUIZ_STATE_QUESTIONING, QUIZ_STATE_GRADING_FEEDBACK]:
    idx = st.session_state.current_question_idx
    data = st.session_state.generated_quiz_data
    total = st.session_state.num_questions_to_ask

    if not data or idx >= total:
        st.balloons()
        correct = sum(1 for i in range(total) if st.session_state.feedback.get(i, {}).get("status") == FEEDBACK_STATUS_CORRECT)
        st.success(_("Quiz Completed Message"))
        st.markdown(_("Result Info").format(correct=correct, total=total))

        nick = controller.get('user_nickname')
        school = controller.get('user_school')
        class_name = controller.get('user_class')
        student_id = controller.get('user_id')
        subject = controller.get('selected_subject_name')
        can_save = all([nick, school, class_name, student_id, subject])

        if not can_save:
            st.warning(_("Save your own results!"))
            st.caption(_("Please fill in your Nickname, School, Class, and Student ID in the sidebar to save results."))

        col1, col2 = st.columns(2)
        with col1:
            if st.button(_("Add to Leaderboards"), disabled=not can_save):
                saved = AddNewResult(nick, school, class_name, student_id, total, correct, subject)
                if saved:
                    st.success(_("Results saved."))
                    reset_quiz_state()
                    st.rerun()
        with col2:
            if st.button(_("Go Back Button")):
                reset_quiz_state()
                st.rerun()

    else:
        q = data[idx]
        st.markdown(_("Question Number Info").format(current_idx_plus_1=idx + 1, total_questions=total))
        st.markdown(f"**{q['question']}**")
        user_input = st.text_area(_("Your Answer Label"), key=f"answer_{idx}", value=st.session_state.user_answers.get(idx, ""))
        timeout = int(st.session_state.time_for_each)
        html(f"""
            <p>{_('Time Remaining Label')} <span id="myButton">{_('Timer')}</span></p>
            <script>
                let countdown = {timeout};
                const btn = document.getElementById('myButton');
                const intvl = setInterval(() => {{
                    countdown--;
                    btn.textContent = countdown;
                    if (countdown <= 0) clearInterval(intvl);
                }}, 1000);
            </script>
        """, height=80)

        col1, col2 = st.columns([0.82, 0.18])
        with col1:
            if st.button(_("Check Answer Button"), key=f"check_{idx}"):
                st.session_state.user_answers[idx] = user_input
                key = controller.get("user_api")
                if not key:
                    st.error(_("API Key Missing In-Quiz Error"))
                    reset_quiz_state()
                    st.rerun()
                with st.spinner(_("Grading Spinner")):
                    result = evaluate_user_answer_clarity(user_input, q['answer'], q['question'], key)
                if result == FEEDBACK_STATUS_CORRECT.upper():
                    st.session_state.feedback[idx] = {"message": _("Correct Feedback Message"), "status": FEEDBACK_STATUS_CORRECT}
                elif result == FEEDBACK_STATUS_INCORRECT.upper():
                    st.session_state.feedback[idx] = {"message": _("Incorrect Feedback Message").format(correct_answer=q['answer']), "status": FEEDBACK_STATUS_INCORRECT}
                else:
                    st.session_state.feedback[idx] = {"message": _("Error Grading Feedback Message").format(correct_answer=q['answer']), "status": FEEDBACK_STATUS_ERROR}
                st.session_state.quiz_step = QUIZ_STATE_GRADING_FEEDBACK
                st.rerun()

        with col2:
            if st.button(_("Exit Quiz Button"), key=f"exit_{idx}_q"):
                reset_quiz_state()
                st.rerun()

        if st.session_state.quiz_step == QUIZ_STATE_GRADING_FEEDBACK:
            feedback = st.session_state.feedback.get(idx, {})
            if feedback.get("status") == FEEDBACK_STATUS_CORRECT:
                st.success(feedback.get("message"))
            else:
                st.error(feedback.get("message"))

            col1, col2 = st.columns([0.82, 0.18])
            with col1:
                if st.button(_("Continue Button"), key=f"next_{idx}"):
                    st.session_state.current_question_idx += 1
                    st.session_state.quiz_step = QUIZ_STATE_QUESTIONING
                    st.rerun()
            with col2:
                if st.button(_("Exit Quiz Button"), key=f"exit_{idx}_fb"):
                    reset_quiz_state()
                    st.rerun()
