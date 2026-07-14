import base64
import datetime
import os
import time  # 알림 대기 시간을 위한 모듈 추가
import urllib.parse

import pandas as pd
import streamlit as st
from supabase import create_client

# ======================================================================
# 상수: Supabase 테이블 및 컬럼
# ======================================================================
TABLE_MACHINES = "machines"  # 신규 추가된 기기 마스터 테이블
TABLE_SPARE_PARTS = "spare_parts"
TABLE_MAINTENANCE_LOGS = "maintenance_logs"

# spare_parts 컬럼
SP_ID = "id"
SP_MACHINE = "machine_name"
SP_PART = "part_name"
SP_SPEC = "spec"
SP_LIFE_M = "life_m"
SP_LIFE_H = "life_h"
SP_MANUAL = "manual_url"
SP_STOCK = "stock"

# maintenance_logs 컬럼 (worker 에러 수정을 위해 worker_name으로 변경)
ML_DATE = "log_date"
ML_MACHINE = "machine_name"
ML_PART = "part_name"
ML_WORKER = "worker_name"  
ML_CONTENT = "content"

# UI 전용 (DB 미저장)
UI_CURRENT_HOURS = "current_hours"
UI_INSTALL_DATE = "install_date"
UI_REMAINING_HOURS = "남은시간"

# (기존 하드코딩된 FACTORY_HIERARCHY는 삭제되었습니다. DB에서 불러옵니다.)

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
    """기기 마스터 테이블에서 전체 목록을 불러옵니다."""
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
    return _execute(
        lambda: init_supabase().table(TABLE_SPARE_PARTS).update(updates).eq(SP_ID, part_id).execute()
    )


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

    column_map = {
        ML_DATE: "날짜",
        ML_PART: "부품명",
        ML_WORKER: "작업자",
        ML_CONTENT: "정비내용",
    }
    available = [col for col in column_map if col in logs_df.columns]
    display_df = logs_df[available].rename(columns=column_map)
    st.dataframe(display_df, use_container_width=True, hide_index=True)


def get_demo_data(machine_name):
    return pd.DataFrame({
        SP_ID: ["D001", "D002", "D003", "D004"],
        SP_MACHINE: [machine_name] * 4,
        SP_PART: ["베어링", "O-ring", "노즐", "실린더"],
        SP_SPEC: ["합금강", "고무", "스테인리스", "알루미늄"],
        SP_LIFE_M: [12, 6, 24, 36],
        SP_LIFE_H: [8000, 4000, 15000, 20000],
        UI_CURRENT_HOURS: [7500, 3900, 5000, 19500],
        SP_MANUAL: ["http://example.com"] * 4,
        SP_STOCK: [1, 5, 2, 0],
        UI_INSTALL_DATE: ["2023-01-01", "2023-06-01", "2022-01-01", "2021-01-01"],
        UI_REMAINING_HOURS: [500, 100, 10000, 500],
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
    defaults = {
        "auth_step": "login_gate",
        "user": None,
        "user_team": None,
        "user_machine": None,
    }
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
        div[data-testid="stStatusWidget"] {{ position: fixed !important; top: 0 !important; right: 0 !important; bottom: 0 !important; left: 0 !important; width: 100vw !important; height: 100vh !important; background-color: rgba(0,0,0,0.7) !important; backdrop-filter: blur(4px) !important; display: flex !important; justify-content: center !important; align-items: center !important; z-index: 99998 !important; }}
        div[data-testid="stStatusWidget"] * {{ display: none !important; }}
        div[data-testid="stStatusWidget"]::after {{ content: "🔄 시스템 처리 및 데이터 로딩 중..."; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; color: white; font-size: 1.1rem; font-weight: bold; padding-bottom: 20px; width: 110px; height: 160px; background-color: transparent; background-image: url("{encoded_logo}"); background-repeat: no-repeat; background-position: center top; background-size: 77px; }}
        div[data-testid="stStatusWidget"]::before {{ content: ""; position: absolute; top: calc(50% - 60px); left: calc(50% - 55px); width: 110px; height: 110px; background-color: #ffffff; border-radius: 50%; z-index: -1; animation: corporate-beat 1.5s infinite ease-in-out, corporate-ripple 1.5s infinite; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_login_css(encoded_bg, encoded_logo):
    st.markdown(
        f"""
        <style>
        header[data-testid="stHeader"], div[data-testid="stToolbar"] {{ visibility: hidden !important; height: 0px !important; }}
        div[data-testid="stAppViewContainer"] {{ background: linear-gradient(rgba(241, 245, 249, 0.86), rgba(241, 245, 249, 0.86)), url('{encoded_bg}') !important; background-size: cover !important; background-position: center !important; background-attachment: fixed !important; }}
        .main {{ background: transparent !important; }}
        .styled-card {{ background-color: rgba(34, 34, 34, 0.96) !important; border-radius: 8px !important; padding: 30px !important; color: #FFFFFF !important; box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important; margin-top: 5vh; margin-bottom: 5vh; }}
        </style>
        """,
        unsafe_allow_html=True,
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
        """,
        unsafe_allow_html=True,
    )


# ======================================================================
# 화면: DB 연동형 공정/기기 라우팅
# ======================================================================
def render_setup_screen():
    if not is_authenticated():
        require_login_message()
        return

    col1, col2, col3 = st.columns([0.5, 3, 0.5])
    with col2:
        st.markdown('<div class="styled-card" style="padding: 40px !important;">', unsafe_allow_html=True)
        st.markdown(
            "<h3 style='text-align:center; color: white; margin-bottom: 30px;'>🏭 스마트 공정 및 라인 라우팅 설정</h3>",
            unsafe_allow_html=True,
        )

        user = st.session_state["user"]
        st.write(f"✅ **접속자:** `{user['display_name']} ({user['email']})`")
        if st.button("🚪 로그아웃", use_container_width=True, key="logout_setup"):
            auth_sign_out()
            st.rerun()
        st.markdown("<hr style='border-color: #555; margin-bottom: 25px;'>", unsafe_allow_html=True)

        # DB에서 기기 리스트 로드
        df_machines = load_machines()

        if df_machines.empty or "factory" not in df_machines.columns:
            st.error("🚧 데이터베이스(machines 테이블)에 등록된 설비가 없습니다. 먼저 설비 데이터를 추가해 주세요.")
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
                # 선택한 조건에 맞는 기기 목록 필터링
                mach_list = df_machines[(df_machines["factory"] == selected_factory) & (df_machines["dept"] == selected_dept) & (df_machines["line"] == selected_line)]["machine_name"].dropna().tolist()
                
                with step_col4:
                    st.success(f"✅ 총 {len(mach_list)}대의 설비가 등록되어 있습니다.")

                st.markdown(
                    f"<h4 style='color: #007BEC; text-align: center; margin: 30px 0 20px; font-weight: 800;'>4️⃣ 대상 기기 선택 ({selected_line})</h4>",
                    unsafe_allow_html=True,
                )
                img_cols = st.columns(4, gap="medium")
                for i, mach_name in enumerate(mach_list):
                    with img_cols[i % 4]:
                        st.markdown(
                            """
                            <div style="width:100%; aspect-ratio:16/9; background:rgba(255,255,255,0.03);
                            border:1px dashed rgba(255,255,255,0.2); border-radius:8px; margin-bottom:10px;
                            display:flex; justify-content:center; align-items:center;">
                            <span style="color:rgba(255,255,255,0.2); font-size:0.8rem;">Image</span></div>
                            """,
                            unsafe_allow_html=True,
                        )
                        if st.button(f"⚙️ {mach_name}", key=f"btn_mach_{i}", use_container_width=True):
                            st.session_state.user_team = f"{selected_factory} / {selected_dept} / {selected_line}"
                            st.session_state.user_machine = mach_name
                            st.session_state.auth_step = "main_app"
                            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


# ======================================================================
# 탭 1: 부품 상태 및 신품 교체
# ======================================================================
def render_tab_parts(mach_df, selected_mach):
    if not is_authenticated():
        require_login_message()
        return

    worker_name = get_worker_name()
    st.markdown(
        f"""
        <div class='menu-hero-banner'>
            <h3>📋 [{selected_mach}] 세부 부품 자산 관제 및 신품 교체</h3>
            <p>기계 내부 핵심 소모품의 잔여 수명과 재고를 파악하고, 교체 시 Supabase에 반영합니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([1, 1.2], gap="medium")

    with col1:
        st.markdown("<span class='section-title'>1️⃣ 세부 부품 선택</span>", unsafe_allow_html=True)
        with st.container():
            selected_part = st.selectbox("🔧 부품명", mach_df[SP_PART].unique(), key="sl_part_only")

        part_info = mach_df[mach_df[SP_PART] == selected_part].iloc[0]
        part_id = part_info.get(SP_ID)

        st.markdown("<span class='section-title'>2️⃣ 선택 부품 실시간 상태 조회</span>", unsafe_allow_html=True)
        with st.container():
            if pd.notna(part_info.get(UI_INSTALL_DATE, None)):
                raw_install_date = str(part_info[UI_INSTALL_DATE]).strip()
                st.markdown(f"📅 **최초 장착일 :** `{raw_install_date}`")
                try:
                    parsed_start = datetime.datetime.strptime(raw_install_date, "%Y-%m-%d").date()
                except ValueError:
                    parsed_start = datetime.date.today()
            else:
                st.markdown("📅 **최초 장착일 :** `기록 없음`")
                parsed_start = datetime.date.today()

            months_to_add = int(part_info.get(SP_LIFE_M, 0))
            year = parsed_start.year + (parsed_start.month + months_to_add - 1) // 12
            month = (parsed_start.month + months_to_add - 1) % 12 + 1
            calculated_replace_date = datetime.date(year, month, min(parsed_start.day, 28))

            st.markdown(f"⏳ **차기 권장 교체일 :** `{calculated_replace_date.strftime('%Y-%m-%d')}`")
            st.markdown(f"📦 **보유 재고 :** `{part_info.get(SP_STOCK, 0)} EA`")
            st.markdown(
                f"⏱️ **가동 런타임 :** `{part_info.get(UI_CURRENT_HOURS, 0)} hr` "
                f"(한계 `{part_info.get(SP_LIFE_H, 0)} hr`)"
            )

            manual_url = part_info.get(SP_MANUAL, "")
            if pd.notna(manual_url) and str(manual_url).strip().startswith("http"):
                st.link_button("📄 표준 정비 매뉴얼 열람", manual_url.strip(), type="primary", use_container_width=True)

        with st.expander("⚙️ 예외 변수 수동 수치 보정"):
            st.number_input("현재 누적 가동 시간 보정 (화면 표시용)", value=int(part_info.get(UI_CURRENT_HOURS, 0)), step=10, key="adj_h", disabled=True)
            new_stock = st.number_input("창고 보관 수량 보정", value=int(part_info.get(SP_STOCK, 0)), step=1, key="adj_s")
            if st.button("💾 수치 수동 보정 저장", use_container_width=True):
                if is_demo_part(part_id):
                    st.warning("⚠️ 시연용 임시 데이터이므로 Supabase에 저장되지 않습니다.")
                else:
                    with st.spinner("spare_parts 테이블 업데이트 중..."):
                        ok, err = update_spare_part(part_id, {SP_STOCK: new_stock})
                        if ok:
                            log_ok, log_err = insert_maintenance_log({
                                ML_DATE: datetime.date.today().strftime("%Y-%m-%d"),
                                ML_MACHINE: selected_mach,
                                ML_PART: selected_part,
                                ML_WORKER: worker_name,
                                ML_CONTENT: f"재고 수량 수동 보정: {new_stock} EA",
                            })
                            if log_ok:
                                st.toast("✅ 수치 보정 완료", icon="💾")
                                st.success("재고 수량 수정 및 작업자 기록이 완료되었습니다.")
                                time.sleep(1.2)
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(f"❌ 작업 이력 저장 실패: {log_err}")
                        else:
                            st.error(f"❌ 재고 수정 실패: {err}")

    with col2:
        st.markdown("<span class='section-title'>3️⃣ 소모품 교체 및 자산 리셋</span>", unsafe_allow_html=True)
        with st.container():
            chosen_execution_date = st.date_input("📆 교체일 지정", datetime.date.today(), key="exec_date_picker")
            if st.button("교체 확정 처리 완료", type="primary", use_container_width=True):
                if part_info.get(SP_STOCK, 0) <= 0:
                    st.error("❌ 보유 재고가 부족하여 교체 명령을 수행할 수 없습니다.")
                elif is_demo_part(part_id):
                    st.warning("⚠️ 시연용 임시 데이터이므로 Supabase에 저장되지 않습니다.")
                else:
                    with st.spinner("spare_parts · maintenance_logs 저장 중..."):
                        ok, err = update_spare_part(part_id, {SP_STOCK: int(part_info.get(SP_STOCK, 1)) - 1})
                        if not ok:
                            st.error(f"❌ 재고 갱신 실패: {err}")
                        else:
                            log_ok, log_err = insert_maintenance_log({
                                ML_DATE: chosen_execution_date.strftime("%Y-%m-%d"),
                                ML_MACHINE: selected_mach,
                                ML_PART: selected_part,
                                ML_WORKER: worker_name,
                                ML_CONTENT: f"[{selected_mach}] 신품 교체 완료 및 사이클 리셋.",
                            })
                            if log_ok:
                                st.toast("✅ 신품 교체 및 자산 리셋 완료", icon="🔄")
                                st.success(f"[{selected_part}] 신품 교체 처리가 데이터베이스에 안전하게 기록되었습니다.")
                                time.sleep(1.2)
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(f"❌ 정비 일지 저장 실패: {log_err}")

        current_hours = int(part_info.get(UI_CURRENT_HOURS, 0))
        max_hours = int(part_info.get(SP_LIFE_H, 1))
        progress_per = max(0, min(100, int((current_hours / max_hours) * 100))) if max_hours > 0 else 0
        st.progress(progress_per, text=f"수명 소모 진척도: {progress_per}%")

        st.markdown("---")
        st.subheader("📱 하드웨어 식별용 스마트 QR코드 라벨")
        app_url = "https://vial-manager-na6qyzsytdcsencg2jwr89.streamlit.app/"
        qr_link = f"{app_url}?machine={urllib.parse.quote(selected_mach)}&part={urllib.parse.quote(selected_part)}"
        qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=130x130&data={urllib.parse.quote(qr_link)}"
        q_col1, q_col2 = st.columns([1, 2.5])
        with q_col1:
            st.image(qr_api_url, caption="정비 태그 QR")
        with q_col2:
            st.code(qr_link)


# ======================================================================
# 탭 2: 정비 일지
# ======================================================================
def render_tab_maintenance_logs(mach_df, selected_mach):
    if not is_authenticated():
        require_login_message()
        return

    worker_name = get_worker_name()
    st.markdown(
        f"""
        <div class='menu-hero-banner'>
            <h3>📝 [{selected_mach}] 전용 정비 일지 기록</h3>
            <p>정비 내역을 maintenance_logs 테이블에 영구 저장합니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    log_col1, log_col2 = st.columns([1, 1.2], gap="medium")

    with log_col1:
        st.markdown("<span class='section-title'>1️⃣ 정비 내역 서식 작성</span>", unsafe_allow_html=True)
        with st.container():
            log_date = st.date_input("정비 및 작업 실행 일자", datetime.date.today(), key="m_log_date")
            log_part = st.selectbox("정비 부품 선택", mach_df[SP_PART].unique(), key="m_log_part")
            st.text_input("작업원 (자동기입)", value=worker_name, disabled=True, key="m_log_worker")
            log_content = st.text_area(
                "상세 정비 작업 내용",
                placeholder="예: 구동 기어 유격 측정 후 중심 정렬 및 볼트 고정 록타이트 처리.",
                key="m_log_content",
            )

            if st.button("🚀 정비 이력 제출", type="primary", use_container_width=True, key="m_log_submit_btn"):
                if not log_content.strip():
                    st.warning("⚠️ 상세 정비 내용을 입력해 주십시오.")
                else:
                    with st.spinner("maintenance_logs 테이블에 저장 중..."):
                        ok, err = insert_maintenance_log({
                            ML_DATE: log_date.strftime("%Y-%m-%d"),
                            ML_MACHINE: selected_mach,
                            ML_PART: log_part,
                            ML_WORKER: worker_name,
                            ML_CONTENT: log_content.strip(),
                        })
                        if ok:
                            st.toast("✅ 정비 일지 기록 완료", icon="📝")
                            st.success("정비 이력이 Supabase에 안전하게 저장되었습니다.")
                            time.sleep(1.2)
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(f"❌ 정비 일지 저장 실패: {err}")

    with log_col2:
        st.markdown("<span class='section-title'>2️⃣ 최근 정비 내역 이력</span>", unsafe_allow_html=True)
        with st.container():
            display_maintenance_logs(selected_mach)


# ======================================================================
# 탭 3: AI 카메라 진단
# ======================================================================
def render_tab_vision(selected_mach):
    if not is_authenticated():
        require_login_message()
        return

    st.markdown(
        f"""
        <div class='menu-hero-banner'>
            <h3>📸 AI 카메라 (비전 진단)</h3>
            <p>[{selected_mach}] 부품의 사진을 올리시면 인공지능이 마모 및 손상도를 진단합니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    vision_api_key = st.secrets.get("GEMINI_API_KEY", "")
    if vision_api_key:
        st.success("🟢 클라우드 공용 AI 보안 엔진 연동 완료.")
    else:
        st.error("⚠️ GEMINI_API_KEY를 설정해주세요.")

    v_col1, v_col2 = st.columns([1, 1.2], gap="medium")
    with v_col1:
        st.markdown("<span class='section-title'>1️⃣ 하드웨어 이미지 입력</span>", unsafe_allow_html=True)
        with st.container():
            input_mode = st.radio("사진 획득 방식", ["📱 카메라 촬영", "📁 파일 업로드"], key="vision_mode")
            captured_file = (
                st.camera_input("외관 비추기")
                if input_mode == "📱 카메라 촬영"
                else st.file_uploader("이미지 선택", type=["jpg", "png"], key="file_vision")
            )
            if captured_file is not None:
                st.image(captured_file, caption="🛠️ AI 분석 대상 이미지", width=360)

    with v_col2:
        st.markdown("<span class='section-title'>2️⃣ AI 비전 실시간 진단 결과</span>", unsafe_allow_html=True)
        if captured_file is None:
            st.info("💡 안내: 사진을 등록하면 분석이 활성화됩니다.")
        elif st.button("🚀 이미지 비전 해독 분석 시작", type="primary", use_container_width=True):
            with st.spinner("AI 픽셀 분석 중..."):
                try:
                    import google.generativeai as genai
                    from PIL import Image

                    genai.configure(api_key=vision_api_key)
                    pil_image = Image.open(captured_file)
                    context_prompt = (
                        f"너는 제조 공장의 기계 정비 마스터야. 이 사진은 '{selected_mach}'의 부품일 가능성이 높아. "
                        "마모, 균열 등을 정밀 진단하고 예방 조치안을 한국어로 보고서 형태로 써줘."
                    )
                    vision_model = genai.GenerativeModel("gemini-2.5-flash")
                    ai_response = vision_model.generate_content([context_prompt, pil_image])
                    st.success("사진 해독이 성공적으로 완료되었습니다!")
                    st.write(ai_response.text)
                except Exception as error_msg:
                    st.error(f"❌ AI 분석 모듈 오류: {error_msg}")


# ======================================================================
# 탭 4: AI 챗봇
# ======================================================================
def render_tab_chat(selected_mach):
    if not is_authenticated():
        require_login_message()
        return

    st.markdown(
        f"""
        <div class='menu-hero-banner'>
            <h3>💬 AI 챗봇</h3>
            <p>[{selected_mach}] 구동부 트러블슈팅 및 기계공학 솔루션을 논의합니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    chat_api_key = st.secrets.get("GEMINI_API_KEY", "")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [{
            "role": "assistant",
            "content": f"안녕하세요! [{selected_mach}] 전담 정비봇입니다. 애로사항을 말씀해 주세요!",
        }]

    st.markdown("<span class='section-title'>💬 1:1 대화 챗봇</span>", unsafe_allow_html=True)
    with st.container():
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    if user_prompt := st.chat_input(f"{selected_mach}의 문제 상황을 타이핑하세요"):
        with st.chat_message("user"):
            st.write(user_prompt)
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})

        if not chat_api_key:
            st.error("❌ GEMINI_API_KEY 누락.")
        else:
            with st.chat_message("assistant"):
                with st.spinner("해결 방안 도출 중..."):
                    try:
                        import google.generativeai as genai

                        genai.configure(api_key=chat_api_key)
                        system_instruction = (
                            f"너는 {selected_mach} 설비 전문 수석 엔지니어 보전원이야. "
                            "해결책을 조항별로 실천적으로 한국어로 설명해."
                        )
                        chat_model = genai.GenerativeModel("gemini-2.5-flash")
                        bot_reply = chat_model.generate_content([system_instruction, user_prompt])
                        st.write(bot_reply.text)
                        st.session_state.chat_history.append({"role": "assistant", "content": bot_reply.text})
                        st.rerun()
                    except Exception as chat_err:
                        st.error(f"❌ 챗봇 엔진 오류: {chat_err}")


# ======================================================================
# 탭 5: 신규 부품 등록
# ======================================================================
def render_tab_register_part(selected_mach):
    if not is_authenticated():
        require_login_message()
        return

    worker_name = get_worker_name()
    st.markdown(
        f"""
        <div class='menu-hero-banner'>
            <h3>📥 [{selected_mach}] 신규 부품 등록</h3>
            <p>spare_parts 테이블에 새 소모품 정보를 등록합니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    reg_col1, reg_col2 = st.columns([1, 1.2], gap="medium")

    with reg_col1:
        st.markdown("<span class='section-title'>1️⃣ 부품 기본 정보</span>", unsafe_allow_html=True)
        with st.container():
            reg_name = st.text_input("부품명 (part_name)", placeholder="예: 베어링, O-ring", key="reg_part_name")
            reg_spec = st.text_input("규격/재질 (spec)", placeholder="예: 합금강, 고무", key="reg_part_spec")
            reg_manual = st.text_input("매뉴얼 URL (manual_url, 선택)", placeholder="https://...", key="reg_manual")

    with reg_col2:
        st.markdown("<span class='section-title'>2️⃣ 수명 및 재고</span>", unsafe_allow_html=True)
        with st.container():
            st.text_input("대상 기계 (machine_name)", value=selected_mach, disabled=True, key="reg_machine_display")
            st.text_input("등록자 (자동기입)", value=worker_name, disabled=True, key="reg_worker_display")
            
            # 수명 시간 제거 완료. 월(month)만 입력받습니다.
            reg_life_m = st.number_input("권장 수명 (life_m, 월)", min_value=0, value=12, step=1, key="reg_life_m")
            reg_stock = st.number_input("초기 재고 (stock, EA)", min_value=0, value=1, step=1, key="reg_stock")

            if st.button("📥 신규 부품 등록", type="primary", use_container_width=True, key="reg_part_submit"):
                if not reg_name.strip():
                    st.error("❌ 부품명(part_name)을 입력해 주세요.")
                else:
                    new_record = {
                        SP_MACHINE: selected_mach,
                        SP_PART: reg_name.strip(),
                        SP_SPEC: reg_spec.strip() or None,
                        SP_LIFE_M: int(reg_life_m),
                        SP_LIFE_H: 0,  # DB 에러 방지를 위해 시간은 0으로 강제 처리
                        SP_STOCK: int(reg_stock),
                    }
                    if reg_manual.strip():
                        new_record[SP_MANUAL] = reg_manual.strip()

                    with st.spinner("spare_parts 테이블에 등록 중..."):
                        ok, err = insert_spare_part(new_record)
                        if ok:
                            insert_maintenance_log({
                                ML_DATE: datetime.date.today().strftime("%Y-%m-%d"),
                                ML_MACHINE: selected_mach,
                                ML_PART: reg_name.strip(),
                                ML_WORKER: worker_name,
                                ML_CONTENT: f"신규 부품 등록: {reg_name.strip()}",
                            })
                            st.toast("✅ 신규 부품 등록 완료", icon="📥")
                            st.success(f"[{reg_name.strip()}] 부품이 시스템에 성공적으로 등록되었습니다.")
                            time.sleep(1.2)
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(f"❌ 부품 등록 실패: {err}")


# ======================================================================
# 화면: 메인 대시보드
# ======================================================================
def render_dashboard(all_parts_df):
    if not is_authenticated():
        require_login_message()
        return

    selected_mach = st.session_state.user_machine
    user = st.session_state["user"]
    
    mach_df = get_machine_parts_df(all_parts_df, selected_mach)

    is_demo_mode = False
    if all_parts_df is None or all_parts_df.empty or SP_MACHINE not in all_parts_df.columns:
        is_demo_mode = True
    elif all_parts_df[all_parts_df[SP_MACHINE] == selected_mach].empty:
        is_demo_mode = True

    nav_col1, nav_col2, nav_col3 = st.columns([6, 2, 2])
    with nav_col1:
        st.caption(f"🔧 소속: {st.session_state.user_team} | 작업자: {user['display_name']} ({user['email']})")
    with nav_col2:
        if st.button("🔒 라우팅 재설정", use_container_width=True):
            st.session_state.auth_step = "setup_gate"
            st.rerun()
    with nav_col3:
        if st.button("🚪 로그아웃", use_container_width=True):
            auth_sign_out()
            st.rerun()

    st.title(f"🖥️ [{selected_mach}] 실시간 관제 대시보드")
    
    if is_demo_mode:
        st.warning("💡 현재 DB에 등록된 해당 기계 부품이 없어 시연용 임시 부품을 표시합니다. [5. 신규 부품 등록] 탭에서 실제 부품을 추가해주세요.")

    with st.expander(f"🏷️ 선택된 기계 명판: {selected_mach} - (주)이수이엔지", expanded=False):
        n_col1, n_col2 = st.columns(2)
        n_col1.markdown(f"**관리번호:** `MGT-2026-{hash(selected_mach) % 1000:03d}`")
        n_col1.markdown("**프로덕션 이어 (제조년도):** `2024년`")
        n_col2.markdown(f"**모델명:** `ISU-{hash(selected_mach) % 100:02d}-X1`")
        n_col2.markdown("**제조사:** `(주)이수이엔지`")

    urgent_parts = mach_df[(mach_df[UI_REMAINING_HOURS] <= 200) | (mach_df[SP_STOCK] <= 2)]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("현재 작동 상태", "🟢 정상 가동 (NORMAL)")
    m2.metric("실시간 불량률", "0.02%")
    m3.metric("위험 소모품", f"{len(urgent_parts)} 건", delta="-조치 요망", delta_color="inverse")
    m4.metric("등록된 세부 부품", f"{len(mach_df)} 종")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 1. 부품 상태 및 신품 교체",
        "📝 2. 정비 일지 기록",
        "📸 3. AI 카메라 진단",
        "💬 4. AI 정비 챗봇",
        "📥 5. 신규 부품 등록",
    ])

    with tab1:
        render_tab_parts(mach_df, selected_mach)
    with tab2:
        render_tab_maintenance_logs(mach_df, selected_mach)
    with tab3:
        render_tab_vision(selected_mach)
    with tab4:
        render_tab_chat(selected_mach)
    with tab5:
        render_tab_register_part(selected_mach)


# ======================================================================
# 앱 진입점
# ======================================================================
st.set_page_config(page_title="Smart Maintenance Pro", layout="wide", initial_sidebar_state="collapsed")


def main():
    init_session_state()

    encoded_bg = get_base64_encoded_image("정관장 이미지.jpg")
    encoded_logo = get_base64_encoded_image("kgc_logo.png")
    render_global_css(encoded_logo)

    if not is_authenticated():
        st.session_state.auth_step = "login_gate"
        render_login_css(encoded_bg, encoded_logo)
        render_login_screen()
        return

    render_main_css(encoded_bg)
    all_parts_df = load_spare_parts()
    if st.session_state.auth_step == "setup_gate":
        render_setup_screen()
    elif st.session_state.auth_step == "main_app":
        render_dashboard(all_parts_df)
    else:
        st.session_state.auth_step = "setup_gate"
        render_setup_screen()


main()