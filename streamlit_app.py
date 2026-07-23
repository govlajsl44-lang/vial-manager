"""
KGC Smart MRO — Streamlit 앱 (Supabase + Google Gemini 실연동)
===============================================================
GitHub → Streamlit Community Cloud 배포용 단일 파이썬 앱.

■ 실행
    pip install -r requirements.txt
    streamlit run streamlit_app.py

■ 비밀값 설정 (.streamlit/secrets.toml 또는 Streamlit Cloud의 Secrets 메뉴)
    SUPABASE_URL = "https://xxxx.supabase.co"
    SUPABASE_KEY = "publishable/anon key"
    GEMINI_API_KEY = "AIza..."          # 선택: 없으면 앱 안에서 입력
  → secrets가 없으면 아래 기본값을 사용합니다.

■ Supabase 테이블
    machines(id, factory, dept, line, machine_name, machine_image_url, sop_url, created_at)
    spare_parts(id, machine_name, part_name, spec, life_m, stock)
    maintenance_logs(id, log_date, machine_name, part_name, worker_name, content)
  ※ anon 키가 노출되므로 RLS 정책을 반드시 설정하세요.
"""

import datetime as dt
from io import BytesIO

import streamlit as st

# ---- 외부 라이브러리 (requirements.txt 참고) ----
try:
    from supabase import create_client, Client
except Exception:  # pragma: no cover
    create_client = None

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover
    genai = None

from PIL import Image

# =====================================================================
# 설정
# =====================================================================
DEFAULT_SUPABASE_URL = "https://mpbcsmckmyjjelyfxiuk.supabase.co"
DEFAULT_SUPABASE_KEY = "sb_publishable_HugvgLttufNx1DYgDvdkvw_Mm1uc-i8"
GEMINI_MODEL = "gemini-1.5-flash"

TEAMS = {
    "부여공장": ["제품 1팀", "제품 2팀", "시설에너지 관리팀", "공정개선팀", "지원팀", "산업안전 보건팀"],
    "원주공장": ["생산팀", "시설에너지 관리팀", "지원팀"],
}
FACILITY_TEAM = "시설에너지 관리팀"

SOP_SECTIONS = [
    ("1. 작업 전 확인 사항", [
        "작업자는 반드시 규정된 보호구(안전모, 안전화 등)를 착용해야 합니다.",
        "기계 주변에 인화성 물질이나 장애물이 없는지 육안으로 확인합니다.",
        "컨베이어 및 구동부 연결 상태를 점검합니다.",
    ]),
    ("2. 정상 가동 (기동) 절차", [
        "메인 전원 차단기를 [ON] 위치로 전환합니다.",
        "제어 패널에서 시스템 [초기화(Reset)] 버튼을 누릅니다.",
        "오류 알람이 발생하지 않는지 30초간 대기하며 패널을 모니터링합니다.",
        "[운전(Start)] 버튼을 눌러 공정을 시작합니다.",
    ]),
    ("3. 비상 상황 발생 시 조치", [
        "기계적 소음·타는 냄새·빨간 경고등이 켜질 경우 즉시 [비상정지(EMG)] 버튼을 누릅니다.",
        "현장 통제 후 [시설에너지관리팀 긴급 호출]을 진행합니다.",
        "임의로 기계를 분해하거나 조작하지 않습니다.",
    ]),
]

# 색상
GREEN = "#0E5A34"
DEEP = "#0E4D2C"
LIME = "#7DB94A"
AMBER = "#D99A2E"
RED = "#D1453B"

st.set_page_config(page_title="KGC Smart MRO", page_icon="🌿", layout="centered",
                   initial_sidebar_state="collapsed")


# =====================================================================
# 비밀값 / 클라이언트
# =====================================================================
def secret(key, default=""):
    try:
        return st.secrets[key]
    except Exception:
        return default


@st.cache_resource(show_spinner=False)
def get_supabase() -> "Client":
    url = secret("SUPABASE_URL", DEFAULT_SUPABASE_URL)
    key = secret("SUPABASE_KEY", DEFAULT_SUPABASE_KEY)
    if create_client is None:
        st.error("supabase 라이브러리가 없습니다. `pip install supabase` 후 다시 실행하세요.")
        st.stop()
    return create_client(url, key)


sb = get_supabase()


def gemini_key():
    return st.session_state.get("gemini_key") or secret("GEMINI_API_KEY", "")


# =====================================================================
# 스타일
# =====================================================================
st.markdown(f"""
<style>
  @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css');
  html, body, [class*="css"] {{ font-family:'Pretendard Variable',Pretendard,system-ui,sans-serif; }}
  #MainMenu, footer {{ visibility:hidden; }}
  .block-container {{ padding-top:1.2rem; max-width:720px; }}
  .kgc-hero {{ background:linear-gradient(135deg,{DEEP},#0B3D23); color:#fff; border-radius:18px;
      padding:20px 22px; margin-bottom:14px; }}
  .kgc-card {{ background:#fff; border:1px solid #E7EAE4; border-radius:16px; padding:16px; margin-bottom:10px; }}
  .kgc-badge {{ display:inline-block; padding:4px 11px; border-radius:20px; font-size:12px; font-weight:700; }}
  .kgc-kpi {{ border-radius:14px; padding:14px 16px; color:#fff; }}
  .stButton>button {{ border-radius:12px; font-weight:700; }}
  .stButton>button[kind="primary"] {{ background:{GREEN}; border-color:{GREEN}; }}
  .warn-box {{ background:#FDECEA; border:1.5px solid #F1B7B1; border-radius:14px; padding:14px 16px;
      color:#B23A31; font-weight:600; margin-bottom:12px; }}
  .ok-box {{ background:#E6EFE7; border:1px solid #B9D6C0; border-radius:14px; padding:12px 15px;
      color:{GREEN}; font-weight:600; }}
  .sop-wm {{ position:relative; }}
</style>
""", unsafe_allow_html=True)


# =====================================================================
# 데이터 접근
# =====================================================================
def load_all():
    try:
        machines = sb.table("machines").select("*").execute().data or []
        parts = sb.table("spare_parts").select("*").execute().data or []
        logs = (sb.table("maintenance_logs").select("*")
                .order("log_date", desc=True).order("id", desc=True).execute().data or [])
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        machines, parts, logs = [], [], []
    st.session_state.machines = machines
    st.session_state.parts = parts
    st.session_state.logs = logs


def machines():
    return st.session_state.get("machines", [])


def parts():
    return st.session_state.get("parts", [])


def logs():
    return st.session_state.get("logs", [])


def logs_for(name):
    return [l for l in logs() if l.get("machine_name") == name]


def status_of(name):
    ls = logs_for(name)
    if ls and "[정비 요청]" in str(ls[0].get("content", "")):
        return {"key": "request", "short": "정비요청", "color": RED}
    if any((p.get("stock") or 0) <= 2 for p in parts() if p.get("machine_name") == name):
        return {"key": "stock", "short": "재고부족", "color": AMBER}
    return {"key": "ok", "short": "정상 가동", "color": GREEN}


def user():
    return st.session_state.get("user")


def scoped_machines():
    u = user()
    ms = machines()
    if not u:
        return []
    if u["is_master"]:
        return ms
    if u["is_facility"]:
        return [m for m in ms if m.get("factory") == u["factory"]]
    return [m for m in ms if m.get("factory") == u["factory"] and m.get("dept") == u["dept"]]


def worker_tag():
    u = user()
    if u["is_master"]:
        return f"[관리자] {u['name']}"
    return f"[{u['factory']}] {u['dept']} / {u['name']}"


def insert_log(machine, part, content):
    try:
        sb.table("maintenance_logs").insert({
            "log_date": dt.date.today().isoformat(),
            "machine_name": machine, "part_name": part,
            "worker_name": worker_tag(), "content": content,
        }).execute()
    except Exception as e:
        st.error(f"저장 실패: {e}")
        return
    load_all()


# =====================================================================
# 인증
# =====================================================================
def profile_from(session_user):
    md = session_user.user_metadata or {}
    email = (session_user.email or "").lower()
    name = md.get("display_name") or email.split("@")[0] or "사용자"
    factory = md.get("factory", "")
    dept = md.get("team", "")
    is_master = ("admin" in email) or ("master" in email)
    is_facility = dept == FACILITY_TEAM
    return {"name": name, "email": email, "factory": factory, "dept": dept,
            "is_master": is_master, "is_facility": is_facility,
            "can_control": is_master or is_facility}


def restore_session():
    if "user" in st.session_state:
        return
    try:
        sess = sb.auth.get_session()
        if sess and sess.user:
            st.session_state.user = profile_from(sess.user)
            load_all()
    except Exception:
        pass


def login_view():
    st.markdown(f"""
    <div style="text-align:center;margin:10px 0 22px">
      <div style="font-size:40px;font-weight:800;color:{DEEP};line-height:1">KGC</div>
      <div style="font-size:28px;font-weight:700"><span style="color:{LIME}">Smart</span>
        <span style="color:{AMBER}">MRO</span></div>
      <div style="color:#6C776F;font-size:13px;margin-top:6px">스마트 설비 정비 관리 시스템</div>
    </div>""", unsafe_allow_html=True)

    tab_login, tab_signup = st.tabs(["로그인", "회원가입"])

    with tab_login:
        email = st.text_input("이메일", key="li_email", placeholder="admin@kgc.com")
        pw = st.text_input("비밀번호", key="li_pw", type="password")
        if st.button("로그인", type="primary", use_container_width=True):
            if not email or not pw:
                st.warning("이메일과 비밀번호를 입력하세요.")
            else:
                try:
                    res = sb.auth.sign_in_with_password({"email": email.strip(), "password": pw})
                    st.session_state.user = profile_from(res.user)
                    load_all()
                    st.rerun()
                except Exception:
                    st.error("로그인 실패: 아이디/비밀번호를 확인하세요.")

    with tab_signup:
        name = st.text_input("성명", key="su_name", placeholder="홍길동")
        factory = st.selectbox("소속 공장", list(TEAMS.keys()), key="su_factory")
        dept = st.selectbox("소속 팀", TEAMS[factory], key="su_dept")
        su_email = st.text_input("이메일", key="su_email", placeholder="user@kgc.com")
        su_pw = st.text_input("비밀번호", key="su_pw", type="password")
        if st.button("가입하고 시작하기", type="primary", use_container_width=True):
            if not (name and su_email and su_pw):
                st.warning("성명·이메일·비밀번호를 모두 입력하세요.")
            else:
                try:
                    sb.auth.sign_up({
                        "email": su_email.strip(), "password": su_pw,
                        "options": {"data": {"display_name": name.strip(),
                                             "factory": factory, "team": dept}},
                    })
                    st.success("회원가입 완료! [로그인] 탭에서 로그인하세요. (이메일 인증이 필요할 수 있습니다)")
                except Exception as e:
                    st.error(f"가입 실패: {e}")

    st.caption("KGC 인삼공사 · © 2026 Korea Ginseng Corporation")


def logout():
    try:
        sb.auth.sign_out()
    except Exception:
        pass
    for k in ["user", "machines", "parts", "logs", "sel_machine", "nav"]:
        st.session_state.pop(k, None)
    st.rerun()


# =====================================================================
# 화면들
# =====================================================================
def kpi(col, value, label, bg, fg="#fff", border=None):
    style = f"background:{bg};" + (f"border:1px solid {border};" if border else "")
    col.markdown(
        f'<div class="kgc-kpi" style="{style}color:{fg}">'
        f'<div style="font-size:26px;font-weight:800;line-height:1">{value}</div>'
        f'<div style="font-size:12px;margin-top:3px;opacity:.85">{label}</div></div>',
        unsafe_allow_html=True)


def alerts_list():
    sc = scoped_machines()
    names = {m["machine_name"] for m in sc}
    out = []
    for m in sc:
        if status_of(m["machine_name"])["key"] == "request":
            out.append((RED, "⚠️", f"{m['machine_name']} 정비 요청",
                        f"{m['factory']} · {m['dept']} · {m['line']}"))
    for p in parts():
        if p.get("machine_name") in names and (p.get("stock") or 0) <= 2:
            out.append((AMBER, "📦", f"{p['part_name']} 재고 부족",
                        f"{p['machine_name']} · 보유 {p.get('stock', 0)} EA"))
    return out


def page_home():
    u = user()
    sc = scoped_machines()
    reqs = [m for m in sc if status_of(m["machine_name"])["key"] == "request"]
    names = {m["machine_name"] for m in sc}
    low = [p for p in parts() if p.get("machine_name") in names and (p.get("stock") or 0) <= 2]
    role = "마스터 관리자" if u["is_master"] else (FACILITY_TEAM if u["is_facility"] else "현장 작업자")

    st.markdown(f"""
    <div class="kgc-hero">
      <div style="font-size:12px;color:#9FD1B0;font-weight:600">담당 범위 · {role}</div>
      <div style="font-size:24px;font-weight:800">{'전체 공장' if u['is_master'] else u['factory']}</div>
      <div style="margin-top:8px;font-size:13px">
        <b>{len(sc)}</b> 설비 &nbsp;·&nbsp;
        <span style="color:#F09B94"><b>{len(reqs)}</b> 정비요청</span> &nbsp;·&nbsp;
        <span style="color:#F2C15A"><b>{len(low)}</b> 재고부족</span>
      </div>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"**{u['name']}님** · {u['factory']} · {u['dept']}")
    st.divider()
    st.subheader("실시간 알림")
    al = alerts_list()
    if not al:
        st.success("현재 처리할 알림이 없습니다.")
    for color, icon, title, desc in al:
        st.markdown(
            f'<div class="kgc-card" style="border-left:4px solid {color}">'
            f'<b>{icon} {title}</b><br><span style="color:#6C776F;font-size:13px">{desc}</span></div>',
            unsafe_allow_html=True)


def page_routing():
    u = user()
    if u["is_facility"] and not u["is_master"]:
        st.info("시설에너지관리팀은 좌측 메뉴의 **통합 관제 센터**를 이용하세요.")
        return

    ms = machines()
    if u["is_master"]:
        facs = sorted({m["factory"] for m in ms if m.get("factory")})
        factory = st.selectbox("공장", facs)
    else:
        factory = u["factory"]
        st.caption(f"공장: {factory} (고정)")

    if u["is_master"]:
        depts = sorted({m["dept"] for m in ms if m.get("factory") == factory and m.get("dept")})
        dept = st.selectbox("담당 팀", depts) if depts else None
    else:
        dept = u["dept"]
        st.caption(f"담당 팀: {dept} (고정)")

    base = [m for m in ms if m.get("factory") == factory and m.get("dept") == dept]
    lines = sorted({m["line"] for m in base if m.get("line")})
    line = st.selectbox("생산 라인", lines) if lines else None

    st.divider()
    st.subheader("정비 대상 기기")
    mlist = [m for m in base if m.get("line") == line]
    if not mlist:
        st.warning("등록된 설비가 없습니다.")
        return
    cols = st.columns(2)
    for i, m in enumerate(mlist):
        s = status_of(m["machine_name"])
        with cols[i % 2]:
            with st.container(border=True):
                img = m.get("machine_image_url") or ""
                if img.startswith("http"):
                    st.image(img, use_container_width=True)
                st.markdown(f"**{m['machine_name']}**")
                st.markdown(f'<span style="color:{s["color"]};font-weight:700;font-size:13px">'
                            f'● {s["short"]}</span>', unsafe_allow_html=True)
                if st.button("모니터링 열기", key=f"open_{m['id']}", use_container_width=True):
                    st.session_state.sel_machine = m
                    st.session_state.nav = "설비 대시보드"
                    st.rerun()


def page_monitor():
    m = st.session_state.get("sel_machine")
    if not m:
        st.info("설비 라우팅에서 기기를 먼저 선택하세요.")
        return
    s = status_of(m["machine_name"])
    risk = [p for p in parts() if p.get("machine_name") == m["machine_name"] and (p.get("stock") or 0) <= 2]
    requested = bool(logs_for(m["machine_name"])) and \
        "[정비 요청]" in str(logs_for(m["machine_name"])[0].get("content", ""))
    defect, avg = 3.8, 1.5

    img = m.get("machine_image_url") or ""
    if img.startswith("http"):
        st.image(img, use_container_width=True)
    st.markdown(f"### {m['machine_name']}")
    st.caption(f"{m['factory']} · {m['dept']} · {m['line']}")

    if defect > avg:
        st.markdown(f'<div class="warn-box">⚠️ 불량률 경고 — 현재 {defect}% · 평균 {avg}% 초과. '
                    f'즉시 점검이 필요합니다.</div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("기계 상태", s["short"])
    c2.metric("생산량", "12,500")
    c3.metric("불량률", f"{defect}%", f"평균 {avg}%", delta_color="inverse")
    c4.metric("위험 소모품", f"{len(risk)}건")

    if requested:
        st.markdown('<div class="warn-box">🚨 시설에너지관리팀에 긴급 정비 요청이 접수되어 있습니다.</div>',
                    unsafe_allow_html=True)
        if st.button("✅ 정비 완료 (호출 해제)", type="primary", use_container_width=True):
            insert_log(m["machine_name"], "기기 전체", "[조치 완료] 시설팀 정비가 완료되어 호출을 해제합니다.")
            st.rerun()
    else:
        if st.button("🚨 시설에너지관리팀 긴급 호출", use_container_width=True):
            insert_log(m["machine_name"], "기기 전체", "[정비 요청] 현장 작업자가 긴급 정비를 요청했습니다.")
            st.rerun()

    st.divider()
    st.subheader("최근 정비 이력")
    recent = logs_for(m["machine_name"])[:5]
    if not recent:
        st.caption("등록된 정비 일지가 없습니다.")
    for l in recent:
        st.markdown(f'<div class="kgc-card"><b>{l["log_date"]}</b> · {l["part_name"]}<br>'
                    f'<span style="color:#6C776F;font-size:13px">{l["content"]} · {l["worker_name"]}</span></div>',
                    unsafe_allow_html=True)


def page_inventory():
    m = st.session_state.get("sel_machine")
    if not m:
        st.info("설비 라우팅에서 기기를 먼저 선택하세요.")
        return
    plist = [p for p in parts() if p.get("machine_name") == m["machine_name"]]
    low = [p for p in plist if (p.get("stock") or 0) <= 2]

    c1, c2 = st.columns(2)
    kpi(c1, len(plist), "관리 품목", GREEN)
    kpi(c2, len(low), "위험 소모품 (≤2)", "#fff", RED, border="#F1B7B1")

    st.markdown(f"#### {m['machine_name']} · 소모품")

    with st.expander("➕ 신규 부품 등록"):
        with st.form("add_part", clear_on_submit=True):
            pn = st.text_input("부품명")
            spec = st.text_input("규격 / 재질")
            life = st.number_input("권장 수명 (개월)", min_value=1, value=12)
            stock = st.number_input("초기 재고 (EA)", min_value=0, value=1)
            if st.form_submit_button("등록", type="primary"):
                if pn.strip():
                    try:
                        sb.table("spare_parts").insert({
                            "machine_name": m["machine_name"], "part_name": pn.strip(),
                            "spec": spec.strip() or None, "life_m": int(life), "stock": int(stock),
                        }).execute()
                        insert_log(m["machine_name"], pn.strip(), f"신규 부품 등록: {pn.strip()}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"등록 실패: {e}")

    if not plist:
        st.warning("이 설비에 등록된 부품이 없습니다.")
        return

    for p in plist:
        repl = [l for l in logs_for(m["machine_name"])
                if l.get("part_name") == p["part_name"] and
                ("교체" in str(l.get("content", "")) or "리셋" in str(l.get("content", "")))]
        last = repl[0]["log_date"] if repl else None
        life = p.get("life_m") or 0
        elapsed = 0
        if last:
            d = dt.date.fromisoformat(last)
            today = dt.date.today()
            elapsed = (today.year - d.year) * 12 + (today.month - d.month)
        remain = max(0, life - elapsed) if life else 0
        pct = int(remain / life * 100) if life else 100
        stock = p.get("stock") or 0
        with st.container(border=True):
            top = st.columns([3, 1])
            top[0].markdown(f"**{p['part_name']}**  \n"
                            f"<span style='color:#8A948C;font-size:12px'>{p.get('spec') or '규격 미지정'} · "
                            f"권장수명 {life}개월 · 최근 교체 {last or '기록 없음'}</span>",
                            unsafe_allow_html=True)
            top[1].markdown(f"<div style='text-align:right'><span style='font-size:11px;color:#8A948C'>보유</span><br>"
                            f"<b style='font-size:18px;color:{RED if stock == 0 else (AMBER if stock <= 2 else GREEN)}'>"
                            f"{stock} EA</b></div>", unsafe_allow_html=True)
            st.progress(pct / 100, text=f"잔여수명 {remain}개월" if life else "수명 기록 없음")
            b1, b2 = st.columns(2)
            if b1.button("🔄 교체 확정", key=f"rep_{p['id']}", use_container_width=True):
                if stock <= 0:
                    st.toast("재고가 부족합니다.", icon="⚠️")
                else:
                    try:
                        sb.table("spare_parts").update({"stock": stock - 1}).eq("id", p["id"]).execute()
                        insert_log(m["machine_name"], p["part_name"], "신품 교체 완료 및 사이클 리셋.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"교체 실패: {e}")
            with b2.popover("📊 재고 보정", use_container_width=True):
                nv = st.number_input("창고 보관 수량", min_value=0, value=int(stock), key=f"adj_{p['id']}")
                if st.button("저장", key=f"adjs_{p['id']}"):
                    try:
                        sb.table("spare_parts").update({"stock": int(nv)}).eq("id", p["id"]).execute()
                        insert_log(m["machine_name"], p["part_name"], f"재고 수량 보정: {int(nv)} EA")
                        st.rerun()
                    except Exception as e:
                        st.error(f"보정 실패: {e}")
            if stock <= 2:
                st.markdown(f"<span style='color:{RED};font-size:12px;font-weight:600'>"
                            f"⚠ 재고가 부족합니다. 발주가 필요합니다.</span>", unsafe_allow_html=True)


def page_ai():
    m = st.session_state.get("sel_machine")
    ctx = m["machine_name"] if m else "설비"
    key = gemini_key()

    if not key:
        with st.expander("🔑 Gemini API 키 설정", expanded=True):
            k = st.text_input("Gemini API 키", type="password",
                              help="브라우저 세션에만 저장됩니다. secrets.toml에 GEMINI_API_KEY로 넣어두면 자동 사용됩니다.")
            if st.button("저장"):
                st.session_state.gemini_key = k.strip()
                st.rerun()

    tab_v, tab_c = st.tabs(["AI 비전 진단", "AI 챗봇"])

    with tab_v:
        st.caption(f"현장 부품을 촬영·업로드하면 Google Gemini가 상태를 진단합니다. (대상: {ctx})")
        up = st.file_uploader("부품 이미지", type=["png", "jpg", "jpeg", "webp"])
        if up:
            st.image(up, use_container_width=True)
        if st.button("🔬 진단 시작", type="primary", disabled=not (up and key)):
            if genai is None:
                st.error("google-generativeai 라이브러리가 없습니다.")
            else:
                try:
                    genai.configure(api_key=key)
                    model = genai.GenerativeModel(GEMINI_MODEL)
                    img = Image.open(up)
                    prompt = (f"이 사진은 [{ctx}] 기계의 부품 또는 상태를 찍은 것입니다. "
                              f"현재 상태를 진단하고 파손·마모·이상 증상이 있는지 한국어로 전문적으로 "
                              f"설명하고, 권장 조치를 제시해주세요.")
                    with st.spinner("Gemini가 이미지를 분석 중…"):
                        res = model.generate_content([prompt, img])
                    st.markdown('<div class="kgc-card" style="border-top:4px solid ' + GREEN + '">'
                                '<b>✅ AI 진단 결과</b></div>', unsafe_allow_html=True)
                    st.write(res.text)
                except Exception as e:
                    st.error(f"진단 오류: {e}")

    with tab_c:
        st.caption(f"{ctx} 전담 AI 엔지니어")
        if "chat" not in st.session_state:
            st.session_state.chat = [("ai", f"안녕하세요! [{ctx}] 전담 정비 어시스턴트입니다. 무엇을 도와드릴까요?")]
        for role, text in st.session_state.chat:
            st.chat_message("user" if role == "user" else "assistant").write(text)
        q = st.chat_input("정비 관련 질문을 입력하세요")
        if q:
            st.session_state.chat.append(("user", q))
            if not key or genai is None:
                st.session_state.chat.append(("ai", "⚠️ Gemini API 키를 먼저 설정해주세요."))
            else:
                try:
                    genai.configure(api_key=key)
                    model = genai.GenerativeModel(GEMINI_MODEL)
                    history = "\n".join(f"{r}: {t}" for r, t in st.session_state.chat[:-1])
                    prompt = (f"너는 공장 설비 [{ctx}] 전문 엔지니어이자 정비 도우미야. "
                              f"작업자의 질문에 친절하고 전문적으로 한국어로 대답해줘.\n\n"
                              f"이전 대화:\n{history}\n\n사용자: {q}")
                    with st.spinner("답변 생성 중…"):
                        res = model.generate_content(prompt)
                    st.session_state.chat.append(("ai", res.text))
                except Exception as e:
                    st.session_state.chat.append(("ai", f"⚠️ 오류: {e}"))
            st.rerun()


def page_control():
    u = user()
    if not u["can_control"]:
        st.error("🔒 통합 관제 센터는 시설에너지관리팀·관리자 전용입니다.")
        return
    base = machines() if u["is_master"] else [m for m in machines() if m.get("factory") == u["factory"]]
    enriched = []
    for m in base:
        s = status_of(m["machine_name"])
        prio = {"request": 0, "stock": 1, "ok": 2}[s["key"]]
        enriched.append((prio, s, m))
    enriched.sort(key=lambda x: x[0])
    reqs = [e for e in enriched if e[0] == 0]
    stock = [e for e in enriched if e[0] == 1]

    st.markdown(f"#### {'마스터 관리자' if u['is_master'] else FACILITY_TEAM} 통합 관제 센터")
    c1, c2, c3 = st.columns(3)
    kpi(c1, len(enriched), "전체 설비", GREEN)
    kpi(c2, len(reqs), "정비 요청", "#fff", RED, border="#F1B7B1")
    kpi(c3, len(stock), "재고 부족", "#fff", AMBER, border="#EAD9B0")

    if reqs:
        st.markdown("##### 🚨 긴급 정비 요청")
        for _, s, m in reqs:
            with st.container(border=True):
                cc = st.columns([4, 1])
                cc[0].markdown(f"<span style='color:{RED};font-weight:800'>⚠️ {m['machine_name']}</span><br>"
                               f"<span style='font-size:12px;color:#994039'>{m['factory']} · {m['dept']} · {m['line']}</span>",
                               unsafe_allow_html=True)
                if cc[1].button("점검", key=f"ck_{m['id']}", type="primary"):
                    st.session_state.sel_machine = m
                    st.session_state.nav = "설비 대시보드"
                    st.rerun()

    st.markdown("##### 전체 설비 현황")
    for _, s, m in enriched:
        cc = st.columns([4, 1])
        cc[0].markdown(f"<div style='border-left:4px solid {s['color']};padding-left:10px'>"
                       f"<b>{m['machine_name']}</b><br>"
                       f"<span style='font-size:12px;color:#8A948C'>{m['dept']} · {m['line']}</span></div>",
                       unsafe_allow_html=True)
        cc[1].markdown(f"<div style='text-align:right;color:{s['color']};font-weight:700;font-size:13px;"
                       f"padding-top:8px'>{s['short']}</div>", unsafe_allow_html=True)


def page_logs():
    u = user()
    names = {m["machine_name"] for m in scoped_machines()}
    ll = logs() if u["is_master"] else [l for l in logs() if l.get("machine_name") in names]

    with st.expander("➕ 신규 정비 이력 제출"):
        with st.form("add_log", clear_on_submit=True):
            sel = st.session_state.get("sel_machine")
            mc = st.text_input("설비명", value=sel["machine_name"] if sel else "")
            pt = st.text_input("정비 부품", value="기기 전체")
            content = st.text_area("작업 내용")
            if st.form_submit_button("제출", type="primary") and mc.strip() and content.strip():
                insert_log(mc.strip(), pt.strip() or "기기 전체", content.strip())
                st.rerun()

    if not ll:
        st.caption("등록된 정비 일지가 없습니다.")
    for l in ll[:60]:
        c = str(l.get("content", ""))
        accent = RED if "[정비 요청]" in c else (GREEN if "[조치 완료]" in c else "#C7DCCB")
        st.markdown(f'<div class="kgc-card" style="border-left:4px solid {accent}">'
                    f'<span style="color:{GREEN};font-weight:700;font-size:13px">{l["log_date"]}</span> '
                    f'<span style="float:right;color:#8A948C;font-size:12px">{l["worker_name"]}</span><br>'
                    f'<b>{l["machine_name"]} · {l["part_name"]}</b><br>'
                    f'<span style="color:#6C776F;font-size:13px">{c}</span></div>',
                    unsafe_allow_html=True)


def page_sop():
    m = st.session_state.get("sel_machine")
    st.markdown('<div style="background:#FDF6E9;border:1px solid #EAD9B0;border-radius:12px;'
                'padding:11px 14px;color:#8A6410;font-weight:600;font-size:13px">'
                '🔒 대외비 문서 · 표준 작업 지침서</div>', unsafe_allow_html=True)
    st.markdown(f"### 표준 작업 지침서 (SOP)")
    st.caption(f"{m['machine_name'] if m else '설비'} · Rev.4")
    sop_url = (m or {}).get("sop_url", "")
    if sop_url and str(sop_url).startswith("http"):
        st.link_button("📄 원문 SOP 문서 열기", sop_url)
    for title, items in SOP_SECTIONS:
        st.markdown(f"**{title}**")
        for it in items:
            st.markdown(f"- {it}")


def page_profile():
    u = user()
    st.markdown(f"""
    <div style="text-align:center;margin-bottom:16px">
      <div style="width:70px;height:70px;margin:0 auto;border-radius:20px;
        background:linear-gradient(135deg,{GREEN},{LIME});color:#fff;font-size:28px;font-weight:800;
        display:flex;align-items:center;justify-content:center">{u['name'][:1]}</div>
      <div style="font-size:19px;font-weight:800;margin-top:10px">{u['name']}</div>
      <div style="color:#6C776F;font-size:13px">{worker_tag()}</div>
    </div>""", unsafe_allow_html=True)
    st.markdown(f"- **소속 공장** : {u['factory'] or '-'}")
    st.markdown(f"- **담당 팀** : {u['dept'] or '-'}")
    st.markdown(f"- **이메일** : {u['email']}")
    role = "마스터 관리자" if u["is_master"] else (FACILITY_TEAM if u["is_facility"] else "현장 작업자")
    st.markdown(f"- **권한** : {role}")
    st.divider()
    kv = "설정됨 ✅" if gemini_key() else "미설정"
    st.markdown(f"**Gemini API 키** : {kv}")
    nk = st.text_input("키 등록/변경", type="password", key="pf_key")
    if st.button("키 저장"):
        st.session_state.gemini_key = nk.strip()
        st.success("저장되었습니다.")


# =====================================================================
# 라우터
# =====================================================================
def main():
    restore_session()
    if not user():
        login_view()
        return

    u = user()
    st.sidebar.markdown(f"### KGC Smart MRO")
    st.sidebar.caption(f"{u['name']} · {u['factory']} · {u['dept']}")

    pages = ["홈", "설비 라우팅", "설비 대시보드", "자산 관제", "AI 진단", "정비 일지", "SOP 지침서", "내 정보"]
    if u["can_control"]:
        pages.insert(5, "통합 관제 센터")

    default = st.session_state.get("nav", "홈")
    if default not in pages:
        default = "홈"
    nav = st.sidebar.radio("메뉴", pages, index=pages.index(default))
    st.session_state.nav = nav

    st.sidebar.divider()
    if st.sidebar.button("🔄 데이터 새로고침", use_container_width=True):
        load_all()
        st.rerun()
    if st.sidebar.button("로그아웃", use_container_width=True):
        logout()

    sel = st.session_state.get("sel_machine")
    if sel:
        st.sidebar.success(f"선택 설비\n\n{sel['machine_name']}")

    {
        "홈": page_home,
        "설비 라우팅": page_routing,
        "설비 대시보드": page_monitor,
        "자산 관제": page_inventory,
        "AI 진단": page_ai,
        "통합 관제 센터": page_control,
        "정비 일지": page_logs,
        "SOP 지침서": page_sop,
        "내 정보": page_profile,
    }[nav]()


if __name__ == "__main__":
    main()
