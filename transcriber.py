import os
import math
import subprocess
from openai import OpenAI
from dotenv import load_dotenv
from runtime_utils import safe_print as print

load_dotenv()

def extract_audio(video_path: str, output_dir: str = "temp") -> str:
    """Tách âm thanh từ video sang định dạng mp3 32kbps mono (tối ưu cho Whisper)."""
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.basename(video_path).rsplit('.', 1)[0]
    audio_path = os.path.join(output_dir, f"{base_name}.mp3")
    
    if os.path.exists(audio_path):
        print(f"File audio đã tồn tại: {audio_path}")
        return audio_path

    print(f"Đang tách audio từ {video_path}...")
    # Nén 32k, 1 kênh để giảm dung lượng (<25MB cho 1 tiếng)
    command = [
        "ffmpeg", "-y", "-i", video_path, 
        "-vn", "-acodec", "libmp3lame", 
        "-ac", "1", "-ab", "32k", 
        audio_path
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Đã tạo file audio: {audio_path}")
    return audio_path

def split_audio_if_needed(audio_path: str, max_size_mb: int = 24) -> list[str]:
    """Cắt file audio ra thành nhiều phần nếu dung lượng lớn hơn max_size_mb."""
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    if file_size_mb <= max_size_mb:
        return [audio_path]
    
    print(f"File audio lớn hơn {max_size_mb}MB ({file_size_mb:.2f}MB). Đang thực hiện chia nhỏ...")
    # Lấy độ dài audio (giây)
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path], stdout=subprocess.PIPE, text=True)
    duration = float(result.stdout.strip())
    
    # Tính số chunk cần thiết
    num_chunks = math.ceil(file_size_mb / max_size_mb)
    chunk_time = math.ceil(duration / num_chunks)
    
    base_name = os.path.basename(audio_path).rsplit('.', 1)[0]
    output_dir = os.path.dirname(audio_path)
    
    chunk_files = []
    for i in range(num_chunks):
        start_time = i * chunk_time
        chunk_path = os.path.join(output_dir, f"{base_name}_chunk{i}.mp3")
        chunk_files.append(chunk_path)
        if not os.path.exists(chunk_path):
            command = [
                "ffmpeg", "-y", "-i", audio_path,
                "-ss", str(start_time), "-t", str(chunk_time),
                "-acodec", "copy", chunk_path
            ]
            subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
    return chunk_files

def format_timestamp(seconds: float) -> str:
    """Chuyển đổi giây sang format SRT: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def get_whisper_keys() -> list[str]:
    """Lấy danh sách Whisper API keys (hỗ trợ nhiều key phân cách bởi dấu phẩy)."""
    raw = os.getenv("WHISPER_API_KEY", "")
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    return keys

def call_whisper_with_rotation(keys: list[str], base_url: str, model: str, audio_file_path: str):
    """Gọi Whisper API với cơ chế xoay vòng key khi bị rate limit / hết quota."""
    last_error = None
    
    for idx, key in enumerate(keys):
        try:
            client = OpenAI(api_key=key, base_url=base_url)
            with open(audio_file_path, "rb") as f:
                response = client.audio.transcriptions.create(
                    model=model,
                    file=f,
                    response_format="verbose_json"
                )
            print(f"  ✅ Whisper thành công với key #{idx+1}")
            return response
        except Exception as e:
            error_str = str(e).lower()
            # Các lỗi quota/rate limit → thử key tiếp theo
            if any(kw in error_str for kw in ["rate", "limit", "quota", "429", "insufficient", "exceeded"]):
                print(f"  ⚠️ Key #{idx+1} hết quota/rate limit, đang chuyển sang key tiếp theo...")
                last_error = e
                continue
            else:
                # Lỗi khác (ví dụ file hỏng, model sai) → không retry
                raise e
    
    # Tất cả key đều hết
    raise Exception(f"Tất cả {len(keys)} API key đều hết quota! Lỗi cuối: {last_error}")

def transcribe_audio(audio_path: str, output_srt: str) -> str:
    """Thực hiện Speech-to-Text dùng Whisper API và lưu file srt."""
    chunks = split_audio_if_needed(audio_path)
    
    keys = get_whisper_keys()
    if not keys:
        raise ValueError("Chưa cấu hình WHISPER_API_KEY! Hãy nhập ít nhất 1 API key.")
    
    base_url = os.getenv("WHISPER_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("WHISPER_MODEL", "whisper-1")

    print(f"Đang transcribe {len(chunks)} chunk(s) với {len(keys)} API key(s)...")
    
    srt_content = ""
    subtitle_index = 1
    cumulative_offset = 0.0
    
    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)}: {chunk}")
        
        response = call_whisper_with_rotation(keys, base_url, model, chunk)
        
        chunk_duration = 0.0
        
        for segment in response.segments:
            start_time = segment.start + cumulative_offset
            end_time = segment.end + cumulative_offset
            text = segment.text.strip()
            
            srt_content += f"{subtitle_index}\n"
            srt_content += f"{format_timestamp(start_time)} --> {format_timestamp(end_time)}\n"
            srt_content += f"{text}\n\n"
            subtitle_index += 1
            
            if segment.end > chunk_duration:
                chunk_duration = segment.end
        
        # Cộng dồn offset cho chunk tiếp theo
        if len(chunks) > 1:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
                 "-of", "default=noprint_wrappers=1:nokey=1", chunk],
                stdout=subprocess.PIPE, text=True
            )
            try:
                cumulative_offset += float(result.stdout.strip())
            except ValueError:
                cumulative_offset += chunk_duration

    with open(output_srt, "w", encoding="utf-8") as f:
        f.write(srt_content)
        
    print(f"Đã lưu SRT tại: {output_srt}")
    return output_srt

if __name__ == "__main__":
    pass

