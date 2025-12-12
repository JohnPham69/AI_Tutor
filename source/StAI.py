# To run this code you need to install the following dependencies:
# pip install google-genai
#
import requests
from google import genai
import streamlit as st
from google.genai import types

# UPDATED: Added "-it" for instruction-tuned model.
DEFAULT_MODEL_NAME = "gemma-3-27b-it"
DEFAULT_MODEL_FLASH_LATEST = "gemma-3-27b-it"

# Giữ nguyên hàm trans
def trans(text, user_api, user_model=None):
    try:
        client = genai.Client(api_key=user_api) # type: ignore
        model_to_use = user_model if user_model else DEFAULT_MODEL_FLASH_LATEST

        prompt = f"""

        Văn bản: "{text}"

        Bắt buộc phải dịch ra tiếng anh. Kết quả phải là tiếng Anh hoàn chỉnh, không có từ lóng hoặc ngôn ngữ địa phương."""

        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        generate_content_config = types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="text/plain",
        )
        
        # FIX: Switched to non-streaming generate_content
        response = client.models.generate_content(
            model=model_to_use, contents=contents, config=generate_content_config
        )
        return response.text.strip() if response.text else ""
    except Exception as e:
        print(f"Error in detect_language: {e}")
        return "Error in translation"

# Giữ nguyên hàm afterStepOne
def afterStepOne(plan_text, user_api, user_model=None):
    try:
        client = genai.Client( # type: ignore
            api_key=user_api,  # Replace with your actual API key or environment variable
        )
        model_to_use = user_model if user_model else DEFAULT_MODEL_FLASH_LATEST
        
        # Construct the prompt/content for after step one
        # Lưu ý: {selected_grade} bị xóa khỏi prompt này vì nó không được truyền vào hàm afterStepOne trong code hiện tại
        prompt_for_after_step_one = """
            Đoạn văn bản đầu vào chứa phản hồi của AI cho người dùng và một câu hỏi ôn tập.
            Nhiệm vụ của bạn là:
            1. Chỉ được phép sử dụng từ ngữ thích hợp với cấp độ học sinh phổ thông.
            2. Giữ nguyên phần phản hồi ở đầu đoạn văn bản (nếu có). KHÔNG thay đổi nội dung của phần phản hồi này.
            3. Xem xét phần CÂU HỎI ở cuối đoạn văn bản. Đánh giá xem đó có phải là một câu hỏi tốt, rõ ràng, và phù hợp không.
            4. Nếu câu hỏi tốt, hãy giữ nguyên nó.
            5. Nếu câu hỏi chưa tốt (ví dụ: không rõ ràng, quá khó, quá dễ, không liên quan chặt chẽ đến ngữ cảnh bài học tiềm năng), hãy chỉnh sửa hoặc thay thế bằng một câu hỏi tốt hơn.
            6. Trả về kết quả là sự kết hợp của [Phần phản hồi gốc (nếu có)] + [Câu hỏi (giữ nguyên hoặc đã cải thiện)].

            Ví dụ:
            - Đầu vào: "Đúng rồi! Câu trả lời rất hay. Câu hỏi tiếp theo: Mặt trời màu gì?"
            - Nếu "Mặt trời màu gì?" là câu hỏi tốt, bạn trả về: "Đúng rồi! Câu trả lời rất hay. Câu hỏi tiếp theo: Mặt trời màu gì?"
            - Nếu "Mặt trời màu gì?" cần cải thiện, bạn có thể trả về: "Đúng rồi! Câu trả lời rất hay. Câu hỏi tiếp theo: Hãy mô tả các lớp chính của Mặt Trời?"

            Toàn bộ đầu ra của bạn phải có giọng điệu thân thiện, dí dỏm.
            KHÔNG thêm bất kỳ lời giải thích nào về quá trình làm việc của bạn. Chỉ trả về chuỗi văn bản cuối cùng.
            """
        # Combine the instruction prompt with the text to be evaluated
        full_prompt_for_step_two = f"{prompt_for_after_step_one}\n\nHere is the text to evaluate:\n{plan_text}"
        contents = [
            types.Content(role="user", parts=[types.Part.from_text(text=full_prompt_for_step_two)]) # type: ignore
        ]

        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            top_p=0.95,
            response_mime_type="text/plain",
        )
        
        # FIX: Switched to non-streaming generate_content
        response = client.models.generate_content(
            model=model_to_use,
            contents=contents,
            config=generate_content_config,
        )
        ans = response.text if response.text else ""
        
        if st.session_state.get('lang') == "en":
            return trans(ans, user_api, user_model)  # Translate to English if needed
        return ans.replace("\n", "\n\n")
    except Exception as e:
        print(f"Error in afterStepOne: {e}")
        return plan_text

# HÀM genRes ĐÃ SỬA ĐỔI
def genRes(
    text_input, chat_history, user_api, user_model=None,
    selected_grade=None, selected_subject_name=None, selected_lesson_data_list=None,
    uploaded_file_text: str = None, translator=None
):
    import streamlit as st 

    try:
        if not user_api:
            return translator("API key not configured...") if translator else "API key not configured..."
        
        lesson_material_combined_content = "" # Sửa lỗi NameError
        active_model_name = user_model if user_model and user_model.strip() else DEFAULT_MODEL_NAME
        
        # 1. FETCH DỮ LIỆU BÀI HỌC (Giữ nguyên logic của bạn)
        lesson_material_fetched_parts = []
        if selected_lesson_data_list:
            for lesson_data in selected_lesson_data_list:
                try:
                    res = requests.get(lesson_data['url'])
                    lesson_material_fetched_parts.append(f"Bài: {lesson_data.get('name')}\n{res.text}")
                except: continue
        if lesson_material_fetched_parts:
            lesson_material_combined_content = "\n\n---\n\n".join(lesson_material_fetched_parts)

        # 2. XÁC ĐỊNH TRẠNG THÁI HỘI THOẠI (Ngăn AI chào lại)
        # Nếu đã có trao đổi trước đó (history > 1), AI không được chào mừng nữa
        is_continuing = len(chat_history) > 1

        # 3. PROMPT TỐI ƯU HÓA (Dựa trên sự ổn định của StLearn)
        step_1_prompt_vi = f"""
            Bạn là AI Gia Sư Kiểm Tra kiến thức môn '{selected_subject_name}' lớp {selected_grade}.
            
            QUY TẮC VỀ TRẠNG THÁI:
            - {"TUYỆT ĐỐI KHÔNG CHÀO HỎI (Chào bạn, bắt đầu nhé...) vì cuộc hội thoại đã diễn ra. Đi thẳng vào đánh giá." if is_continuing else "Chào hỏi thân thiện và đặt câu hỏi đầu tiên."}
            
            NHIỆM VỤ THEO THỨ TỰ:
            1. ĐÁNH GIÁ: Nếu tin nhắn của người dùng là câu trả lời cho câu hỏi trước đó của bạn, hãy đánh giá Đúng/Sai/Chưa đủ ngay lập tức.
            2. GIẢI THÍCH: Cung cấp đáp án đúng và giải thích ngắn gọn dựa trên bài học.
            3. ĐẶT CÂU HỎI MỚI: Đặt một câu hỏi ôn tập tiếp theo.
               - LƯU Ý: Câu hỏi mới PHẢI khác hoàn toàn nội dung người dùng vừa trả lời. Không hỏi lại những gì họ đã biết.
            
            ĐỊNH DẠNG PHẢN HỒI (BẮT BUỘC):
            [Đánh giá & Giải thích kiến thức cũ]. [Câu hỏi ôn tập mới]?
            """

        # Thêm các tùy chọn Hard/Fun từ session_state
        if st.session_state.get('ai_hard'): step_1_prompt_vi = "Độ khó cao. " + step_1_prompt_vi
        if st.session_state.get('ai_fun'): step_1_prompt_vi = "Hài hước, dí dỏm. " + step_1_prompt_vi

        # 4. XÂY DỰNG NỘI DUNG GỬI AI
        prompt_elements = [
            f"BÀI HỌC CONTEXT:\n{lesson_material_combined_content}",
            f"FILE UPLOADED:\n{uploaded_file_text}",
            f"USER MESSAGE: {text_input}",
            f"INSTRUCTIONS: {step_1_prompt_vi}"
        ]
        
        # 5. XỬ LÝ LỊCH SỬ VÀ GỌI MODEL
        client = genai.Client(api_key=user_api)
        contents = []
        if chat_history:
            for msg in chat_history[-15:]: # Lấy 15 tin nhắn gần nhất để giữ context
                role = "model" if msg["role"] == "assistant" else "user"
                contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))
        
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text="\n\n".join(prompt_elements))]))

        response = client.models.generate_content(
            model=active_model_name,
            contents=contents,
            config=types.GenerateContentConfig(temperature=0.8) # Giảm nhẹ độ sáng tạo để bám sát prompt
        )
        
        output = response.text if response.text else ""
        
        # 6. HẬU XỬ LÝ (afterStepOne để lọc lại câu hỏi)
        return afterStepOne(output, user_api, active_model_name)

    except Exception as e:
        return f"Lỗi: {str(e)}"
