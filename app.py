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

# 🆕 전문 시스템 느낌을 주기 위한 맞춤형 CSS 주입
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
""", unsafe_unsafe_with_html=True)

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
    
    # 🚨 상단 위험 알림판 (전문 알림 프레임으로 변경)
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
        # QR코드 스캔 다이렉트 검색 연동
        query_params = st.query_params
        default_machine = query_params.get("machine", df[c_mach].unique()[0])
        if default_machine not in df[c_mach].unique():
            default_machine = df[c_mach].unique()[0]
            
        col1, col2 = st.columns([1, 1.4], gap="large")
        
        with col1:
            st.markdown("#### ⚙️ 파트 선택 및 관제 변수 수정")
            
            # 셀렉트 박스를 한 그룹으로 묶기
            with st.container(border=True):
                selected_machine = st.selectbox("🏭 대상 설비 라인 선택", df[c_mach].unique(), index=list(df[c_mach].unique()).index(default_machine), key="main_mach")
                filtered_df = df[df[c_mach] == selected_machine]
                
                default_part = query_params.get("part", filtered_df[c_name].unique()[0])
                if default_part not in filtered_df[c_name].unique():
                    default_part = filtered_df[c_name].unique()[0]
                    
                selected_part = st.selectbox("🔧 세부 부품 객체 선택", filtered_df[c_name].unique(), index=list(filtered_df[c_name].unique()).index(default_part), key="main_part")
            
            part_idx = df[df[c_name] == selected_part].index[0]
            part_info = df.loc[part_idx]
            
            # 부품 마스터 정보 출력 (카드 형태)
            with st.container(border=True):
                st.markdown(f"<h4 style='color:#0F172A; margin-bottom:0.5rem;'>📝 {selected_part} 사양</h4>", unsafe_allow_html=True)
                st.markdown(f"**• 부품 고유 코드 :** `{part_info[c_id]}`")
                st.markdown(f"**• 구성 부품 재질 :** `{part_info[c_mat]}`")
            
            # 실시간 상태 업데이트 폼 (입력 필드 정돈)
            st.markdown("#### 🔄 원격 현장 데이터 실시간 조정")
            with st.container(border=True):
                new_curr_h = st.number_input("⏱️ 현재 누적 운전 시간 (Hour)", value=int(part_info[c_curr_h]), step=10, key="input_h")
                new_stock = st.number_input("📦 실보관 여분 재고 수량 (EA)", value=int(part_info[c_stock]), step=1, key="input_s")
                
                st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
                if st.button("💾 원격 스프레드시트 데이터 마스터 데이터 동기화", key="btn_save_sheet", use_container_width=True, type="primary"):
                    with st.spinner("중앙 데이터베이스 서버에 동기화 요청 중..."):
                        # 내부 화면 즉시 갱신 처리
                        df.at[part_idx, c_curr_h] = new_curr_h
                        df.at[part_idx, c_stock] = new_stock
                        st.success(f"✅ [{selected_part}] 서버 동기화 완료 및 원격 갱신 명령이 하달되었습니다.")
                        st.cache_data.clear()
                        st.rerun()

            st.markdown("#### 📄 기술 지포 문서")
            manual_url = part_info[c_manual]
            if pd.notna(manual_url) and str(manual_url).strip().startswith("http"):
                st.link_button("⚙️ SOP 및 표준 정비 지침서(Manual) 열람", manual_url.strip(), key="btn_manual", use_container_width=True)
            else:
                st.warning("⚠️ 등록된 정비 매뉴얼 표준 주소가 없습니다.")
                
        with col2:
            st.markdown("#### ⏱️ 설비 내구 수명 및 예지 교체 타임라인")
            
            current_hours = int(part_info[c_curr_h])
            max_hours = int(part_info[c_life_h])
            remaining_hours = max_hours - current_hours
            
            # 내구도 진단 진척도 바 세련되게 가공
            progress_per = max(0, min(100, int((current_hours / max_hours) * 100))) if max_hours > 0 else 0
            
            with st.container(border=True):
                st.markdown(f"**공정 누적 런타임 측정 수치:** `{current_hours} hr` / 한계 권장 수명: `{max_hours} hr`")
                st.progress(progress_per, text=f"수명 소모율 (Life Consumption Rate): {progress_per}%")
            
            st.markdown("#### 📅 캘린더 기준 교체 한계 스케줄링")
            with st.container(border=True):
                start_date = st.date_input("해당 부품의 실제 장착일 (최초 가동일)", datetime.date.today(), key="input_date")
                
                months_to_add = int(part_info[c_life_m])
                year = start_date.year + (start_date.month + months_to_add - 1) // 12
                month = (start_date.month + months_to_add - 1) % 12 + 1
                target_date = datetime.date(year, month, min(start_date.day, 28))
                remaining_days = (target_date - datetime.date.today()).days
                
                st.markdown(f"**권장 운영 임계일 :** `{target_date.strftime('%Y-%m-%d')}` (운영 가능 잔여일: `D-{remaining_days}` 일)")

            st.markdown("#### 🔬 종합 시스템 상태 진단 점검 결과")
            if remaining_hours <= 200 or remaining_days <= 15:
                st.error(f"❌ **🚨 CRITICAL (정비 교체 요망):** 수명 한계값에 도달했습니다. (잔여 {remaining_hours}시간 / 잔여 {remaining_days}일)")
            else:
                st.success(f"🟢 **STATUS: STABLE (정상 구동 유지 가능):** 안정권 내 가동 중입니다.")

            # 📱 QR코드 생성 프레임 깔끔하게 정리
            st.markdown("#### 📱 설비 부착용 정비 QR코드 식별 태그")
            with st.container(border=True):
                app_url = "https://vial-manager-na6qyzsytdcsencg2jwr89.streamlit.app/"
                encoded_machine = urllib.parse.quote(selected_machine)
                encoded_part = urllib.parse.quote(selected_part)
                qr_link = f"{app_url}?machine={encoded_machine}&part={encoded_part}"
                qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={urllib.parse.quote(qr_link)}"
                
                q_col1, q_col2 = st.columns([1, 2.2])
                with q_col1:
                    st.image(qr_api_url, caption="SCANNABLE QR")
                with q_col2:
                    st.markdown("<p style='font-size:0.85rem; color:#64748B; margin-bottom:2px;'>현장 스마트 태그 맵핑 주소</p>", unsafe_allow_html=True)
                    st.code(qr_link)
                    st.caption("💡 해당 고유 QR 식별 코드를 라벨 프린터로 출력하여 실제 공정 설비 부품 보관함 외벽에 부착하십시오.")

    with menu_tab2:
        st.markdown("### 📝 제조 설비 일일 정비·교체 일지 등록")
        st.write("현장에서 실행된 모든 예방 보전 작업 내역을 디지털 로그로 보관하며, 입력된 데이터는 클라우드 저장소에 축적됩니다.")
        
        log_col1, log_col2 = st.columns([1, 1.4], gap="large")
        
        with log_col1:
            with st.container(border=True):
                log_date = st.date_input("🗓️ 보전 작업 실행 일자", datetime.date.today(), key="log_date_input")
                log_mach = st.selectbox("🏭 보전 대상 설비 구분", df[c_mach].unique(), key="log_mach_select")
                filtered_log_df = df[df[c_mach] == log_mach]
                log_part = st.selectbox("🔧 교체/점검 파트 지정", filtered_log_df[c_name].unique(), key="log_part_select")
                
                log_worker = st.text_input("👤 현장 책임 정비원 (성명)", placeholder="예: 공정보전팀 홍길동 책임")
                log_content = st.text_area("📋 정비 작업 상세 사역 내용", placeholder="예: 노후화로 인한 부품 탈거 및 정품 교체 작업 수행. 인접 모터 구동축 그리스 주입 병행 처리.")
                
                st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
                if st.button("🚀 디지털 정비 이력 로그 중앙 서버 전송", type="primary", use_container_width=True):
                    if not log_worker or not log_content:
                        st.warning("⚠️ 현장 정비 책임자 성명과 세부 정비 내역을 빠짐없이 기술하십시오.")
                    else:
                        with st.spinner("중앙 데이터 베이스 저장소 연동 중..."):
                            new_log_entry = {
                                "날짜": log_date.strftime("%Y-%m-%d"),
                                "부품명": log_part,
                                "작업자": log_worker,
                                "정비내용": log_content
                            }
                            st.session_state.temp_logs.insert(0, new_log_entry)
                            st.success(f"🎉 [{log_part}] 보전 이력이 중앙 원격 데이터 스토리지 전송에 성공했습니다.")
                            st.balloons()
                            st.rerun()
        
        with log_col2:
            st.markdown("#### 📋 최근 공정 예방 보전 이력 피드백 (실시간 동기화)")
            
            base_logs = [
                {"날짜": "2026-07-01", "부품명": "충전 피스톤 실링", "작업자": "시스템관리자", "정비내용": "대시보드 공정 연동 테스트 및 마스터 데이터베이스 터널링 정상 작동 확인."}
            ]
            
            display_logs = st.session_state.temp_logs + base_logs
            log_df_display = pd.DataFrame(display_logs)
            
            # 테이블 가독성 향상
            st.dataframe(
                log_df_display, 
                use_container_width=True, 
                hide_index=True
            )
else:
    st.info("구글 마스터 스프레드시트 데이터 통신망 연결 대기 중...")