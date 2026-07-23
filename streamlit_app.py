# KGC Smart MRO - Streamlit 실행 래퍼
# 완성된 단일 HTML 앱(Supabase + Gemini 실연동)을 Streamlit 안에서 그대로 렌더링합니다.
#
# 실행:  streamlit run streamlit_app.py
# 배포:  Streamlit Community Cloud / 사내 서버 어디서든 동작 (별도 백엔드 불필요)

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="KGC Smart MRO",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Streamlit 기본 여백/헤더 제거 → 앱이 전체 화면을 쓰도록
st.markdown(
    """
    <style>
      #MainMenu, header, footer {visibility: hidden;}
      .block-container {padding: 0 !important; max-width: 100% !important;}
      [data-testid="stAppViewContainer"] > .main {padding: 0 !important;}
      iframe {border: none !important;}
    </style>
    """,
    unsafe_allow_html=True,
)

HTML_FILE = Path(__file__).parent / "KGC Smart MRO (standalone).html"
html = HTML_FILE.read_text(encoding="utf-8")

# 모바일 우선 앱이라 세로로 길게. 필요 시 height 조정.
components.html(html, height=920, scrolling=True)
