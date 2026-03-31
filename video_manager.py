import os
import re
from pathlib import Path
import yt_dlp
from runtime_utils import safe_print as print

def is_youtube_url(url: str) -> bool:
    """Kiểm tra xem chuỗi đầu vào có phải là link YouTube không."""
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    )
    return re.match(youtube_regex, url) is not None

def download_youtube_video(url: str, output_dir: str = "downloads") -> str:
    """Tải video từ YouTube về thư mục cục bộ."""
    os.makedirs(output_dir, exist_ok=True)
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(output_dir, '%(title)s_%(id)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'noplaylist': True,
        'quiet': False
    }

    print(f"Bắt đầu tải video từ YouTube: {url} ...")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info_dict)
        # yt-dlp prepare_filename có thể trả .webm trong khi merge_output_format đã ép .mp4
        base, ext = os.path.splitext(filename)
        if ext.lower() != '.mp4':
            mp4_path = base + '.mp4'
            if os.path.exists(mp4_path):
                filename = mp4_path
        print(f"Đã tải xong: {filename}")
        return filename

def get_video_path(input_source: str) -> str:
    """Xử lý input: Tải về nếu là URL youtube, hoặc verify nếu là file máy tính."""
    if is_youtube_url(input_source):
        return download_youtube_video(input_source)
    else:
        file_path = Path(input_source)
        if file_path.exists() and file_path.is_file():
            print(f"Sử dụng video local: {input_source}")
            return input_source
        else:
            raise FileNotFoundError(f"Không tìm thấy file video tại: {input_source}")

if __name__ == "__main__":
    # Test
    # video_path = get_video_path("https://www.youtube.com/watch?v=jNQXAC9IVRw")
    pass
