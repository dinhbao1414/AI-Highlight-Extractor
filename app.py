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


def parse_input_sources(raw_value: str) -> list[str]:
    return [line.strip() for line in raw_value.splitlines() if line.strip()]


def get_source_label(input_source: str) -> str:
    normalized_source = input_source.rstrip("/\\")
    return os.path.basename(normalized_source) or input_source


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
    st.header("Cau hinh he thong")
    st.caption("Cac gia tri nhap trong giao dien se duoc luu vao SQLite va giu lai cho cac lan mo localhost sau.")

    st.subheader("1. Whisper")
    st.text_input("Whisper Base URL", key="whisper_url")
    st.text_input(
        "Whisper Model",
        key="whisper_model",
        help="Vi du: whisper-1 hoac whisper-large-v3-turbo",
    )
    st.text_area(
        "Whisper API Key(s)",
        key="whisper_key",
        height=80,
        help="Co the nhap nhieu key, tach nhau bang dau phay.",
    )

    key_count = len([key for key in st.session_state["whisper_key"].split(",") if key.strip()])
    if key_count > 1:
        st.caption(f"Da phat hien {key_count} Whisper API keys. Co che xoay vong key se duoc dung khi can.")

    st.subheader("2. LLM")
    st.text_input("LLM Base URL", key="llm_url")
    st.text_input("LLM Ten Model", key="llm_model")
    st.text_input("LLM API Key", key="llm_key", type="password")
    st.markdown("---")
    st.caption("Ho tro OpenAI, Gemini hoac cac dich vu tuong thich chuan OpenAI.")

persist_settings()

st.title("Tool trich xuat video highlight tu dong")
st.markdown(
    "Ung dung ket hop Whisper va LLM de phan tich video dai, tim cao trao va cat thanh nhieu doan ngan."
)

input_sources_text = st.text_area(
    "Nhap URL YouTube hoac duong dan file video (.mp4), moi dong mot muc",
    placeholder="https://www.youtube.com/watch?v=video_1\nhttps://www.youtube.com/watch?v=video_2",
    height=140,
)

if st.button("Trich xuat highlight ngay", type="primary", use_container_width=True):
    input_sources = parse_input_sources(input_sources_text)

    if not input_sources:
        st.error("Vui long nhap it nhat 1 URL hoac duong dan file.")
    else:
        config_data = {key: st.session_state[key] for key in SETTING_KEYS}
        total_sources = len(input_sources)
        results_by_source: list[tuple[str, list[str]]] = []
        failed_sources: list[tuple[str, str]] = []

        progress_bar = st.progress(0, text="Khoi dong he thong...")
        status_text = st.empty()

        with st.spinner("He thong dang xu ly tung video theo thu tu..."):
            for source_index, input_source in enumerate(input_sources, start=1):
                source_label = get_source_label(input_source)

                def update_progress(
                    percent: float,
                    message: str,
                    *,
                    current_index: int = source_index,
                    current_label: str = source_label,
                ) -> None:
                    overall_percent = ((current_index - 1) + (percent / 100.0)) / total_sources
                    progress_text = f"[{current_index}/{total_sources}] {current_label}: {message}"
                    progress_bar.progress(max(0.0, min(1.0, overall_percent)), text=progress_text)
                    status_text.info(progress_text)

                try:
                    final_videos = run_pipeline(
                        input_source,
                        config=config_data,
                        progress_callback=update_progress,
                    )
                    results_by_source.append((input_source, final_videos))
                except Exception as exc:
                    failed_sources.append((input_source, str(exc)))

        progress_bar.progress(1.0, text="Hoan tat")

        if failed_sources:
            status_text.warning("Da xu ly xong danh sach, co muc bi loi.")
        else:
            status_text.success("Da xu ly xong toan bo danh sach.")

        st.markdown("### Danh sach video highlight")

        for input_source, final_videos in results_by_source:
            st.markdown(f"#### {input_source}")

            if final_videos:
                cols = st.columns(2)
                for index, video_file in enumerate(final_videos):
                    with cols[index % 2]:
                        st.markdown(f"**{os.path.basename(video_file)}**")
                        try:
                            with open(video_file, "rb") as video_handle:
                                st.video(video_handle.read())
                        except Exception:
                            st.error("Khong the hien thi player cho video nay.")
            else:
                st.warning("Khong tao duoc highlight nao tu nguon nay.")

        for input_source, error_message in failed_sources:
            st.error(f"Loi khi xu ly {input_source}: {error_message}")
