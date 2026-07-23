import base64
import datetime
import os
import time
import urllib.parse

import pandas as pd
import streamlit as st
from supabase import create_client

# ======================================================================
# 상수: Supabase 테이블 및 컬럼
# ======================================================================
TABLE_MACHINES = "machines"
TABLE_SPARE_PARTS = "spare_parts"
TABLE_MAINTENANCE_LOGS = "maintenance_logs"

SP_ID = "id"
SP_MACHINE = "machine_name"
SP_PART = "part_name"
SP_SPEC = "spec"
SP_LIFE_M = "life_m"  
SP_MANUAL = "manual_url"
SP_STOCK = "stock"

ML_DATE = "log_date"
ML_MACHINE = "machine_name"
ML_PART = "part_name"
ML_WORKER = "worker_name"  
ML_CONTENT = "content"

# ======================================================================
# Supabase 연결 및 데이터 레이어
# ======================================================================
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"].rstrip("/")
    if url.endswith("/rest/v1"):
        url = url[: -len("/rest/v1")]
    return create_client(url, st.secrets["SUPABASE_KEY"])

@st.cache_data(ttl=10)
def load_machines():
    try:
        response = init_supabase().table(TABLE_MACHINES).select("*").execute()
        return pd.DataFrame(response.data)
    except Exception:
        return pd.DataFrame()

# ======================================================================
# 권한 및 인증
# ======================================================================
def is_authenticated():
    return st.session_state.get("user") is not None

def is_manager():
    """로그인한 유저가 '시설에너지관리팀' 이거나 '마스터 관리자'인지 확인"""
    user = st.session_state.get("user")
    if not user:
        return False
        
    email = user.get("email", "").lower()
    team = user.get("team", "")
    
    if "admin" in email or "master" in email:
        return True
    if team == "시설에너지관리팀":
        return True
        
    return False

def store_auth_user(response):
    user = response.user
    if not user:
        return False
    metadata = user.user_metadata or {}
    st.session_state["user"] = {
        "id": user.id,
        "email": user.email,
        "display_name": metadata.get("display_name") or (user.email or "").split("@")[0],
        "factory": metadata.get("factory", ""),
        "team": metadata.get("team", "")
    }
    return True

def auth_sign_in(email, password):
    try:
        response = init_supabase().auth.sign_in_with_password({"email": email, "password": password})
        return True, response, None
    except Exception as exc:
        return False, None, str(exc)

def auth_sign_up(email, password, name, factory, team):
    try:
        payload = {
            "email": email, 
            "password": password,
            "options": {
                "data": {
                    "display_name": name,
                    "factory": factory,
                    "team": team
                }
            }
        }
        response = init_supabase().auth.sign_up(payload)
        return True, response, None
    except Exception as exc:
        return False, None, str(exc)

def auth_sign_out():
    try:
        init_supabase().auth.sign_out()
    except Exception:
        pass
    st.session_state["user"] = None
    st.session_state["auth_step"] = "login_gate"
    st.session_state["user_team"] = None
    st.session_state["user_machine"] = None

def get_worker_name():
    user = st.session_state.get("user")
    if not user:
        return "미인증 사용자"
        
    email = user.get("email", "").lower()
    name = user.get("display_name") or email.split("@")[0]
    factory = user.get("factory", "")
    team = user.get("team", "")
    
    if "admin" in email or "master" in email:
        return f"[👑 마스터 관리자] {name}"
        
    if factory and team:
        return f"[{factory}] {team} / {name}"
    return name

def require_login_message():
    st.warning("🔒 로그인이 필요합니다. 로그인 후 이용해 주세요.")

def _execute(action):
    try:
        action()
        return True, None
    except Exception as exc:
        return False, str(exc)

@st.cache_data(ttl=5)
def load_spare_parts():
    try:
        response = init_supabase().table(TABLE_SPARE_PARTS).select("*").execute()
        df = pd.DataFrame(response.data)
        if df.empty:
            return df
        for col in (SP_STOCK, SP_LIFE_M):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        return df
    except Exception:
        return None

def insert_spare_part(record):
    return _execute(lambda: init_supabase().table(TABLE_SPARE_PARTS).insert(record).execute())

def update_spare_part(part_id, updates):
    return _execute(lambda: init_supabase().table(TABLE_SPARE_PARTS).update(updates).eq(SP_ID, part_id).execute())

@st.cache_data(ttl=5)
def load_maintenance_logs(machine_name=None):
    try:
        query = init_supabase().table(TABLE_MAINTENANCE_LOGS).select("*")
        if machine_name:
            query = query.eq(ML_MACHINE, machine_name)
        response = query.order(ML_DATE, desc=True).order("id", desc=True).execute() 
        return pd.DataFrame(response.data)
    except Exception:
        return pd.DataFrame()

def insert_maintenance_log(record):
    return _execute(lambda: init_supabase().table(TABLE_MAINTENANCE_LOGS).insert(record).execute())

def display_maintenance_logs(machine_name):
    logs_df = load_maintenance_logs(machine_name)
    if logs_df.empty:
        st.info("등록된 정비 일지가 없습니다.")
        return
    column_map = {ML_DATE: "날짜", ML_PART: "부품명", ML_WORKER: "작업자", ML_CONTENT: "정비내용"}
    available = [col for col in column_map if col in logs_df.columns]
    display_df = logs_df[available].rename(columns=column_map)
    st.dataframe(display_df, use_container_width=True, hide_index=True)

def get_machine_parts_df(all_parts_df, machine_name):
    if all_parts_df is None or all_parts_df.empty or SP_MACHINE not in all_parts_df.columns:
        return pd.DataFrame()
    return all_parts_df[all_parts_df[SP_MACHINE] == machine_name].copy()

# ======================================================================
# UI 유틸리티 
# ======================================================================
def get_base64_encoded_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return f"data:image/png;base64,{base64.b64encode(img_file.read()).decode()}"
    return None

def init_session_state():
    defaults = {"auth_step": "login_gate", "user": None, "user_team": None, "user_machine": None}
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# 로그인 전용 스타일 (정관장 배경 사진 + 깔끔한 불투명 박스)
def render_login_css(encoded_bg):
    st.markdown(
        f"""
        <style>
        header[data-testid="stHeader"], div[data-testid="stToolbar"] {{ visibility: hidden !important; }}
        
        /* 배경 설정: 정관장 이미지 위에 은은한 어두운 필터 */
        div[data-testid="stAppViewContainer"] {{ 
            background: linear-gradient(rgba(10, 10, 15, 0.55), rgba(10, 10, 15, 0.65)), url('{encoded_bg}') !important; 
            background-size: cover !important; 
            background-position: center !important; 
            background-attachment: fixed !important; 
        }}
        
        /* 로그인 중앙 카드 디자인 */
        .styled-card {{ 
            background-color: rgba(30, 30, 35, 0.88) !important; 
            border: 1px solid rgba(255, 255, 255, 0.08) !important; 
            border-radius: 16px !important; 
            padding: 40px !important; 
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.5) !important; 
            margin-top: 5vh;
        }}
        
        h1, h2, h3, h4, p, span, label, div {{ color: #F8FAFC !important; font-family: 'Pretendard', sans-serif; }}
        
        div[data-baseweb="input"] {{ background-color: #1E1E24 !important; border: 1px solid #4A4A55 !important; border-radius: 8px !important; }}
        div[data-baseweb="input"] input {{ color: #FFFFFF !important; }}
        
        div[data-testid="stButton"] button {{ border-radius: 8px !important; font-weight: bold; background-color: #3B82F6 !important; color: white !important; border: none !important; }}
        div[data-testid="stButton"] button:hover {{ background-color: #2563EB !important; }}
        </style>
        """, unsafe_allow_html=True
    )

def render_main_css():
    st.markdown(
        f"""
        <style>
        div[data-testid="stAppViewContainer"] {{ background-color: #FFFFFF !important; }}
        header[data-testid="stHeader"] {{ visibility: hidden !important; height: 0px !important; }}
        .block-container {{ padding-top: 0rem !important; padding-bottom: 15rem !important; max-width: 1100px !important; }}
        
        h1, h2, h3, h4, p, span, label, div {{ color: #1E293B !important; font-family: 'Pretendard', sans-serif; }}
        
        .styled-card {{ 
            background-color: #F8F9FA !important; 
            border: 1px solid #E9ECEF !important; 
            border-radius: 12px !important; 
            padding: 40px !important; 
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px -1px rgba(0, 0, 0, 0.01) !important; 
            margin-bottom: 30px;
        }}
        
        div[data-testid="stMetric"] {{ background-color: #FFFFFF !important; border: 1px solid #E2E8F0 !important; border-top: 4px solid #6B8E7B !important; padding: 0.8rem !important; border-radius: 12px !important; box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important; margin-bottom: 8px !important; }}
        div[data-testid="stButton"] button {{ border-radius: 8px !important; font-weight: bold; }}
        
        @keyframes alert-pulse {{
            0% {{ box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.3); }}
            70% {{ box-shadow: 0 0 0 10px rgba(220, 38, 38, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(220, 38, 38, 0); }}
        }}
        </style>
        """, unsafe_allow_html=True
    )

def render_hero_banner():
    hero_b64 = get_base64_encoded_image("KGC Smart MRO.png")
    if hero_b64:
        st.markdown(
            f"""
            <div style="width: 100%; display: flex; justify-content: center; align-items: center; padding: 3rem 1rem; margin-bottom: 2rem; background-color: #6B8E7B; border-radius: 0 0 20px 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
                <img src="{hero_b64}" style="max-height: 80px; width: auto; object-fit: contain;">
            </div>
            """, unsafe_allow_html=True
        )

# ======================================================================
# 로그인 & 회원가입 화면 (안정적인 카드 UI)
# ======================================================================
def render_login_screen():
    logo_b64 = get_base64_encoded_image("KGC Smart MRO.png")
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<div class="styled-card">', unsafe_allow_html=True)
        
        if logo_b64:
            st.markdown(f'''
                <div style="text-align:center; margin-bottom: 25px; background-color: rgba(255, 255, 255, 0.95); padding: 20px; border-radius: 8px;">
                    <img src="{logo_b64}" style="max-width: 200px; width: 100%; object-fit: contain;">
                </div>
            ''', unsafe_allow_html=True)
            
        tab_login, tab_register = st.tabs(["로그인", "회원가입"])
        
        with tab_login:
            login_email = st.text_input("이메일", key="login_email_input", placeholder="user@kgc.com")
            login_pw = st.text_input("비밀번호", type="password", key="login_pw_input")
            if st.button("로그인", type="primary", use_container_width=True):
                with st.spinner("로그인 중..."):
                    ok, response, err = auth_sign_in(login_email.strip(), login_pw)
                    if ok and store_auth_user(response):
                        st.session_state.auth_step = "setup_gate"
                        st.rerun()
                    else: 
                        st.error("❌ 로그인 실패. 아이디와 비밀번호를 확인하세요.")
                        
        with tab_register:
            reg_email = st.text_input("가입 이메일", key="reg_email_input", placeholder="user@kgc.com")
            reg_pw = st.text_input("비밀번호", type="password", key="reg_pw_input")
            
            st.markdown("---")
            st.markdown("#### 개인 및 소속 정보")
            reg_name = st.text_input("성명", key="reg_name_input", placeholder="홍길동")
            
            reg_factory = st.selectbox("소속 공장", ["선택해주세요", "부여공장", "원주공장"])
            
            reg_team = "선택해주세요"
            if reg_factory == "부여공장":
                reg_team = st.selectbox("소속 팀", ["선택해주세요", "제품1팀", "제품2팀", "시설에너지관리팀", "공정개선팀", "지원팀", "산업안전 보건팀"])
            elif reg_factory == "원주공장":
                reg_team = st.selectbox("소속 팀", ["선택해주세요", "생산팀", "시설에너지관리팀", "지원팀"])
            else:
                st.info("👆 공장을 먼저 선택하시면 팀 목록이 표시됩니다.")

            if st.button("회원가입 완료", use_container_width=True):
                if reg_factory == "선택해주세요" or reg_team == "선택해주세요" or not reg_name.strip():
                    st.warning("⚠️ 성명, 소속 공장 및 팀을 모두 선택해주세요.")
                else:
                    with st.spinner("가입 처리 중..."):
                        ok, response, err = auth_sign_up(reg_email.strip(), reg_pw, reg_name.strip(), reg_factory, reg_team)
                        if ok:
                            st.success("✅ 회원가입 완료! 로그인 탭에서 접속해주세요.")
                        else: 
                            st.error(f"❌ 가입 실패: {err}")
                        
        st.markdown("</div>", unsafe_allow_html=True)

# ======================================================================
# 시설에너지관리팀 전용 통합 관제 센터 화면
# ======================================================================
def render_manager_dashboard(all_parts_df):
    if not is_authenticated(): return require_login_message()

    nav_col1, nav_col2 = st.columns([8, 2])
    with nav_col2:
        if st.button("⬅️ 작업 라우팅 화면으로", use_container_width=True):
            st.session_state.auth_step = "setup_gate"
            st.rerun()

    user = st.session_state["user"]
    email = user.get("email", "").lower()
    is_master = "admin" in email or "master" in email
    
    title_text = "👑 마스터 관리자 통합 관제 센터" if is_master else "🛠️ 시설에너지관리팀 통합 관제 센터"

    st.markdown(f"<div style='background-color: #F1F5F9; padding: 25px; border-radius: 12px; border-left: 6px solid #6B8E7B; margin-bottom: 30px;'><h2 style='margin:0; padding:0; color:#334155;'>{title_text}</h2><p style='margin-top:8px; color:#64748B;'>전체 설비의 실시간 상태를 모니터링하고 정비 요청에 즉각 대응합니다.</p></div>", unsafe_allow_html=True)

    df_machines = load_machines()
    if df_machines.empty:
        st.error("데이터베이스에 등록된 기계가 없습니다.")
        return

    all_logs_df = load_maintenance_logs()

    def get_machine_status(mach_name):
        if all_logs_df is not None and not all_logs_df.empty:
            m_logs = all_logs_df[all_logs_df[ML_MACHINE] == mach_name]
            if not m_logs.empty:
                latest_log = m_logs.iloc[0]
                if "[정비 요청]" in str(latest_log[ML_CONTENT]):
                    return "🚨 긴급 정비 요청됨", "#FEF2F2", "#DC2626", "border: 1px solid #FCA5A5; animation: alert-pulse 1.5s infinite;"

        if all_parts_df is not None and not all_parts_df.empty: 
            m_parts = all_parts_df[all_parts_df[SP_MACHINE] == mach_name]
            if not m_parts.empty:
                urgent_parts = m_parts[m_parts[SP_STOCK] <= 2]
                if not urgent_parts.empty:
                    return "⚠️ 부품 재고 부족", "#FFFBEB", "#B45309", "border: 1px solid #FDE68A;"
        
        return "🟢 정상 가동", "#FFFFFF", "#475569", "border: 1px solid #E2E8F0;"

    departments = sorted(df_machines["dept"].dropna().unique())

    for dept in departments:
        st.markdown(f"<h3 style='margin-top: 30px; border-bottom: 2px solid #E2E8F0; padding-bottom: 10px; color: #475569;'>🏢 {dept}</h3>", unsafe_allow_html=True)
        dept_machines = df_machines[df_machines["dept"] == dept]
        
        lines = sorted(dept_machines["line"].dropna().unique())
        for line in lines:
            st.markdown(f"<h5 style='color: #94A3B8; margin-top:15px; margin-bottom:10px;'>📍 라인: {line}</h5>", unsafe_allow_html=True)
            line_machines = dept_machines[dept_machines["line"] == line]
            
            cols = st.columns(4)
            for i, (_, row) in enumerate(line_machines.iterrows()):
                mach_name = row["machine_name"]
                status_text, bg_color, text_color, border_style = get_machine_status(mach_name)
                
                with cols[i % 4]:
                    card_html = f"""
                    <div style="background-color: {bg_color}; {border_style} border-radius: 12px; padding: 20px; margin-bottom: 15px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
                        <h4 style="margin: 0; color: #1E293B; font-size: 1.05rem; font-weight: 700;">{mach_name}</h4>
                        <div style="margin: 12px 0 0 0; padding: 6px; border-radius: 6px; background-color: rgba(255,255,255,0.8); font-weight: bold; color: {text_color}; font-size: 0.95rem;">
                            {status_text}
                        </div>
                    </div>
                    """
                    st.markdown(card_html, unsafe_allow_html=True)
                    
                    if st.button(f"🔍 점검하기", key=f"mgr_btn_{mach_name}_{i}", use_container_width=True):
                        st.session_state.user_team = f"관제센터 ({dept})"
                        st.session_state.user_machine = mach_name
                        st.session_state.auth_step = "main_app"
                        st.rerun()

# ======================================================================
# 라우팅(공정 선택) 화면
# ======================================================================
def render_setup_screen():
    if not is_authenticated(): return require_login_message()
    
    render_hero_banner()
    
    col1, col2, col3 = st.columns([0.5, 3, 0.5])
    with col2:
        user = st.session_state["user"]
        
        if is_manager():
            email = user.get("email", "").lower()
            is_master = "admin" in email or "master" in email
            
            menu_title = "👑 마스터 최고 관리자 전용 메뉴" if is_master else "🛠️ 시설에너지관리팀 전용 메뉴"
            btn_title = "👑 마스터 통합 관제 센터 입장" if is_master else "🚨 통합 관제 센터 입장"
            
            st.markdown(f"""
                <div style="background-color: #F8FAFC; border: 1px solid #CBD5E1; padding: 20px; border-radius: 12px; margin-bottom: 30px; border-left: 6px solid #6B8E7B;">
                    <h3 style='margin-top: 0; margin-bottom: 15px; color: #334155;'>{menu_title}</h3>
            """, unsafe_allow_html=True)
            col_m1, col_m2, col_m3 = st.columns([1,2,1])
            with col_m2:
                if st.button(btn_title, type="primary", use_container_width=True):
                    st.session_state.auth_step = "manager_dashboard"
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown('<div class="styled-card">', unsafe_allow_html=True)
        st.markdown("<h3 style='color: #0F172A; margin-bottom: 20px; border-bottom: 2px solid #E2E8F0; padding-bottom: 10px;'>작업 공정 및 기기 라우팅</h3>", unsafe_allow_html=True)

        worker_info = get_worker_name()
        st.caption(f"👤 현재 접속자: **{worker_info}**")
        
        df_machines = load_machines()
        if df_machines.empty or "factory" not in df_machines.columns:
            st.error("🚧 데이터베이스에 등록된 설비가 없습니다.")
            if st.button("🚪 로그아웃", use_container_width=True):
                auth_sign_out()
                st.rerun()
            return st.markdown("</div>", unsafe_allow_html=True)

        step_col1, step_col2 = st.columns(2)
        with step_col1:
            factory_options = ["선택해주세요"] + sorted(df_machines["factory"].dropna().unique().tolist())
            selected_factory = st.selectbox("1️⃣ 소속 공장", factory_options)
        with step_col2:
            if selected_factory != "선택해주세요":
                dept_options = ["선택해주세요"] + sorted(df_machines[df_machines["factory"] == selected_factory]["dept"].dropna().unique().tolist())
                selected_dept = st.selectbox("2️⃣ 담당 부서", dept_options)
            else: selected_dept = "선택해주세요"

        if selected_dept != "선택해주세요":
            line_options = ["선택해주세요"] + sorted(df_machines[(df_machines["factory"] == selected_factory) & (df_machines["dept"] == selected_dept)]["line"].dropna().unique().tolist())
            step_col3, step_col4 = st.columns(2)
            with step_col3:
                selected_line = st.selectbox("3️⃣ 생산 라인", line_options)
            if selected_line != "선택해주세요":
                mach_list = df_machines[(df_machines["factory"] == selected_factory) & (df_machines["dept"] == selected_dept) & (df_machines["line"] == selected_line)]["machine_name"].dropna().tolist()
                with step_col4: st.success(f"✅ 총 {len(mach_list)}대의 설비 확인됨")

                st.markdown(f"<h4 style='color: #6B8E7B; margin: 30px 0 15px; font-weight: 700;'>4️⃣ 정비 대상 기기 선택</h4>", unsafe_allow_html=True)
                img_cols = st.columns(4, gap="medium")
                for i, mach_name in enumerate(mach_list):
                    mach_info = df_machines[df_machines["machine_name"] == mach_name].iloc[0]
                    img_url = mach_info.get("machine_image_url")
                    with img_cols[i % 4]:
                        if pd.notna(img_url) and str(img_url).strip().startswith("http"):
                            st.markdown(f"""<div style="width:100%; aspect-ratio:16/9; background-image:url('{img_url}'); background-size:cover; background-position:center; border:1px solid #E2E8F0; border-radius:8px; margin-bottom:12px; box-shadow: 0 2px 4px rgba(0,0,0,0.03);"></div>""", unsafe_allow_html=True)
                        else:
                            st.markdown("""<div style="width:100%; aspect-ratio:16/9; background:#F8FAFC; border:1px dashed #CBD5E1; border-radius:8px; margin-bottom:12px; display:flex; justify-content:center; align-items:center;"><span style="color:#94A3B8; font-size:0.8rem;">사진 없음</span></div>""", unsafe_allow_html=True)
                        
                        if st.button(f"⚙️ {mach_name}", key=f"btn_mach_{i}", use_container_width=True):
                            st.session_state.user_team = f"{selected_factory} / {selected_dept} / {selected_line}"
                            st.session_state.user_machine = mach_name
                            st.session_state.auth_step = "main_app"
                            st.rerun()
        
        st.markdown("<hr style='border-color: #E2E8F0; margin: 30px 0;'>", unsafe_allow_html=True)
        if st.button("🚪 로그아웃", use_container_width=True):
            auth_sign_out()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ======================================================================
# 탭 1 ~ 5 (기존 정비 기능)
# ======================================================================
def render_tab_parts(mach_df, selected_mach):
    if not is_authenticated(): return
    if mach_df.empty:
        st.warning("⚠️ 이 기계에 등록된 부품이 없습니다. [신규 등록] 탭에서 부품을 먼저 추가해주세요.")
        return

    worker_name = get_worker_name()
    col1, col2 = st.columns([1, 1.2], gap="medium")

    with col1:
        st.markdown("<span class='section-title' style='color:#6B8E7B; font-weight:700;'>1️⃣ 세부 부품 선택</span>", unsafe_allow_html=True)
        selected_part = st.selectbox("부품명", mach_df[SP_PART].unique(), key="sl_part_only")
        part_info = mach_df[mach_df[SP_PART] == selected_part].iloc[0]
        part_id = part_info.get(SP_ID)

        logs_df = load_maintenance_logs(selected_mach)
        recent_replace_date = "기록 없음"
        if not logs_df.empty:
            replace_logs = logs_df[(logs_df[ML_PART] == selected_part) & (logs_df[ML_CONTENT].str.contains("교체|리셋", na=False))]
            if not replace_logs.empty:
                recent_replace_date = replace_logs.iloc[0][ML_DATE]

        st.markdown("<br><span class='section-title' style='color:#6B8E7B; font-weight:700;'>2️⃣ 실시간 상태 조회</span>", unsafe_allow_html=True)
        st.markdown(f"📅 **최근 교체일 :** `{recent_replace_date}`")
        st.markdown(f"📦 **보유 재고 :** `{part_info.get(SP_STOCK, 0)} EA`")
        
        with st.expander("⚙️ 창고 보관 수량 수동 보정"):
            new_stock = st.number_input("창고 보관 수량 보정", value=int(part_info.get(SP_STOCK, 0)), step=1, key="adj_s")
            if st.button("💾 수치 보정 저장", use_container_width=True):
                ok, err = update_spare_part(part_id, {SP_STOCK: new_stock})
                if ok:
                    insert_maintenance_log({ML_DATE: datetime.date.today().strftime("%Y-%m-%d"), ML_MACHINE: selected_mach, ML_PART: selected_part, ML_WORKER: worker_name, ML_CONTENT: f"재고 수량 보정: {new_stock} EA"})
                    st.toast("✅ 보정 완료", icon="💾")
                    time.sleep(1)
                    st.cache_data.clear()
                    st.rerun()
                else: st.error(f"❌ 수정 실패: {err}")

    with col2:
        st.markdown("<span class='section-title' style='color:#6B8E7B; font-weight:700;'>3️⃣ 소모품 교체 및 사이클 리셋</span>", unsafe_allow_html=True)
        chosen_date = st.date_input("📆 교체일 지정", datetime.date.today(), key="exec_date_picker")
        if st.button("🚀 교체 확정 처리 완료", type="primary", use_container_width=True):
            if part_info.get(SP_STOCK, 0) <= 0: st.error("❌ 재고 부족. 창고 보관 수량을 확인하세요.")
            else:
                ok, err = update_spare_part(part_id, {SP_STOCK: int(part_info.get(SP_STOCK, 1)) - 1})
                if ok:
                    insert_maintenance_log({ML_DATE: chosen_date.strftime("%Y-%m-%d"), ML_MACHINE: selected_mach, ML_PART: selected_part, ML_WORKER: worker_name, ML_CONTENT: "신품 교체 완료 및 사이클 리셋."})
                    st.toast("✅ 신품 교체 기록 완료", icon="🔄")
                    time.sleep(1)
                    st.cache_data.clear()
                    st.rerun()
                else: st.error(f"❌ 교체 처리 실패: {err}")

def render_tab_maintenance_logs(mach_df, selected_mach):
    if not is_authenticated(): return
    worker_name = get_worker_name()
    log_col1, log_col2 = st.columns([1, 1.2], gap="medium")
    with log_col1:
        log_date = st.date_input("정비 일자", datetime.date.today())
        part_options = mach_df[SP_PART].unique() if not mach_df.empty else ["부품 없음"]
        log_part = st.selectbox("정비 부품", part_options)
        log_content = st.text_area("작업 내용")
        if st.button("🚀 정비 이력 제출", type="primary", use_container_width=True):
            if log_content.strip() and log_part != "부품 없음":
                insert_maintenance_log({ML_DATE: log_date.strftime("%Y-%m-%d"), ML_MACHINE: selected_mach, ML_PART: log_part, ML_WORKER: worker_name, ML_CONTENT: log_content.strip()})
                st.toast("✅ 일지 기록 완료", icon="📝")
                time.sleep(1)
                st.cache_data.clear()
                st.rerun()
            else: st.warning("내용을 입력하고 부품을 선택하세요.")
    with log_col2: display_maintenance_logs(selected_mach)

def render_tab_vision(selected_mach):
    if not is_authenticated(): return
    try: vision_api_key = st.secrets["GEMINI_API_KEY"]
    except KeyError:
        st.error("🚨 서버에 GEMINI_API_KEY가 설정되지 않았습니다. 관리자에게 문의하세요.")
        return
    input_mode = st.radio("사진 획득 방법", ["카메라 촬영", "파일 업로드"])
    captured_file = st.camera_input("카메라") if input_mode == "카메라 촬영" else st.file_uploader("사진 선택", type=['jpg', 'jpeg', 'png'])
    if captured_file and st.button("🚀 AI 비전 해독 시작", type="primary"):
        with st.spinner("이미지 분석 중입니다..."):
            try:
                import google.generativeai as genai
                from PIL import Image
                genai.configure(api_key=vision_api_key)
                vision_model = genai.GenerativeModel("gemini-1.5-flash") 
                img = Image.open(captured_file)
                prompt = f"이 사진은 [{selected_mach}] 기계의 부품 또는 상태를 찍은 것입니다. 현재 상태를 진단하고 혹시 파손, 마모, 이상 증상이 있는지 한국어로 전문적으로 설명해주세요."
                resp = vision_model.generate_content([prompt, img])
                st.success("✅ AI 진단 완료")
                st.write(resp.text)
            except Exception as e: st.error(f"오류가 발생했습니다: {e}")

def render_tab_chat(selected_mach):
    if not is_authenticated(): return
    try: chat_api_key = st.secrets["GEMINI_API_KEY"]
    except KeyError:
        st.error("🚨 서버에 GEMINI_API_KEY가 설정되지 않았습니다. 관리자에게 문의하세요.")
        return
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [{"role": "assistant", "content": f"안녕하세요! [{selected_mach}] 전담 정비 어시스턴트입니다. 무엇을 도와드릴까요?"}]
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]): st.write(msg["content"])
    if user_prompt := st.chat_input("정비 관련 질문을 입력하세요"):
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"): st.write(user_prompt)
        with st.chat_message("assistant"):
            with st.spinner("AI가 답변을 작성 중입니다..."):
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=chat_api_key)
                    chat_model = genai.GenerativeModel("gemini-1.5-flash")
                    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.chat_history[:-1]])
                    system_prompt = f"너는 공장 설비 [{selected_mach}] 전문 엔지니어이자 정비 도우미야. 작업자의 질문에 친절하고 전문적으로 한국어로 대답해줘.\n\n이전 대화:\n{history_text}\n\n사용자: {user_prompt}"
                    bot_reply = chat_model.generate_content(system_prompt)
                    st.write(bot_reply.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": bot_reply.text})
                except Exception as e: st.error(f"오류가 발생했습니다: {e}")

def render_tab_register_part(selected_mach):
    if not is_authenticated(): return
    worker_name = get_worker_name()
    reg_col1, reg_col2 = st.columns([1, 1.2], gap="medium")
    with reg_col1:
        reg_name = st.text_input("부품명 (part_name)")
        reg_spec = st.text_input("규격/재질 (spec)")
    with reg_col2:
        reg_life_m = st.number_input("권장 수명 (월)", min_value=0, value=12)
        reg_stock = st.number_input("초기 재고 (EA)", min_value=0, value=1)
        if st.button("📥 신규 부품 등록", type="primary", use_container_width=True):
            if reg_name.strip():
                new_record = {
                    SP_MACHINE: selected_mach, 
                    SP_PART: reg_name.strip(), 
                    SP_SPEC: reg_spec.strip() or None, 
                    SP_LIFE_M: int(reg_life_m), 
                    SP_STOCK: int(reg_stock)
                }
                with st.spinner("저장 중..."):
                    ok, err = insert_spare_part(new_record)
                    if ok:
                        insert_maintenance_log({ML_DATE: datetime.date.today().strftime("%Y-%m-%d"), ML_MACHINE: selected_mach, ML_PART: reg_name.strip(), ML_WORKER: worker_name, ML_CONTENT: f"신규 부품 등록: {reg_name.strip()}"})
                        st.toast("✅ 부품 등록 완료", icon="📥")
                        time.sleep(1)
                        st.cache_data.clear()
                        st.rerun()
                    else: st.error(f"❌ 데이터베이스 오류: {err}")

# ======================================================================
# 탭 6: SOP 매뉴얼 (보안 탭 - 캡쳐, 저장, 우클릭 방지)
# ======================================================================
def render_tab_sop(selected_mach):
    if not is_authenticated(): return
    st.markdown(f"<h3 style='color:#334155; margin-bottom:20px;'>📖 [{selected_mach}] 표준 작업 지침서 (SOP)</h3>", unsafe_allow_html=True)
    
    st.markdown("""
        <style>
        .secure-sop-container {
            position: relative;
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 40px;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);
            -webkit-user-select: none;
            -moz-user-select: none;
            -ms-user-select: none;
            user-select: none;
        }
        .watermark-overlay {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) rotate(-30deg);
            font-size: 4rem;
            font-weight: 900;
            color: rgba(107, 142, 123, 0.08); 
            pointer-events: none; 
            white-space: nowrap;
            z-index: 999;
        }
        </style>
        
        <div class="secure-sop-container">
            <div class="watermark-overlay">KGC MRO CONFIDENTIAL</div>
            
            <h4 style="color:#1E293B; border-bottom:2px solid #F1F5F9; padding-bottom:8px;">1. 작업 전 확인 사항</h4>
            <ul style="color:#475569; line-height:1.8;">
                <li>작업자는 반드시 규정된 보호구(안전모, 안전화 등)를 착용해야 합니다.</li>
                <li>기계 주변에 인화성 물질이나 장애물이 없는지 육안으로 확인합니다.</li>
                <li>컨베이어 및 구동부 연결 상태를 점검합니다.</li>
            </ul>
            
            <h4 style="color:#1E293B; border-bottom:2px solid #F1F5F9; padding-bottom:8px; margin-top:30px;">2. 정상 가동 (기동) 절차</h4>
            <ul style="color:#475569; line-height:1.8;">
                <li>메인 전원 차단기를 [ON] 위치로 전환합니다.</li>
                <li>제어 패널에서 시스템 [초기화(Reset)] 버튼을 누릅니다.</li>
                <li>오류 알람이 발생하지 않는지 30초간 대기하며 패널을 모니터링합니다.</li>
                <li>[운전(Start)] 버튼을 눌러 공정을 시작합니다.</li>
            </ul>

            <h4 style="color:#1E293B; border-bottom:2px solid #F1F5F9; padding-bottom:8px; margin-top:30px;">3. 비상 상황 발생 시 조치</h4>
            <ul style="color:#475569; line-height:1.8;">
                <li>기계적 소음, 타는 냄새, 혹은 패널에 빨간 경고등이 켜질 경우 <b>즉시 [비상정지(EMG)] 버튼</b>을 누릅니다.</li>
                <li>현장 통제 후, MRO 앱을 통해 <b>[시설에너지관리팀 긴급 호출]</b>을 진행합니다.</li>
                <li>임의로 기계를 분해하거나 조작하지 않습니다.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.info("🔒 **보안 정책 안내:** 본 SOP 문서는 기업 대외비로 분류되어 시스템적으로 마우스 우클릭, 텍스트 드래그 및 복사가 전면 차단되어 있습니다.")

# ======================================================================
# 메인 대시보드 (작업자 화면)
# ======================================================================
def render_dashboard(all_parts_df):
    if not is_authenticated(): return
    selected_mach = st.session_state.user_machine
    mach_df = get_machine_parts_df(all_parts_df, selected_mach)

    nav_col1, nav_col2, nav_col3 = st.columns([6, 2, 2])
    with nav_col1: st.caption(f"🔧 작업자: {get_worker_name()} | 기기: {selected_mach}")
    with nav_col2:
        if st.button("⬅️ 상위 메뉴로 이동", use_container_width=True):
            if is_manager():
                st.session_state.auth_step = "manager_dashboard"
            else:
                st.session_state.auth_step = "setup_gate"
            st.rerun()
    with nav_col3:
        if st.button("🚪 로그아웃", use_container_width=True):
            auth_sign_out()
            st.rerun()

    st.markdown(f"<h2 style='color:#1E293B; margin-top:10px;'>🖥️ [{selected_mach}] 실시간 대시보드</h2>", unsafe_allow_html=True)
    
    df_machines = load_machines()
    mach_info_row = df_machines[df_machines["machine_name"] == selected_mach]
    machine_img_url = mach_info_row.iloc[0].get("machine_image_url") if not mach_info_row.empty else None

    all_logs_df = load_maintenance_logs(selected_mach)
    is_requested = False
    if not all_logs_df.empty:
        latest_log = all_logs_df.iloc[0]
        if "[정비 요청]" in str(latest_log[ML_CONTENT]):
            is_requested = True

    current_production = "12,500" 
    defect_rate_percent = 3.8 
    avg_defect_percent = 1.5  
    is_defect_warning = defect_rate_percent > avg_defect_percent 

    img_col, metric_col = st.columns([1.2, 2.8], gap="large")
    with img_col:
        if pd.notna(machine_img_url) and str(machine_img_url).strip().startswith("http"):
            st.markdown(f"""<div style="width:100%; aspect-ratio:16/9; background-image:url('{machine_img_url}'); background-size:cover; background-position:center; border-radius:12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);"></div>""", unsafe_allow_html=True)
        else: st.info("📷 기기 사진이 없습니다.")
        
    with metric_col:
        m1, m2, m3, m4 = st.columns(4)
        
        m1.metric("기계 상태", "🟢 운전중")
        m2.metric("현재 생산량", f"{current_production} 개")
        
        if is_defect_warning:
            m3.markdown(f"""
                <div style='background-color:#FEF2F2; border:2px solid #DC2626; padding:0.8rem; border-radius:12px; animation: alert-pulse 1.5s infinite; box-shadow: 0 2px 4px rgba(0,0,0,0.02); margin-bottom:8px;'>
                    <div style='color:#DC2626; font-size:0.8rem; font-weight:600;'>🚨 불량률 증가</div>
                    <div style='color:#DC2626; font-size:1.6rem; font-weight:900;'>{defect_rate_percent}%</div>
                </div>
            """, unsafe_allow_html=True)
        else:
            m3.metric("불량률", f"{defect_rate_percent}%", delta="정상범위" if not is_defect_warning else "")
            
        urgent_count = len(mach_df[mach_df[SP_STOCK] <= 2]) if not mach_df.empty else 0
        m4.metric("위험 소모품", f"{urgent_count} 건", delta="-조치 요망" if urgent_count > 0 else "", delta_color="inverse")

        st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)
        
        if is_requested:
            if st.button("✅ 정비 완료 (시설팀 호출 해제)", type="primary", use_container_width=True):
                worker_name = get_worker_name()
                ok, err = insert_maintenance_log({
                    ML_DATE: datetime.date.today().strftime("%Y-%m-%d"), 
                    ML_MACHINE: selected_mach, 
                    ML_PART: "기기 전체", 
                    ML_WORKER: worker_name, 
                    ML_CONTENT: "[조치 완료] 시설팀 정비가 완료되어 호출을 해제합니다."
                })
                if ok:
                    st.toast("✅ 정상 가동 상태로 복귀했습니다.", icon="✅")
                    time.sleep(1)
                    st.cache_data.clear()
                    st.rerun()
        else:
            if st.button("🚨 시설에너지관리팀 긴급 호출 (정비 요청)", type="primary", use_container_width=True):
                worker_name = get_worker_name()
                ok, err = insert_maintenance_log({
                    ML_DATE: datetime.date.today().strftime("%Y-%m-%d"), 
                    ML_MACHINE: selected_mach, 
                    ML_PART: "기기 전체", 
                    ML_WORKER: worker_name, 
                    ML_CONTENT: "[정비 요청] 현장 작업자가 긴급 정비를 요청했습니다."
                })
                if ok:
                    st.toast("🚨 관리팀으로 출동 요청이 전송되었습니다!", icon="🚨")
                    time.sleep(1)
                    st.cache_data.clear()
                    st.rerun()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📋 자산 관제 및 교체", "📝 정비 일지 기록", "📸 AI 진단", "💬 AI 챗봇", "📥 신규 등록", "📖 SOP 메뉴얼"])
    with tab1: render_tab_parts(mach_df, selected_mach)
    with tab2: render_tab_maintenance_logs(mach_df, selected_mach)
    with tab3: render_tab_vision(selected_mach)
    with tab4: render_tab_chat(selected_mach)
    with tab5: render_tab_register_part(selected_mach)
    with tab6: render_tab_sop(selected_mach)

def main():
    init_session_state()
    encoded_bg = get_base64_encoded_image("정관장 이미지.jpg")
    
    if not is_authenticated():
        st.session_state.auth_step = "login_gate"
        render_login_css(encoded_bg)
        render_login_screen()
        return
        
    render_main_css()
    all_parts_df = load_spare_parts()
    
    if st.session_state.auth_step == "setup_gate": 
        render_setup_screen()
    elif st.session_state.auth_step == "manager_dashboard":
        render_manager_dashboard(all_parts_df)
    elif st.session_state.auth_step == "main_app": 
        render_dashboard(all_parts_df)
    else:
        st.session_state.auth_step = "setup_gate"
        render_setup_screen()

main()