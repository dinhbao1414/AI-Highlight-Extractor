import os
import json
from video_manager import get_video_path
from transcriber import extract_audio, transcribe_audio
from llm_analyzer import analyze_transcript
from editor import process_highlights

def run_pipeline(input_source: str, config: dict = None, progress_callback=None) -> list[str]:
    """
    Hàm thực thi toàn bộ pipeline phục vụ cho GUI.
    Trả về danh sách các đường dẫn file video MP4 đã lưu.
    """
    if progress_callback:
        progress_callback(5, "Đang khởi tạo cấu hình...")
        
    # Cập nhật biến môi trường trực tiếp từ API Keys trong UI
    if config:
        if config.get("whisper_key"): os.environ["WHISPER_API_KEY"] = config["whisper_key"]
        if config.get("whisper_url"): os.environ["WHISPER_BASE_URL"] = config["whisper_url"]
        if config.get("whisper_model"): os.environ["WHISPER_MODEL"] = config["whisper_model"]
        if config.get("llm_key"): os.environ["LLM_API_KEY"] = config["llm_key"]
        if config.get("llm_url"): os.environ["LLM_BASE_URL"] = config["llm_url"]
        if config.get("llm_model"): os.environ["LLM_MODEL"] = config["llm_model"]

    try:
        if progress_callback:
            progress_callback(10, "[1/4] Đang tải / xác minh video đầu vào...")
        video_path = get_video_path(input_source)
        
        base_name = os.path.basename(video_path).rsplit('.', 1)[0]
        workspace_dir = os.path.join("workspace", base_name)
        os.makedirs(workspace_dir, exist_ok=True)
        
        if progress_callback:
            progress_callback(30, "[2/4] Đang tách âm thanh khỏi video...")
        audio_path = extract_audio(video_path, output_dir=workspace_dir)
        
        srt_path = os.path.join(workspace_dir, f"{base_name}.srt")
        if not os.path.exists(srt_path):
            if progress_callback:
                progress_callback(40, "[2/4] Đang gọi Whisper API để nhận diện giọng nói (vui lòng đợi vài phút)...")
            transcribe_audio(audio_path, srt_path)
            
        highlights_json_path = os.path.join(workspace_dir, "highlights.json")
        if not os.path.exists(highlights_json_path):
            if progress_callback:
                progress_callback(60, "[3/4] Đang phân tích cao trào và nội dung bằng LLM (ChatGPT/Gemini)...")
            highlights = analyze_transcript(srt_path)
            with open(highlights_json_path, "w", encoding="utf-8") as f:
                json.dump(highlights, f, indent=4, ensure_ascii=False)
        else:
            if progress_callback:
                progress_callback(70, "[3/4] Đang tải kết quả LLM từ phiên làm việc trước...")
            with open(highlights_json_path, "r", encoding="utf-8") as f:
                highlights = json.load(f)
                
        if not highlights:
            if progress_callback: progress_callback(100, "Xong! (Lỗi: Video không có phần nào đủ thú vị để làm Highlight).")
            return []

        if progress_callback:
            progress_callback(80, f"[4/4] Bắt đầu cắt {len(highlights)} đoạn video, tiến hành chèn hardsub...")
            
        output_dir = os.path.join("output", base_name)
        # Gọi trực tiếp process_highlights (đã tích hợp progress_callback)
        final_video_paths = process_highlights(
            video_path, srt_path, highlights, 
            output_dir=output_dir, 
            progress_callback=progress_callback
        )

        if progress_callback:
            progress_callback(100, f"🎉 Hoàn thành! Đã trích xuất {len(final_video_paths)} video thành công!")
            
        return final_video_paths
        
    except Exception as e:
        if progress_callback: progress_callback(100, f"Lỗi nghiêm trọng: {str(e)}")
        raise e
