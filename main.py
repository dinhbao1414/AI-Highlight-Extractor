import os
import argparse
import time
from dotenv import load_dotenv

from runtime_utils import configure_stdio, safe_print as print
from video_manager import get_video_path
from transcriber import extract_audio, transcribe_audio
from llm_analyzer import analyze_transcript
from editor import process_highlights

def main():
    configure_stdio()
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Chương trình AI tự động trích xuất Video Highlight")
    parser.add_argument("input", nargs="?", help="Đường dẫn file video máy tính hoặc URL YouTube")
    args = parser.parse_args()
    
    input_source = args.input
    if not input_source:
        input_source = input("Nhập URL YouTube hoặc đường dẫn file video máy tính (vd: C:/video.mp4): ").strip()
        
    if not input_source:
        print("Lỗi: Không có dữ liệu đầu vào.")
        return

    print("="*60)
    print("🚀 BẮT ĐẦU QUY TRÌNH HỆ THỐNG EXTRACT HIGHLIGHTS")
    print("="*60)
    
    start_time_total = time.time()
    
    # Bước 1: Chuẩn bị Video
    print("\n[1/4] CHUẨN BỊ VIDEO ĐẦU VÀO...")
    try:
        video_path = get_video_path(input_source)
    except Exception as e:
         print(f"❌ Lỗi: {e}")
         return
        
    base_name = os.path.basename(video_path).rsplit('.', 1)[0]
    workspace_dir = os.path.join("workspace", base_name)
    os.makedirs(workspace_dir, exist_ok=True)
    
    print(f"✅ Đã chuẩn bị xong video gốc: {video_path}")
    
    # Bước 2: Tách & Transcribe Audio
    print(f"\n[2/4] TÁCH ÂM THANH & NHẬN DIỆN GIỌNG NÓI (WHISPER API)...")
    audio_path = extract_audio(video_path, output_dir=workspace_dir)
    srt_path = os.path.join(workspace_dir, f"{base_name}.srt")
    
    if not os.path.exists(srt_path):
        transcribe_audio(audio_path, srt_path)
    else:
        print(f"✅ Đã dùng lại file phụ đề có sẵn: {srt_path}")
        
    # Bước 3: Phân tích LLM
    print(f"\n[3/4] PHÂN TÍCH CAO TRÀO & NGỮ NGHĨA BẰNG AI (LLM)...")
    highlights_json_path = os.path.join(workspace_dir, "highlights.json")
    
    import json
    if not os.path.exists(highlights_json_path):
         highlights = analyze_transcript(srt_path)
         with open(highlights_json_path, "w", encoding="utf-8") as f:
              json.dump(highlights, f, indent=4, ensure_ascii=False)
    else:
         print("✅ Đã dùng lại thông tin highlight có sẵn từ những lần chạy trước.")
         with open(highlights_json_path, "r", encoding="utf-8") as f:
              highlights = json.load(f)
              
    if not highlights:
         print("❌ Không tìm thấy highlight nào. Kết thúc luồng.")
         return
         
    # Bước 4: Xử lý Cắt Video
    print(f"\n[4/4] CẮT VIDEO VÀ GẮN PHỤ ĐỀ CỨNG (HARDSUB)...")
    output_dir = os.path.join("output", base_name)
    process_highlights(video_path, srt_path, highlights, output_dir=output_dir)
    
    total_time = time.time() - start_time_total
    print("\n" + "="*60)
    print(f"🎉 HOÀN THÀNH QUY TRÌNH!")
    print(f"⏱️ Tổng thời gian: {total_time:.2f} giây")
    print(f"📁 Kiểm tra kết quả tại thư mục: {os.path.abspath(output_dir)}")
    print("="*60)

if __name__ == "__main__":
    main()
