import streamlit as st
from streamlit_cookies_controller import CookieController # Để lấy API key
import time
import threading
# Đảm bảo import từ đúng tên file đã được đổi thành Prac_AI.py
from Prac_AI import generate_quiz_data, evaluate_user_answer_clarity

# --- Initialization of Session State Variables ---
if "quiz_step" not in st.session_state:
    st.session_state.quiz_step = "initial"  # "initial", "config", "questioning", "grading_feedback"
if "num_questions_to_ask" not in st.session_state:
    st.session_state.num_questions_to_ask = 0
# if "quiz_duration_minutes" not in st.session_state: # Sẽ không dùng biến này nữa
#     st.session_state.current_question_idx = 0 # Dòng này có vẻ bị đặt nhầm, current_question_idx đã có ở dưới
if "current_question_idx" not in st.session_state:
    st.session_state.current_question_idx = 0
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {} # Using a dict: {q_idx: answer}
if "feedback" not in st.session_state:
    st.session_state.feedback = {} # Using a dict: {q_idx: "Đúng rồi! ✅" / "Sai rồi! ❌ Đáp án đúng là: ..."}
if "generated_quiz_data" not in st.session_state: # Để lưu trữ câu hỏi và đáp án từ AI
    st.session_state.generated_quiz_data = []
if "quiz_error_message" not in st.session_state:
    st.session_state.quiz_error_message = None
if "quiz_duration_seconds" not in st.session_state:
    st.session_state.quiz_duration_seconds = 60  # 1 phút
if "time_left" not in st.session_state:
    st.session_state.time_left = st.session_state.quiz_duration_seconds
if "timer_active" not in st.session_state:
    st.session_state.timer_active = False
if "quiz_time_up" not in st.session_state:
    st.session_state.quiz_time_up = False

# Khởi tạo cookie controller
controller = CookieController()

# --- Page Title ---
st.title("Practice Quiz")

# --- State: Initial ---
if st.session_state.quiz_step == "initial":
    st.markdown("### Bắt đầu một phiên luyện tập mới")
    if st.session_state.quiz_error_message:
        st.error(st.session_state.quiz_error_message)
        st.session_state.quiz_error_message = None # Xóa lỗi sau khi hiển thị

    if st.button("Bắt đầu bài quiz"):
        st.session_state.quiz_step = "config"
        st.rerun()
    st.caption("Dựa trên môn học và bài học đã chọn ở thanh bên (nếu có).")

# --- State: Configuration ---
elif st.session_state.quiz_step == "config":
    st.markdown("### Cấu hình Bài Quiz của Bạn")
    
    # Lấy chủ đề và bài học từ session_state (được đặt bởi Tester.py hoặc StUI.py)
    selected_subject = st.session_state.get('sb_subject_tester') # Giả sử key này được dùng chung
    selected_lesson_id = st.session_state.get('sb_lesson_tester')

    num_q_value = st.session_state.num_questions_to_ask if st.session_state.num_questions_to_ask > 0 else 5 # Mặc định 5 câu
    num_q = st.number_input(
        "Bạn muốn trả lời bao nhiêu câu?", 
        min_value=1, 
        max_value=20, # Giới hạn thực tế
        value=num_q_value,
        step=1,
        key="num_questions_input"
    )
    
    if st.button("Tạo Quiz và Bắt đầu"):
        user_api_key = controller.get("user_api")
        if not user_api_key:
            st.error("Vui lòng nhập API key ở mục Config hoặc thanh bên.")
        else:
            with st.spinner(f"Đang tạo {num_q} câu hỏi quiz..."):
                quiz_content = generate_quiz_data(
                    num_questions=num_q, 
                    user_api=user_api_key,
                    subject_name=selected_subject,
                    lesson_id_str=selected_lesson_id
                )
            
            if quiz_content and len(quiz_content) == num_q:
                st.session_state.generated_quiz_data = quiz_content
                st.session_state.num_questions_to_ask = num_q
                st.session_state.current_question_idx = 0
                st.session_state.user_answers = {} 
                st.session_state.feedback = {}     
                st.session_state.quiz_error_message = None
                st.session_state.quiz_step = "questioning"
                
                # Start the timer
                st.session_state.time_left = st.session_state.quiz_duration_seconds
                st.session_state.quiz_time_up = False
                st.session_state.timer_active = True
                timer_thread = threading.Thread(target=quiz_timer_thread, daemon=True)
                timer_thread.start()
                st.rerun()
            else:
                st.error(f"Không thể tạo đủ {num_q} câu hỏi. Vui lòng thử lại hoặc kiểm tra API key và kết nối mạng.")
                if quiz_content is not None: # AI trả về nhưng không đủ số lượng
                     st.warning(f"AI chỉ tạo được {len(quiz_content)} câu hỏi.")
                st.session_state.generated_quiz_data = [] # Xóa dữ liệu cũ nếu có lỗi

    if st.button("Quay lại"):
        st.session_state.quiz_step = "initial"
        st.session_state.timer_active = False # Dừng timer nếu đang chạy
        st.rerun()

# --- Timer Thread Function ---
def quiz_timer_thread():
    # time_left và quiz_time_up được khởi tạo bởi main thread trước khi start thread này
    while st.session_state.time_left > 0:
        if not st.session_state.timer_active:  # Kiểm tra nếu main thread yêu cầu dừng
            break
        time.sleep(1)
        if not st.session_state.timer_active:  # Kiểm tra lại sau khi sleep
            break
        st.session_state.time_left -= 1

    if st.session_state.timer_active and st.session_state.time_left <= 0:
        # Hết giờ tự nhiên và timer không bị dừng sớm
        st.session_state.quiz_time_up = True
    
    st.session_state.timer_active = False # Báo hiệu timer đã hoàn thành nhiệm vụ

# --- State: Questioning or Showing Feedback ---
elif st.session_state.quiz_step in ["questioning", "grading_feedback"]:
    q_idx = st.session_state.current_question_idx
    timer_display_area = st.empty()

    # Xử lý hết giờ (nếu quiz đang ở trạng thái questioning và hết giờ)
    if st.session_state.quiz_time_up and st.session_state.quiz_step == "questioning":
        st.session_state.timer_active = False # Đảm bảo logic timer dừng hoàn toàn
        timer_display_area.error("⏳ Hết giờ!")
        st.warning("Hết giờ! Bài quiz sẽ được chấm điểm với các câu trả lời đã nộp.")
        st.session_state.current_question_idx = st.session_state.num_questions_to_ask # Buộc quiz kết thúc
        # Không cần rerun ở đây, script sẽ tiếp tục và kiểm tra quiz_is_finished

    # Hiển thị timer nếu quiz đang ở trạng thái questioning và timer đang chạy
    if st.session_state.quiz_step == "questioning" and st.session_state.timer_active:
        minutes = st.session_state.time_left // 60
        seconds = st.session_state.time_left % 60
        timer_display_area.markdown(f"**⏳ Thời gian còn lại: {minutes:02d}:{seconds:02d}**")

    # Điều kiện kiểm tra xem quiz đã hoàn thành chưa
    quiz_is_finished = (
        st.session_state.quiz_time_up or # Thêm điều kiện hết giờ
        not st.session_state.generated_quiz_data or
        q_idx >= st.session_state.num_questions_to_ask or
        q_idx >= len(st.session_state.generated_quiz_data) # Đảm bảo q_idx không vượt quá số câu hỏi thực có
    )

    if quiz_is_finished:
        st.session_state.timer_active = False # Đảm bảo timer dừng nếu quiz kết thúc vì lý do bất kỳ
        if st.session_state.quiz_time_up:
            # Thông báo hết giờ đã được hiển thị bởi timer_display_area.error() hoặc warning ở trên
             pass
        else:
            st.balloons()
            st.success("Chúc mừng! Bạn đã hoàn thành bài quiz.")
            timer_display_area.empty() # Xóa hiển thị timer nếu quiz hoàn thành bình thường

        # Tính toán và hiển thị điểm số
        num_questions_in_quiz = st.session_state.num_questions_to_ask
        correct_answers = 0
        if num_questions_in_quiz > 0 and st.session_state.feedback:
            for i in range(num_questions_in_quiz):
                feedback_for_q = st.session_state.feedback.get(i, "")
                if "Đúng rồi! ✅" in feedback_for_q:
                    correct_answers += 1
            
            incorrect_answers = num_questions_in_quiz - correct_answers
            st.markdown("---")
            st.markdown(f"**Kết quả bài làm của bạn:**")
            st.markdown(f"- Số câu đúng: **{correct_answers} / {num_questions_in_quiz}**")
            st.markdown(f"- Số câu sai: **{incorrect_answers} / {num_questions_in_quiz}**")
            st.markdown("---")

        if st.button("Làm bài quiz khác"):
            st.session_state.timer_active = False # Dừng timer
            st.session_state.quiz_step = "initial"
            st.session_state.num_questions_to_ask = 0
            st.session_state.current_question_idx = 0
            st.session_state.user_answers = {}
            st.session_state.feedback = {}
            st.session_state.generated_quiz_data = []
            st.rerun()

    else: # Quiz đang diễn ra, hiển thị câu hỏi hiện tại
        st.markdown(f"### Câu hỏi {q_idx + 1} / {st.session_state.num_questions_to_ask}")
        current_question_text = st.session_state.generated_quiz_data[q_idx]["question"]
        st.markdown(f"**{current_question_text}**")

        if st.session_state.quiz_step == "questioning":
            user_answer = st.text_area(
                "Câu trả lời của bạn:", 
                key=f"answer_q{q_idx}", 
                value=st.session_state.user_answers.get(q_idx, "")
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Kiểm tra", key=f"submit_q{q_idx}"):
                    user_api_key = controller.get("user_api")
                    if not user_api_key:
                        st.error("Vui lòng nhập API key.")
                        st.session_state.quiz_error_message = "API key không tìm thấy để kiểm tra đáp án."
                        st.session_state.timer_active = False # Dừng timer
                        st.session_state.quiz_step = "initial" # Quay về trang đầu nếu lỗi API
                        st.rerun()
                    else:
                        st.session_state.user_answers[q_idx] = user_answer
                        correct_answer_text = st.session_state.generated_quiz_data[q_idx]["answer"]
                        with st.spinner("AI đang chấm điểm..."):
                            evaluation_result = evaluate_user_answer_clarity(user_answer, correct_answer_text, current_question_text, user_api_key)
                        
                        if evaluation_result == "CORRECT":
                            st.session_state.feedback[q_idx] = "Đúng rồi! ✅"
                        elif evaluation_result == "INCORRECT":
                            st.session_state.feedback[q_idx] = f"Sai rồi! ❌ Đáp án đúng là: {correct_answer_text}"
                        else: # ERROR case
                            st.session_state.feedback[q_idx] = f"Lỗi khi chấm điểm. Đáp án đúng là: {correct_answer_text}"
                        st.session_state.quiz_step = "grading_feedback"
                        st.rerun()
            with col2:
                if st.button("Thoát Quiz", key=f"exit_quiz_q{q_idx}_questioning"):
                    st.session_state.timer_active = False # Dừng timer
                    st.session_state.quiz_step = "initial" # Quay về trang đầu nếu lỗi API
                    st.session_state.num_questions_to_ask = 0
                    st.session_state.current_question_idx = 0
                    st.session_state.user_answers = {}
                    st.session_state.feedback = {}
                    st.session_state.generated_quiz_data = []
                    st.rerun()

        elif st.session_state.quiz_step == "grading_feedback":
            feedback_message = st.session_state.feedback[q_idx]
            if "Đúng rồi" in feedback_message:
                st.success(feedback_message)
            else:
                st.error(feedback_message)

            # Đặt các nút "Tiếp tục" và "Thoát Quiz" gần nhau hơn
            button_col_continue, button_col_exit, _ = st.columns([1, 1, 3]) # Nút chiếm 2 phần, 3 phần còn lại trống
            with button_col_continue:
                if st.button("Tiếp tục", key=f"continue_q{q_idx}"):
                    st.session_state.current_question_idx += 1
                    st.session_state.quiz_step = "questioning"
                    st.rerun()
            with button_col_exit:
                if st.button("Thoát Quiz", key=f"exit_quiz_q{q_idx}_feedback"):
                    st.session_state.timer_active = False # Dừng timer
                    st.session_state.quiz_step = "initial"
                    st.session_state.num_questions_to_ask = 0
                    st.session_state.current_question_idx = 0
                    st.session_state.user_answers = {}
                    st.session_state.feedback = {}
                    st.session_state.generated_quiz_data = []
                    st.rerun()

    # Tự động rerun để cập nhật hiển thị timer, đặt ở cuối logic của state này
    # Chỉ chạy nếu quiz đang ở "questioning", timer đang active và chưa hết giờ
    if st.session_state.quiz_step == "questioning" and \
       st.session_state.timer_active and \
       not st.session_state.quiz_time_up:
        time.sleep(1) # Chờ 1 giây
        st.rerun()    # Rerun để cập nhật hiển thị timer