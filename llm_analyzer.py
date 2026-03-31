import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv
from runtime_utils import safe_print as print

load_dotenv()

def extract_json_from_text(text: str) -> dict:
    """Trích xuất khối JSON từ chuỗi văn bản LLM trả về."""
    # Tìm đoạn bắt đầu bằng ```json và kết thúc bằng ```
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        json_str = text # Giả định text là pure JSON
        
    try:
        return json.loads(json_str)
    except Exception as e:
        print(f"Lỗi khi chuyển đổi thành JSON: {e}")
        # Thử chữa các lỗi phổ biến (trailing commas, v.v.)
        # Nếu fail thì trả về list rỗng
        return {"highlights": []}

def analyze_transcript(srt_path: str) -> list[dict]:
    """Gửi nội dung SRT cho LLM để phân tích và trả về danh sách các Part."""
    client = OpenAI(
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    )
    model = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")

    print(f"Đang đọc nội dung phân tích từ file: {srt_path}")
    with open(srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()

    system_prompt = """
Bạn là một chuyên gia biên tập video chuyên nghiệp (Video Editor / Storyteller).

NHIỆM VỤ: Phân tích file phụ đề (.srt) của một video dài và chia nó thành các PHẦN (Part) theo cấu trúc kịch bản phim tài liệu.

QUY TẮC BẮT BUỘC:
1. Mỗi Part phải dài TỐI THIỂU 1 PHÚT và TỐI ĐA 3 PHÚT.
2. Mỗi Part phải có cấu trúc NGUYÊN NHÂN → DIỄN BIẾN → KẾT QUẢ hoàn chỉnh. Không cắt giữa chừng.
3. ƯU TIÊN CAO cho các đoạn có: xung đột, cãi nhau, đối đầu, tranh luận gay gắt, bạo lực, đuổi bắt, hành động căng thẳng.
4. Các Part phải LIÊN TỤC VỀ MẶT CÂU CHUYỆN, không trùng lặp thời gian. Part sau phải diễn ra SAU Part trước.
5. Đặt tiêu đề Part theo phong cách kịch tính, ngắn gọn, thu hút.
6. Mỗi video khoảng 8-10 phút nên chia khoảng 3-4 Part. Video dài hơn thì nhiều Part hơn.

CÁCH SUY NGHĨ:
- Đọc toàn bộ transcript trước
- Xác định các điểm ngoặt (turning points) chính trong câu chuyện
- Mỗi Part bắt đầu từ nguyên nhân/bối cảnh và kết thúc ở hệ quả/phản ứng
- Đảm bảo người xem mỗi Part đều hiểu chuyện gì đang xảy ra mà không cần xem Part khác

Hãy trả về CHỈ chuỗi JSON với cấu trúc:
{
  "highlights": [
    {
      "part": 1,
      "start": "HH:MM:SS,mmm",
      "end": "HH:MM:SS,mmm",
      "title": "Tiêu đề kịch tính cho Part",
      "reason": "Mô tả ngắn: Nguyên nhân gì → Diễn biến gì → Kết quả gì trong Part này"
    }
  ]
}

- start và end phải khớp chính xác định dạng timestamp SRT (ví dụ 00:01:15,500).
- KHÔNG trả lời bất kỳ văn bản nào ngoài khối JSON.
"""

    print(f"Đang gửi dữ liệu ({len(srt_content)} chars) lên LLM ({model}) để tìm cao trào...")
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Đây là file SRT của tôi:\n\n{srt_content}"}
        ],
        temperature=0.7
    )

    result_text = response.choices[0].message.content.strip()
    
    # Xử lý trích xuất JSON
    print("Đã nhận kết quả phân tích JSON. Đang bóc tách...")
    parsed_json = extract_json_from_text(result_text)
    
    highlights = parsed_json.get("highlights", [])
    if not highlights:
        print("Cảnh báo: Không tìm thấy highlights hợp lệ từ phản hồi của LLM.")
        print(f"Nguyên văn phản hồi: {result_text}")
    else:
         print(f"Đã tìm thấy {len(highlights)} đoạn highlight tiềm năng.")
         for idx, h in enumerate(highlights):
             print(f"[{idx+1}] {h['start']} -> {h['end']} | {h.get('title', 'No Title')}")
             
    return highlights

if __name__ == "__main__":
    pass
