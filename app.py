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
SP_LIFE_H = "life_h"
SP_MANUAL = "manual_url"
SP_STOCK = "stock"

ML_DATE = "log_date"
ML_MACHINE = "machine_name"
ML_PART = "part_name"
ML_WORKER = "worker_name"  
ML_CONTENT = "content"

UI_CURRENT_HOURS = "current_hours"
UI_INSTALL_DATE = "install_date"
UI_REMAINING_HOURS = "남은시간"

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
# Supabase Auth
# ======================================================================
def is_authenticated():
    return st.session_state.get("user") is not None

def store_auth_user(response):
    user = response.user
    if not user:
        return False
    metadata = user.user_metadata or {}
    st.session_state["user"] = {
        "id": user.id,
        "email": user.email,
        "display_name": metadata.get("display_name") or (user.email or "").split("@")[0],
    }
    return True

def auth_sign_in(email, password):
    try:
        response = init_supabase().auth.sign_in_with_password({"email": email, "password": password})
        return True, response, None
    except Exception as exc:
        return False, None, str(exc)

def auth_sign_up(email, password, display_name=None):
    try:
        payload = {"email": email, "password": password}
        if display_name:
            payload["options"] = {"data": {"display_name": display_name}}
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
    name = user.get("display_name") or user.get("email", "")
    team = st.session_state.get("user_team")
    return f"{team} / {name}" if team else name

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
        for col in (SP_STOCK, SP_LIFE_H, SP_LIFE_M):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        if UI_CURRENT_HOURS not in df.columns:
            df[UI_CURRENT_HOURS] = 0
        else:
            df[UI_CURRENT_HOURS] = pd.to_numeric(df[UI_CURRENT_HOURS], errors="coerce").fillna(0).astype(int)
        df[UI_REMAINING_HOURS] = df[SP_LIFE_H] - df[UI_CURRENT_HOURS]
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
        response = query.order(ML_DATE, desc=True).execute()
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

def get_demo_data(machine_name):
    return pd.DataFrame({
        SP_ID: ["D001", "D002"],
        SP_MACHINE: [machine_name] * 2,
        SP_PART: ["임시 베어링", "임시 O-ring"],
        SP_SPEC: ["합금강", "고무"],
        SP_LIFE_M: [12, 6],
        SP_LIFE_H: [8000, 4000],
        UI_CURRENT_HOURS: [7500, 3900],
        SP_MANUAL: ["http://example.com"] * 2,
        SP_STOCK: [1, 5],
        UI_INSTALL_DATE: ["2023-01-01", "2023-06-01"],
        UI_REMAINING_HOURS: [500, 100],
    })

def get_machine_parts_df(all_parts_df, machine_name):
    if all_parts_df is None or all_parts_df.empty or SP_MACHINE not in all_parts_df.columns:
        return get_demo_data(machine_name)
    mach_df = all_parts_df[all_parts_df[SP_MACHINE] == machine_name].copy()
    if not mach_df.empty:
        return mach_df
    return get_demo_data(machine_name)

def is_demo_part(part_id):
    return part_id is None or not pd.notna(part_id) or str(part_id).startswith("D")

# ======================================================================
# UI 유틸리티
# ======================================================================
def get_base64_encoded_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return f"data:image/jpeg;base64,{base64.b64encode(img_file.read()).decode()}"
    return "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?q=80&w=1600"

def init_session_state():
    defaults = {"auth_step": "login_gate", "user": None, "user_team": None, "user_machine": None}
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def render_global_css(encoded_logo):
    st.markdown(
        f"""
        <style>
        @keyframes corporate-ripple {{ 0% {{ box-shadow: 0 0 0 0 rgba(0, 123, 236, 0.6); }} 70% {{ box-shadow: 0 0 0 30px rgba(0, 123, 236, 0); }} 100% {{ box-shadow: 0 0 0 0 rgba(0, 123, 236, 0); }} }}
        @keyframes corporate-beat {{ 0% {{ transform: scale(0.95); }} 50% {{ transform: scale(1.02); }} 100% {{ transform: scale(0.95); }} }}
        div[data-testid="stSpinner"] {{ position: fixed !important; top: 0; left: 0; width: 100vw; height: 100vh; background-color: rgba(0, 0, 0, 0.7) !important; backdrop-filter: blur(4px); z-index: 99999 !important; display: flex !important; justify-content: center !important; align-items: center !important; }}
        div[data-testid="stSpinner"] > div > svg {{ display: none !important; }}
        div[data-testid="stSpinner"] > div {{ color: white !important; font-size: 1.1rem !important; font-weight: bold !important; display: flex !important; flex-direction: column !important; align-items: center !important; gap: 30px !important; }}
        div[data-testid="stSpinner"] > div::before {{ content: ""; display: block; width: 110px; height: 110px; background-color: #ffffff; border-radius: 50%; background-image: url("{encoded_logo}"); background-repeat: no-repeat; background-position: center; background-size: 70%; animation: corporate-beat 1.5s infinite ease-in-out, corporate-ripple 1.5s infinite; }}
        </style>
        """, unsafe_allow_html=True
    )

def render_login_css(encoded_bg):
    st.markdown(
        f"""
        <style>
        header[data-testid="stHeader"] {{ visibility: hidden !important; height: 0px !important; }}
        div[data-testid="stAppViewContainer"] {{ background: linear-gradient(rgba(241, 245, 249, 0.86), rgba(241, 245, 249, 0.86)), url('{encoded_bg}') !important; background-size: cover !important; background-position: center !important; background-attachment: fixed !important; }}
        .styled-card {{ background-color: rgba(34, 34, 34, 0.96) !important; border-radius: 8px !important; padding: 30px !important; color: #FFFFFF !important; box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important; margin-top: 5vh; margin-bottom: 5vh; }}
        </style>
        """, unsafe_allow_html=True
    )

def render_main_css(encoded_bg):
    st.markdown(
        f"""
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
        """, unsafe_allow_html=True
    )

# ======================================================================
# 로그인 화면 (이 부분이 누락되어 에러가 났었습니다)
# ======================================================================
def render_login_screen():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown('<div class="styled-card">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center; color:white; font-weight: 800; margin-bottom: 0;'>스마트 정비 앱</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#AAAAAA; margin-bottom: 25px;'>KGC 인삼공사</p>", unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["로그인", "회원가입"])
        with tab_login:
            login_email = st.text_input("이메일", placeholder="example@company.com")
            login_pw = st.text_input("비밀번호", type="password")
            if st.button("로그인", type="primary", use_container_width=True):
                with st.spinner("Supabase Auth 로그인 중..."):
                    ok, response, err = auth_sign_in(login_email.strip(), login_pw)
                    if ok and store_auth_user(response):
                        st.session_state.auth_step = "setup_gate"
                        st.rerun()
                    else: 
                        st.error(f"❌ 로그인 실패: {err}")

        with tab_register:
            reg_email = st.text_input("가입 이메일")
            reg_name = st.text_input("표시 이름")
            reg_pw = st.text_input("등록 비밀번호", type="password")
            if st.button("회원가입", use_container_width=True):
                with st.spinner("회원가입 중..."):
                    ok, response, err = auth_sign_up(reg_email.strip(), reg_pw, reg_name.strip() or None)
                    if ok:
                        if response.user and store_auth_user(response):
                            st.session_state.auth_step = "setup_gate"
                            st.rerun()
                        else: 
                            st.success("✅ 회원가입 신청 완료.")
                    else: 
                        st.error(f"❌ 회원가입 실패: {err}")
        st.markdown("</div>", unsafe_allow_html=True)

# ======================================================================
# 화면: DB 연동형 기기 선택 (사진 출력 기능 복구)
# ======================================================================
def render_setup_screen():
    if not is_authenticated(): 
        return require_login_message()

    col1, col2, col3 = st.columns([0.5, 3, 0.5])
    with col2:
        st.markdown('<div class="styled-card" style="padding: 40px !important;">', unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center; color: white; margin-bottom: 30px;'>🏭 스마트 공정 및 라인 라우팅 설정</h3>", unsafe_allow_html=True)
        
        user = st.session_state["user"]
        st.write(f"✅ **접속자:** `{user['display_name']} ({user['email']})`")
        if st.button("🚪 로그아웃", use_container_width=True):
            auth_sign_out()
            st.rerun()
        st.markdown("<hr style='border-color: #555; margin-bottom: 25px;'>", unsafe_allow_html=True)

        df_machines = load_machines()
        if df_machines.empty or "factory" not in df_machines.columns:
            st.error("🚧 데이터베이스에 등록된 설비가 없습니다.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        step_col1, step_col2 = st.columns(2)
        with step_col1:
            factory_options = ["선택해주세요"] + sorted(df_machines["factory"].dropna().unique().tolist())
            selected_factory = st.selectbox("1️⃣ 공장 선택", factory_options)

        with step_col2:
            if selected_factory != "선택해주세요":
                dept_options = ["선택해주세요"] + sorted(df_machines[df_machines["factory"] == selected_factory]["dept"].dropna().unique().tolist())
                selected_dept = st.selectbox("2️⃣ 부서 선택", dept_options)
            else: 
                selected_dept = "선택해주세요"

        if selected_dept != "선택해주세요":
            line_options = ["선택해주세요"] + sorted(df_machines[(df_machines["factory"] == selected_factory) & (df_machines["dept"] == selected_dept)]["line"].dropna().unique().tolist())
            
            step_col3, step_col4 = st.columns(2)
            with step_col3:
                selected_line = st.selectbox("3️⃣ 생산 라인 선택", line_options)
            
            if selected_line != "선택해주세요":
                mach_data = df_machines[(df_machines["factory"] == selected_factory) & (df_machines["dept"] == selected_dept) & (df_machines["line"] == selected_line)]
                
                with step_col4:
                    st.success(f"✅ 총 {len(mach_data)}대의 설비가 등록되어 있습니다.")

                st.markdown(f"<h4 style='color: #007BEC; text-align: center; margin: 30px 0 20px; font-weight: 800;'>4️⃣ 대상 기기 선택 ({selected_line})</h4>", unsafe_allow_html=True)
                
                img_cols = st.columns(4, gap="medium")
                for i, (_, row) in enumerate(mach_data.iterrows()):
                    mach_name = row["machine_name"]
                    img_url = row.get("machine_image_url", None)
                    
                    with img_cols[i % 4]:
                        if pd.notna(img_url) and str(img_url).strip().startswith("http"):
                            st.markdown(
                                f"""
                                <div style="width:100%; aspect-ratio:16/9; background-image:url('{img_url}'); background-size:cover; background-position:center;
                                border:1px solid rgba(255,255,255,0.2); border-radius:8px; margin-bottom:10px;">
                                </div>
                                """, unsafe_allow_html=True
                            )
                        else:
                            st.markdown(
                                """
                                <div style="width:100%; aspect-ratio:16/9; background:rgba(255,255,255,0.03);
                                border:1px dashed rgba(255,255,255,0.2); border-radius:8px; margin-bottom:10px;
                                display:flex; justify-content:center; align-items:center;">
                                <span style="color:rgba(255,255,255,0.2); font-size:0.8rem;">사진 없음</span></div>
                                """, unsafe_allow_html=True
                            )
                            
                        if st.button(f"⚙️ {mach_name}", key=f"btn_mach_{i}", use_container_width=True):
                            st.session_state.user_team = f"{selected_factory} / {selected_dept} / {selected_line}"
                            st.session_state.user_machine = mach_name
                            st.session_state.auth_step = "main_app"
                            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ======================================================================
# 탭 기능 1~5
# ======================================================================
def render_tab_parts(mach_df, selected_mach):
    worker_name = get_worker_name()
    col1, col2 = st.columns([1, 1.2], gap="medium")
    with col1:
        st.markdown("<span class='section-title'>1️⃣ 세부 부품 선택</span>", unsafe_allow_html=True)
        selected_part = st.selectbox("🔧 부품명", mach_df[SP_PART].unique(), key="sl_part_only")
        part_info = mach_df[mach_df[SP_PART] == selected_part].iloc[0]
        part_id = part_info.get(SP_ID)

        st.markdown("<span class='section-title'>2️⃣ 실시간 상태 조회</span>", unsafe_allow_html=True)
        st.markdown(f"📦 **보유 재고 :** `{part_info.get(SP_STOCK, 0)} EA`")
        st.markdown(f"⏱️ **가동 런타임 :** `{part_info.get(UI_CURRENT_HOURS, 0)} hr`")
        
        with st.expander("⚙️ 예외 변수 수동 수치 보정"):
            new_stock = st.number_input("창고 보관 수량 보정", value=int(part_info.get(SP_STOCK, 0)), step=1)
            if st.button("💾 수치 보정 저장", use_container_width=True):
                if not is_demo_part(part_id):
                    update_spare_part(part_id, {SP_STOCK: new_stock})
                    insert_maintenance_log({
                        ML_DATE: datetime.date.today().strftime("%Y-%m-%d"),
                        ML_MACHINE: selected_mach, ML_PART: selected_part,
                        ML_WORKER: worker_name, ML_CONTENT: f"재고 수량 보정: {new_stock} EA",
                    })
                    st.toast("✅ 수치 보정 완료", icon="💾")
                    time.sleep(1)
                    st.cache_data.clear()
                    st.rerun()

    with col2:
        st.markdown("<span class='section-title'>3️⃣ 소모품 교체 및 자산 리셋</span>", unsafe_allow_html=True)
        chosen_date = st.date_input("📆 교체일 지정", datetime.date.today())
        if st.button("교체 확정 처리 완료", type="primary", use_container_width=True):
            if part_info.get(SP_STOCK, 0) <= 0: 
                st.error("❌ 재고 부족.")
            elif not is_demo_part(part_id):
                update_spare_part(part_id, {SP_STOCK: int(part_info.get(SP_STOCK, 1)) - 1})
                insert_maintenance_log({
                    ML_DATE: chosen_date.strftime("%Y-%m-%d"),
                    ML_MACHINE: selected_mach, ML_PART: selected_part,
                    ML_WORKER: worker_name, ML_CONTENT: "신품 교체 완료.",
                })
                st.toast("✅ 신품 교체 완료", icon="🔄")
                time.sleep(1)
                st.cache_data.clear()
                st.rerun()

def render_tab_maintenance_logs(mach_df, selected_mach):
    worker_name = get_worker_name()
    log_col1, log_col2 = st.columns([1, 1.2], gap="medium")
    with log_col1:
        log_date = st.date_input("작업 일자", datetime.date.today())
        log_part = st.selectbox("정비 부품", mach_df[SP_PART].unique())
        log_content = st.text_area("작업 내용")
        if st.button("🚀 정비 이력 제출", type="primary", use_container_width=True):
            if log_content.strip():
                insert_maintenance_log({
                    ML_DATE: log_date.strftime("%Y-%m-%d"),
                    ML_MACHINE: selected_mach, ML_PART: log_part,
                    ML_WORKER: worker_name, ML_CONTENT: log_content.strip(),
                })
                st.toast("✅ 정비 일지 기록 완료", icon="📝")
                time.sleep(1)
                st.cache_data.clear()
                st.rerun()
            else: 
                st.warning("내용을 입력하세요.")
    with log_col2: 
        display_maintenance_logs(selected_mach)

def render_tab_vision(selected_mach):
    st.info("비전 카메라 모듈 연동 준비 중입니다.")

def render_tab_chat(selected_mach):
    st.info("AI 챗봇 모듈 연동 준비 중입니다.")

def render_tab_register_part(selected_mach):
    worker_name = get_worker_name()
    reg_name = st.text_input("부품명 (part_name)")
    reg_spec = st.text_input("규격 (spec)")
    reg_stock = st.number_input("초기 재고 (EA)", min_value=0, value=1)
    if st.button("📥 신규 부품 등록", type="primary"):
        if reg_name.strip():
            insert_spare_part({
                SP_MACHINE: selected_mach, SP_PART: reg_name.strip(),
                SP_SPEC: reg_spec.strip() or None, SP_LIFE_M: 12, SP_LIFE_H: 0, SP_STOCK: int(reg_stock),
            })
            insert_maintenance_log({
                ML_DATE: datetime.date.today().strftime("%Y-%m-%d"),
                ML_MACHINE: selected_mach, ML_PART: reg_name.strip(),
                ML_WORKER: worker_name, ML_CONTENT: f"신규 등록: {reg_name.strip()}",
            })
            st.toast("✅ 부품 등록 완료", icon="📥")
            time.sleep(1)
            st.cache_data.clear()
            st.rerun()

# ======================================================================
# 메인 대시보드 (기기 사진 출력 기능 복구)
# ======================================================================
def render_dashboard(all_parts_df):
    if not is_authenticated(): 
        return require_login_message()

    selected_mach = st.session_state.user_machine
    user = st.session_state["user"]
    
    df_machines = load_machines()
    mach_info_row = df_machines[df_machines["machine_name"] == selected_mach]
    machine_img_url = mach_info_row.iloc[0].get("machine_image_url") if not mach_info_row.empty else None

    mach_df = get_machine_parts_df(all_parts_df, selected_mach)

    nav_col1, nav_col2, nav_col3 = st.columns([6, 2, 2])
    with nav_col1: 
        st.caption(f"🔧 소속: {st.session_state.user_team} | 작업자: {user['display_name']}")
    with nav_col2:
        if st.button("🔒 라우팅 재설정", use_container_width=True):
            st.session_state.auth_step = "setup_gate"
            st.rerun()
    with nav_col3:
        if st.button("🚪 로그아웃", use_container_width=True):
            auth_sign_out()
            st.rerun()

    st.title(f"🖥️ [{selected_mach}] 실시간 관제 대시보드")

    img_col, metric_col = st.columns([1, 2], gap="large")
    
    with img_col:
        if pd.notna(machine_img_url) and str(machine_img_url).strip().startswith("http"):
            st.image(str(machine_img_url).strip(), use_container_width=True, caption=f"현장 설비 사진: {selected_mach}")
        else:
            st.info("📷 DB에 등록된 현장 기기 사진이 없습니다.")

    with metric_col:
        with st.expander(f"🏷️ 설비 제원 정보", expanded=True):
            n_col1, n_col2 = st.columns(2)
            n_col1.markdown(f"**관리번호:** `MGT-{hash(selected_mach) % 1000:03d}`")
            n_col1.markdown("**제조년도:** `2024년`")
            n_col2.markdown(f"**모델명:** `ISU-X1`")
            n_col2.markdown("**제조사:** `(주)이수이엔지`")

        urgent_parts = mach_df[(mach_df[UI_REMAINING_HOURS] <= 200) | (mach_df[SP_STOCK] <= 2)]
        m1, m2 = st.columns(2)
        m1.metric("현재 작동 상태", "🟢 정상 가동")
        m2.metric("위험 소모품", f"{len(urgent_parts)} 건", delta="-조치 요망", delta_color="inverse")

    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 1. 부품 상태 및 신품 교체", "📝 2. 정비 일지", "📸 3. 비전 진단", "💬 4. AI 챗봇", "📥 5. 부품 등록"
    ])
    with tab1: render_tab_parts(mach_df, selected_mach)
    with tab2: render_tab_maintenance_logs(mach_df, selected_mach)
    with tab3: render_tab_vision(selected_mach)
    with tab4: render_tab_chat(selected_mach)
    with tab5: render_tab_register_part(selected_mach)

# ======================================================================
# 실행
# ======================================================================
st.set_page_config(page_title="Smart Maintenance Pro", layout="wide")
def main():
    init_session_state()
    encoded_bg = get_base64_encoded_image("정관장 이미지.jpg")
    encoded_logo = get_base64_encoded_image("kgc_logo.png")
    render_global_css(encoded_logo)
    
    if not is_authenticated():
        render_login_css(encoded_bg)
        return render_login_screen()
        
    render_main_css(encoded_bg)
    all_parts_df = load_spare_parts()
    if st.session_state.auth_step == "setup_gate": 
        render_setup_screen()
    else: 
        render_dashboard(all_parts_df)

main()