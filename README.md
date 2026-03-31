# 🎬 AI Video Highlight Extractor

Công cụ AI tự động phân tích video dài (30 phút - 1 tiếng) và cắt thành các **Part** theo cấu trúc kịch bản: **Nguyên nhân → Diễn biến → Kết quả**.

Hệ thống ưu tiên các đoạn có **xung đột**, **căng thẳng**, **đối đầu** — mỗi Part dài **1-3 phút**, được re-render sạch sang **1080p H.264** để phát mượt trên mọi nền tảng.

---

## 📋 Yêu Cầu Hệ Thống

| Phần mềm | Phiên bản | Ghi chú |
|-----------|-----------|---------|
| **Python** | 3.9+ | Kiểm tra: `python --version` |
| **FFmpeg** | 5.0+ | Phải được thêm vào biến môi trường PATH |
| **pip** | mới nhất | Kiểm tra: `pip --version` |

### Cài FFmpeg (bắt buộc)

**Windows (dùng winget):**
```bash
winget install Gyan.FFmpeg
```

**Windows (thủ công):**
1. Tải từ [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/) → bản `ffmpeg-release-essentials.zip`
2. Giải nén vào `C:\ffmpeg`
3. Thêm `C:\ffmpeg\bin` vào biến môi trường **PATH** của Windows
4. Mở Terminal mới, gõ `ffmpeg -version` để kiểm tra

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update && sudo apt install ffmpeg
```

---

## 🚀 Cài Đặt & Khởi Chạy

### Bước 1: Cài thư viện Python

Mở Terminal, di chuyển vào thư mục dự án và cài đặt:

```bash
cd highlight-extractor
pip install -r requirements.txt
```

Thư viện sẽ được cài gồm:
- `yt-dlp` — Tải video từ YouTube
- `openai` — Gọi API Whisper & LLM
- `python-dotenv` — Đọc file cấu hình `.env`
- `streamlit` — Giao diện Web

### Bước 2: Cấu hình API Key (tuỳ chọn)

Bạn có thể cấu hình trước bằng file `.env` hoặc nhập trực tiếp trên giao diện Web.

**Cách 1 — File `.env` (cấu hình 1 lần):**

```bash
cp .env.example .env
```

Mở file `.env` và điền API Key:

```env
# === WHISPER (Nhận diện giọng nói) ===
WHISPER_API_KEY=gsk_your_groq_key_here
WHISPER_BASE_URL=https://api.groq.com/openai/v1
WHISPER_MODEL=whisper-large-v3-turbo

# === LLM (Phân tích cao trào) ===
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o
```

**Cách 2 — Nhập trên giao diện Web:** Không cần tạo file `.env`. Mở app lên rồi điền trực tiếp vào thanh Sidebar bên trái.

### Bước 3: Chạy ứng dụng

```bash
streamlit run app.py
```

Trình duyệt sẽ tự động mở tại `http://localhost:8501` 🎉

---

## 🖥️ Hướng Dẫn Sử Dụng

### Giao diện chính

```
┌─────────────────────────────────────────────────────────┐
│  ⚙️ SIDEBAR (Trái)          │  🎬 MAIN (Giữa)          │
│  ─────────────────           │  ─────────────────        │
│  Whisper Base URL            │  🔗 Nhập URL YouTube      │
│  Whisper Model               │     hoặc đường dẫn file   │
│  Whisper API Key(s)          │                            │
│  ─────────────────           │  [🔥 Trích Xuất Ngay]     │
│  LLM Base URL                │                            │
│  LLM Tên Model               │  ━━━━━━━━━━━ 75%          │
│  LLM API Key                 │  ⏳ Đang phân tích LLM... │
│                               │                            │
│                               │  🍿 Video Part thành phẩm │
│                               │  ▶ Part_1_xxx.mp4         │
│                               │  ▶ Part_2_xxx.mp4         │
└─────────────────────────────────────────────────────────┘
```

### Các bước xử lý

1. **Điền cấu hình API** ở Sidebar bên trái (nếu chưa có file `.env`)
2. **Dán link YouTube** hoặc **đường dẫn file video** vào ô giữa màn hình
3. **Bấm nút "🔥 Trích Xuất Highlight Ngay"**
4. Theo dõi thanh tiến trình:
   - `[1/4]` Tải / xác minh video
   - `[2/4]` Tách audio + Whisper nhận diện giọng nói
   - `[3/4]` LLM phân tích cao trào, chia Part
   - `[4/4]` FFmpeg cắt + re-render từng Part
5. **Xem video ngay** trên giao diện hoặc mở thư mục `output/`

---

## 🔑 Hướng Dẫn Lấy API Key

### Whisper (Nhận diện giọng nói)

| Nhà cung cấp | Base URL | Model | Ghi chú |
|---------------|----------|-------|---------|
| **Groq** (Miễn phí, nhanh) | `https://api.groq.com/openai/v1` | `whisper-large-v3-turbo` | [Tạo key tại đây](https://console.groq.com/keys) |
| **OpenAI** | `https://api.openai.com/v1` | `whisper-1` | Trả phí theo phút |

### LLM (Phân tích video)

| Nhà cung cấp | Base URL | Model | Ghi chú |
|---------------|----------|-------|---------|
| **Google Gemini** | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-2.0-flash` | [Lấy key](https://aistudio.google.com/apikey) |
| **OpenAI** | `https://api.openai.com/v1` | `gpt-4o` | Trả phí |

### 🔄 Xoay vòng API Key (Key Rotation)

Hỗ trợ nhập **nhiều Whisper API Key** để tự động xoay vòng khi key hết quota:

```
gsk_key_1_xxx, gsk_key_2_yyy, gsk_key_3_zzz
```

Nhập các key cách nhau bằng dấu phẩy. Khi key đầu bị rate limit, hệ thống tự chuyển sang key tiếp theo.

---

## 📁 Cấu Trúc Thư Mục

```
highlight-extractor/
├── app.py              # Giao diện Web (Streamlit)
├── core.py             # Pipeline điều phối chính
├── video_manager.py    # Tải YouTube / xác thực file local
├── transcriber.py      # Tách audio + gọi Whisper API
├── llm_analyzer.py     # Gửi transcript cho LLM phân tích
├── editor.py           # Cắt video + re-render FFmpeg
├── main.py             # CLI mode (chạy bằng dòng lệnh)
├── requirements.txt    # Thư viện Python
├── .env.example        # Mẫu cấu hình API
│
├── downloads/          # Video tải từ YouTube (tự tạo)
├── workspace/          # Dữ liệu trung gian: audio, SRT, JSON
│   └── {tên_video}/
│       ├── xxx.mp3           # Audio đã tách
│       ├── xxx.srt           # Phụ đề Whisper
│       └── highlights.json   # Kết quả phân tích LLM
│
└── output/             # 🎯 VIDEO THÀNH PHẨM
    └── {tên_video}/
        ├── Part_1_Tiêu_đề.mp4
        ├── Part_2_Tiêu_đề.mp4
        └── Part_3_Tiêu_đề.mp4
```

---

## 💻 Chạy bằng Dòng Lệnh (CLI Mode)

Ngoài giao diện Web, bạn cũng có thể chạy trực tiếp bằng Terminal:

```bash
# Với link YouTube
python main.py "https://www.youtube.com/watch?v=xxxxx"

# Với file local
python main.py "C:/Videos/my_video.mp4"

# Không có tham số → nhập tay
python main.py
```

---

## ❓ Xử Lý Sự Cố

| Lỗi | Nguyên nhân | Cách sửa |
|------|-------------|----------|
| `ffmpeg: command not found` | FFmpeg chưa cài hoặc chưa thêm PATH | Xem mục "Cài FFmpeg" ở trên |
| `model_not_found` | Tên model Whisper/LLM sai | Kiểm tra lại tên model trong Sidebar |
| `rate limit / quota exceeded` | API key hết quota | Nhập thêm key (xoay vòng) hoặc đổi nhà cung cấp |
| `Video không tạo ra Part nào` | FFmpeg render quá lâu | Video có thể là 4K → hệ thống đã tự scale 1080p, chờ thêm |
| Lỗi `content-script-start.js` | Extension trình duyệt | Bỏ qua hoàn toàn, không ảnh hưởng tool |

### Chạy lại từ đầu (xoá cache)

Nếu muốn LLM phân tích lại video đã xử lý:

```bash
# Xoá kết quả phân tích cũ (giữ lại file SRT để không mất quota Whisper)
del workspace\{tên_video}\highlights.json

# Xoá toàn bộ output cũ
rmdir /s output\{tên_video}
```

---

## 📜 License

MIT License — Sử dụng tự do cho mục đích cá nhân và thương mại.
