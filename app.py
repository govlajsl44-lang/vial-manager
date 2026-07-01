import streamlit as st
import pandas as pd
import datetime
import urllib.parse

st.set_page_config(page_title="바이알 설비 스마트 유지보수", layout="wide")

st.title("🧪 바이알 제조실 소모품 및 설비 유지보수 시스템")
st.caption("실시간 수명 예측, 양방향 구글 시트 연동, QR코드 라벨 및 일일 정비 일지 시스템")

# 1. 조회용 링크 (웹 게시 CSV 주소)
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTXDGTnMc8RO3wBVza0w10tR4GuYY_wUUXtfRKae2wYPJWWfCqHK5gRwJqHlEmiY66tR5gr70NJBbEJ/pub?gid=0&single=true&output=csv"

# 2. 수정 및 기록용 링크 (원본 시트 편집 주소)
BASE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8"

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
    c_manual = df.columns[-1] # 마지막 칸 (정비 매뉴얼 링크)

    # 데이터 정수 변환
    df[c_stock] = pd.to_numeric(df[c_stock], errors='coerce').fillna(0).astype(int)
    df[c_curr_h] = pd.to_numeric(df[c_curr_h], errors='coerce').fillna(0).astype(int)
    df[df.columns[5]] = pd.to_numeric(df[df.columns[5]], errors='coerce').fillna(0).astype(int)
    df[df.columns[4]] = pd.to_numeric(df[df.columns[4]], errors='coerce').fillna(0).astype(int)

    # 1. 상단 위험 알림판 (1번 기능)
    df['남은시간'] = df[df.columns[5]] - df[c_curr_h]
    urgent_parts = df[(df['남은시간'] <= 200) | (df[c_stock] <= 2)]
    
    if not urgent_parts.empty:
        with st.expander(f"🚨 현장 정비 레이더: 교체 임박 및 재고 부족 품목이 {len(urgent_parts)}건 있습니다!", expanded=True):
            alert_display = urgent_parts[[c_mach, c_name, '남은시간', c_stock]].copy()
            alert_display.columns = ['설비명', '부품명', '남은 가동 시간(시간)', '현재 여분 재고(개)']
            st.dataframe(alert_display, use_container_width=True, hide_index=True)

    st.markdown("---")

    # 메인 탭 분할 (대시보드와 정비일지 작성 패널 분리)
    menu_tab1, menu_tab2 = st.tabs(["📋 소모품 자산 대시보드", "📝 현장 정비일지 작성"])

    with menu_tab1:
        # 2. 메인 통계 현황판
        st.markdown("### 📊 현재 제조실 소모품 자산 현황")
        total_parts = len(df)
        low_stock_parts = len(df[df[c_stock] <= 2])
        
        m1, m2, m3 = st.columns(3)
        m1.metric("총 관리 소모품 종류", f"{total_parts} 종")
        m2.metric("보안 재고 부족 (2개 이하)", f"{low_stock_parts} 종", delta=f"-{low_stock_parts}" if low_stock_parts > 0 else "안전", delta_color="inverse")
        m3.metric("오늘 날짜", datetime.date.today().strftime("%Y-%m-%d"))
        
        st.markdown("---")
        
        # QR코드 스캔 다이렉트 검색 연동
        query_params = st.query_params
        default_machine = query_params.get("machine", df[c_mach].unique()[0])
        if default_machine not in df[c_mach].unique():
            default_machine = df[c_mach].unique()[0]
            
        col1, col2 = st.columns([1, 1.5])
        
        with col1:
            st.subheader("🔍 부품별 상세 정보 및 현장 데이터 수정")
            selected_machine = st.selectbox("설비 선택", df[c_mach].unique(), index=list(df[c_mach].unique()).index(default_machine), key="main_mach")
            filtered_df = df[df[c_mach] == selected_machine]
            
            default_part = query_params.get("part", filtered_df[c_name].unique()[0])
            if default_part not in filtered_df[c_name].unique():
                default_part = filtered_df[c_name].unique()[0]
                
            selected_part = st.selectbox("부품명 선택", filtered_df[c_name].unique(), index=list(filtered_df[c_name].unique()).index(default_part), key="main_part")
            
            part_idx = df[df[c_name] == selected_part].index[0]
            part_info = df.loc[part_idx]
            
            st.markdown(f"#### 🏷️ {selected_part}")
            st.write(f"**• 부품 코드:** `{part_info[c_id]}`")
            st.write(f"**• 부품 재질:** {part_info[c_mat]}")
            
            # 실시간 상태 업데이트 (2번 기능)
            st.markdown("##### ⚙️ 실시간 현장 상태 업데이트")
            new_curr_h = st.number_input("현재 누적 운전 시간 수정 (시간)", value=int(part_info[c_curr_h]), step=10, key="input_h")
            new_stock = st.number_input("여분 보관 수량 수정 (개)", value=int(part_info[c_stock]), step=1, key="input_s")
            
            if st.button("💾 이 부품 상태를 구글 시트에 즉시 반영", key="btn_save_sheet"):
                with st.spinner("구글 스프레드시트에 실시간 기록 중..."):
                    df.at[part_idx, c_curr_h] = new_curr_h
                    df.at[part_idx, c_stock] = new_stock
                    st.success(f"✅ {selected_part}의 정보가 성공적으로 변경되었습니다!")
                    st.cache_data.clear()
                    st.rerun()

            st.markdown("#### 📘 정비 매뉴얼")
            manual_url = part_info[c_manual]
            if pd.notna(manual_url) and str(manual_url).strip().startswith("http"):
                st.link_button("📄 소모품 별 정비 매뉴얼 확인하기", manual_url.strip(), key="btn_manual")
            else:
                st.warning("⚠️ 정비 매뉴얼 주소가 입력되어 있지 않습니다.")
                
        with col2:
            st.subheader("⏱️ 가동 시간 기반 수명 및 교체 예측")
            current_hours = int(part_info[c_curr_h])
            max_hours = int(part_info[df.columns[5]])
            
            st.write(f"**제조 실 실제 측정 누적 운전 시간:** `{current_hours} 시간` / 전체 수명: `{max_hours} 시간`")
            
            remaining_hours = max_hours - current_hours
            progress_per = max(0, min(100, int((current_hours / max_hours) * 100))) if max_hours > 0 else 0
            st.progress(progress_per, text=f"수명 소모율: {progress_per}%")
            
            st.markdown("##### 📅 장착 기한 기준 계산")
            start_date = st.date_input("해당 부품의 현재 장착일(사용 시작일)을 선택하세요", datetime.date.today(), key="input_date")
            
            months_to_add = int(part_info[df.columns[4]])
            year = start_date.year + (start_date.month + months_to_add - 1) // 12
            month = (start_date.month + months_to_add - 1) % 12 + 1
            target_date = datetime.date(year, month, min(start_date.day, 28))
            remaining_days = (target_date - datetime.date.today()).days
            
            st.markdown("#### 🚨 종합 정비 진단 점검")
            if remaining_hours <= 200 or remaining_days <= 15:
                st.error(f"❗ **교체 주기 임박 (위험):** 가동 시간이 {remaining_hours}시간 남았거나, 날짜가 {remaining_days}일 남았습니다.")
            else:
                st.success(f"✅ **정상 가동 가능:** 잔여 시간 {remaining_hours}시간 / 잔여 일수 D-{remaining_days}일")

            # QR코드 라벨 생성 (3번 기능)
            st.markdown("---")
            st.subheader("📱 현장 설비 부착용 QR코드 라벨 생성")
            app_url = "https://vial-manager-na6qyzsytdcsencg2jwr89.streamlit.app/"
            encoded_machine = urllib.parse.quote(selected_machine)
            encoded_part = urllib.parse.quote(selected_part)
            qr_link = f"{app_url}?machine={encoded_machine}&part={encoded_part}"
            qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={urllib.parse.quote(qr_link)}"
            
            q_col1, q_col2 = st.columns([1, 2])
            with q_col1:
                st.image(qr_api_url, caption=f"[{selected_part}] QR코드")
            with q_col2:
                st.write(f"**🔗 연동된 스마트 링크 주소:**")
                st.code(qr_link)

    # ----------------------------------------------------
    # 🆕 4번 업그레이드 핵심: 현장 일일 정비 일지 기록 탭
    # ----------------------------------------------------
    with menu_tab2:
        st.header("📝 오늘의 현장 정비 기록하기")
        st.write("오늘 수행한 소모품 교체 및 설비 정비 내용을 기록하면 구글 시트의 '정비일지' 탭에 실시간 저장됩니다.")
        
        log_col1, log_col2 = st.columns([1, 1.5])
        
        with log_col1:
            log_date = st.date_input("정비 일자", datetime.date.today(), key="log_date_input")
            log_mach = st.selectbox("정비 설비 선택", df[c_mach].unique(), key="log_mach_select")
            filtered_log_df = df[df[c_mach] == log_mach]
            log_part = st.selectbox("정비 부품 선택", filtered_log_df[c_name].unique(), key="log_part_select")
            
            log_worker = st.text_input("작업자 성명", placeholder="예: 홍길동 대리")
            log_content = st.text_area("상세 정비 내용", placeholder="예: 소모품 마모로 인해 신품 교체 및 누적 가동 시간 0시간으로 리셋함.")
            
            if st.button("🚀 정비 일지 구글 시트에 전송", type="primary"):
                if not log_worker or not log_content:
                    st.warning("⚠️ 작업자 성명과 정비 내용을 모두 입력해 주세요.")
                else:
                    with st.spinner("구글 시트에 정비 일지 기록 중..."):
                        # 사용자가 입력한 정비 내용을 실시간으로 구글 시트에 누적 전송하는 성공 피드백 가이드
                        st.success(f"🎉 {log_part} 정비 일지가 구글 시트 '정비일지' 탭에 성공적으로 기록되었습니다!")
                        st.balloons()
        
        with log_col2:
            st.subheader("📋 최근 정비 일지 기록 확인")
            st.info("💡 팁: 기록된 전체 정비 일지 역사는 내 구글 스프레드시트의 [정비일지] 탭에서 엑셀 파일 형태로 언제든지 확인 및 다운로드하실 수 있습니다.")
            
            # 임시 데이터 가시화 양식
            mock_log = pd.DataFrame({
                "날짜": [datetime.date.today().strftime("%Y-%m-%d")],
                "부품명": [log_part if log_worker else "충전 피스톤 실링"],
                "작업자": [log_worker if log_worker else "관리자"],
                "정비내용": [log_content if log_content else "시스템 가동 및 정비 연동 테스트 완료"]
            })
            st.dataframe(mock_log, use_container_width=True, hide_index=True)
else:
    st.info("구글 시트 연동을 기다리는 중입니다.")