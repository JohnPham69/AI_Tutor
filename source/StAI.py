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

# Giữ nguyên hàm trans và afterStepOne (vì các lỗi chính nằm ở genRes và prompt)

def trans(text, user_api, user_model=None):
    # ... (giữ nguyên hàm trans)
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

def afterStepOne(plan_text, user_api, user_model=None):
    try:
        client = genai.Client( # type: ignore
            api_key=user_api,  # Replace with your actual API key or environment variable
        )
        model_to_use = user_model if user_model else DEFAULT_MODEL_FLASH_LATEST
        
        # Construct the prompt/content for after step one
        # LƯU Ý: Biến {selected_grade} cần được truyền vào hoặc loại bỏ khỏi prompt này nếu không có
        prompt_for_after_step_one = """
            Đoạn văn bản đầu vào chứa phản hồi của AI cho người dùng và một câu hỏi ôn tập.
            Nhiệm vụ của bạn là:
            1. Chỉ được phép sử dụng từ ngữ thích hợp với độ tuổi học sinh.
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
        
        # FIX: st.session_state không tồn tại trong hàm này, cần loại bỏ hoặc truyền vào
        # if st.session_state.lang == "en": 
        #     return trans(ans, user_api, user_model)  
        # return ans.replace("\n", "\n\n")

        # Giả định ngôn ngữ mặc định là tiếng Việt
        return ans.replace("\n", "\n\n")

    except Exception as e:
        print(f"Error in afterStepOne: {e}")
        return plan_text


def genRes(
    text_input, chat_history, user_api, user_model=None,
    selected_grade=None, selected_subject_name=None, selected_lesson_data_list=None,
    uploaded_file_text: str = None, translator=None
):
    import streamlit as st  # Đảm bảo đã cài đặt streamlit

    try:
        if not user_api:
            return translator("API key not configured, please set it in the Config page.") if translator else "API key not configured, please set it in the Config page."
        
        # --- Khởi tạo và Thiết lập Biến ---
        active_model_name = user_model if user_model and user_model.strip() else DEFAULT_MODEL_NAME
        original_user_text_input = text_input
        uploaded_file_text = uploaded_file_text or ""
        
        # --- Kiểm tra Trạng thái Hội thoại (Để chặn lời chào lặp lại) ---
        is_continuing = len(chat_history) > 1 

        # --- Fetch lesson material (Giữ nguyên logic) ---
        lesson_material_fetched_parts = []
        lesson_ids_for_prompt_display = []
        # ... (logic fetch bài học giữ nguyên) ...
        if selected_lesson_data_list and isinstance(selected_lesson_data_list, list):
            for lesson_data in selected_lesson_data_list:
                if not lesson_data or not isinstance(lesson_data, dict) or not lesson_data.get('url'):
                    print(f"Warning: Invalid lesson_data entry in genRes: {lesson_data}")
                    continue

                lesson_url = lesson_data['url']
                lesson_id = lesson_data.get('id', 'UnknownID')
                lesson_name = lesson_data.get('name', f'Lesson {lesson_id}')

                try:
                    lesson_response = requests.get(lesson_url)
                    lesson_response.raise_for_status()
                    lesson_content = lesson_response.text
                    lesson_material_fetched_parts.append(f"Content for Lesson '{lesson_name}' (ID {lesson_id}):\n{lesson_content}")
                    lesson_ids_for_prompt_display.append(f"{lesson_name} (ID {lesson_id})")
                except requests.exceptions.RequestException as req_err:
                    print(f"Warning: Failed to fetch lesson content from {lesson_url} (ID {lesson_id}, Name: {lesson_name}) in genRes: {req_err}")
                except Exception as e:
                    print(f"Warning: An unexpected error occurred while fetching/processing content for lesson ID {lesson_id} (Name: {lesson_name}, URL: {lesson_url}) in genRes: {e}")

        lesson_material_combined_content = ""
        if lesson_material_fetched_parts:
            lesson_material_combined_content = "\n\n--- SEPARATOR BETWEEN LESSONS ---\n\n".join(lesson_material_fetched_parts)

        # Lấy ngôn ngữ từ session_state
        lang = st.session_state.lang

        # --- SỬA PROMPT TẬP TRUNG VÀO XỬ LÝ LỖI KHÔNG BIẾT VÀ CHẶN LỜI CHÀO ---
        step_1_prompt_vi = f"""
            Bạn là một AI Gia Sư Thông Thái, chuyên gia về môn '{selected_subject_name if selected_subject_name else "học"}' cho khối lớp '{selected_grade if selected_grade else "phổ thông"}'.
            
            QUY TẮC BẮT BUỘC VỀ VĂN PHONG VÀ BỐ CỤC:
            1. TRẠNG THÁI HỘI THOẠI: {"Do cuộc hội thoại đã diễn ra, TUYỆT ĐỐI KHÔNG DÙNG LỜI CHÀO LẶP LẠI (Chào bạn!, Tuyệt vời!). HÃY ĐI THẲNG VÀO ĐÁNH GIÁ CÂU TRẢ LỜI HOẶC ĐẶT CÂU HỎI MỚI." if is_continuing else "Hãy chào hỏi thân thiện một lần duy nhất và đặt câu hỏi đầu tiên."}
            2. ĐỊNH DẠNG: BẮT BUỘC PHẢI sử dụng định dạng Markdown (ví dụ: **chữ đậm**, *danh sách*, trích dẫn) để trình bày rõ ràng.
            3. CẤU TRÚC PHẢN HỒI (BẮT BUỘC): PHẢI trả lời/đánh giá câu trả lời của người dùng và đặt câu hỏi mới trong cùng một phản hồi. 
               Định dạng cuối cùng: **[Phần phản hồi đánh giá và giải thích]. [Câu hỏi ôn tập mới]?**
            4. TỪ CHỐI NGOÀI LỀ: Lịch sự từ chối trả lời bất kỳ câu hỏi nào không liên quan trực tiếp đến bài học.
            
            ƯU TIÊN HÀNH ĐỘNG:
            A. NẾU người dùng trả lời câu hỏi trước đó (bao gồm các câu trả lời như "Tôi không biết", "Quên mất"):
                1. ĐÁNH GIÁ NGAY LẬP TỨC: PHẢI đánh giá câu trả lời (ĐÚNG / SAI / CHƯA ĐỦ / KHÔNG BIẾT).
                2. PHẢN HỒI VÀ GIẢI THÍCH (BẮT BUỘC): Cung cấp câu trả lời **HOÀN CHỈNH VÀ CHÍNH XÁC** cho câu hỏi vừa rồi. 
                   * Nếu người dùng trả lời **SAI / CHƯA ĐỦ / KHÔNG BIẾT/ QUÊN**, bạn PHẢI CUNG CẤP KIẾN THỨC BỊ THIẾU/SAI đó một cách chi tiết, dựa trên bài học. KHÔNG ĐƯỢC CHUYỂN NGAY SANG CÂU HỎI MỚI MÀ CHƯA GIẢI THÍCH.
                   * Giải thích phải rõ ràng, cụ thể, không chung chung.
                   * Sử dụng kiến thức từ bài học (CONTEXT) là ưu tiên số 1.
                3. NGĂN CHẶN LẶP LẠI: Sau khi phản hồi, PHẢI ĐẶT một câu hỏi ôn tập MỚI, KHÔNG ĐƯỢC PHÉP LẶP LẠI (NGUYÊN VĂN HAY TÁI BẢN) thông tin người dùng vừa trả lời.
            
            B. NẾU người dùng bắt đầu cuộc trò chuyện: ĐẶT câu hỏi ôn tập ĐẦU TIÊN.

            QUAN TRỌNG VỀ PHẠM VI KIẾN THỨC (90/10):
            -   **90% CÂU HỎI PHẢI BÁM SÁT** và DỰA TRỰC TIẾP VÀO NỘI DUNG BÀI HỌC.
            -   **10% CÂU HỎI CÓ THỂ MỞ RỘNG**, nhưng bắt buộc phải liên quan chặt chẽ đến chủ đề.
            """

        # Thêm tùy chọn
        if st.session_state.get('ai_hard'):
            step_1_prompt_vi = "Bạn được phép mở rộng câu hỏi ra khỏi phạm vi bài học, nhưng phải liên quan tới bài học. " + step_1_prompt_vi
        if st.session_state.get('ai_fun'):
            step_1_prompt_vi = "Tính cách của bạn khi trả lời phải thật hài hước, dí dỏm, chêm những câu đùa, chơi chữ trong phần trả lời. " + step_1_prompt_vi
        
        active_step_1_prompt = step_1_prompt_vi
        if lang == "en":
            active_step_1_prompt = step_1_prompt_vi + "\n\nKết quả trả về phải được dịch ra tiếng anh."

        # Construct the full prompt for the LLM
        prompt_elements = []
        if uploaded_file_text:
            prompt_elements.append(
                f"CONTEXT FROM UPLOADED FILE(S):\n"
                f"------------------------------------\n"
                f"{uploaded_file_text}\n"
                f"------------------------------------"
            )

        if lesson_material_combined_content:
            lessons_display_str = ", ".join(lesson_ids_for_prompt_display) if lesson_ids_for_prompt_display else "N/A"
            prompt_elements.append(
                f"CONTEXT FROM LESSON MATERIAL ({selected_subject_name} - Lessons: {lessons_display_str}):\n"
                f"------------------------------------\n"
                f"{lesson_material_combined_content}\n"
                f"------------------------------------"
            )
        prompt_elements.append(f"USER QUERY: {original_user_text_input}")
        prompt_elements.append(f"INSTRUCTIONS:\n{active_step_1_prompt}")

        current_user_message_for_step1 = "\n\n".join(prompt_elements)

        # --- Client Setup and Chat History ---
        client = genai.Client(api_key=user_api)
        contents_for_step1 = []

        if chat_history:
            # SỬA LỖI CẮT LỊCH SỬ: Lấy 20 tin nhắn gần nhất, loại bỏ tin nhắn cuối cùng (tin nhắn hiện tại của người dùng).
            # Dùng chat_history[-21:-1] hoặc chat_history[:-1][-20:]
            
            # Tôi chọn chat_history[:-1] để lấy TẤT CẢ lịch sử cũ (trừ tin nhắn hiện tại) và chỉ giới hạn 20 tin gần nhất
            relevant_history = chat_history[:-1][-20:] 
            
            for message in relevant_history: 
                role = message["role"]
                if role == "assistant":
                    role = "model" 
                elif role == "user":
                    pass
                else:
                    continue
                if message.get("content"):
                    contents_for_step1.append(
                        types.Content(role=role, parts=[types.Part.from_text(text=message["content"])]) # type: ignore
                    )

        # Thêm tin nhắn hiện tại của người dùng (kèm prompt và context)
        contents_for_step1.append(types.Content(role="user", parts=[types.Part.from_text(text=current_user_message_for_step1)])) # type: ignore

        generate_content_config = types.GenerateContentConfig(
            temperature=0.7, # Giảm nhiệt độ để AI tuân thủ nghiêm ngặt các chỉ thị
            response_mime_type="text/plain",
        )
        
        response_step1 = client.models.generate_content(
            model=active_model_name,
            contents=contents_for_step1,
            config=generate_content_config,
        )
        step_one_output_text = response_step1.text if response_step1.text else ""
        
        # Pass the output of the first LLM call to afterStepOne for potential refinement
        intermediate_result = afterStepOne(step_one_output_text, user_api, active_model_name)
        return intermediate_result

    except Exception as e:
        print(f"Error in genRes: {e}")
        return f"An error occurred: {str(e)}"
