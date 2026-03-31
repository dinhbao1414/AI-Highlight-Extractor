from runtime_utils import configure_stdio

configure_stdio()

import os

import streamlit as st
from dotenv import load_dotenv

from core import run_pipeline
from settings_store import load_settings, save_settings

load_dotenv()

SETTING_KEYS = (
    "whisper_key",
    "whisper_url",
    "whisper_model",
    "llm_key",
    "llm_url",
    "llm_model",
)

DEFAULT_SETTINGS = {
    "whisper_key": os.getenv("WHISPER_API_KEY", ""),
    "whisper_url": os.getenv("WHISPER_BASE_URL", "https://api.groq.com/openai/v1"),
    "whisper_model": os.getenv("WHISPER_MODEL", "large-v3-turbo"),
    "llm_key": os.getenv("LLM_API_KEY", ""),
    "llm_url": os.getenv("LLM_BASE_URL", "http://127.0.0.1:8045/v1"),
    "llm_model": os.getenv("LLM_MODEL", "gemini-3-flash"),
}


def initialize_settings() -> None:
    stored_settings = load_settings()
    for key in SETTING_KEYS:
        if key not in st.session_state:
            st.session_state[key] = stored_settings.get(key, DEFAULT_SETTINGS[key])


def persist_settings() -> None:
    current_settings = {key: st.session_state.get(key, "") for key in SETTING_KEYS}
    if st.session_state.get("_persisted_settings") == current_settings:
        return

    save_settings(current_settings)
    st.session_state["_persisted_settings"] = current_settings.copy()


st.set_page_config(
    page_title="Semantic Video Highlight Extractor",
    page_icon="🎬",
    layout="wide",
)

initialize_settings()

with st.sidebar:
    st.header("⚙️ Cấu hình hệ thống")
    st.caption("Các giá trị bên dưới được lưu cục bộ vào SQLite và tự nạp lại khi bạn mở lại localhost.")

    st.subheader("1. Whisper")
    st.text_input("Whisper Base URL", key="whisper_url")
    st.text_input(
        "Whisper Model",
        key="whisper_model",
        help="Ví dụ: whisper-1 hoặc whisper-large-v3-turbo",
    )
    st.text_area(
        "Whisper API Key(s)",
        key="whisper_key",
        height=80,
        help="Có thể nhập nhiều key, phân tách bằng dấu phẩy.",
    )

    key_count = len([key for key in st.session_state["whisper_key"].split(",") if key.strip()])
    if key_count > 1:
        st.caption(f"Đã phát hiện {key_count} Whisper API keys. Cơ chế xoay vòng key sẽ được dùng khi cần.")

    st.subheader("2. LLM")
    st.text_input("LLM Base URL", key="llm_url")
    st.text_input("LLM Tên Model", key="llm_model")
    st.text_input("LLM API Key", key="llm_key", type="password")
    st.markdown("---")
    st.caption("Hỗ trợ OpenAI, Gemini hoặc các dịch vụ tương thích chuẩn OpenAI.")

persist_settings()

st.title("🎬 Tool trích xuất video highlight tự động")
st.markdown(
    "Ứng dụng kết hợp Whisper và LLM để phân tích video dài, tìm các cao trào và cắt thành nhiều phần ngắn."
)

input_source = st.text_input(
    "🔗 Nhập URL YouTube hoặc đường dẫn file video (.mp4)",
    placeholder="https://www.youtube.com/watch?v=....",
)

if st.button("🚀 Trích xuất highlight ngay", type="primary", use_container_width=True):
    if not input_source:
        st.error("Vui lòng nhập link video hoặc đường dẫn file.")
    else:
        config_data = {key: st.session_state[key] for key in SETTING_KEYS}

        progress_bar = st.progress(0, text="Khởi động hệ thống...")
        status_text = st.empty()

        def update_progress(percent: float, message: str) -> None:
            progress_bar.progress(max(0.0, min(1.0, percent / 100.0)), text=message)
            status_text.info(message)

        try:
            with st.spinner("Hệ thống đang xử lý video..."):
                final_videos = run_pipeline(
                    input_source,
                    config=config_data,
                    progress_callback=update_progress,
                )

            progress_bar.progress(1.0, text="Hoàn tất")
            status_text.success("Render highlight thành công.")
            st.markdown("### Danh sách video highlight")

            if final_videos:
                cols = st.columns(2)
                for index, video_file in enumerate(final_videos):
                    with cols[index % 2]:
                        st.markdown(f"**{os.path.basename(video_file)}**")
                        try:
                            with open(video_file, "rb") as video_handle:
                                st.video(video_handle.read())
                        except Exception:
                            st.error("Không thể tải player cho video này.")
            else:
                st.warning("Không tạo được highlight nào từ video này.")

        except Exception as exc:
            st.error(f"Có lỗi xảy ra trong quá trình chạy: {exc}")
            progress_bar.empty()
