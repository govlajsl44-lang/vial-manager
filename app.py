import streamlit as st
import pandas as pd
import datetime
import urllib.parse
import requests

# 1. 페이지 테마 및 레이아웃 정의
st.set_page_config(
    page_title="Vial Line Smart Maintenance System", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 🚨 [여기만 수정하세요!] 방금 구글 Apps Script 배포 후 받은 본인의 웹 앱 주소를 여기에 넣어주세요.
MACRO_URL = "https://script.google.com/macros/s/AKfycbyjK1WAHKg3qwzRz_MdfeEKv56sza7KYeki7PCToudO30Eo7XWo-9i_IktOzydoDPvc/exec"

# 🚨 [확인!] 구글 시트 하단 탭 이름이 '시트1'인지 'Sheet1'인지 확인하고 똑같이 적어주세요.
SHEET_NAME = "시트1"

# Enterprise MES 대시보드 전용 프리미엄 CSS 테마 주입
st.markdown("""
    <style>
    .main { background-color: #F8FAFC !important; }
    .block-container { padding-top: 1.5rem !important; padding-bottom: 1.5rem !important; max-width: 96% !important; }
    h1 {
        color: #0F172A !important;
        font-weight: 800 !important;
        font-size: 2.1rem !important;
        border-bottom: 3px solid #0284C7;
        padding-bottom: 8px;
        margin-bottom: 18px !important;
    }
    h2, h3, h4 { color: #1E293B !important; font-weight: 700 !important; margin-top: 1rem !important; }
    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-top: 4px solid #0284C7 !important;
        padding: 1.1rem !important;
        border-radius: 6px !important;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05) !important;
    }
    div[data-testid="stMetricLabel"] p { font-size: 0.85rem !important; color: #475569 !important; font-weight: 700 !important; }
    div[data-testid="stMetricValue"] div { font-size: 1.7rem !important; font-weight: 800 !important; color: #0F172A !important; }
    div[data-testid="stContainer"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        padding: 1.4rem !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1) !important;
        margin-bottom: 12px !important;
    }
    .stButton>button { font-weight: 700 !important; border-radius: 5px !important; padding: 0.5rem 1rem !important; }
    button[data-baseweb="tab"] { font-size: 1.05rem !important; font-weight: 700 !important; color: #64748B !important; }
    button[aria-selected="true"] { color: #0284C7 !important; border-bottom-color: #0284C7 !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🏭 바이알 제조공정 스마트 설비 예지정비 시스템 (MES Pro)")

# 실시간 0초 동기화 조회용 라이브 export 주소
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8/export?format=csv&gid=0"

# 중앙 구글 시트 셀 원격 직접 제어 함수
def update_google_sheet(sheet_id, sheet_name, row_idx, col_idx, new_value):
    if "여기에_본인의_웹앱_주소를_넣으세요" in MACRO_URL:
        return False
    try:
        params = {
            "id": sheet_id,
            "sheet": sheet_name,
            "row": int(row_idx + 2),
            "col": int(col_idx + 1),
            "val": new_value
        }
        requests.get(MACRO_URL, params=params, timeout=5)
        return True
    except:
        return False

# 가짜 주소 방어용 경고 시스템
if "여기에_본인의_웹앱_주소를_넣으세요" in MACRO_URL:
    st.error("⚠️ [연동 필수 설정] 코드 상단의 MACRO_URL 변수에 본인의 Apps Script 웹 앱 주소를 붙여넣어야 구글 시트에 실제로 값이 저장됩니다.")

if "temp_logs" not in st.session_state:
    st.session_state.temp_logs = []

@st.cache_data(ttl=1)
def load_data(url):
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"마스터 허브 접속 대기 실패: {e}")
        return None

df = load_data(SHEET_CSV_URL)

if df is not None:
    col_list = list(df.columns)
    
    # 구글 시트 고정 열 매핑 (A~J)
    c_id = col_list[0]          # A: 부품ID
    c_mach = col_list[1]        # B: 소속설비
    c_name = col_list[2]        # C: 부품명
    c_mat = col_list[3]         # D: 재질
    c_life_m = col_list[4]      # E: 수명개월
    c_life_h = col_list[5]      # F: 권장수명시간
    c_curr_h = col_list[6]      # G: 현재운전시간
    
    idx_manual = 7              # H: 정비 메뉴얼 (SOP)
    idx_stock = 8               # I: 여분 수량 (재고)
    idx_install = 9             # J: 최초 장착일

    c_manual = col_list[idx_manual]
    c_stock = col_list[idx_stock]
    c_install_date = col_list[idx_install] if len(col_list) > 9 else col_list[-1]

    # 포맷 강제 형변환
    df[c_stock] = pd.to_numeric(df[c_stock], errors='coerce').fillna(0).astype(int)
    df[c_curr_h] = pd.to_numeric(df[c_curr_h], errors='coerce').fillna(0).astype(int)
    df[c_life_h] = pd.to_numeric(df[c_life_h], errors='coerce').fillna(0).astype(int)
    df[c_life_m] = pd.to_numeric(df[c_life_m], errors='coerce').fillna(0).astype(int)

    # 잔여 런타임 수명 진단 계산
    df['남은시간'] = df[c_life_h] - df[c_curr_h]
    urgent_parts = df[(df['남은시간'] <= 200) | (df[c_stock] <= 2)]
    
    if not urgent_parts.empty:
        with st.expander(f"⚠️ 현장 정비 레이더: 예방보전 임계점 도달 품목 {len(urgent_parts)}건 검출", expanded=True):
            alert_display = urgent_parts[[c_mach, c_name, '남은시간', c_stock]].copy()
            alert_display.columns = ['설비구분', '부품품목명', '잔여 수명(Hr)', '창고 실재고(EA)']
            st.dataframe(alert_display, use_container_width=True, hide_index=True)

    st.markdown("### 📊 실시간 공정 자산 현황")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("총 관리 소모품 종류", f"{len(df)} SKU")
    m2.metric("보안 재고 위험 (2개 이하)", f"{len(df[df[c_stock] <= 2])} 종")
    m3.metric("공정 라인 가동 상태", "NORMAL (안정 구동)")
    m4.metric("종합 시스템 동기화 기준", datetime.date.today().strftime("%Y-%m-%d"))
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    menu_tab1, menu_tab2 = st.tabs(["📋 소모품 자산 관제 및 신품 교체 제어", "📝 디지털 정비 일지 관리실"])

    with menu_tab1:
        query_params = st.query_params
        default_machine = query_params.get("machine", df[c_mach].unique()[0])
        if default_machine not in df[c_mach].unique():
            default_machine = df[c_mach].unique()[0]
            
        col1, col2 = st.columns([1, 1.2], gap="large")
        
        with col1:
            st.markdown("#### 🔍 관제 소모품 라인 설정")
            with st.container():
                selected_machine = st.selectbox("🏭 대상 설비 라인 선택", df[c_mach].unique(), index=list(df[c_mach].unique()).index(default_machine), key="sl_mach")
                filtered_df = df[df[c_mach] == selected_machine]
                
                default_part = query_params.get("part", filtered_df[c_name].unique()[0])
                if default_part not in filtered_df[c_name].unique():
                    default_part = filtered_df[c_name].unique()[0]
                    
                selected_part = st.selectbox("🔧 세부 부품 객체 선택", filtered_df[c_name].unique(), index=list(filtered_df[c_name].unique()).index(default_part), key="sl_part")
            
            part_idx = df[df[c_name] == selected_part].index[0]
            part_info = df.loc[part_idx]
            
            st.markdown("#### 📋 선택 부품 실시간 장착 및 자산 현황")
            with st.container():
                if pd.notna(part_info[c_install_date]):
                    raw_install_date = str(part_info[c_install_date]).strip()
                    st.markdown(f"**📅 현재 부품 최초 장착일 (J열) :** `{raw_install_date}`")
                    try:
                        parsed_start = datetime.datetime.strptime(raw_install_date, "%Y-%m-%d").date()
                    except:
                        parsed_start = datetime.date.today()
                else:
                    st.markdown("**📅 현재 부품 최초 장착일 (J열) :** `기록 없음`")
                    parsed_start = datetime.date.today()

                months_to_add = int(part_info[c_life_m])
                year = parsed_start.year + (parsed_start.month + months_to_add - 1) // 12
                month = (parsed_start.month + months_to_add - 1) % 12 + 1
                calculated_replace_date = datetime.date(year, month, min(parsed_start.day, 28))
                
                st.markdown(f"**⏳ 차기 정비 권장 교체일 :** `{calculated_replace_date.strftime('%Y-%m-%d')}` (보증 주기: {months_to_add}개월)")
                st.markdown(f"**📦 창고 실보관 여분 재고 (I열) :** `{part_info[c_stock]} EA`")
                st.markdown(f"**⏱️ 가동 누적 측정 스펙 :** `{part_info[c_curr_h]} hr` / 한계 수명시간: `{part_info[c_life_h]} hr` (잔여: `{part_info['남은시간']} hr`)")
                
                st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
                
                manual_url = part_info[c_manual]
                if pd.notna(manual_url) and str(manual_url).strip().startswith("http"):
                    st.link_button("📄 표준 정비 지침서(SOP) 열람 (H열)", manual_url.strip(), type="primary", use_container_width=True)
                else:
                    st.info("ℹ️ 현재 선택된 소모품은 등록된 H열 정비 매뉴얼 웹링크 주소가 없습니다.")

            # 수동 원격 보정 제어실
            with st.expander("⚙️ 예외 변수 수동 수치 보정 익스팬더"):
                new_curr_h = st.number_input("현재 누적 가동 시간 보정", value=int(part_info[c_curr_h]), step=10, key="adj_h")
                new_stock = st.number_input("창고 보관 수량 보정", value=int(part_info[c_stock]), step=1, key="adj_s")
                if st.button("💾 데이터 보정 명령 동기화", use_container_width=True):
                    with st.spinner("서버 전송 중..."):
                        update_google_sheet("1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8", SHEET_NAME, part_idx, 6, new_curr_h) 
                        update_google_sheet("1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8", SHEET_NAME, part_idx, idx_stock, new_stock) 
                        st.success("✅ 원격 마스터 수치 수동 보정 완료")
                        st.cache_data.clear()
                        st.rerun()
                        
        with col2:
            st.markdown("#### 🛠️ 현장 소모품 신품 교체 집행 제어실")
            with st.container():
                st.warning(f"⚠️ **공정 작업 집행 알림:** [{selected_part}] 파트를 새 부품으로 교체하는 경우, 아래에서 실제 교체 처리 날짜를 직접 선택한 뒤 집행 단추를 누르십시오. **[운전시간 0Hr 리셋, 여분재고 1개 차감, 최초 장착일 자동 갱신]**이 엑셀 시트에 영구 반영됩니다.")
                
                chosen_execution_date = st.date_input("📆 실제 신품 교체(장착) 집행 처리 일자 지정", datetime.date.today(), key="exec_date_picker")
                
                if st.button("🔧 지정을 확인하였으며 새 소모품 교체 확정 처리", type="primary", use_container_width=True):
                    if part_info[c_stock] <= 0:
                        st.error("❌ 창고 내 여분 재고 자산이 부족(0개)하여 신품 마스터 교체 명령을 수행할 수 없습니다.")
                    else:
                        with st.spinner("중앙 ERP 스프레드시트 클라우드 원격 갱신 명령 전송 중..."):
                            reset_hours = 0
                            reduced_stock = int(part_info[c_stock]) - 1
                            formatted_install_date = chosen_execution_date.strftime("%Y-%m-%d")
                            
                            update_google_sheet("1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8", SHEET_NAME, part_idx, 6, reset_hours)       
                            update_google_sheet("1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8", SHEET_NAME, part_idx, idx_stock, reduced_stock) 
                            update_google_sheet("1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8", SHEET_NAME, part_idx, idx_install, formatted_install_date) 
                            
                            auto_system_log = {
                                "날짜": formatted_install_date,
                                "부품명": selected_part,
                                "작업자": "대시보드 원격 제어실 (시스템 자동)",
                                "정비내용": f"[신품 교체 집행 완수] 수량(I열) 1EA 차감 및 장착일(J열) 세팅 완료."
                            }
                            st.session_state.temp_logs.insert(0, auto_system_log)
                            
                            st.success(f"🎉 [{selected_part}] 신품 장착 처리 및 마스터 스케줄링 리셋이 완벽하게 완수되었습니다.")
                            st.balloons()
                            st.cache_data.clear()
                            st.rerun()

            st.markdown("##### ⏱️ 현재 소모품 실시간 수명 소모율 진행 바")
            current_hours = int(part_info[c_curr_h])
            max_hours = int(part_info[c_life_h])
            progress_per = max(0, min(100, int((current_hours / max_hours) * 100))) if max_hours > 0 else 0
            st.progress(progress_per, text=f"수명 소모 진척도: {progress_per}%")

            st.markdown("---")
            st.subheader("📱 하드웨어 식별용 스마트 QR코드 라벨")
            app_url = "https://vial-manager-na6qyzsytdcsencg2jwr89.streamlit.app/"
            qr_link = f"{app_url}?machine={urllib.parse.quote(selected_machine)}&part={urllib.parse.quote(selected_part)}"
            qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=130x130&data={urllib.parse.quote(qr_link)}"
            
            q_col1, q_col2 = st.columns([1, 2.5])
            with q_col1: st.image(qr_api_url, caption="정비 태그 QR")
            with q_col2: st.code(qr_link)

    with menu_tab2:
        st.markdown("### 📝 제조 설비 일일 정비·교체 일지 수동 기록")
        st.write("현장에서 수행한 일상 예방보전 내역 및 라인 조치 사항을 마스터 로그에 수동 기입하는 양식입니다.")
        
        log_col1, log_col2 = st.columns([1, 1.2], gap="large")
        
        with log_col1:
            with st.container():
                st.markdown("##### 🖊️ 이력 등록 양식 서식")
                log_date = st.date_input("정비 및 작업 실행 일자", datetime.date.today(), key="m_log_date")
                log_mach = st.selectbox("정비 대상 설비 선택", df[c_mach].unique(), key="m_log_mach")
                filtered_log_df = df[df[c_mach] == log_mach]
                log_part = st.selectbox("정비 처리 부품 선택", filtered_log_df[c_name].unique(), key="m_log_part")
                
                log_worker = st.text_input("작업 정비원 성명 기입", placeholder="예: 보전팀 홍길동 과장", key="m_log_worker")
                log_content = st.text_area("상세 정비 작업 사역 내역 기술", placeholder="예: 구동 기어 유격 측정 후 중심 정렬 및 볼트 고정 록타이트 처리.", key="m_log_content")
                
                st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
                if st.button("🚀 정비 이력 로그 중앙 서버 전송", type="primary", use_container_width=True, key="m_log_submit_btn"):
                    if not log_worker or not log_content:
                        st.warning("⚠️ 입력창에 누락된 데이터가 있습니다. 정비 책임자 명과 상세 내용을 기술해 주십시오.")
                    else:
                        with st.spinner("마스터 로그 테이블에 데이터 주입 중..."):
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
            st.markdown("#### 📋 최근 공정 예방 보전 이력 피드백 (실시간 반영)")
            with st.container():
                base_logs = [
                    {"날짜": "2026-07-01", "부품명": "충전 피스톤 실링", "작업자": "시스템관리자", "정비내용": "스마트 예지정비 모니터링 제어실 연동 상태 정상 작동 중."}
                ]
                display_logs = st.session_state.temp_logs + base_logs
                log_df_display = pd.DataFrame(display_logs)
                st.dataframe(log_df_display, use_container_width=True, hide_index=True)
else:
    st.info("구글 마스터 스프레드시트 데이터 통신망 연결 대기 중...")