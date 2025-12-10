# d:\NCKH_2025\QuizGenerator.py
from google import genai
from google.genai import types
import json
import requests # Để lấy tài liệu bài học
import time
import streamlit as st
import re
import random

count_recursive_evaluate = 0

#
# Hàm phụ trợ để lấy tài liệu bài học (tương tự như trong StAI.py)
# Điều này có thể được tái cấu trúc thành một module tiện ích chung sau này
def _fetch_lesson_content(subject_name, lesson_id_str):
    
    # Lấy nội dung bài học từ một URL JSON chính và sau đó từ link .md cụ thể.
    # Trả về nội dung bài học dưới dạng chuỗi hoặc chuỗi rỗng nếu có lỗi.
    
    if not subject_name or not lesson_id_str:
        return ""
    try:
        main_json_url = "https://raw.githubusercontent.com/JohnPham69/Quiz_Maker_AI/refs/heads/main/lessons/GTSL.json"
        response = requests.get(main_json_url)
        response.raise_for_status()
        subjects_data = response.json()

        subject_found_data = None
        # Iterate through the correct structure: grade -> textbook_set -> subjects
        for grade_entry in subjects_data.get("grade", []):
            for textbook_set_entry in grade_entry.get("textbook_set", []):
                for subj_entry in textbook_set_entry.get("subjects", []):
                    if subj_entry.get("name") == subject_name:
                        subject_found_data = subj_entry
                        break # Found subject
                if subject_found_data:
                    break # Stop searching textbook_sets
            if subject_found_data:
                break # Stop searching grades

        if subject_found_data:
            # The rest of the logic to find the lesson by ID and fetch its .md content
            lesson_id_int = int(lesson_id_str)
            lesson_info_found = None
            for lesson_info in subject_found_data.get("link", []):
                if lesson_info.get("ID") == lesson_id_int:
                    lesson_info_found = lesson_info
                    break
            
            if lesson_info_found:
                lesson_link_url = lesson_info_found.get("link")
                if lesson_link_url:
                    lesson_response = requests.get(lesson_link_url)
                    lesson_response.raise_for_status()
                    fetched_content = lesson_response.text
                    return fetched_content
        return ""
    except requests.exceptions.RequestException as req_err:
        print(f"Lỗi khi lấy dữ liệu bài học (QuizGenerator): {req_err}")
        return ""
    except (json.JSONDecodeError, ValueError) as parse_err:
        print(f"Lỗi xử lý dữ liệu bài học (QuizGenerator): {parse_err}")
        return ""
    except Exception as e:
        print(f"Lỗi không mong muốn khi lấy nội dung bài học (QuizGenerator): {e}")
        return ""

def refine_quiz_quality(raw_quiz_json: list, user_api: str, user_model: str = "gemma-3-27b-it"):
    """
    Nhận đầu ra từ Step 1 (generate_quiz_data).
    Dùng prompt thứ hai để đánh giá và chỉnh sửa chất lượng câu hỏi.
    - Đảm bảo mỗi câu hỏi rõ ràng, không lặp.
    - Câu hỏi có độ khó đa dạng (dễ, trung bình, khó).
    - Câu trả lời chính xác, ngắn gọn, không mơ hồ.
    """
    try:
        client = genai.Client(api_key=user_api)
        prompt = f"""
        Bạn là một chuyên gia biên soạn câu hỏi trắc nghiệm.

        Dưới đây là danh sách các câu hỏi (và đáp án) được sinh ra từ AI:

        {json.dumps(raw_quiz_json, ensure_ascii=False, indent=2)}

        Nhiệm vụ:
        1. Đánh giá từng câu hỏi: nếu thấy mơ hồ, trùng lặp, hoặc không đúng trọng tâm, hãy chỉnh lại.
        2. Phân loại độ khó: dễ, trung bình, khó (bổ sung nhãn nếu cần).
        3. Giữ nguyên định dạng JSON gốc, không thêm văn bản ngoài.
        4. Mỗi phần tử gồm: "question", "answer", và (tùy chọn) "level": "easy"/"medium"/"hard".

        Trả về mảng JSON hoàn chỉnh.
        """

        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        config = types.GenerateContentConfig(
            temperature=0.7,
            response_mime_type="application/json",
        )

        # FIX: Non-streaming call
        response = client.models.generate_content(
            model=user_model,
            contents=contents,
            config=config,
        )
        refined_json = response.text if response.text else ""

        json_start, json_end = refined_json.find("["), refined_json.rfind("]")
        if json_start != -1 and json_end != -1:
            refined_json = refined_json[json_start:json_end+1]
        return json.loads(refined_json)
    except Exception as e:
        print(f"Error in refine_quiz_quality: {e}")
        return raw_quiz_json


def balance_quiz_set(refined_quiz_json: list, user_api: str, user_model: str = "gemma-3-27b-it"):
    """
    Bước 3: Cân bằng toàn bộ bộ câu hỏi — tránh lặp chủ đề, bảo đảm độ khó phân bố hợp lý.
    """
    try:
        client = genai.Client(api_key=user_api)
        prompt = f"""
        Bạn là một chuyên gia kiểm định đề thi.
        Dưới đây là bộ câu hỏi đã qua tinh chỉnh:
        {json.dumps(refined_quiz_json, ensure_ascii=False, indent=2)}

        Nhiệm vụ:
        1. Loại bỏ các câu trùng nội dung.
        2. Đảm bảo có đủ 3 cấp độ: dễ, trung bình, khó (nếu có nhãn độ khó).
        3. Nếu chưa có nhãn độ khó, hãy tự phân bổ.
        4. Giữ nguyên định dạng JSON đầu ra.
        """

        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        config = types.GenerateContentConfig(
            temperature=0.6,
            response_mime_type="application/json",
        )

        # FIX: Non-streaming call
        response = client.models.generate_content(
            model=user_model, contents=contents, config=config
        )
        ans = response.text if response.text else ""

        json_start, json_end = ans.find("["), ans.rfind("]")
        if json_start != -1 and json_end != -1:
            ans = ans[json_start:json_end+1]
        return json.loads(ans)
    except Exception as e:
        print(f"Error in balance_quiz_set: {e}")
        return refined_quiz_json




def generate_quiz_data(num_questions: int, user_api: str, subject_name: str = None,
                       lesson_id_str: str = None, question_type: str = None, lesson_text: str = None, advance: bool = False):
    """
    Generate N quiz questions based on a subject and optionally a lesson's content.
    If lesson_text is provided, it overrides the fetch from GitHub.
    """
    if not user_api:
        print("Error: API key missing.")
        return None

    try:
        client = genai.Client(api_key=user_api)
        model_name = "gemma-3-27b-it"

        # Use pre-fetched lesson_text if available
        lesson_material = lesson_text if lesson_text else ""
        if not lesson_material and subject_name and lesson_id_str:
            lesson_material = _fetch_lesson_content(subject_name, lesson_id_str)
        
        # Question type handling
        advance_or_not = " gồm 50% tổng số câu hỏi đơn giản có thể tìm thấy đáp án trong tài liệu, 40% tổng số câu hỏi trung bình phải suy luận từ tài liệu, 10% tổng số câu hỏi là những câu hỏi nâng cao là về kiến thức liên quan đến bài học nhưng không nằm trong tài liệu bài học."
        if advance:
            advance_or_not = " nâng cao là những câu hỏi về kiến thức liên quan đến bài học nhưng không nằm trong tài liệu bài học."
        
        prompt_text = f"""
            Bạn là một trợ lý AI chuyên tạo các câu hỏi loại TRẮC NGHIỆM, TRẢ LỜI DÀI / NGẮN chất lượng cao.
            BẠN PHẢI TUYỆT ĐỐI TUÂN THEO CÁC VÍ DỤ VÀ CHỈ DẪN NHƯ BÊN DƯỚI:
            
            Nhiệm vụ của bạn là tạo ra chính xác {num_questions} câu hỏi {advance_or_not}.
            Đối với các câu toán nâng cao, hãy tạo bài toán mà muốn giải phải áp dụng nhiều định lí khác nhau, đi qua nhiều bước để giải.
            Đối với các môn học nâng cao ngoài toán, hãy tạo các câu hỏi TRẮC NGHIỆM khó như trên, câu trả lời cũng phải có ý trong câu hỏi TRẮC NGHIỆM gần giống nhau để làm lựa chọn trở nên khó nhằn.
            Dạng của tất cả các câu hỏi phải dưới dạng {question_type} và chỉ được ở dưới dạng {question_type}. PHẢI VIẾT RỠ CÂU HỎI. NẾU LÀ TRẮC NGHIỆM, PHẢI CHO THẤY ĐƯỢC 4 PHƯƠNG ÁN LỰA CHỌN A, B, C, D.
            {'Dựa trên tài liệu bài học sau đây:\n---BEGIN LESSON MATERIAL---\n' + lesson_material + '\n---END LESSON MATERIAL---\n' if lesson_material else f'Chủ đề chung là "{subject_name if subject_name else "kiến thức phổ thông"}".'}
            
            Đối với mỗi câu hỏi, hãy cho biết đây là câu hỏi gì, TRẮC NGHIỆM, hay trả lời dài / ngắn sau đó cung cấp nội dung câu hỏi và tiếp đến trả lời chính xác và ngắn gọn.
            Bạn PHẢI trả về kết quả dưới dạng một mảng JSON hợp lệ. Mỗi phần tử trong mảng là một đối tượng JSON với hai khóa: "question" (string) và "answer" (string).
            QUAN TRỌNG: Đối với câu hỏi dạng trả lời dài / ngắn, câu hỏi của bạn phải là câu hỏi mở (open - ended questions) theo nguyên tắc 5W1H
            QUAN TRỌNG: Nếu nội dung của trường "question" hoặc "answer" có nhiều dòng (ví dụ như trong câu hỏi TRẮC NGHIỆM).
            Có nghĩa, đối với dạng TRẮC NGHIỆM, bạn PHẢI XUỐNG DÒNG, trước khi viết mỗi lựa chọn tính từ lựa chọn thứ nhất.
            Ví dụ cho câu hỏi TRẮC NGHIỆM CÓ 4 PHƯƠNG ÁN LỰA CHỌN cần phải in ra màn hình:
            
            BẠN PHẢI TUÂN THỦ ĐÚNG CHỈ DẪN VÍ DỤ:
            ```
            Nội dung câu hỏi TRẮC NGHIỆM?
            
            A. Lựa chọn A
            
            B. Lựa chọn B
            
            C. Lựa chọn C
            
            D. Lựa chọn D

            Nội dung câu hỏi TRẮC NGHIỆM?
            
            A. Lựa chọn A
            
            B. Lựa chọn B
            
            C. Lựa chọn C
            
            D. Lựa chọn D

            Nội dung câu hỏi TRẮC NGHIỆM?
            
            A. Lựa chọn A
            
            B. Lựa chọn B
            
            C. Lựa chọn C
            
            D. Lựa chọn D        

            Nội dung câu hỏi TRẮC NGHIỆM?
            
            A. Lựa chọn A
            
            B. Lựa chọn B
            
            C. Lựa chọn C
            
            D. Lựa chọn D

            Nội dung câu hỏi TRẮC NGHIỆM?
            
            A. Lựa chọn A
            
            B. Lựa chọn B
            
            C. Lựa chọn C
            
            D. Lựa chọn D
            ```
            luôn luôn bắt buộc phải tuân thủ 100% theo định dạng đã cho.
            ```
            Nội dung câu hỏi là câu hỏi TRẮC NGHIỆM?
            
            A. Lựa chọn A
            
            B. Lựa chọn B
            
            C. Lựa chọn C
            
            D. Lựa chọn D

            Nội dung câu hỏi là câu hỏi TRẮC NGHIỆM?
            
            A. Lựa chọn A
            
            B. Lựa chọn B
            
            C. Lựa chọn C
            
            D. Lựa chọn D

            Nội dung câu hỏi là câu hỏi TRẮC NGHIỆM?
            
            A. Lựa chọn A
            
            B. Lựa chọn B
            
            C. Lựa chọn C
            
            D. Lựa chọn D

            Nội dung câu hỏi là câu hỏi TRẮC NGHIỆM?
            
            A. Lựa chọn A
            
            B. Lựa chọn B
            
            C. Lựa chọn C
            
            D. Lựa chọn D
            ```
            BẠN PHẢI TUÂN THỦ KHẮT KHE:
            Không thêm bất kỳ văn bản, giải thích, hay định dạng markdown nào khác ngoài mảng JSON.
            Ví dụ về định dạng code JSON bắt buộc cho 2 loại câu hỏi, TRẮC NGHIỆM 4 LỰA CHỌN A, B, C, D và TỰ LUẬN:
            ```
            [
                {{
                    "question": 
                    "Ví dụ câu hỏi là câu hỏi TRẮC NGHIỆM, đây là câu hỏi TRẮC NGHIỆM thứ nhất là gì?                    
                    
                    A. abcde
                    
                    B. abcde
                    
                    C. abcde
                    
                    D. abcde
                    ",
                    "answer": "Đây là ví dụ câu trả lời A."
                }},
                {{
                    "question": 
                    "Ví dụ câu hỏi là câu hỏi TRẮC NGHIỆM, đây là câu hỏi TRẮC NGHIỆM thứ nhất là gì?                    
                    
                    A. abcde
                    
                    B. abcde
                    
                    C. abcde
                    
                    D. abcde
                    ",
                    "answer": "Đây là ví dụ câu trả lời A."
                }},
                {{
                    "question": 
                    "Ví dụ câu hỏi là câu hỏi TRẮC NGHIỆM, đây là câu hỏi TRẮC NGHIỆM thứ nhất là gì?                    
                    
                    A. abcde
                    
                    B. abcde
                    
                    C. abcde
                    
                    D. abcde
                    ",
                    "answer": "Đây là ví dụ câu trả lời A."
                }},
                {{
                    "question": 
                    "Ví dụ câu hỏi là câu hỏi TRẮC NGHIỆM, đây là câu hỏi TRẮC NGHIỆM thứ nhất là gì?                    
                    
                    A. abcde
                    
                    B. abcde
                    
                    C. abcde
                    
                    D. abcde
                    ",
                    "answer": "Đây là ví dụ câu trả lời A."
                }},
                {{
                    "question": "Ví dụ câu hỏi tự luận, và KHÔNG LÀ TRẮC NGHIỆM là gì?",
                    "answer": "Đây là ví dụ câu trả lời 2."
                }},
                {{
                    "question": "Ví dụ câu hỏi tự luận, và KHÔNG LÀ TRẮC NGHIỆM là gì?",
                    "answer": "Đây là ví dụ câu trả lời 2."
                }}
            ]
            ```
            Hãy tạo {num_questions} câu hỏi và câu trả lời ngay bây giờ.
            """
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt_text)])]
        
        config = types.GenerateContentConfig( # Đổi tên để nhất quán
            temperature=0.2, # Tăng một chút để có sự đa dạng hơn trong câu hỏi
            response_mime_type="application/json", # Yêu cầu AI trả về JSON trực tiếp
        )

        # FIX: Non-streaming call
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )
        ans = response.text if response.text else ""
        
        # AI có thể trả về JSON được bao bọc trong markdown hoặc văn bản khác.
        # Chúng ta cần trích xuất chuỗi JSON thô một cách an toàn.
        json_str = ans
        json_start = ans.find('[')
        json_end = ans.rfind(']')
        
        if json_start != -1 and json_end != -1 and json_start < json_end:
            json_str = ans[json_start:json_end+1]

        print("AI raw response:", ans)
        print("Extracted JSON string:", json_str)

        # Fix: Escape unescaped newlines inside string values for JSON parsing
        def escape_newlines_in_json_strings(s):
            # This regex finds newlines inside double-quoted strings and replaces them with \n
            def replacer(match):
                return match.group(0).replace('\n', '\\n')
            return re.sub(r'\"(.*?)(?<!\\)\"', replacer, s, flags=re.DOTALL)

        json_str_fixed = escape_newlines_in_json_strings(json_str)

        try:
            quiz_data_list = json.loads(json_str_fixed)
            # --- Step 2: refine quiz quality ---
            quiz_data_list = refine_quiz_quality(quiz_data_list, user_api)
            
            # --- Step 3: balance quiz set (optional) ---
            quiz_data_list = balance_quiz_set(quiz_data_list, user_api)
        except Exception as e:
            print("JSON decode error:", e)
            print("json_str_fixed was:", json_str_fixed)
            return None

        if isinstance(quiz_data_list, list) and all(isinstance(item, dict) and "question" in item and "answer" in item for item in quiz_data_list):
            return quiz_data_list[:num_questions]
        else:
            print(f"Lỗi: AI không trả về định dạng JSON như mong đợi. Dữ liệu nhận được: {json_str_fixed}")
            return None

    except json.JSONDecodeError as json_err:
        print(f"Lỗi giải mã JSON từ AI: {json_err}")
        response_text = json_str if 'json_str' in locals() else (ans if 'ans' in locals() else 'Không có phản hồi')
        print(f"Phản hồi nhận được từ AI (đã cố gắng xử lý): {response_text}")
        return None
    except Exception as e:
        print(f"Lỗi trong generate_quiz_data: {e}")
        return None

def evaluate_user_answer_clarity(user_answer: str, correct_answer: str, question_context: str, user_api: str):
    """
    Đánh giá câu trả lời của người dùng so với đáp án đúng, xem xét sự khác biệt về từ ngữ.
    Trả về "CORRECT", "INCORRECT", hoặc "ERROR" nếu có lỗi.
    """
    global count_recursive_evaluate
    
    if not user_api:
        print("Lỗi: API key không được cung cấp cho evaluate_user_answer_clarity.")
        return "ERROR"
    try:
        client = genai.Client(api_key=user_api)
        model_name = "gemma-3-27b-it"

        prompt_text = f"""
            Bạn là một chuyên gia AI trong việc đánh giá câu trả lời, có khả năng hiểu ngữ nghĩa.
            Nhiệm vụ của bạn là so sánh "Câu trả lời của người dùng" với "Câu trả lời đúng" trong bối cảnh của "Câu hỏi" được đưa ra.
            Hãy xác định xem "Câu trả lời của người dùng" có về cơ bản là đúng hay không, ngay cả khi cách diễn đạt, từ đồng nghĩa, hoặc cấu trúc câu có chút khác biệt so với "Câu trả lời đúng".

            Ví dụ:
            Câu hỏi: "Thủ đô của Pháp là gì?"
            Câu trả lời đúng: "Paris"
            Câu trả lời của người dùng: "Là Paris đó bạn" -> Kết quả nên là CORRECT
            Câu trả lời của người dùng: "Paris chính là thủ đô" -> Kết quả nên là CORRECT
            Câu trả lời của người dùng: "Berlin" -> Kết quả nên là INCORRECT

            Chỉ trả lời bằng một từ duy nhất: "CORRECT" nếu câu trả lời của người dùng về cơ bản là đúng, hoặc "INCORRECT" nếu không.
            Không cung cấp bất kỳ giải thích nào, chỉ một từ duy nhất.

            Câu hỏi: '{question_context}'
            Câu trả lời đúng: '{correct_answer}'
            Câu trả lời của người dùng: '{user_answer}'

            Đánh giá của bạn (CORRECT hoặc INCORRECT):
            """
        
        # Check session state safely
        if 'ai_hard' in st.session_state and st.session_state['ai_hard']:
            prompt_text = "Bạn được phép mở rộng câu hỏi ra khỏi phạm vi bài học, nhưng phải liên quan tới bài học." + prompt_text
            
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt_text)])]
        
        config = types.GenerateContentConfig( # Đổi tên để nhất quán
            temperature=0.1, # Cần sự nhất quán cao
            response_mime_type="text/plain",
        )
        
        # FIX: Non-streaming call
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )
        evaluation_text = response.text.strip().upper() if response.text else "ERROR"
        print("AI grading response:", repr(evaluation_text))  # <-- Add this line

        if evaluation_text in ["CORRECT", "INCORRECT"]:
            count_recursive_evaluate = 0 # Reset counter on success
            return evaluation_text
        else:
            print(f"Phản hồi không mong đợi từ AI khi đánh giá: {evaluation_text}")
            # Simplified fallback logic to avoid infinite recursion
            return "INCORRECT" 
            
    except Exception as e:
        print(f"Lỗi trong evaluate_user_answer_clarity: {e}")
        return "ERROR"
