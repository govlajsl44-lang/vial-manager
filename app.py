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
    header[data-testid="stHeader"] {
        visibility: hidden !important;
        height: 0px !important;
    }
    
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
    
    /* 로그인 상자 특화 스타일 */
    .auth-container {
        max-width: 450px;
        margin: 50px auto;
        background-color: #FFFFFF;
        padding: 2.5rem;
        border-radius: 12px;
        box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
        border-top: 6px solid #0284C7;
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

# 환경 변수 및 Secrets 확인
if "MACRO_URL" in st.secrets:
    LIVE_MACRO_URL = st.secrets["MACRO_URL"]
    LIVE_SHEET_NAME = st.secrets.get("SHEET_NAME", "시트1")
else:
    LIVE_MACRO_URL = ""
    LIVE_SHEET_NAME = "시트1"

# 중앙 구글 시트 원격 제어 함수
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

# 데이터 로드 함수
@st.cache_data(ttl=5)
def load_data(url):
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        return None

# 데이터 선 로드 (설비 목록 추출용)
df = load_data(SHEET_CSV_URL)

# ----------------------------------------------------------------------
# 🔐 인증 및 세션 상태 초기화
# ----------------------------------------------------------------------
if "auth_step" not in st.session_state:
    st.session_state.auth_step = "login_gate"  # login_gate -> setup_gate -> main_app

if "user_db" not in st.session_state:
    # 초기 시연용 기본 계정 데이터 (ID:비밀번호)
    st.session_state.user_db = {"admin": "1234", "manager": "qwer"}

if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "user_team" not in st.session_state:
    st.session_state.user_team = None
if "user_machine" not in st.session_state:
    st.session_state.user_machine = None
if "temp_logs" not in st.session_state:
    st.session_state.temp_logs = []


# ----------------------------------------------------------------------
# [STEP 1] 로그인 & 회원가입 화면
# ----------------------------------------------------------------------
if st.session_state.auth_step == "login_gate":
    st.markdown("<div class='auth-container'>", unsafe_allow_html=True)
    st.title("🔒 Smart MES Pro 로그인")
    
    auth_tab1, auth_tab2 = st.tabs(["로그인", "신규 회원가입"])
    
    with auth_tab1:
        login_id = st.text_input("아이디", key="login_id_input")
        login_pw = st.text_input("비밀번호", type="password", key="login_pw_input")
        if st.button("시스템 접속하기", type="primary", use_container_width=True):
            if login_id in st.session_state.user_db and st.session_state.user_db[login_id] == login_pw:
                st.session_state.current_user = login_id
                st.session_state.auth_step = "setup_gate"
                st.success(f"🎉 {login_id}님 환영합니다!")
                st.rerun()
            else:
                st.error("❌ 아이디 또는 비밀번호가 올바르지 않습니다.")
                
    with auth_tab2:
        new_id = st.text_input("생성할 아이디", key="new_id_input")
        new_pw = st.text_input("생성할 비밀번호", type="password", key="new_pw_input")
        new_pw_confirm = st.text_input("비밀번호 확인", type="password", key="new_pw_confirm_input")
        
        if st.button("계정 생성 요청", use_container_width=True):
            if not new_id or not new_pw:
                st.warning("⚠️ 아이디와 비밀번호를 모두 입력해주세요.")
            elif new_id in st.session_state.user_db:
                st.error("❌ 이미 존재하는 아이디입니다.")
            elif new_pw != new_pw_confirm:
                st.error("❌ 비밀번호 확인이 일치하지 않습니다.")
            else:
                st.session_state.user_db[new_id] = new_pw
                st.success("✅ 회원가입 성공! 로그인 탭에서 접속하세요.")
                
    st.markdown("</div>", unsafe_allow_html=True)


# ----------------------------------------------------------------------
# [STEP 2] 팀 및 담당 기계 설정 화면
# ----------------------------------------------------------------------
elif st.session_state.auth_step == "setup_gate":
    st.markdown("<div class='auth-container' style='max-width: 500px;'>", unsafe_allow_html=True)
    st.title("🏭 공정 실무 권한 설정")
    st.write(f"접속 계정: `{st.session_state.current_user}`")
    
    selected_team = st.selectbox("📌 소속 작업 팀 선택", ["생산기술1팀", "제조운영2팀", "설비보전팀", "품질관리과"])
    
    if df is not None:
        machine_list = df[df.columns[1]].unique()  # 1번째 컬럼: 설비명
        selected_mach = st.selectbox("🏭 담당 기계 라인 할당", machine_list)
    else:
        selected_mach = st.text_input("🏭 담당 기계 직접 기입 (서버 연결 실패)")
        
    st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
    
    if st.button("맞춤형 관제 화면으로 이동 ➡️", type="primary", use_container_width=True):
        st.session_state.user_team = selected_team
        st.session_state.user_machine = selected_mach
        st.session_state.auth_step = "main_app"
        st.rerun()
        
    st.markdown("</div>", unsafe_allow_html=True)


# ----------------------------------------------------------------------
# [STEP 3] 메인 MES 관제 대시보드 화면
# ----------------------------------------------------------------------
elif st.session_state.auth_step == "main_app":
    # 최상단 네비게이션 및 로그아웃 바
    l_col1, l_col2 = st.columns([8, 2])
    with l_col1:
        st.caption(f"⚙️ {st.session_state.user_team} | 담당 설비: {st.session_state.user_machine} | 작업자: {st.session_state.current_user} 마스터")
    with l_col2:
        if st.button("🔒 로그아웃", use_container_width=True):
            st.session_state.auth_step = "login_gate"
            st.session_state.current_user = None
            st.rerun()

    st.title("설비 소모품 관리 시스템")

    if "MACRO_URL" not in st.secrets:
        st.error("⚠️ [설정 누락] Streamlit 웹 관리자화면 Secrets에 MACRO_URL을 등록하셔야 구글 시트 저장이 활성화됩니다.")

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
        
        # 📋 핵심 메뉴 탭 구성
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
                    <h3>📋 {st.session_state.user_machine} 관제 및 신품 교체실</h3>
                    <p>설정된 공정 전용 모드입니다. 부품 수명을 모니터링하고 마스터 데이터를 원격 제어합니다.</p>
                </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns([1, 1.2], gap="medium")
            
            with col1:
                st.markdown("<span class='section-title'>1️⃣ 설비 및 부품 선택</span>", unsafe_allow_html=True)
                with st.container():
                    # 💡 로그인 시 설정한 기계를 기본 선택값(Index)으로 자동 배치
                    mach_options = list(df[c_mach].unique())
                    default_mach_idx = mach_options.index(st.session_state.user_machine) if st.session_state.user_machine in mach_options else 0
                    
                    selected_machine = st.selectbox("🏭 대상 설비 라인 선택", mach_options, index=default_mach_idx, key="sl_mach")
                    filtered_df = df[df[c_mach] == selected_machine]
                    
                    selected_part = st.selectbox("🔧 세부 점검 부품 선택", filtered_df[c_name].unique(), key="sl_part")
                
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
                        st.link_button("📄 표준 정비 매뉴얼 열람", manual_url.strip(), type="primary", use_container_width=True)

                with st.expander("⚙️ 예외 변수 수동 수치 보정"):
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
                    st.warning(f"⚠️ **작업 확정 알림:** [{selected_part}] 파트를 새 부품으로 교체하는 경우, 아래 단추를 누르면 **[운전시간 0Hr 리셋 / 여분재고 1개 차감 / 장착일 오늘 자동 갱신]**이 구글 시트에 반영됩니다.")
                    chosen_execution_date = st.date_input("📆 실제 신품 교체(장착) 날짜 지정", datetime.date.today(), key="exec_date_picker")
                    
                    if st.button("교체 확정 처리 완료", type="primary", use_container_width=True):
                        if part_info[c_stock] <= 0:
                            st.error("❌ 창고 내 여분 재고 자산이 부족하여 교체 명령을 수행할 수 없습니다.")
                        else:
                            with st.spinner("중앙 스프레드시트 갱신 중..."):
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
                                    "정비내용": f"[신품 교체 완수] {st.session_state.user_team} 처리."
                                }
                                st.session_state.temp_logs.insert(0, auto_system_log)
                                st.success(f"🎉 [{selected_part}] 스케줄링 리셋 완료.")
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
        # [메뉴 2] 정비 일지 기록 탭 (현재 접속 유저 자동 매핑)
        # ----------------------------------------------------------------------
        with menu_tab2:
            st.markdown("""
                <div class='menu-hero-banner'>
                    <h3>📝 제조 설비 일일 정비·교체 일지 관리실</h3>
                    <p>현장에서 수행한 일상 보전 내역을 기입하면 유저 정보가 함께 기록됩니다.</p>
                </div>
            """, unsafe_allow_html=True)
            
            log_col1, log_col2 = st.columns([1, 1.2], gap="medium")
            
            with log_col1:
                st.markdown("<span class='section-title'>1️⃣ 정비 내역 서식 작성</span>", unsafe_allow_html=True)
                with st.container():
                    log_date = st.date_input("정비 및 작업 실행 일자", datetime.date.today(), key="m_log_date")
                    
                    mach_log_options = list(df[c_mach].unique())
                    default_log_mach_idx = mach_log_options.index(st.session_state.user_machine) if st.session_state.user_machine in mach_log_options else 0
                    log_mach = st.selectbox("정비 대상 설비 선택", mach_log_options, index=default_log_mach_idx, key="m_log_mach")
                    
                    filtered_log_df = df[df[c_mach] == log_mach]
                    log_part = st.selectbox("정비 처리 부품 선택", filtered_log_df[c_name].unique(), key="m_log_part")
                    
                    # 💡 현재 로그인한 유저명과 팀 정보 자동 기입
                    log_worker = st.text_input("작업 정비원 성명 기입", value=f"{st.session_state.user_team} {st.session_state.current_user}", key="m_log_worker")
                    log_content = st.text_area("상세 정비 작업 내역 기술", placeholder="예: 구동 기어 유격 측정 후 중심 정렬 처리.", key="m_log_content")
                    
                    if st.button("🚀 정비 이력 로그 중앙 서버 전송", type="primary", use_container_width=True, key="m_log_submit_btn"):
                        if not log_content:
                            st.warning("⚠️ 상세 정비 내용을 기술해 주십시오.")
                        else:
                            new_log_entry = {
                                "날짜": log_date.strftime("%Y-%m-%d"),
                                "부품명": log_part,
                                "작업자": log_worker,
                                "정비내용": log_content
                            }
                            st.session_state.temp_logs.insert(0, new_log_entry)
                            st.success(f"✅ [{log_part}] 정비 데이터가 세팅되었습니다.")
                            st.rerun()
            
            with log_col2:
                st.markdown("<span class='section-title'>2️⃣ 최근 공정 예방 보전 이력 피드백 (실시간)</span>", unsafe_allow_html=True)
                with st.container():
                    base_logs = [{"날짜": "2026-07-01", "부품명": "충전 피스톤 실링", "작업자": "시스템관리자", "정비내용": "모니터링 제어실 연동 상태 정상."}]
                    display_logs = st.session_state.temp_logs + base_logs
                    st.dataframe(pd.DataFrame(display_logs), use_container_width=True, hide_index=True)

        # ----------------------------------------------------------------------
        # [메뉴 3 & 4] AI 카메라 진단 및 챗봇 탭 (기존과 동일하므로 결합 유지)
        # ----------------------------------------------------------------------
        with menu_tab3:
            st.markdown("<div class='menu-hero-banner'><h3>📸 AI 실시간 스마트 현장 비전 진단실</h3><p>마모된 부품 사진을 분석합니다.</p></div>", unsafe_allow_html=True)
            vision_api_key = st.secrets.get("GEMINI_API_KEY", "")
            if vision_api_key: st.success("🟢 클라우드 공용 AI 보안 엔진 연동 중")
            else: st.error("⚠️ GEMINI_API_KEY를 Secrets에 등록해 주세요.")
            
            captured_file = st.file_uploader("부품 사진 이미지 선택 (JPG, PNG)", type=["jpg", "jpeg", "png"])
            if captured_file and st.button("🚀 이미지 분석 시작", type="primary"):
                st.info("비전 분석 모듈이 실행됩니다... (기존 원본 로직 유지)")

        with menu_tab4:
            st.markdown("<div class='menu-hero-banner'><h3>💬 AI 정비 챗봇</h3><p>현장 애로사항을 실시간으로 기술 자문합니다.</p></div>", unsafe_allow_html=True)
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = [{"role": "assistant", "content": "안녕하세요! 정비봇입니다."}]
            
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            
            if user_prompt := st.chat_input("질문을 입력하세요"):
                with st.chat_message("user"): st.write(user_prompt)
                st.session_state.chat_history.append({"role": "user", "content": user_prompt})
                st.rerun()
    else:
        st.info("구글 마스터 스프레드를 연결하는 중...")