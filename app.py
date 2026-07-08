import streamlit as st
import pandas as pd
import datetime
import urllib.parse
import requests
import base64
import os

# ======================================================================
# 1. 페이지 및 레이아웃 설정
# ======================================================================
st.set_page_config(
    page_title="Smart Maintenance Pro", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

def get_base64_encoded_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return f"data:image/jpeg;base64,{base64.b64encode(img_file.read()).decode()}"
    return "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?q=80&w=1600"

encoded_bg = get_base64_encoded_image("정관장 이미지.jpg")
encoded_logo = get_base64_encoded_image("kgc_logo.png")

# ======================================================================
# 2. 🔐 인증 관련 세션 상태 초기화
# ======================================================================
if "auth_step" not in st.session_state:
    st.session_state.auth_step = "login_gate"
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "user_team" not in st.session_state:
    st.session_state.user_team = None
if "user_machine" not in st.session_state:
    st.session_state.user_machine = None
if "temp_logs" not in st.session_state:
    st.session_state.temp_logs = []
if "user_db" not in st.session_state:
    st.session_state.user_db = {"admin": {"password": "1234", "name": "관리자", "sabun": "9999", "team": "설비보전팀"}}

# ======================================================================
# 3. 🎨 [통합 CSS 및 기업형 맥박(Pulse/Ripple) 로딩 인디게이터]
# ======================================================================
global_loader_css = f"""
    <style>
    /* 1. 바깥쪽으로 퍼져나가는 파동(Ripple) 애니메이션 */
    @keyframes corporate-ripple {{
        0% {{ box-shadow: 0 0 0 0 rgba(0, 123, 236, 0.6); }}
        70% {{ box-shadow: 0 0 0 30px rgba(0, 123, 236, 0); }}
        100% {{ box-shadow: 0 0 0 0 rgba(0, 123, 236, 0); }}
    }}
    /* 2. 심장 박동처럼 미세하게 수축/이완하는 애니메이션 */
    @keyframes corporate-beat {{
        0% {{ transform: scale(0.95); }}
        50% {{ transform: scale(1.02); }}
        100% {{ transform: scale(0.95); }}
    }}
    
    /* 버튼 클릭 시 발생하는 전역 스피너 오버레이 */
    div[data-testid="stSpinner"] {{
        position: fixed !important; top: 0; left: 0; width: 100vw; height: 100vh;
        background-color: rgba(0, 0, 0, 0.7) !important; backdrop-filter: blur(4px); z-index: 99999 !important; display: flex !important; justify-content: center !important; align-items: center !important;
    }}
    div[data-testid="stSpinner"] > div > svg {{ display: none !important; }}
    div[data-testid="stSpinner"] > div {{ color: white !important; font-size: 1.1rem !important; font-weight: bold !important; display: flex !important; flex-direction: column !important; align-items: center !important; gap: 30px !important; }}
    
    /* 실제 로고가 담기는 원형 아이콘 컨테이너 */
    div[data-testid="stSpinner"] > div::before {{ 
        content: ""; display: block; width: 110px; height: 110px; 
        background-color: #ffffff; border-radius: 50%;
        background-image: url("{encoded_logo}"); background-repeat: no-repeat; background-position: center; background-size: 70%; 
        animation: corporate-beat 1.5s infinite ease-in-out, corporate-ripple 1.5s infinite; 
    }}
    
    /* 페이지 이동 시 발생하는 시스템 로딩 오버레이 */
    div[data-testid="stStatusWidget"] {{ position: fixed !important; top: 0 !important; right: 0 !important; bottom: 0 !important; left: 0 !important; width: 100vw !important; height: 100vh !important; background-color: rgba(0,0,0,0.7) !important; backdrop-filter: blur(4px) !important; display: flex !important; justify-content: center !important; align-items: center !important; z-index: 99998 !important; }}
    div[data-testid="stStatusWidget"] * {{ display: none !important; }}
    div[data-testid="stStatusWidget"]::after {{ 
        content: "🔄 시스템 처리 및 데이터 로딩 중..."; 
        display: flex; flex-direction: column; align-items: center; justify-content: flex-end; color: white; font-size: 1.1rem; font-weight: bold; padding-bottom: 20px;
        width: 110px; height: 160px; /* 로고와 텍스트 배치 간격 */
        background-color: transparent;
        background-image: url("{encoded_logo}"); background-repeat: no-repeat; background-position: center top; background-size: 77px; 
    }}
    /* StatusWidget의 로고 부분을 원형 아이콘으로 독립시키기 위한 꼼수 (가상요소 중첩) */
    div[data-testid="stStatusWidget"]::before {{
        content: ""; position: absolute; top: calc(50% - 60px); left: calc(50% - 55px);
        width: 110px; height: 110px; background-color: #ffffff; border-radius: 50%; z-index: -1;
        animation: corporate-beat 1.5s infinite ease-in-out, corporate-ripple 1.5s infinite;
    }}
    </style>
"""
st.markdown(global_loader_css, unsafe_allow_html=True)

if st.session_state.auth_step == "login_gate":
    login_css = f"""
        <style>
        header[data-testid="stHeader"], div[data-testid="stToolbar"] {{ visibility: hidden !important; height: 0px !important; }}
        div[data-testid="stAppViewContainer"] {{ background: linear-gradient(rgba(241, 245, 249, 0.86), rgba(241, 245, 249, 0.86)), url('{encoded_bg}') !important; background-size: cover !important; background-position: center !important; background-attachment: fixed !important; }}
        .main {{ background: transparent !important; }}
        .styled-card {{ background-color: rgba(34, 34, 34, 0.96) !important; border-radius: 8px !important; padding: 30px !important; color: #FFFFFF !important; box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important; margin-top: 5vh; margin-bottom: 5vh; }}
        
        .loading-overlay-intro {{ position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-color: rgba(0, 0, 0, 0.7); backdrop-filter: blur(4px); display: flex; justify-content: center; align-items: center; z-index: 999999; visibility: hidden; flex-direction: column; gap: 30px; color: white; font-size: 1.1rem; font-weight: bold; }}
        .loading-logo-intro {{ 
            width: 110px; height: 110px; background-color: white; border-radius: 50%;
            display: flex; justify-content: center; align-items: center;
            animation: corporate-beat 1.5s infinite ease-in-out, corporate-ripple 1.5s infinite; 
        }}
        .loading-logo-intro img {{ width: 70%; }}
        .loading-active-intro {{ visibility: visible; }}
        </style>
        
        <div class="loading-overlay-intro" id="loadingOverlayIntro">
            <div class="loading-logo-intro">
                <img src="{encoded_logo}" alt="KGC Logo" />
            </div>
            <div>🔄 스마트 앱 엔진 로드 중...</div>
        </div>
        <script>
            window.onload = function() {{
                var overlay = document.getElementById("loadingOverlayIntro");
                if(overlay) {{ overlay.classList.add("loading-active-intro"); setTimeout(function() {{ overlay.classList.remove("loading-active-intro"); }}, 1200); }}
            }};
        </script>
    """
    st.markdown(login_css, unsafe_allow_html=True)
else:
    main_css = f"""
        <style>
        header[data-testid="stHeader"] {{ visibility: hidden !important; height: 0px !important; }}
        div[data-testid="stAppViewContainer"] {{ background: linear-gradient(rgba(241, 245, 249, 0.86), rgba(241, 245, 249, 0.86)), url('{encoded_bg}') !important; background-size: cover !important; background-position: center !important; background-attachment: fixed !important; }}
        .styled-card {{ background-color: rgba(34, 34, 34, 0.96) !important; border-radius: 8px !important; padding: 30px !important; color: #FFFFFF !important; box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important; margin-top: 5vh; margin-bottom: 5vh; }}
        .block-container {{ padding-top: 2.5rem !important; padding-bottom: 1rem !important; max-width: 96% !important; }}
        h1 {{ color: #0F172A !important; font-weight: 800 !important; font-size: 1.8rem !important; border-bottom: 3px solid #007BEC; padding-bottom: 8px; margin-bottom: 15px !important; }}
        div[data-testid="stMetric"] {{ background-color: #FFFFFF !important; border: 1px solid #E2E8F0 !important; border-top: 4px solid #007BEC !important; padding: 0.8rem !important; border-radius: 8px !important; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05) !important; margin-bottom: 8px !important; }}
        div[data-testid="stContainer"] {{ background-color: #FFFFFF !important; border: 1px solid #E2E8F0 !important; padding: 1.2rem !important; border-radius: 8px !important; box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.05) !important; margin-bottom: 15px !important; }}
        .section-title {{ background-color: #E0F2FE; color: #0369A1; padding: 6px 12px; border-radius: 4px; font-weight: 700; font-size: 1rem; margin-bottom: 10px; display: inline-block; }}
        .menu-hero-banner {{ background: linear-gradient(135deg, #007BEC 0%, #0059B2 100%); color: #FFFFFF !important; padding: 1rem !important; border-radius: 8px !important; margin-bottom: 15px !important; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1) !important; }}
        </style>
    """
    st.markdown(main_css, unsafe_allow_html=True)

# ======================================================================
# 4. 데이터 로드 및 통신 모듈
# ======================================================================
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8/export?format=csv&gid=0"
if "MACRO_URL" in st.secrets:
    LIVE_MACRO_URL = st.secrets["MACRO_URL"]
    LIVE_SHEET_NAME = st.secrets.get("SHEET_NAME", "시트1")
else:
    LIVE_MACRO_URL = ""
    LIVE_SHEET_NAME = "시트1"

def update_google_sheet(sheet_id, sheet_name, row_idx, col_idx, new_value):
    if not LIVE_MACRO_URL: return False
    try:
        params = {"id": sheet_id, "sheet": sheet_name, "row": int(row_idx + 2), "col": int(col_idx + 1), "val": new_value}
        requests.get(LIVE_MACRO_URL, params=params, timeout=5)
        return True
    except: return False

@st.cache_data(ttl=5)
def load_data(url):
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        return df
    except: return None

df = load_data(SHEET_CSV_URL)

if df is not None:
    col_list = list(df.columns)
    c_id, c_mach, c_name, c_mat, c_life_m, c_life_h, c_curr_h = col_list[0:7]
    idx_manual, idx_stock, idx_install = 7, 8, 9
    c_manual = col_list[idx_manual]
    c_stock = col_list[idx_stock]
    c_install_date = col_list[idx_install] if len(col_list) > 9 else col_list[-1]

    df[c_stock] = pd.to_numeric(df[c_stock], errors='coerce').fillna(0).astype(int)
    df[c_curr_h] = pd.to_numeric(df[c_curr_h], errors='coerce').fillna(0).astype(int)
    df[c_life_h] = pd.to_numeric(df[c_life_h], errors='coerce').fillna(0).astype(int)
    df[c_life_m] = pd.to_numeric(df[c_life_m], errors='coerce').fillna(0).astype(int)
    df['남은시간'] = df[c_life_h] - df[c_curr_h]

# ======================================================================
# 📺 [STEP 1] 중앙 정렬 로그인 인터페이스
# ======================================================================
if st.session_state.auth_step == "login_gate":
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown('<div class="styled-card">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center; color:white; font-weight: 800; margin-bottom: 0;'>스마트 정비 앱</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#AAAAAA; margin-bottom: 25px;'>KGC 인삼공사</p>", unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["로그인", "회원가입"])
        with tab1:
            st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
            in_id = st.text_input("아이디", placeholder="아이디를 입력하세요", key="l_id")
            in_pw = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요", key="l_pw")
            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
            if st.button("로그인", type="primary", use_container_width=True):
                user = st.session_state.user_db.get(in_id)
                if user and user["password"] == in_pw:
                    st.session_state.current_user = in_id
                    st.session_state.auth_step = "setup_gate"
                    st.rerun()
                else: st.error("❌ 등록되지 않은 정보이거나 패스워드가 올바르지 않습니다.")
                    
        with tab2:
            st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
            reg_id = st.text_input("신규아이디", placeholder="등록할 신규 아이디", key="field_id_reg")
            reg_pw = st.text_input("신규비밀번호", type="password", placeholder="등록할 비밀번호", key="field_pw_reg")
            reg_pw_c = st.text_input("신규확인", type="password", placeholder="비밀번호 재입력 확인", key="field_pwc_reg")
            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
            if st.button("신청서 제출", use_container_width=True, key="action_register_submit"):
                if not reg_id or not reg_pw: st.error("❌ 생성할 아이디 및 패스워드를 입력해 주세요.")
                elif reg_id in st.session_state.user_db: st.error("❌ 이미 발급되었거나 사용 중인 아이디입니다.")
                elif reg_pw != reg_pw_c: st.error("❌ 패스워드 확인 입력값이 일치하지 않습니다.")
                else:
                    st.session_state.user_db[reg_id] = {"password": reg_pw, "name": "신규등록자", "sabun": "0000", "team": "미배정"}
                    st.success("✅ 가입 신청이 수락되었습니다. 탭을 이동하여 로그인해 주십시오.")
        st.markdown('</div>', unsafe_allow_html=True)

# ======================================================================
# ⚙️ [STEP 2] 단계별 공정 선택 및 기기(이미지) 라우팅 스크린
# ======================================================================
elif st.session_state.auth_step == "setup_gate":
    col1, col2, col3 = st.columns([0.5, 3, 0.5])
    with col2:
        st.markdown('<div class="styled-card" style="padding: 40px !important;">', unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center; color: white; margin-bottom: 30px;'>🏭 스마트 공정 및 라인 라우팅 설정</h3>", unsafe_allow_html=True)
        
        current_user_info = st.session_state.user_db.get(st.session_state.current_user, {})
        user_display_name = current_user_info.get("name", st.session_state.current_user)
        st.write(f"✅ **접속자 승인 계정:** `{user_display_name} ({st.session_state.current_user})`")
        st.markdown("<hr style='border-color: #555; margin-bottom: 25px;'>", unsafe_allow_html=True)
        
        step_col1, step_col2 = st.columns(2)
        with step_col1: factory = st.selectbox("1️⃣ 공장 선택", ["선택해주세요", "부여공장", "원주공장"])
        with step_col2:
            if factory == "부여공장": dept = st.selectbox("2️⃣ 부서 선택", ["선택해주세요", "제품 1팀", "제품 2팀", "품질부", "시설에너지관리 팀", "홍삼부"])
            else: dept = "선택해주세요"
                
        line = "선택해주세요"
        prod = "선택해주세요"
        if factory == "부여공장" and dept == "제품 1팀":
            step_col3, step_col4 = st.columns(2)
            with step_col3: line = st.selectbox("3️⃣ 라인 선택", ["선택해주세요", "미니병", "액상", "고형제", "스틱"])
            with step_col4:
                if line == "미니병": prod = st.selectbox("4️⃣ 세부 제품군 선택", ["선택해주세요", "활삼", "액상", "바이알"])
                    
            if line == "미니병" and prod == "바이알":
                st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
                st.markdown("<h4 style='color: #007BEC; text-align: center; margin-bottom: 20px; font-weight: 800;'>5️⃣ 대상 기기 선택 (아래 이미지를 클릭하세요)</h4>", unsafe_allow_html=True)
                
                machines = [
                    {"name": "병 정렬기", "img": "https://images.unsplash.com/photo-1589792923962-537704632910?w=400&q=80"},
                    {"name": "세병기", "img": "https://images.unsplash.com/photo-1584916201218-f4242ceb4809?w=400&q=80"},
                    {"name": "충전기", "img": "https://images.unsplash.com/photo-1615811361523-6bd03d7748e7?w=400&q=80"},
                    {"name": "캡핑기", "img": "https://images.unsplash.com/photo-1563720224244-67d1655ce24c?w=400&q=80"},
                    {"name": "살균기", "img": "https://images.unsplash.com/photo-1585435421671-0c16764628ce?w=400&q=80"},
                    {"name": "레이블", "img": "https://images.unsplash.com/photo-1507560461415-99731cfa9ac8?w=400&q=80"},
                    {"name": "수거로봇", "img": "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?w=400&q=80"}
                ]
                
                img_cols = st.columns(4, gap="medium")
                for i, mach in enumerate(machines):
                    with img_cols[i % 4]:
                        st.image(mach["img"], use_container_width=True)
                        if st.button(f"⚙️ {mach['name']}", key=f"btn_mach_{i}", use_container_width=True):
                            st.session_state.user_team = f"{factory} {dept} {line} {prod}"
                            st.session_state.user_machine = mach["name"]
                            st.session_state.auth_step = "main_app"
                            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ======================================================================
# 📊 [STEP 3] 기기 전용 맞춤형 스마트 관제 대시보드
# ======================================================================
elif st.session_state.auth_step == "main_app":
    # ---------------------------------------------------------
    # [데이터 필터링 및 더미 데이터 안전장치]
    # ---------------------------------------------------------
    selected_mach = st.session_state.user_machine
    
    mach_df = df[df[c_mach] == selected_mach].copy() if df is not None else pd.DataFrame()
    
    if mach_df.empty:
        dummy_data = {
            c_id: ['D001', 'D002', 'D003', 'D004'],
            c_mach: [selected_mach] * 4,
            c_name: ['베어링', 'O-ring', '노즐', '실린더'],
            c_mat: ['합금강', '고무', '스테인리스', '알루미늄'],
            c_life_m: [12, 6, 24, 36],
            c_life_h: [8000, 4000, 15000, 20000],
            c_curr_h: [7500, 3900, 5000, 19500],
            c_manual: ['http://example.com'] * 4,
            idx_stock: [1, 5, 2, 0],
            c_install_date: ['2023-01-01', '2023-06-01', '2022-01-01', '2021-01-01'],
            '남은시간': [500, 100, 10000, 500]
        }
        df_cols = list(df.columns) if df is not None and not df.empty else list(dummy_data.keys())
        mach_df = pd.DataFrame(dummy_data)
        mach_df.rename(columns={idx_stock: c_stock}, inplace=True)
        st.info("💡 안내: 현재 구글 시트에 해당 기계의 데이터가 없어, 화면 시연을 위해 임시 부품 데이터(베어링, O-ring 등)를 띄웠습니다.")

    # ---------------------------------------------------------
    # [화면 상단 UI 랜더링]
    # ---------------------------------------------------------
    nav_col1, nav_col2 = st.columns([8, 2])
    with nav_col1: st.caption(f"🔧 소속: {st.session_state.user_team} | 인증 책임자: {st.session_state.current_user}")
    with nav_col2:
        if st.button("🔒 라우팅 재설정 (뒤로가기)", use_container_width=True):
            st.session_state.auth_step = "setup_gate"
            st.rerun()

    st.title(f"🖥️ [{selected_mach}] 실시간 관제 대시보드")

    with st.expander(f"🏷️ 선택된 기계 명판: 바이알 {selected_mach} - (주)이수이엔지", expanded=False):
        n_col1, n_col2 = st.columns(2)
        n_col1.markdown(f"**관리번호:** `MGT-2026-{hash(selected_mach) % 1000:03d}`")
        n_col1.markdown("**프로덕션 이어 (제조년도):** `2024년`")
        n_col2.markdown(f"**모델명:** `ISU-V-{selected_mach[:2]}-X1`")
        n_col2.markdown("**제조사:** `(주)이수이엔지`")

    urgent_parts = mach_df[(mach_df['남은시간'] <= 200) | (mach_df[c_stock] <= 2)]
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("현재 작동 상태", "🟢 정상 가동 (NORMAL)")
    m2.metric("실시간 불량률", "0.02%")
    m3.metric("위험 소모품", f"{len(urgent_parts)} 건", delta="-조치 요망", delta_color="inverse")
    m4.metric("등록된 세부 부품", f"{len(mach_df)} 종")
    
    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
    
    # ---------------------------------------------------------
    # [메뉴 탭 구성]
    # ---------------------------------------------------------
    menu_tab1, menu_tab2, menu_tab3, menu_tab4 = st.tabs([
        "📋 1. 부품 상태 및 신품 교체", "📝 2. 정비 일지 기록", "📸 3. AI 카메라 진단", "💬 4. AI 정비 챗봇"
    ])

    with menu_tab1:
        st.markdown(f"""
            <div class='menu-hero-banner'>
                <h3>📋 [{selected_mach}] 세부 부품 자산 관제 및 신품 교체</h3>
                <p>기계 내부 핵심 소모품의 잔여 수명과 재고를 파악하고, 교체 시 데이터를 리셋합니다.</p>
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 1.2], gap="medium")
        
        with col1:
            st.markdown("<span class='section-title'>1️⃣ 세부 부품 선택</span>", unsafe_allow_html=True)
            with st.container():
                part_list = mach_df[c_name].unique()
                selected_part = st.selectbox("🔧 부품명 (베어링, O-ring, 노즐 등)", part_list, key="sl_part_only")
            
            part_info = mach_df[mach_df[c_name] == selected_part].iloc[0]
            real_indices = df[df[c_name] == selected_part].index if df is not None else []
            part_idx = real_indices[0] if len(real_indices) > 0 else -1
            
            st.markdown("<span class='section-title'>2️⃣ 선택 부품 실시간 상태 조회</span>", unsafe_allow_html=True)
            with st.container():
                if pd.notna(part_info.get(c_install_date, None)):
                    raw_install_date = str(part_info[c_install_date]).strip()
                    st.markdown(f"📅 **최초 장착일 :** `{raw_install_date}`")
                    try: parsed_start = datetime.datetime.strptime(raw_install_date, "%Y-%m-%d").date()
                    except: parsed_start = datetime.date.today()
                else:
                    st.markdown("📅 **최초 장착일 :** `기록 없음`")
                    parsed_start = datetime.date.today()

                months_to_add = int(part_info.get(c_life_m, 0))
                year = parsed_start.year + (parsed_start.month + months_to_add - 1) // 12
                month = (parsed_start.month + months_to_add - 1) % 12 + 1
                calculated_replace_date = datetime.date(year, month, min(parsed_start.day, 28))
                
                st.markdown(f"⏳ **차기 권장 교체일 :** `{calculated_replace_date.strftime('%Y-%m-%d')}`")
                st.markdown(f"📦 **보유 재고 :** `{part_info.get(c_stock, 0)} EA`")
                st.markdown(f"⏱️ **가동 런타임 :** `{part_info.get(c_curr_h, 0)} hr` (한계 `{part_info.get(c_life_h, 0)} hr`)")
                
                manual_url = part_info.get(c_manual, "")
                if pd.notna(manual_url) and str(manual_url).strip().startswith("http"):
                    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
                    st.link_button("📄 표준 정비 매뉴얼 열람", manual_url.strip(), type="primary", use_container_width=True)

            with st.expander("⚙️ 예외 변수 수동 수치 보정"):
                new_curr_h = st.number_input("현재 누적 가동 시간 보정", value=int(part_info.get(c_curr_h, 0)), step=10, key="adj_h")
                new_stock = st.number_input("창고 보관 수량 보정", value=int(part_info.get(c_stock, 0)), step=1, key="adj_s")
                if st.button("💾 수치 수동 보정 저장", use_container_width=True):
                    if part_idx != -1:
                        with st.spinner("보전 서버로 보정 값을 전송 중..."):
                            update_google_sheet("1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8", LIVE_SHEET_NAME, part_idx, 6, new_curr_h) 
                            update_google_sheet("1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8", LIVE_SHEET_NAME, part_idx, idx_stock, new_stock) 
                            st.success("✅ 수치 수정 완료")
                            st.cache_data.clear()
                            st.rerun()
                    else:
                        st.warning("⚠️ 시연용 임시 데이터이므로 구글 시트에 저장되지 않습니다.")
                        
        with col2:
            st.markdown("<span class='section-title'>3️⃣ 소모품 교체 및 자산 리셋</span>", unsafe_allow_html=True)
            with st.container():
                chosen_execution_date = st.date_input("📆 교체일 지정", datetime.date.today(), key="exec_date_picker")
                
                if st.button("교체 확정 처리 완료", type="primary", use_container_width=True):
                    if part_info.get(c_stock, 0) <= 0:
                        st.error("❌ 보유 재고가 부족하여 교체 명령을 수행할 수 없습니다.")
                    else:
                        if part_idx != -1:
                            with st.spinner("중앙 ERP 원격 갱신 중..."):
                                update_google_sheet("1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8", LIVE_SHEET_NAME, part_idx, 6, 0)       
                                update_google_sheet("1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8", LIVE_SHEET_NAME, part_idx, idx_stock, int(part_info.get(c_stock, 1)) - 1) 
                                update_google_sheet("1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8", LIVE_SHEET_NAME, part_idx, idx_install, chosen_execution_date.strftime("%Y-%m-%d")) 
                        
                        auto_system_log = {
                            "날짜": chosen_execution_date.strftime("%Y-%m-%d"), 
                            "부품명": selected_part, 
                            "작업자": st.session_state.current_user,
                            "정비내용": f"[{selected_mach}] 신품 교체 완료 및 사이클 리셋."
                        }
                        st.session_state.temp_logs.insert(0, auto_system_log)
                        st.success(f"🎉 [{selected_part}] 신품 장착 및 스케줄링 리셋이 완료되었습니다.")
                        st.balloons()
                        st.cache_data.clear()
                        st.rerun()

            st.markdown("##### ⏱ ... 예상 수명 바")
            current_hours = int(part_info.get(c_curr_h, 0))
            max_hours = int(part_info.get(c_life_h, 1))
            progress_per = max(0, min(100, int((current_hours / max_hours) * 100))) if max_hours > 0 else 0
            st.progress(progress_per, text=f"수명 소모 진척도: {progress_per}%")
            
            st.markdown("---")
            st.subheader("📱 하드웨어 식별용 스마트 QR코드 라벨")
            app_url = "https://vial-manager-na6qyzsytdcsencg2jwr89.streamlit.app/"
            qr_link = f"{app_url}?machine={urllib.parse.quote(selected_mach)}&part={urllib.parse.quote(selected_part)}"
            qr_link_enc = urllib.parse.quote(qr_link)
            qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=130x130&data={qr_link_enc}"
            
            q_col1, q_col2 = st.columns([1, 2.5])
            with q_col1: st.image(qr_api_url, caption="정비 태그 QR")
            with q_col2: st.code(qr_link)

    with menu_tab2:
        st.markdown(f"""
            <div class='menu-hero-banner'>
                <h3>📝 [{selected_mach}] 전용 정비 일지 기록</h3>
                <p>수행한 보전 내역, 고장 처리 및 유격 조정 조치 사항을 기록합니다.</p>
            </div>
        """, unsafe_allow_html=True)
        
        log_col1, log_col2 = st.columns([1, 1.2], gap="medium")
        
        with log_col1:
            st.markdown("<span class='section-title'>1️⃣ 정비 내역 서식 작성</span>", unsafe_allow_html=True)
            with st.container():
                log_date = st.date_input("정비 및 작업 실행 일자", datetime.date.today(), key="m_log_date")
                
                log_part = st.selectbox("정비 부품 선택", mach_df[c_name].unique(), key="m_log_part")
                
                current_user_name = st.session_state.user_db.get(st.session_state.current_user, {}).get("name", st.session_state.current_user)
                auto_worker_info = f"{st.session_state.user_team} / {current_user_name}"
                
                log_worker = st.text_input("작업원 (자동기입)", value=auto_worker_info, disabled=True, key="m_log_worker")
                
                log_content = st.text_area("상세 정비 작업 내용", placeholder="예: 구동 기어 유격 측정 후 중심 정렬 및 볼트 고정 록타이트 처리.", key="m_log_content")
                
                st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
                if st.button("🚀 정비 이력 제출", type="primary", use_container_width=True, key="m_log_submit_btn"):
                    if not log_content:
                        st.warning("⚠️ 상세 정비 내용을 입력해 주십시오.")
                    else:
                        with st.spinner("작업 일지 데이터를 안전하게 저장 중..."):
                            new_log_entry = {"날짜": log_date.strftime("%Y-%m-%d"), "부품명": f"[{selected_mach}] {log_part}", "작업자": auto_worker_info, "정비내용": log_content}
                            st.session_state.temp_logs.insert(0, new_log_entry)
                            st.success(f"✅ 정비 이력이 타임라인에 세팅되었습니다.")
                            st.rerun()
        
        with log_col2:
            st.markdown("<span class='section-title'>2️⃣ 최근 정비 내역 이력</span>", unsafe_allow_html=True)
            with st.container():
                base_logs = [{"날짜": "2026-07-01", "부품명": f"[{selected_mach}] 센서부", "작업자": "시스템관리자", "정비내용": "스마트 예지정비 모니터링 제어실 연동 상태 확인."}]
                display_logs = st.session_state.temp_logs + base_logs
                st.dataframe(pd.DataFrame(display_logs), use_container_width=True, hide_index=True)

    with menu_tab3:
        st.markdown(f"""
            <div class='menu-hero-banner'>
                <h3>📸 AI 카메라 (비전 진단)</h3>
                <p>[{selected_mach}] 부품의 사진을 올리시면 인공지능이 마모 및 손상도를 진단합니다.</p>
            </div>
        """, unsafe_allow_html=True)
        
        vision_api_key = st.secrets.get("GEMINI_API_KEY", "")
        if vision_api_key: st.success("🟢 클라우드 공용 AI 보안 엔진 연동 완료.")
        else: st.error("⚠️ GEMINI_API_KEY를 설정해주세요.")
        
        v_col1, v_col2 = st.columns([1, 1.2], gap="medium")
        
        with v_col1:
            st.markdown("<span class='section-title'>1️⃣ 하드웨어 이미지 입력</span>", unsafe_allow_html=True)
            with st.container():
                input_mode = st.radio("사진 획득 방식", ["📱 카메라 촬영", "📁 파일 업로드"], key="vision_mode")
                captured_file = st.camera_input("외관 비추기") if input_mode == "📱 카메라 촬영" else st.file_uploader("이미지 선택", type=["jpg", "png"], key="file_vision")
                    
                if captured_file is not None:
                    st.image(captured_file, caption="🛠️ AI 분석 대상 이미지", width=360)
        
        with v_col2:
            st.markdown("<span class='section-title'>2️⃣ AI 비전 실시간 진단 결과</span>", unsafe_allow_html=True)
            if captured_file is None:
                st.info("💡 안내: 사진을 등록하면 분석이 활성화됩니다.")
            else:
                if st.button("🚀 이미지 비전 해독 분석 시작", type="primary", use_container_width=True):
                    with st.spinner("AI 픽셀 분석 중..."):
                        try:
                            import google.generativeai as genai
                            from PIL import Image
                            genai.configure(api_key=vision_api_key)
                            pil_image = Image.open(captured_file)
                            context_prompt = f"너는 제조 공장의 기계 정비 마스터야. 이 사진은 '{selected_mach}'의 부품일 가능성이 높아. 마모, 균열 등을 정밀 진단하고 예방 조치안을 한국어로 보고서 형태로 써줘."
                            vision_model = genai.GenerativeModel('gemini-2.5-flash')
                            ai_response = vision_model.generate_content([context_prompt, pil_image])
                            st.success("사진 해독이 성공적으로 완료되었습니다!")
                            st.write(ai_response.text)
                        except Exception as error_msg:
                            st.error(f"❌ AI 분석 모듈 오류: {error_msg}")

    with menu_tab4:
        st.markdown(f"""
            <div class='menu-hero-banner'>
                <h3>💬 AI 챗봇</h3>
                <p>[{selected_mach}] 구동부 트러블슈팅 및 기계공학 솔루션을 논의합니다.</p>
            </div>
        """, unsafe_allow_html=True)
        
        chat_api_key = st.secrets.get("GEMINI_API_KEY", "")
            
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = [{"role": "assistant", "content": f"안녕하세요! [{selected_mach}] 전담 정비봇입니다. 애로사항을 말씀해 주세요!"}]
            
        st.markdown("<span class='section-title'>💬 1:1 대화 챗봇</span>", unsafe_allow_html=True)
        with st.container():
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]): st.write(msg["content"])
                
        if user_prompt := st.chat_input(f"{selected_mach}의 문제 상황을 타이핑하세요"):
            with st.chat_message("user"): st.write(user_prompt)
            st.session_state.chat_history.append({"role": "user", "content": user_prompt})
            
            if not chat_api_key: st.error("❌ GEMINI_API_KEY 누락.")
            else:
                with st.chat_message("assistant"):
                    with st.spinner("해결 방안 도출 중..."):
                        try:
                            import google.generativeai as genai
                            genai.configure(api_key=chat_api_key)
                            system_instruction = f"너는 {selected_mach} 설비 전문 수석 엔지니어 보전원이야. 해결책을 조항별로 실천적으로 한국어로 설명해."
                            c_model = genai.GenerativeModel('gemini-2.5-flash')
                            bot_reply = c_model.generate_content([system_instruction, user_prompt])
                            st.write(bot_reply.text)
                            st.session_state.chat_history.append({"role": "assistant", "content": bot_reply.text})
                            st.rerun()
                        except Exception as chat_err:
                            st.error(f"❌ 챗봇 엔진 오류: {chat_err}")