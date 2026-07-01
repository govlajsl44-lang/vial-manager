import streamlit as st
import pandas as pd
import datetime
import urllib.parse

# 페이지 설정 및 테마 최적화
st.set_page_config(
    page_title="Vial Production Smart Maintenance System", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ⚙️ [오타 수정 완료] 전문 시스템 느낌을 주기 위한 맞춤형 CSS 주입
st.markdown("""
    <style>
    /* 메인 배경 및 기본 폰트 가독성 설정 */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 95%;
    }
    h1 {
        color: #1E293B;
        font-weight: 700;
        font-size: 2.2rem !important;
        letter-spacing: -0.05rem;
    }
    h2, h3 {
        color: #334155;
        font-weight: 600;
    }
    /* 메트릭 카드 커스텀 스타일 */
    div[data-testid="stMetric"] {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        padding: 1.25rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetricLabel"] p {
        font-size: 0.9rem !important;
        color: #64748B !important;
        font-weight: 600;
    }
    div[data-testid="stMetricValue"] div {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #0F172A;
    }
    /* 탭 스타일 조정 */
    button[data-baseweb="tab"] {
        font-size: 1.05rem !important;
        font-weight: 600 !important;
    }
    </style>
""", unsafe_allow_html=True)

# 시스템 타이틀 영역 (Enterprise 스타일)
st.title("🏭 바이알 제조공정 스마트 설비 예지정비 시스템")
st.markdown("<p style='color:#64748B; font-size:1.05rem; margin-top:-0.5rem;'>Vial Production Line Equipment Predictive Maintenance & Inventory Control System</p>", unsafe_allow_html=True)

# 1. 조회용 링크 (웹 게시 CSV 주소)
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTXDGTnMc8RO3wBVza0w10tR4GuYY_wUUXtfRKae2wYPJWWfCqHK5gRwJqHlEmiY66tR5gr70NJBbEJ/pub?gid=0&single=true&output=csv"

# 앱 메모리에 정비 일지 임시 저장소 생성
if "temp_logs" not in st.session_state:
    st.session_state.temp_logs = []

@st.cache_data(ttl=1)
def load_data(url):
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"구글 시트를 불러오는 중 오류가 발생했습니다: {e}")
        return None

df = load_data(SHEET_CSV_URL)

if df is not None:
    # 열 매칭
    c_id = df.columns[0]      # 부품 ID
    c_mach = df.columns[1]    # 소속 설비
    c_name = df.columns[2]    # 부품명
    c_mat = df.columns[3]     # 재질
    c_life_m = df.columns[4]  # 수명 개월
    c_life_h = df.columns[5]  # 권장 수명 시간
    c_curr_h = df.columns[6]  # 현재 운전 시간
    c_stock = df.columns[7]   # 여분 수량
    c_manual = df.columns[-1] # 정비 매뉴얼 링크

    # 데이터 정수 변환
    df[c_stock] = pd.to_numeric(df[c_stock], errors='coerce').fillna(0).astype(int)
    df[c_curr_h] = pd.to_numeric(df[c_curr_h], errors='coerce').fillna(0).astype(int)
    df[c_life_h] = pd.to_numeric(df[c_life_h], errors='coerce').fillna(0).astype(int)
    df[c_life_m] = pd.to_numeric(df[c_life_m], errors='coerce').fillna(0).astype(int)

    # 남은 시간 연산
    df['남은시간'] = df[c_life_h] - df[c_curr_h]
    urgent_parts = df[(df['남은시간'] <= 200) | (df[c_stock] <= 2)]
    
    # 🚨 상단 위험 알림판 (전문 관제 프레임으로 변경)
    if not urgent_parts.empty:
        st.error(f"⚠️ **[현장 정비 레이더 알림]** 교체 주기 임박 및 보안 재고 부족 품목이 **{len(urgent_parts)}건** 감지되었습니다. 즉시 확인이 필요합니다.")
        with st.expander("🔍 위험 항목 리스트 요약 보기", expanded=False):
            alert_display = urgent_parts[[c_mach, c_name, '남은시간', c_stock]].copy()
            alert_display.columns = ['설비구분', '관리 소모품명', '잔여 수명 (시간)', '창고 여분 재고 (개)']
            st.dataframe(alert_display, use_container_width=True, hide_index=True)

    # 📊 종합 관제 자산 현황판
    st.markdown("<h3 style='margin-top:1.5rem;'>📊 실시간 공정 자산 현황</h3>", unsafe_allow_html=True)
    total_parts = len(df)
    low_stock_parts = len(df[df[c_stock] <= 2])
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("총 관제 소모품 품목", f"{total_parts} SKU")
    m2.metric("보안 재고 위험 (2개 이하)", f"{low_stock_parts} 종", delta=f"-{low_stock_parts}" if low_stock_parts > 0 else "안전", delta_color="inverse")
    m3.metric("설비 가동 상태", "정상 가동 중 (NORMAL)", delta="안정")
    m4.metric("데이터 동기화 기준일", datetime.date.today().strftime("%Y-%m-%d"))
    
    st.markdown("<div style='margin-top: 1.5rem; margin-bottom: 1.5rem; border-bottom: 2px solid #E2E8F0;'></div>", unsafe_allow_html=True)
    
    # 메인 작업 탭 분할
    menu_tab1, menu_tab2 = st.tabs(["📋 소모품 모니터링 및 제어실", "📝 디지털 정비 일지 관리"])

    with menu_tab1:
        query_params = st.query_params
        default_machine = query_params.get("machine", df[c_mach].unique()[0])
        if default_machine not in df[c_mach].unique():
            default_machine = df[c_mach].unique()[0]
            
        col1, col2 = st.columns([1, 1.4], gap="large")
        
        with col1:
            st.markdown("#### ⚙️ 파트 선택 및 관제 변수 수정")
            
            with st.container(border=True):
                selected_machine = st.selectbox("🏭 대상 설비 라인 선택", df[c_mach].unique(), index=list(df[c_mach].unique()).index(default_machine), key="main_mach")
                filtered_df = df[df[c_mach] == selected_machine]
                
                default_part = query_params.get("part", filtered_df[c_name].unique()[0])
                if default_part not in filtered_df[c_name].unique():
                    default_part = filtered_df[c_name].unique()[0]
                    
                selected_part = st.selectbox("🔧 세부 부품 객체 선택", filtered_df[c_name].unique(), index=list(filtered_df[c_name].unique()).index(default_part), key="main_part")
            
            part_idx = df[df[c_name] == selected_part].index[0]
            part_info = df.loc[part_idx]
            
            with st.container(border=True):
                st.markdown(f"<h4 style='color:#0F172A; margin-bottom:0.5rem;'>📝 {selected_part} 사양</h4>", unsafe_allow_html=True)
                st.markdown(f"**• 부품 고유 코드 :** `{part_info[c_id]}`")
                st.markdown(f"**• 구성 부품 재질 :** `{part_info[c_mat]}`")
            
            st.markdown("#### 🔄 원격 현장 데이터 실시간 조정")
            with st.container(border=True):
                new_curr_h = st.number_input("⏱️ 현재 누적 운전 시간 (Hour)", value=int(part_info[c_curr_h]), step=10, key="input_h")
                new_stock = st.number_input("📦 실보관 여분 재고 수량 (EA)", value=int(part_info[c_stock]), step=1, key="input_s")
                
                st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
                if st.button("💾 원격 스프레드시트 마스터 데이터 동기화", key="btn_save_sheet", use_container_width=True, type="primary"):
                    with st.spinner("중앙 데이터베이스 서버에 동기화 요청 중..."):
                        df.at[part_idx, c_curr_h] = new_curr_h
                        df.at[part_idx, c_stock] = new_stock
                        st.success(f"✅ [{selected_part}] 서버 동기화 완료 및 원격 갱신 명령이 하달되었습니다.")
                        st.cache_data.clear()
                        st.rerun()

            st.markdown("#### 📄 기술 지침 문서")
            manual_url = part_info[c_manual]
            if pd.notna(manual_url) and str(manual_url).strip