import os
import re
import datetime
import subprocess
from runtime_utils import safe_print as print

def time_to_seconds(ts: str) -> float:
    """Chuyển format HH:MM:SS,mmm thành số giây."""
    # Xử lý các lỗi đánh máy chuẩn của LLM
    ts = ts.strip().replace('.', ',')
    parts = ts.split(',')
    if len(parts) == 1:
        # Nếu LLM quên phần mmm
        parts.append('000')
    time_str, ms_str = parts[0], parts[1]
    
    t = datetime.datetime.strptime(time_str, "%H:%M:%S")
    td = datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second, milliseconds=int(ms_str))
    return td.total_seconds()

def seconds_to_time(seconds: float) -> str:
    """Chuyển số giây thành HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def extract_and_shift_srt(original_srt: str, start_sec: float, end_sec: float, output_srt: str):
    """Lấy các dòng SRT nằm trong khoảng thời gian và kéo chúng về mốc 0."""
    with open(original_srt, 'r', encoding='utf-8') as f:
        blocks = f.read().strip().split('\n\n')
        
    shifted_blocks = []
    idx = 1
    for block in blocks:
        lines = block.split('\n')
        if len(lines) >= 3:
            time_line = lines[1]
            if '-->' in time_line:
                start_str, end_str = time_line.split('-->')
                s_sec = time_to_seconds(start_str)
                e_sec = time_to_seconds(end_str)
                
                # Nới lỏng 1 chút (trường hợp sub kéo dài ra ngoài 1 xíu cũng không sao)
                if s_sec >= start_sec - 1.0 and s_sec <= end_sec + 1.0:
                    # Shift
                    new_s = max(0, s_sec - start_sec)
                    new_e = max(new_s + 0.1, e_sec - start_sec)
                    
                    new_time_line = f"{seconds_to_time(new_s)} --> {seconds_to_time(new_e)}"
                    text_lines = "\n".join(lines[2:])
                    
                    shifted_blocks.append(f"{idx}\n{new_time_line}\n{text_lines}")
                    idx += 1
                    
    with open(output_srt, 'w', encoding='utf-8') as f:
        f.write("\n\n".join(shifted_blocks) + "\n\n")

def escape_subtitle_path(path: str) -> str:
    """Escape đường dẫn cho FFmpeg subtitles filter trên Windows/Linux."""
    # FFmpeg subtitles filter cần forward slashes
    path = path.replace("\\", "/")
    # Nếu là ổ đĩa Windows (Vd: C:/) thì phải escape dấu hai chấm (C\:/)
    path = path.replace(":", "\\:")
    return path

def format_filename(s: str) -> str:
    """Loại bỏ ký tự đặc biệt để làm tên file."""
    s = str(s).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)

def process_highlights(video_path: str, srt_path: str, highlights: list, output_dir: str = "output", progress_callback=None) -> list[str]:
    """Cắt video thành các Part và re-render sạch. Trả về danh sách file MP4."""
    os.makedirs(output_dir, exist_ok=True)
    final_video_paths = []
    total = len(highlights)
    
    for i, hl in enumerate(highlights):
        try:
            start_str = hl['start'].strip()
            end_str = hl['end'].strip()
            part_num = hl.get('part', i + 1)
            title = hl.get('title', f"Part_{part_num}")
            
            start_sec = time_to_seconds(start_str)
            end_sec = time_to_seconds(end_str)
            duration = end_sec - start_sec
            
            if duration <= 0:
                 print(f"Bỏ qua Part {part_num} vì thời lượng không hợp lệ.")
                 continue

            clean_title = format_filename(title)
            output_file = os.path.join(output_dir, f"Part_{part_num}_{clean_title}.mp4")
            
            if progress_callback:
                current_prog = 80 + int((i / total) * 19)
                progress_callback(current_prog, f"[4/4] Render Part {part_num}/{total}: {title}...")
            
            print(f"Đang render Part {part_num}: {title} ({start_str} -> {end_str}, {duration:.0f}s)...")
            
            # === BƯỚC 1: Cắt nhanh bằng stream copy ===
            temp_cut = os.path.join(output_dir, f"temp_cut_{i}.mp4")
            cut_cmd = [
                "ffmpeg", "-y",
                "-ss", str(start_sec),
                "-i", video_path,
                "-t", str(duration),
                "-c", "copy",
                "-avoid_negative_ts", "make_zero",
                temp_cut
            ]
            subprocess.run(cut_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if not os.path.exists(temp_cut) or os.path.getsize(temp_cut) == 0:
                print(f"Cảnh báo: Bước cắt nhanh thất bại cho Part {part_num}")
                continue
            
            # === BƯỚC 2: Re-render sang 1080p H.264 (sạch codec, tránh trùng lặp) ===
            render_cmd = [
                "ffmpeg", "-y",
                "-i", temp_cut,
                "-vf", "scale=1920:-2",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart",
                output_file
            ]
            subprocess.run(render_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Cleanup temp
            if os.path.exists(temp_cut):
                os.remove(temp_cut)
            
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                final_video_paths.append(output_file)
                print(f"✅ Part {part_num} lưu thành công: {output_file}")
            else:
                print(f"Cảnh báo: FFmpeg không tạo được file Part {part_num}")
                
        except Exception as e:
            print(f"Lỗi khi xử lý Part {part_num} [{title}]: {e}")
    
    return final_video_paths
