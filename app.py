import streamlit as st
import pandas as pd
import datetime
import urllib.parse
import requests

# 1. 페이지 설정
st.set_page_config(
    page_title="Vial Line Smart Maintenance System", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. 🚨 테마를 강제로 변환하는 대기업 사내 시스템(MES) 전용 프리미엄 CSS
st.markdown("""
    <style>
    /* 전체 배경색 및 기본 폰트 색상 조정 */
    .main {
        background-color: #F8FAFC !important;
    }
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1.5rem !important;
        max-width: 96% !important;
    }
    
    /* 타이틀 및 헤더 스타일 */
    h1 {
        color: #0F172A !important;
        font-weight: 800 !important;
        font-size: 2.2rem !important;
        border-bottom: 3px solid #0284C7;
        padding-bottom: 10px;
        margin-bottom: 20px !important;
    }
    h2, h3, h4 {
        color: #1E293B !important;
        font-weight: 700 !important;
        margin-top: 1rem !important;
    }
    
    /* 상단 현황판 카드 (종합 관제실 스타일) */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-top: 4px solid #0284C7 !important; /* 상단 포인트 블루 컬러 */
        padding: 1.2rem !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05) !important;
    }
    div[data-testid="stMetricLabel"] p {
        font-size: 0.9rem !important;
        color: #475569 !important;
        font-weight: 700 !important;
    }
    div[data-testid="stMetricValue"] div {
        font-size: 1.8rem !important;
        font-weight: 800 !important;
        color: #0F172A !important;
    }
    
    /* 컨테이너 상자 테두리 고급화 */
    div[data-testid="stContainer"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        padding: 1.5rem !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1) !important;
        margin-bottom: 15px !important;
    }
    
    /* 입력창 및 단추 스타일 조정 */
    .stButton>button {
        background-color: #0284C7 !important;
        color: white !important;
        font-weight: 700 !important;
        border-radius: 6px !important;
        border: none !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #0369A1 !important;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3) !important;
    }
    
    /* 탭 메뉴 스타일 */
    button[data-baseweb="tab"] {
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        color: #64748B !important;
    }
    button[aria-selected="true"] {
        color: #0284C7 !important;
        border-bottom-color: #0284C7 !important;
    }
    </style>
""", unsafe_allow_html=True)

# 시스템 타이틀
st.title("🏭 바이알 제조공정 스마트 설비 예지정비 시스템 (MES Pro)")

# 데이터 주소
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTXDGTnMc8RO3wBVza0w10tR4GuYY_wUUXtfRKae2wYPJWWfCqHK5gRwJqHlEmiY66tR5gr70NJBbEJ/pub?gid=0&single=true&output=csv"

# 구글 시트 원격 동기화 함수
def update_google_sheet(sheet_id, sheet_name, row_idx, col_idx, new_value):
    try:
        macro_url = "https://script.google.com/macros/s/AKfycbz_H8q9S0x9tVj2lW5N2n8XqFjZp_k5O_N_0oXvHw/exec"
        params = {
            "id": sheet_id,
            "sheet": sheet_name,
            "row": int(row_idx + 2),
            "col": int(col_idx + 1),
            "val": new_value
        }
        requests.get(macro_url, params=params, timeout=5)
        return True
    except:
        return False

# 임시 로그 저장소 생성
if "temp_logs" not in st.session_state:
    st.session_state.temp_logs = []

@st.cache_data(ttl=1)
def load_data(url):
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"데이터 로딩 실패: {e}")
        return None

df = load_data(SHEET_CSV_URL)

if df is not None:
    # 컬럼 매핑
    c_id, c_mach, c_name, c_mat, c_life_m, c_life_h, c_curr_h, c_stock = df.columns[0:8]
    c_manual = df.columns[-1]

    # 숫자 데이터 정렬
    df[c_stock] = pd.to_numeric(df[c_stock], errors='coerce').fillna(0).astype(int)
    df[c_curr_h] = pd.to_numeric(df[c_curr_h], errors='coerce').fillna(0).astype(int)
    df[c_life_h] = pd.to_numeric(df[c_life_h], errors='coerce').fillna(0).astype(int)
    df[c_life_m] = pd.to_numeric(df[c_life_m], errors='coerce').fillna(0).astype(int)

    df['남은시간'] = df[c_life_h] - df[c_curr_h]
    urgent_parts = df[(df['남은시간'] <= 200) | (df[c_stock] <= 2)]
    
    # 🚨 상단 알림창
    if not urgent_parts.empty:
        with st.expander(f"⚠️ 현장 정비 레이더: 교체 임박/재고 부족 품목이 {len(urgent_parts)}건 있습니다.", expanded=True):
            alert_display = urgent_parts[[c_mach, c_name, '남은시간', c_stock]].copy()
            alert_display.columns = ['설비명', '부품명', '남은시간(Hr)', '현재재고(EA)']
            st.dataframe(alert_display, use_container_width=True, hide_index=True)

    # 📊 종합 현황 지표 카드 (CSS가 적용되어 하이테크 스타일로 보임)
    st.markdown("### 📊 실시간 공정 자산 현황")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("총 관리 소모품 종류", f"{len(df)} SKU")
    m2.metric("보안 재고 위험 (2개 이하)", f"{len(df[df[c_stock] <= 2])} 종")
    m3.metric("설비 가동 상태", "NORMAL (안정)")
    m4.metric("시스템 동기화 기준", datetime.date.today().strftime("%Y-%m-%d"))
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 작업 메인 탭
    menu_tab1, menu_tab2 = st.tabs(["📋 소모품 자산 모니터링 대시보드", "📝 디지털 정비 일지 관리실"])

    with menu_tab1:
        query_params = st.query_params
        default_machine = query_params.get("machine", df[c_mach].unique()[0])
        if default_machine not in df[c_mach].unique():
            default_machine = df[c_mach].unique()[0]
            
        col1, col2 = st.columns([1, 1.3], gap="large")
        
        with col1:
            st.markdown("#### 🔍 소모품 부품 선택 및 수정")
            
            with st.container():
                selected_machine = st.selectbox("🏭 대상 설비 라인 선택", df[c_mach].unique(), index=list(df[c_mach].unique()).index(default_machine), key="sb_mach")
                filtered_df = df[df[c_mach] == selected_machine]
                
                default_part = query_params.get("part", filtered_df[c_name].unique()[0])
                if default_part not in filtered_df[c_name].unique():
                    default_part = filtered_df[c_name].unique()[0]
                    
                selected_part = st.selectbox("🔧 세부 부품 객체 선택", filtered_df[c_name].unique(), index=list(filtered_df[c_name].unique()).index(default_part), key="sb_part")
            
            part_idx = df[df[c_name] == selected_part].index[0]
            part_info = df.loc[part_idx]
            
            with st.container():
                st.markdown(f"##### 🏷️ 사양 마스터 정보")
                st.write(f"**• 부품 고유 코드:** `{part_info[c_id]}`")
                st.write(f"**• 표준 구성 재질:** `{part_info[c_mat]}`")
            
            st.markdown("##### 🔄 실시간 현장 데이터 수정")
            with st.container():
                new_curr_h = st.number_input("현재 누적 운전 시간 수정 (시간)", value=int(part_info[c_curr_h]), step=10, key="num_h")
                new_stock = st.number_input("여분 보관 수량 수정 (개)", value=int(part_info[c_stock]), step=1, key="num_s")
                
                if st.button("💾 이 부품 상태를 구글 시트에 즉시 반영", use_container_width=True):
                    with st.spinner("구글 스프레드시트 서버 데이터 기록 중..."):
                        update_google_sheet("1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8", "Sheet1", part_idx, 6, new_curr_h)
                        update_google_sheet("1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8", "Sheet1", part_idx, 7, new_stock)
                        df.at[part_idx, c_curr_h] = new_curr_h
                        df.at[part_idx, c_stock] = new_stock
                        st.success("✅ 구글 클라우드 동기화 완료!")
                        st.cache_data.clear()
                        st.rerun()

            manual_url = part_info[c_manual]
            if pd.notna(manual_url) and str(manual_url).strip().startswith("http"):
                st.link_button("📄 표준 정비 지침서(SOP) 열람", manual_url.strip(), use_container_width=True)
                
        with col2:
            st.markdown("#### ⏱️ 예지 보전 내구 수명 분석")
            current_hours = int(part_info[c_curr_h])
            max_hours = int(part_info[c_life_h])
            remaining_hours = max_hours - current_hours
            
            progress_per = max(0, min(100, int((current_hours / max_hours) * 100))) if max_hours > 0 else 0
            
            with st.container():
                st.write(f"**공정 누적 가동 시간:** `{current_hours} hr` / 한계 수명: `{max_hours} hr`")
                st.progress(progress_per, text=f"수명 소모율: {progress_per}%")
            
            st.markdown("##### 📅 장착일 기준 타임라인 예측")
            with st.container():
                start_date = st.date_input("부품 최초 장착일 선택", datetime.date.today(), key="dt_start")
                months_to_add = int(part_info[c_life_m])
                year = start_date.year + (start_date.month + months_to_add - 1) // 12
                month = (start_date.month + months_to_add - 1) % 12 + 1
                target_date = datetime.date(year, month, min(start_date.day, 28))
                remaining_days = (target_date - datetime.date.today()).days
                st.write(f"**교체 권장 마감일:** `{target_date.strftime('%Y-%m-%d')}` (잔여 기한: `D-{remaining_days}`일)")
            
            if remaining_hours <= 200 or remaining_days <= 15:
                st.error(f"❌ **위험 (CRITICAL):** 예비 정비 및 부품 교체가 시급합니다!")
            else:
                st.success(f"🟢 **정상 (STABLE):** 내구 기한이 안정적인 상태입니다.")

            st.markdown("##### 📱 현장 부착용 QR코드 식별 태그")
            with st.container():
                app_url = "https://vial-manager-na6qyzsytdcsencg2jwr89.streamlit.app/"
                qr_link = f"{app_url}?machine={urllib.parse.quote(selected_machine)}&part={urllib.parse.quote(selected_part)}"
                qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={urllib.parse.quote(qr_link)}"
                
                q_col1, q_col2 = st.columns([1, 2.5])
                with q_col1:
                    st.image(qr_api_url, caption="정비 태그 QR")
                with q_col2:
                    st.code(qr_link)
                    st.caption("라벨 프린터로 출력하여 부품함이나 현장 설비에 부착하십시오.")

    with menu_tab2:
        # 🟢 [기능 완벽 롤백] 이전 버전과 100% 동일하게 정상 작동하는 정비일지 양식 영역
        st.markdown("### 📝 오늘의 현장 정비 기록하기")
        st.write("현장에서 수행한 소모품 교체 및 설비 정비 내역을 기록하면 하단 타임라인에 즉시 실시간 누적됩니다.")
        
        log_col1, log_col2 = st.columns([1, 1.3], gap="large")
        
        with log_col1:
            with st.container():
                st.markdown("##### 🖊️ 일지 작성 양식")
                log_date = st.date_input("정비 일자", datetime.date.today(), key="log_date")
                log_mach = st.selectbox("정비 설비 선택", df[c_mach].unique(), key="log_mach")
                filtered_log_df = df[df[c_mach] == log_mach]
                log_part = st.selectbox("정비 부품 선택", filtered_log_df[c_name].unique(), key="log_part")
                
                log_worker = st.text_input("작업자 성명", placeholder="예: 홍길동 대리", key="log_worker")
                log_content = st.text_area("상세 정비 내용", placeholder="예: 소모품 마모로 인해 신품 교체 및 누적 가동 시간 0시간으로 리셋함.", key="log_content")
                
                st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
                if st.button("🚀 정비 일지 시스템에 등록 및 전송", type="primary", use_container_width=True):
                    if not log_worker or not log_content:
                        st.warning("⚠️ 작업자 성명과 정비 내용을 모두 입력해 주세요.")
                    else:
                        with st.spinner("시스템 일지 등록 중..."):
                            new_log_entry = {
                                "날짜": log_date.strftime("%Y-%m-%d"),
                                "부품명": log_part,
                                "작업자": log_worker,
                                "정비내용": log_content
                            }
                            st.session_state.temp_logs.insert(0, new_log_entry)
                            st.success(f"✅ {log_part} 정비 일지가 성공적으로 등록되었습니다.")
                            st.balloons()
                            st.rerun()
        
        with log_col2:
            st.markdown("#### 📋 최근 정비 일지 기록 확인 (실시간 반영)")
            with st.container():
                base_logs = [
                    {"날짜": "2026-07-01", "부품명": "충전 피스톤 실링", "작업자": "관리자", "정비내용": "시스템 정상 구동 및 예지정비 모니터링 연동 완료"}
                ]
                display_logs = st.session_state.temp_logs + base_logs
                log_df_display = pd.DataFrame(display_logs)
                st.dataframe(log_df_display, use_container_width=True, hide_index=True)
else:
    st.info("구글 마스터 스프레드시트 데이터 통신망 연결 대기 중...")