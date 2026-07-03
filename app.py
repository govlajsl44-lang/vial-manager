import streamlit as st
import pandas as pd
import datetime
import urllib.parse
import requests

# 1. 하이브리드 반응형 페이지 레이아웃 정의
st.set_page_config(
    page_title="Smart MES Pro", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 📱 모바일 및 웹 동시 최적화 프리미엄 하이브리드 CSS 테마 주입
st.markdown("""
    <style>
    /* 기본 배경 및 여백 설정 */
    /* 1. 스트림릿 자체 헤더(Share, 깃허브 아이콘, 점 3개)를 완전히 숨겨 앱처럼 만들기 */
    header[data-testid="stHeader"] {
        visibility: hidden !important;
        height: 0px !important;
    }
    
    /* 2. 기본 배경 및 상단 여백 보정 (1rem에서 2.5rem으로 올려 타이틀 짤림 방지) */
    .main { background-color: #F8FAFC !important; }
    .block-container { padding-top: 2.5rem !important; padding-bottom: 1rem !important; max-width: 96% !important; }
    
    /* 타이틀 모바일 최적화 */
    h1 {
        color: #0F172A !important;
        font-weight: 800 !important;
        font-size: 1.8rem !important;
        border-bottom: 3px solid #0284C7;
        padding-bottom: 8px;
        margin-bottom: 15px !important;
    }
    h2, h3, h4 { color: #1E293B !important; font-weight: 700 !important; margin-top: 0.8rem !important; }
    
    /* 대형 관제 메트릭 카드 가시성 확보 */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-top: 4px solid #0284C7 !important;
        padding: 0.8rem !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05) !important;
        margin-bottom: 8px !important;
    }
    div[data-testid="stMetricLabel"] p { font-size: 0.8rem !important; color: #475569 !important; font-weight: 700 !important; }
    div[data-testid="stMetricValue"] div { font-size: 1.4rem !important; font-weight: 800 !important; color: #0F172A !important; }
    
    /* 모바일 스크롤용 카드 형태 컨테이너 */
    div[data-testid="stContainer"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        padding: 1.2rem !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.05) !important;
        margin-bottom: 15px !important;
    }
    
    /* 모바일 엄지손가락 터치 전용 버튼 스타일 고도화 */
    .stButton>button { 
        font-weight: 700 !important; 
        border-radius: 6px !important; 
        padding: 0.6rem 1rem !important;
        font-size: 1rem !important;
    }
    
    /* 상단 탭 모바일 스크롤 지원 및 폰트 강조 */
    button[data-baseweb="tab"] { font-size: 0.95rem !important; font-weight: 700 !important; color: #64748B !important; }
    button[aria-selected="true"] { color: #0284C7 !important; border-bottom-color: #0284C7 !important; }
    
    /* 섹션 구분을 위한 서브 배너 스타일 */
    .section-title {
        background-color: #E0F2FE;
        color: #0369A1;
        padding: 6px 12px;
        border-radius: 4px;
        font-weight: 700;
        font-size: 1rem;
        margin-bottom: 10px;
        display: inline-block;
    }
    
    /* 안내 배너 스타일 */
    .menu-hero-banner {
        background: linear-gradient(135deg, #0284C7 0%, #0369A1 100%);
        color: #FFFFFF !important;
        padding: 1rem !important;
        border-radius: 8px !important;
        margin-bottom: 15px !important;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1) !important;
    }
    .menu-hero-banner h3 { color: #FFFFFF !important; margin: 0 0 5px 0 !important; font-size: 1.2rem !important; }
    .menu-hero-banner p { color: #E0F2FE !important; margin: 0 !important; font-size: 0.85rem !important; }
    
    /* ----------------------------------------------------------- */
    /* 📸 레퍼런스 스타일 완벽 반영 커스텀 로그인 레이아웃 스타일 */
    /* ----------------------------------------------------------- */
    .reference-login-box {
        background-color: rgba(38, 38, 38, 0.95) !important; /* 이미지 속 짙은 투명 차콜 카드 */
        border: 1px solid #404040 !important;
        padding: 3rem 2.2rem !important;
        border-radius: 4px !important;
        color: #FFFFFF !important;
        box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.3) !important;
        text-align: center;
    }
    .ref-corp-title {
        font-size: 1.4rem !important;
        font-weight: 800 !important;
        color: #FFFFFF !important;
        margin-bottom: 2px !important;
        letter-spacing: -0.5px;
    }
    .ref-sys-title {
        font-size: 1.1rem !important;
        font-weight: 500 !important;
        color: #A3A3A3 !important;
        margin-bottom: 2rem !important;
    }
    
    /* 이미지 내부 인풋 폼처럼 레이블을 제거하고 투명하게 커스텀 */
    div[data-testid="stTextInput"] input {
        background-color: rgba(255, 255, 255, 0.08) !important;
        color: #FFFFFF !important;
        border: 1px solid #52525B !important;
        border-radius: 2px !important;
        padding: 0.65rem 0.8rem !important;
        font-size: 0.95rem !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #3B82F6 !important;
        box-shadow: 0 0 0 1px #3B82F6 !important;
    }
    
    /* 레퍼런스 전용 선명한 블루 로그인 버튼 */
    .ref-login-btn button {
        background-color: #007BEC !important; /* 사진 속 직사각형 파란색 버튼 컬러 */
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
        border: none !important;
        border-radius: 2px !important;
        padding: 0.7rem 0px !important;
        transition: all 0.2s;
    }
    .ref-login-btn button:hover {
        background-color: #0069CB !important;
    }
    
    /* 세팅 상자 스타일 */
    .setup-container {
        max-width: 480px;
        margin: 60px auto;
        background-color: #FFFFFF;
        padding: 2.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border-top: 5px solid #007BEC;
    }
    
    @media (max-width: 768px) {
        .block-container { padding-left: 0.4rem !important; padding-right: 0.4rem !important; }
        h1 { font-size: 1.35rem !important; }
        div[data-testid="stMetricValue"] div { font-size: 1.2rem !important; }
        button[data-baseweb="tab"] { font-size: 0.85rem !important; padding-left: 8px !important; padding-right: 8px !important; }
        .stButton>button { font-size: 0.95rem !important; }
    }
    </style>
""", unsafe_allow_html=True)

# 0초 무지연 실시간 라이브 데이터 주소
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8/export?format=csv&gid=0"

# 🔑 Secrets 상자에서 안전하게 환경 변수 호출
if "MACRO_URL" in st.secrets:
    LIVE_MACRO_URL = st.secrets["MACRO_URL"]
    LIVE_SHEET_NAME = st.secrets.get("SHEET_NAME", "시트1")
else:
    LIVE_MACRO_URL = ""
    LIVE_SHEET_NAME = "시트1"

# 중앙 구글 시트 셀 원격 직접 제어 함수
def update_google_sheet(sheet_id, sheet_name, row_idx, col_idx, new_value):
    if not LIVE_MACRO_URL:
        return False
    try:
        params = {
            "id": sheet_id,
            "sheet": sheet_name,
            "row": int(row_idx + 2),
            "col": int(col_idx + 1),
            "val": new_value
        }
        requests.get(LIVE_MACRO_URL, params=params, timeout=5)
        return True
    except:
        return False

if "temp_logs" not in st.session_state:
    st.session_state.temp_logs = []

@st.cache_data(ttl=5)
def load_data(url):
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        return None

df = load_data(SHEET_CSV_URL)

# ----------------------------------------------------------------------
# 🔐 인증 관련 세션 상태 정의
# ----------------------------------------------------------------------
if "auth_step" not in st.session_state:
    st.session_state.auth_step = "login_gate"  # login_gate -> setup_gate -> main_app
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "user_team" not in st.session_state:
    st.session_state.user_team = None
if "user_machine" not in st.session_state:
    st.session_state.user_machine = None
if "user_db" not in st.session_state:
    # 초기 시연용 기본 가상 계정 명부 (ID : PW)
    st.session_state.user_db = {"admin": "1234", "manager": "qwer"}


# ----------------------------------------------------------------------
# [공통 데이터 파싱 구조 유지] 로그인 이후 구동 최적화
# ----------------------------------------------------------------------
if df is not None:
    col_list = list(df.columns)
    c_id = col_list[0]          
    c_mach = col_list[1]        
    c_name = col_list[2]        
    c_mat = col_list[3]         
    c_life_m = col_list[4]      
    c_life_h = col_list[5]      
    c_curr_h = col_list[6]      
    
    idx_manual = 7              
    idx_stock = 8               
    idx_install = 9             

    c_manual = col_list[idx_manual]
    c_stock = col_list[idx_stock]
    c_install_date = col_list[idx_install] if len(col_list) > 9 else col_list[-1]

    df[c_stock] = pd.to_numeric(df[c_stock], errors='coerce').fillna(0).astype(int)
    df[c_curr_h] = pd.to_numeric(df[c_curr_h], errors='coerce').fillna(0).astype(int)
    df[c_life_h] = pd.to_numeric(df[c_life_h], errors='coerce').fillna(0).astype(int)
    df[c_life_m] = pd.to_numeric(df[c_life_m], errors='coerce').fillna(0).astype(int)
    df['남은시간'] = df[c_life_h] - df[c_curr_h]


# ======================================================================
# 📺 [STEP 1] 레퍼런스 스타일 완벽 모사 로그인 화면
# ======================================================================
if st.session_state.auth_step == "login_gate":
    # 배경 화면을 꽉 채우기 위한 기본 가상 여백 확보
    st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
    
    # 🖼️ 사진 예시처럼 좌측엔 와이드 배경 전경 카드, 우측엔 짙은 로그인 폼 배치 (분할 배율 적용)
    col_visual, col_auth = st.columns([1.4, 1], gap="large")
    
    with col_visual:
        # 사진 왼쪽의 건물 전경/공장 스킨 느낌을 프리미엄 UI 카드로 대치
        st.markdown("""
            <div style="background: linear-gradient(135deg, rgba(15, 23, 42, 0.2) 0%, rgba(15, 23, 42, 0.7) 100%), 
                        url('https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?q=80&w=1200'); 
                        background-size: cover; background-position: center; height: 460px; border-radius: 6px; 
                        display: flex; flex-direction: column; justify-content: flex-end; padding: 2.5rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
                <h2 style='color: #FFFFFF !important; font-weight:800; font-size: 2.2rem; margin: 0;'>Smart MES Pro</h2>
                <p style='color: #93C5FD; font-size: 1rem; font-weight:500; margin: 6px 0 0 0;'>제조 혁신 통합 관리 플랫폼 및 실시간 예방보전 엔진</p>
            </div>
        """, unsafe_allow_html=True)
        
    with col_auth:
        auth_sub_tab1, auth_sub_tab2 = st.tabs(["🔒 시스템 로그인", "📝 신규 계정 등록"])
        
        with auth_sub_tab1:
            st.markdown("<div class='reference-login-box'>", unsafe_allow_html=True)
            st.markdown("<p class='ref-corp-title'>Smart MES Pro</p>", unsafe_allow_html=True)
            st.markdown("<p class='ref-sys-title'>Smart MR</p>", unsafe_allow_html=True)
            
            # 레퍼런스 사진과 동일하게 상단 타이틀 텍스트 레이블을 제거(collapsed)하고 인풋 내부에 표시
            in_id = st.text_input("아이디_레이블숨김", placeholder="아이디", label_visibility="collapsed", key="ref_id_gate")
            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
            in_pw = st.text_input("비밀번호_레이블숨김", type="password", placeholder="비밀번호", label_visibility="collapsed", key="ref_pw_gate")
            
            st.markdown("<div style='margin-top:25px;'></div>", unsafe_allow_html=True)
            
            # 파란색 로그인 버튼 주입
            st.markdown("<div class='ref-login-btn'>", unsafe_allow_html=True)
            if st.button("로그인", use_container_width=True, key="ref_login_action_btn"):
                if not in_id or not in_pw:
                    st.warning("⚠️ 인증 정보를 채워주십시오.")
                elif in_id in st.session_state.user_db and st.session_state.user_db[in_id] == in_pw:
                    st.session_state.current_user = in_id
                    st.session_state.auth_step = "setup_gate"
                    st.rerun()
                else:
                    st.error("❌ 아이디 또는 비밀번호가 불일치합니다.")
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with auth_sub_tab2:
            st.markdown("<div class='reference-login-box' style='padding: 2rem 2.2rem !important;'>", unsafe_allow_html=True)
            st.markdown("<h4 style='color:white; margin-top:0px !important; margin-bottom:15px;'>작업자 가입 신청</h4>", unsafe_allow_html=True)
            reg_id = st.text_input("가입아이디", placeholder="새로운 아이디 입력", label_visibility="collapsed", key="reg_id_key")
            st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
            reg_pw = st.text_input("가입비밀번호", type="password", placeholder="새로운 비밀번호 입력", label_visibility="collapsed", key="reg_pw_key")
            st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
            reg_pw_c = st.text_input("가입비밀번호확인", type="password", placeholder="비밀번호 확인 재입력", label_visibility="collapsed", key="reg_pwc_key")
            
            st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
            if st.button("계정 생성", use_container_width=True):
                if not reg_id or not reg_pw:
                    st.error("❌ 빈칸을 모두 입력하세요.")
                elif reg_id in st.session_state.user_db:
                    st.error("❌ 이미 할당된 아이디입니다.")
                elif reg_pw != reg_pw_c:
                    st.error("❌ 비밀번호 불일치")
                else:
                    st.session_state.user_db[reg_id] = reg_pw
                    st.success("✅ 가입 완료! 로그인해 주십시오.")


# ======================================================================
# ⚙️ [STEP 2] 공정 설정 및 기계 라인 권한 할당 화면
# ======================================================================
elif st.session_state.auth_step == "setup_gate":
    st.markdown("<div class='setup-container'>", unsafe_allow_html=True)
    st.markdown("<h3>🏭 공정 실무 권한 설정</h3>", unsafe_allow_html=True)
    st.write(f"접속 승인 계정: `{st.session_state.current_user} 마스터`")
    st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)
    
    selected_team = st.selectbox("📌 소속 작업 부서/팀 선택", ["생산기술1팀", "제조운영2팀", "설비보전팀", "품질관리과"])
    
    if df is not None:
        machine_list = df[c_mach].unique()
        selected_mach = st.selectbox("🏭 금일 담당 지정 설비 기계 설정", machine_list)
    else:
        selected_mach = st.text_input("🏭 담당 기계 수동 기입 (마스터 연결 필요)")
        
    st.markdown("<div style='margin-top:25px;'></div>", unsafe_allow_html=True)
    
    if st.button("개인 맞춤형 대시보드 진입 ➡️", type="primary", use_container_width=True):
        st.session_state.user_team = selected_team
        st.session_state.user_machine = selected_mach
        st.session_state.auth_step = "main_app"
        st.rerun()
        
    st.markdown("</div>", unsafe_allow_html=True)


# ======================================================================
# 📊 [STEP 3] 메인 고도화 MES 시스템 본문 (기존 코드 완벽 통합)
# ======================================================================
elif st.session_state.auth_step == "main_app":
    # 🔐 최상단 실시간 권한 네비게이션 및 세션 로그아웃 바 아키텍처
    nav_col1, nav_col2 = st.columns([8, 2])
    with nav_col1:
        st.caption(f"🛡️ {st.session_state.user_team} 전용 관제 가동 중 | 할당 설비: [{st.session_state.user_machine}] | 인증 계정: {st.session_state.current_user}")
    with nav_col2:
        if st.button("🔒 로그아웃 / 권한 리셋", use_container_width=True, key="logout_action_btn"):
            st.session_state.auth_step = "login_gate"
            st.session_state.current_user = None
            st.session_state.user_machine = None
            st.session_state.user_team = None
            st.rerun()

    st.title("설비 소모품 관리 시스템")

    if "MACRO_URL" not in st.secrets:
        st.error("⚠️ [설정 누락] Streamlit 웹 관리자화면 Secrets에 MACRO_URL을 등록하셔야 구글 시트 저장이 활성화됩니다.")

    if df is not None:
        urgent_parts = df[(df['남은시간'] <= 200) | (df[c_stock] <= 2)]
        
        if not urgent_parts.empty:
            with st.expander(f"🚨 위험물품 알림: 정비 임계 품목 {len(urgent_parts)}건 검출", expanded=True):
                alert_display = urgent_parts[[c_mach, c_name, '남은시간', c_stock]].copy()
                alert_display.columns = ['설비명', '부품명', '잔여(Hr)', '재고(EA)']
                st.dataframe(alert_display, use_container_width=True, hide_index=True)

        # 📊 상단 실시간 공정 자산 대시보드
        st.markdown("### 📊 실시간 공정 지표")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("총 관리 소모품 종류", f"{len(df)} 종류")
        m2.metric("보안재고 위험군 (2개 이하)", f"{len(df[df[c_stock] <= 2])} 종")
        m3.metric("라인 가동 상태", "NORMAL (안정 구동)")
        m4.metric("시스템 동기화 기준", datetime.date.today().strftime("%Y-%m-%d"))
        
        st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
        
        # 📋 시각적 직관성을 강화한 4대 핵심 메뉴 탭 구성
        menu_tab1, menu_tab2, menu_tab3, menu_tab4 = st.tabs([
            "📋 1. 자산 관리 & 신품 교체", 
            "📝 2. 정비 일지 기록", 
            "📸 3. AI 카메라 진단",
            "💬 4. AI 정비 챗봇"
        ])

        # ----------------------------------------------------------------------
        # [메뉴 1] 자산 관리 & 신품 교체 탭
        # ----------------------------------------------------------------------
        with menu_tab1:
            st.markdown(f"""
                <div class='menu-hero-banner'>
                    <h3>📋 소모품 자산 관제 및 신품 교체실 (담당 설비 타겟: {st.session_state.user_machine})</h3>
                    <p>설비별 부품의 남은 수명을 실시간으로 모니터링하고, 신품 교체 시 마스터 데이터를 동기화하는 공간입니다.</p>
                </div>
            """, unsafe_allow_html=True)
            
            # 로그인 시 선택한 기계가 드롭다운 메뉴의 기본 시작 선택값(Index)으로 자동 바인딩되도록 업그레이드
            query_params = st.query_params
            session_mach = st.session_state.get("user_machine", df[c_mach].unique()[0])
            default_machine = query_params.get("machine", session_mach)
            if default_machine not in df[c_mach].unique():
                default_machine = df[c_mach].unique()[0]
                
            col1, col2 = st.columns([1, 1.2], gap="medium")
            
            with col1:
                st.markdown("<span class='section-title'>1️⃣ 설비 및 부품 선택</span>", unsafe_allow_html=True)
                with st.container():
                    selected_machine = st.selectbox("🏭 대상 설비 라인 선택", df[c_mach].unique(), index=list(df[c_mach].unique()).index(default_machine), key="sl_mach")
                    filtered_df = df[df[c_mach] == selected_machine]
                    
                    default_part = query_params.get("part", filtered_df[c_name].unique()[0])
                    if default_part not in filtered_df[c_name].unique():
                        default_part = filtered_df[c_name].unique()[0]
                        
                    selected_part = st.selectbox("🔧 세부 점검 부품 선택", filtered_df[c_name].unique(), index=list(filtered_df[c_name].unique()).index(default_part), key="sl_part")
                
                part_idx = df[df[c_name] == selected_part].index[0]
                part_info = df.loc[part_idx]
                
                st.markdown("<span class='section-title'>2️⃣ 선택 부품 실시간 상태 조회</span>", unsafe_allow_html=True)
                with st.container():
                    if pd.notna(part_info[c_install_date]):
                        raw_install_date = str(part_info[c_install_date]).strip()
                        st.markdown(f"📅 **최초 장착일 :** `{raw_install_date}`")
                        try:
                            parsed_start = datetime.datetime.strptime(raw_install_date, "%Y-%m-%d").date()
                        except:
                            parsed_start = datetime.date.today()
                    else:
                        st.markdown("📅 **최초 장착일 :** `기록 없음`")
                        parsed_start = datetime.date.today()

                    months_to_add = int(part_info[c_life_m])
                    year = parsed_start.year + (parsed_start.month + months_to_add - 1) // 12
                    month = (parsed_start.month + months_to_add - 1) % 12 + 1
                    calculated_replace_date = datetime.date(year, month, min(parsed_start.day, 28))
                    
                    st.markdown(f"⏳ **차기 권장 교체일 :** `{calculated_replace_date.strftime('%Y-%m-%d')}` (주기: {months_to_add}개월)")
                    st.markdown(f"📦 **창고 보관 여분 재고 :** `{part_info[c_stock]} EA`")
                    st.markdown(f"⏱️ **가동 런타임 :** `{part_info[c_curr_h]} hr` / 한계 `{part_info[c_life_h]} hr` (잔여: `{part_info['남은시간']} hr`)")
                    
                    manual_url = part_info[c_manual]
                    if pd.notna(manual_url) and str(manual_url).strip().startswith("http"):
                        st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
                        st.link_button("📄 표준 정비 매뉴얼 열람", manual_url.strip(), type="primary", use_container_width=True)

                with st.expander("⚙️ 예외 변수 수동 수치 보정 (필요시에만 사용)"):
                    new_curr_h = st.number_input("현재 누적 가동 시간 보정", value=int(part_info[c_curr_h]), step=10, key="adj_h")
                    new_stock = st.number_input("창고 보관 수량 보정", value=int(part_info[c_stock]), step=1, key="adj_s")
                    if st.button("💾 데이터 보정 명령 동기화", use_container_width=True):
                        with st.spinner("보전 서버 통신 중..."):
                            update_google_sheet("1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8", LIVE_SHEET_NAME, part_idx, 6, new_curr_h) 
                            update_google_sheet("1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8", LIVE_SHEET_NAME, part_idx, idx_stock, new_stock) 
                            st.success("✅ 수치 수동 보정 완료")
                            st.cache_data.clear()
                            st.rerun()
                            
            with col2:
                st.markdown("<span class='section-title'>3️⃣ 소모품 교체 및 자산 리셋</span>", unsafe_allow_html=True)
                with st.container():
                    st.warning(f"⚠️ **작업 확정 알림:** [{selected_part}] 파트를 새 부품으로 교체하는 경우, 아래 단추를 누르면 **[운전시간 0Hr 리셋 / 여분재고 1개 차감 / 장착일 오늘 자동 갱신]**이 구글 시트에 영구 반영됩니다.")
                    chosen_execution_date = st.date_input("📆 실제 신품 교체(장착) 날짜 지정", datetime.date.today(), key="exec_date_picker")
                    
                    if st.button("교체 확정 처리 완료", type="primary", use_container_width=True):
                        if part_info[c_stock] <= 0:
                            st.error("❌ 창고 내 여분 재고 자산이 부족(0개)하여 교체 명령을 수행할 수 없습니다.")
                        else:
                            with st.spinner("중앙 ERP 스프레드시트 클라우드 원격 갱신 중..."):
                                reset_hours = 0
                                reduced_stock = int(part_info[c_stock]) - 1
                                formatted_install_date = chosen_execution_date.strftime("%Y-%m-%d")
                                
                                update_google_sheet("1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8", LIVE_SHEET_NAME, part_idx, 6, reset_hours)       
                                update_google_sheet("1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8", LIVE_SHEET_NAME, part_idx, idx_stock, reduced_stock) 
                                update_google_sheet("1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8", LIVE_SHEET_NAME, part_idx, idx_install, formatted_install_date) 
                                
                                auto_system_log = {
                                    "날짜": formatted_install_date,
                                    "부품명": selected_part,
                                    "작업자": st.session_state.current_user,
                                    "정비내용": f"[신품 교체 완수] {st.session_state.user_team} 부서 조치 완료."
                                }
                                st.session_state.temp_logs.insert(0, auto_system_log)
                                st.success(f"🎉 [{selected_part}] 신품 장착 처리 및 스케줄링 리셋이 완벽하게 완수되었습니다.")
                                st.balloons()
                                st.cache_data.clear()
                                st.rerun()

                st.markdown("##### ⏱ ... 실시간 수명 소모 진행 바")
                current_hours = int(part_info[c_curr_h])
                max_hours = int(part_info[c_life_h])
                progress_per = max(0, min(100, int((current_hours / max_hours) * 100))) if max_hours > 0 else 0
                st.progress(progress_per, text=f"수명 소모 진척도: {progress_per}%")

                st.markdown("---")
                st.subheader("📱 하드웨어 식별용 스마트 QR코드 라벨")
                app_url = "https://vial-manager-na6qyzsytdcsencg2jwr89.streamlit.app/"
                qr_link = f"{app_url}?machine={urllib.parse.quote(selected_machine)}&part={urllib.parse.quote(selected_part)}"
                qr_link_enc = urllib.parse.quote(qr_link)
                qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=130x130&data={qr_link_enc}"
                
                q_col1, q_col2 = st.columns([1, 2.5])
                with q_col1: st.image(qr_api_url, caption="정비 태그 QR")
                with q_col2: st.code(qr_link)

        # ----------------------------------------------------------------------
        # [메뉴 2] 정비 일지 기록 탭 (현재 접속 유저 정보 기본 대입 연동)
        # ----------------------------------------------------------------------
        with menu_tab2:
            st.markdown("""
                <div class='menu-hero-banner'>
                    <h3>📝 제조 설비 일일 정비·교체 일지 관리실</h3>
                    <p>현장에서 수행한 일상 보전 내역, 고장 처리 및 유격 조정 조치 사항을 수동 기입하고 누적 타임라인을 확인합니다.</p>
                </div>
            """, unsafe_allow_html=True)
            
            log_col1, log_col2 = st.columns([1, 1.2], gap="medium")
            
            with log_col1:
                st.markdown("<span class='section-title'>1️⃣ 정비 내역 서식 작성</span>", unsafe_allow_html=True)
                with st.container():
                    log_date = st.date_input("정비 및 작업 실행 일자", datetime.date.today(), key="m_log_date")
                    
                    # 로그인 시 권한 선택한 기계로 기본 디폴트 선택
                    mach_log_options = list(df[c_mach].unique())
                    default_log_mach_idx = mach_log_options.index(st.session_state.user_machine) if st.session_state.user_machine in mach_log_options else 0
                    log_mach = st.selectbox("정비 대상 설비 선택", mach_log_options, index=default_log_mach_idx, key="m_log_mach")
                    
                    filtered_log_df = df[df[c_mach] == log_mach]
                    log_part = st.selectbox("정비 처리 부품 선택", filtered_log_df[c_name].unique(), key="m_log_part")
                    
                    # 💡 현재 로그인 세션에 보유 중인 팀과 아이디 자동 문자열 매핑 적용
                    log_worker = st.text_input("작업 정비원 성명 기입", value=f"{st.session_state.user_team} {st.session_state.current_user}", key="m_log_worker")
                    log_content = st.text_area("상세 정비 작업 내역 기술", placeholder="예: 구동 기어 유격 측정 후 중심 정렬 및 볼트 고정 록타이트 처리.", key="m_log_content")
                    
                    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
                    if st.button("🚀 정비 이력 로그 중앙 서버 전송", type="primary", use_container_width=True, key="m_log_submit_btn"):
                        if not log_content:
                            st.warning("⚠️ 입력창에 누락된 데이터가 있습니다. 상세 내용을 기술해 주십시오.")
                        else:
                            new_log_entry = {
                                "날짜": log_date.strftime("%Y-%m-%d"),
                                "부품명": log_part,
                                "작업자": log_worker,
                                "정비내용": log_content
                            }
                            st.session_state.temp_logs.insert(0, new_log_entry)
                            st.success(f"✅ [{log_part}] 정비 데이터 이력이 타임라인에 안전하게 세팅되었습니다.")
                            st.rerun()
            
            with log_col2:
                st.markdown("<span class='section-title'>2️⃣ 최근 공정 예방 보전 이력 피드백 (실시간)</span>", unsafe_allow_html=True)
                with st.container():
                    base_logs = [
                        {"날짜": "2026-07-01", "부품명": "충전 피스톤 실링", "작업자": "시스템관리자", "정비내용": "스마트 예지정비 모니터링 제어실 연동 상태 정상 작동 중."}
                    ]
                    display_logs = st.session_state.temp_logs + base_logs
                    log_df_display = pd.DataFrame(display_logs)
                    st.dataframe(log_df_display, use_container_width=True, hide_index=True)

        # ----------------------------------------------------------------------
        # [메뉴 3] AI 카메라 진단 탭
        # ----------------------------------------------------------------------
        with menu_tab3:
            st.markdown("""
                <div class='menu-hero-banner'>
                    <h3>📸 AI 실시간 스마트 현장 비전 진단실</h3>
                    <p>마모된 부품이나 외관 손상이 의심되는 기계 부위를 촬영하십시오. 고성능 비전 엔진이 균열 및 오염도를 즉시 진단합니다.</p>
                </div>
            """, unsafe_allow_html=True)
            
            if "GEMINI_API_KEY" in st.secrets:
                vision_api_key = st.secrets["GEMINI_API_KEY"]
                st.success("🟢 클라우드 공용 AI 보안 엔진이 안전하게 연동되어 있습니다.")
            else:
                vision_api_key = ""
                st.error("⚠️ [알림] 공용으로 사용하시려면 Streamlit Settings -> Secrets 메뉴에 GEMINI_API_KEY를 등록해 주세요.")
            
            v_col1, v_col2 = st.columns([1, 1.2], gap="medium")
            
            with v_col1:
                st.markdown("<span class='section-title'>1️⃣ 하드웨어 이미지 입력 소스</span>", unsafe_allow_html=True)
                with st.container():
                    input_mode = st.radio("사진 획득 방식을 고르세요", ["📱 모바일 카메라로 직접 촬영", "📁 갤러리/컴퓨터 파일 업로드"], key="vision_mode")
                    
                    captured_file = None
                    if input_mode == "📱 모바일 카메라로 직접 촬영":
                        captured_file = st.camera_input("부품 외관 비추기")
                    else:
                        captured_file = st.file_uploader("부품 사진 이미지 선택 (JPG, PNG)", type=["jpg", "jpeg", "png"], key="file_vision")
                        
                    if captured_file is not None:
                        st.image(captured_file, caption="🛠️ AI 분석 대상 이미지", width=360)
            
            with v_col2:
                st.markdown("<span class='section-title'>2️⃣ AI 비전 실시간 진단 및 정비 권고안</span>", unsafe_allow_html=True)
                if captured_file is None:
                    st.info("💡 안내: 왼쪽 입력 장치에서 카메라로 사진을 찍거나 파일을 등록하시면 실시간 분석 대기 모드로 전환됩니다.")
                else:
                    if st.button("🚀 이미지 비전 해독 및 진단 분석 시작", type="primary", use_container_width=True):
                        with st.spinner("AI가 고해상도 픽셀 분석을 통해 사물을 해독하는 중..."):
                            try:
                                import google.generativeai as genai
                                from PIL import Image
                                
                                genai.configure(api_key=vision_api_key)
                                pil_image = Image.open(captured_file)
                                
                                context_prompt = (
                                    "너는 제조 공장의 최고 숙련된 기계 정비 마스터이자 스마트 팩토리 인공지능 비전이야. "
                                    "제시된 사진을 정밀 해독해서 1. 이 부품이 어떤 기계 부품이거나 도구/설비인지 이름을 유추해주고, "
                                    "2. 현재 표면 마모, 균열, 오염, 혹은 손상 징후가 육안상 식별되는지 외관 상태를 정밀 진단해줘. "
                                    "3. 마지막으로 현장 정비원이 조치해야 할 예방보전 조치안을 대기업 공장 보고서 스타일로 깔끔하고 신뢰감 있게 한국어로 나누어 설명해줘."
                                )
                                
                                models_to_try = ['gemini-2.5-flash', 'gemini-flash-latest', 'gemini-3.5-flash', 'gemini-2.0-flash', 'gemini-pro-latest']
                                ai_response = None
                                used_model = ""
                                
                                for model_name in models_to_try:
                                    try:
                                        vision_model = genai.GenerativeModel(model_name)
                                        ai_response = vision_model.generate_content([context_prompt, pil_image])
                                        used_model = model_name
                                        break
                                    except:
                                        continue
                                
                                if ai_response is not None:
                                    st.success(f"사진 해독이 성공적으로 완료되었습니다! (적용 엔진: {used_model})")
                                    st.write(ai_response.text)
                                else:
                                    st.error("❌ 모든 구글 AI 모델이 거부 응답을 보냈습니다. 한도를 점검해 주세요.")
                            except Exception as error_msg:
                                st.error(f"❌ AI 분석 모듈 연동 중 오류가 발생했습니다: {error_msg}")

        # ----------------------------------------------------------------------
        # [메뉴 4] AI 정비 챗봇 탭
        # ----------------------------------------------------------------------
        with menu_tab4:
            st.markdown("""
                <div class='menu-hero-banner'>
                    <h3>💬 AI 정비 챗봇</h3>
                    <p>설비 구동부 트러블슈팅, 기계공학 조치 지식, 볼트 체결 토크값 등 현장 애로사항에 대한 솔루션을 실시간으로 논의합니다.</p>
                </div>
            """, unsafe_allow_html=True)
            
            chat_api_key = st.secrets.get("GEMINI_API_KEY", "")
                
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = [
                    {
                        "role": "assistant", 
                        "content": "안녕하세요! 정비봇입니다. 설비 구동부 트러블이나 규격 노하우 등 현장 애로사항을 말씀해 주시면 해결책을 찾아드리겠습니다!"
                    }
                ]
                
            st.markdown("<span class='section-title'>💬 1:1 대화 챗봇</span>", unsafe_allow_html=True)
            with st.container():
                for msg in st.session_state.chat_history:
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])
                    
            if user_prompt := st.chat_input("정비 문제 상황이나 기계 질문을 타이핑하세요"):
                with st.chat_message("user"):
                    st.write(user_prompt)
                st.session_state.chat_history.append({"role": "user", "content": user_prompt})
                
                if not chat_api_key:
                    st.error("❌ 대시보드 Secrets에 GEMINI_API_KEY가 세팅되어 있지 않습니다.")
                else:
                    with st.chat_message("assistant"):
                        with st.spinner("정비 챗봇이 조치 방안을 도출하는 중..."):
                            try:
                                import google.generativeai as genai
                                genai.configure(api_key=chat_api_key)
                                
                                system_instruction = (
                                    "너는 제조 공장의 최고 숙련된 기계 정비 마스터이자 스마트 팩토리 수석 엔지니어 보전원이야. "
                                    "해결책을 조항별로 나누어 한국어로 설명해줘. 불필요한 서론은 생략하고 현장에서 당장 조치할 수 있는 실천적인 행동 매뉴얼 위주로 작성해야 해."
                                )
                                
                                chat_models = ['gemini-2.5-flash', 'gemini-flash-latest', 'gemini-3.5-flash', 'gemini-2.0-flash', 'gemini-pro-latest']
                                bot_reply = None
                                for m_name in chat_models:
                                    try:
                                        c_model = genai.GenerativeModel(m_name)
                                        bot_reply = c_model.generate_content([system_instruction, user_prompt])
                                        break
                                    except:
                                        continue
                                        
                                if bot_reply is not None:
                                    st.write(bot_reply.text)
                                    st.session_state.chat_history.append({"role": "assistant", "content": bot_reply.text})
                                    st.rerun()
                                else:
                                    st.error("❌ 구글 AI 통신망 릴레이 연결이 일시적으로 거부되었습니다.")
                            except Exception as chat_err:
                                st.error(f"❌ 챗봇 엔진 작동 오류: {chat_err}")
else:
    st.info("구글 마스터 스프레드를 연결하는 중...")