# To run this code you need to install the following dependencies:
# pip install google-genai
#
import requests
from google import genai
import streamlit as st
from google.genai import types

# UPDATED: Added "-it" for instruction-tuned model.
DEFAULT_MODEL_NAME = "gemma-3-27b-it"
DEFAULT_MODEL_FLASH_LATEST = "gemma-3-27b-it" # Dùng chung model lớn để đảm bảo logic tốt hơn

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
        
        response = client.models.generate_content(
            model=model_to_use, contents=contents, config=generate_content_config
        )
        return response.text.strip() if response.text else ""
    except Exception as e:
        print(f"Error in detect_language: {e}")
        return "Error in translation"

def afterStepOne(plan_text, user_api, user_model=None):
    try:
        client = genai.Client( # type: ignore
            api_key=user_api,
        )
        model_to_use = user_model if user_model else DEFAULT_MODEL_FLASH_LATEST
        
        # PROMPT CẢI TIẾN: Tập trung vào việc giữ lại sự xác nhận ĐÚNG/SAI
        prompt_for_after_step_one = """
            Bạn là một Biên tập viên Sư phạm tài năng. Nhiệm vụ của bạn là trau chuốt lại câu trả lời của AI Gia sư để phù hợp với học sinh lớp {selected_grade}.
            
            Đầu vào là một đoạn văn bản gồm 3 phần: [Xác nhận Đúng/Sai] + [Giải thích] + [Câu hỏi tiếp theo].

            QUY TẮC BẤT DI BẤT DỊCH:
            1. **KHÔNG ĐƯỢC XÓA** từ khóa xác nhận ở đầu câu (Ví dụ: "Chính xác!", "Đúng rồi!", "Chưa đúng", "Sai rồi"). Nếu đầu vào thiếu, bạn PHẢI TỰ THÊM VÀO dựa trên nội dung giải thích.
            2. Giọng văn phải thân thiện, khích lệ (nếu đúng) hoặc nhẹ nhàng (nếu sai).
            3. Đảm bảo [Câu hỏi tiếp theo] rõ ràng, tách biệt với phần giải thích.
            4. Chỉ trả về kết quả đã biên tập, không giải thích gì thêm.

            Ví dụ input: "Bạn nói về đấu tranh vũ trang là đúng. Nó mạnh bạo nên hiệu quả. Câu hỏi: Ai lãnh đạo?"
            Ví dụ output: "**Chính xác!** Bạn đã nắm rất chắc bài. Đấu tranh vũ trang hiệu quả nhờ tính triệt để của nó. Vậy bạn có nhớ **ai là người lãnh đạo** phong trào này không?"
            """
        
        full_prompt_for_step_two = f"{prompt_for_after_step_one}\n\nNội dung cần biên tập:\n{plan_text}"
        contents = [
            types.Content(role="user", parts=[types.Part.from_text(text=full_prompt_for_step_two)]) # type: ignore
        ]

        generate_content_config = types.GenerateContentConfig(
            temperature=0.7, # Giảm temp để bớt "sáng tạo" lung tung làm mất ý
            top_p=0.95,
            response_mime_type="text/plain",
        )
        
        response = client.models.generate_content(
            model=model_to_use,
            contents=contents,
            config=generate_content_config,
        )
        ans = response.text if response.text else ""
        
        if st.session_state.get('lang') == "en": # Dùng .get để tránh lỗi nếu chưa init
            return trans(ans, user_api, user_model)
        return ans.replace("\n", "\n\n")
    except Exception as e:
        print(f"Error in afterStepOne: {e}")
        return plan_text


def genRes(
    text_input, chat_history, user_api, user_model=None,
    selected_grade=None, selected_subject_name=None, selected_lesson_data_list=None,
    uploaded_file_text: str = None, translator=None
):
    import streamlit as st

    try:
        if not user_api:
            return translator("API key not configured...") if translator else "API key missing."
        
        active_model_name = user_model if user_model and user_model.strip() else DEFAULT_MODEL_NAME
        
        # ... (Phần code fetch lesson data giữ nguyên như cũ) ...
        # [Để tiết kiệm không gian, tôi giả định phần fetch lesson data ở đây không đổi]
        # Bắt đầu từ đoạn xử lý Prompt
        
        lesson_material_fetched_parts = []
        if selected_lesson_data_list and isinstance(selected_lesson_data_list, list):
             for lesson_data in selected_lesson_data_list:
                if not lesson_data or not isinstance(lesson_data, dict) or not lesson_data.get('url'): continue
                try:
                    lesson_response = requests.get(lesson_data['url'])
                    lesson_response.raise_for_status()
                    lesson_material_fetched_parts.append(f"Content Lesson '{lesson_data.get('name')}':\n{lesson_response.text}")
                except: pass
        
        lesson_material_combined_content = "\n---\n".join(lesson_material_fetched_parts)

        # PROMPT CẢI TIẾN: Cấu trúc hóa cực mạnh (Structured Prompting)
        step_1_prompt_vi = """
            Bạn là AI Gia Sư môn '{subject}' lớp '{grade}'.
            
            NHIỆM VỤ CỐT LÕI: Kiểm tra kiến thức người dùng dựa trên TÀI LIỆU BÀI HỌC cung cấp.

            QUY TRÌNH XỬ LÝ 3 BƯỚC (BẮT BUỘC TUÂN THỦ):
            
            BƯỚC 1: PHÂN TÍCH INPUT
            - Nếu user chào/muốn bắt đầu: -> Đi thẳng tới BƯỚC 3 (Đặt câu hỏi đầu tiên).
            - Nếu user trả lời câu hỏi trước đó: -> Sang BƯỚC 2 (Đánh giá).
            - Nếu user hỏi kiến thức: -> Giải thích -> Sang BƯỚC 3.

            BƯỚC 2: ĐÁNH GIÁ & GIẢI THÍCH (Quan trọng nhất)
            - Bạn PHẢI bắt đầu câu trả lời bằng một trong các cụm từ: "**✅ Chính xác!**", "**❌ Sai rồi**", "**⚠️ Chưa đầy đủ**".
            - Sau đó: Giải thích ngắn gọn tại sao đúng/sai dựa vào TÀI LIỆU BÀI HỌC.
            - Nếu sai, hãy đưa ra đáp án đúng.

            BƯỚC 3: CÂU HỎI TIẾP THEO
            - Luôn kết thúc bằng 1 câu hỏi ôn tập MỚI liên quan đến bài học.
            - Câu hỏi phải ngắn gọn, rõ ràng.

            VÍ DỤ MẪU (Hãy học theo cấu trúc này):
            User: "Cách mạng tư sản là do nông dân lãnh đạo."
            AI: "**❌ Sai rồi.** Theo bài học, cách mạng tư sản do **giai cấp tư sản** lãnh đạo để lật đổ chế độ phong kiến, không phải nông dân. **Câu hỏi tiếp theo:** Bạn có biết cuộc cách mạng tư sản đầu tiên diễn ra ở đâu không?"

            User: "Do giai cấp tư sản."
            AI: "**✅ Chính xác!** Giai cấp tư sản đã lãnh đạo để giành quyền lực. **Câu hỏi ôn tập:** Một trong những hình thức đấu tranh chính của họ là gì?"

            User: "Cách mạng tư sản Anh do tư sản lãnh đạo."
            AI: "**⚠️ Chưa đầy đủ** Theo bài học, cách mạng tư sản Anh do liên minh giữa **quý tộc mới** và **tư sản** lãnh đạo để giành quyền lực. **Câu hỏi ôn tập:** Cách mạng tư sản Anh lật đổ giai cấp nào?"
            
            LƯU Ý: 
            - Chỉ sử dụng thông tin trong TÀI LIỆU BÀI HỌC.
            - Không lan man sang các vấn đề đạo đức/xã hội trừ khi bài học đề cập.
            """

        step_1_prompt_vi = step_1_prompt_vi.replace("{subject}", selected_subject_name or "Môn học").replace("{grade}", selected_grade or "Cơ bản")

        # Xử lý các mode AI Hard/Fun
        if st.session_state.get('ai_hard'):
            step_1_prompt_vi += "\n[MODE: KHÓ] Hãy hỏi những câu hỏi chi tiết, yêu cầu tư duy tổng hợp."
        if st.session_state.get('ai_fun'):
            step_1_prompt_vi += "\n[MODE: VUI VẺ] Hãy dùng giọng điệu hài hước, dùng emoji, có thể trêu đùa nhẹ nhàng."

        # Ghép Prompt
        prompt_elements = []
        if uploaded_file_text:
            prompt_elements.append(f"TÀI LIỆU TẢI LÊN:\n{uploaded_file_text}")
        if lesson_material_combined_content:
            prompt_elements.append(f"TÀI LIỆU BÀI HỌC:\n{lesson_material_combined_content}")
        
        prompt_elements.append(f"INPUT CỦA USER: {text_input}")
        prompt_elements.append(f"HƯỚNG DẪN HỆ THỐNG:\n{step_1_prompt_vi}")

        current_user_message = "\n\n".join(prompt_elements)

        # Gọi API
        client = genai.Client(api_key=user_api)
        
        contents_for_step1 = []
        if chat_history:
            # Lấy lịch sử chat để AI nhớ ngữ cảnh câu hỏi trước
            for message in chat_history[-6:]: # Chỉ cần 3-4 lượt hội thoại gần nhất
                role = "model" if message["role"] == "assistant" else "user"
                contents_for_step1.append(types.Content(role=role, parts=[types.Part.from_text(text=message["content"])]))
        
        contents_for_step1.append(types.Content(role="user", parts=[types.Part.from_text(text=current_user_message)]))

        generate_content_config = types.GenerateContentConfig(
            temperature=0.4, # Giảm nhiệt độ để AI tập trung vào độ chính xác và cấu trúc
            response_mime_type="text/plain",
        )
        
        response_step1 = client.models.generate_content(
            model=active_model_name,
            contents=contents_for_step1,
            config=generate_content_config,
        )
        step_one_output_text = response_step1.text if response_step1.text else ""
        
        # Chuyển sang bước 2 để làm mượt văn bản
        intermediate_result = afterStepOne(step_one_output_text, user_api, active_model_name)
        return intermediate_result

    except Exception as e:
        print(f"Error in genRes: {e}")
        return f"Lỗi hệ thống: {str(e)}"
