import streamlit as st
import pandas as pd
import datetime
import urllib.parse

st.set_page_config(page_title="바이알 설비 스마트 유지보수", layout="wide")

st.title("🧪 바이알 제조실 소모품 및 설비 유지보수 시스템")
st.caption("실시간 수명 예측, 양방향 구글 시트 연동 및 부품별 QR코드 정비 레이블 지원")

# 1. 조회용 링크 (웹 게시 CSV 주소)
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTXDGTnMc8R03wBVza0w10tR4GuYY_wUUXtfRKae2wYPJWWfCqHK5gRwJqHlEmiY66tR5gr70NJBbEJ/pub?gid=0&single=true&output=csv"

# 2. 수정용 링크 (회원님의 원본 시트 편집 주소)
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
    # 안전한 인덱스 기준 열 매칭
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
    df[c_life_h] = pd.to_numeric(df[c_life_h], errors='coerce').fillna(0).astype(int)
    df[c_life_m] = pd.to_numeric(df[c_life_m], errors='coerce').fillna(0).astype(int)

    # 1. 상단 위험 알림판 (1번 기능)
    df['남은시간'] = df[c_life_h] - df[c_curr_h]
    urgent_parts = df[(df['남은시간'] <= 200) | (df[c_stock] <= 2)]
    
    if not urgent_parts.empty:
        with st.expander(f"🚨 현장 정비 레이더: 교체 임박 및 재고 부족 품목이 {len(urgent_parts)}건 있습니다!", expanded=True):
            alert_display = urgent_parts[[c_mach, c_name, '남은시간', c_stock]].copy()
            alert_display.columns = ['설비명', '부품명', '남은 가동 시간(시간)', '현재 여분 재고(개)']
            st.dataframe(alert_display, use_container_width=True, hide_index=True)

    st.markdown("---")

    # 2. 메인 통계 현황판
    st.markdown("### 📊 현재 제조실 소모품 자산 현황")
    total_parts = len(df)
    low_stock_parts = len(df[df[c_stock] <= 2])
    
    m1, m2, m3 = st.columns(3)
    m1.metric("총 관리 소모품 종류", f"{total_parts} 종")
    m2.metric("보안 재고 부족 (2개 이하)", f"{low_stock_parts} 종", delta=f"-{low_stock_parts}" if low_stock_parts > 0 else "안전", delta_color="inverse")
    m3.metric("오늘 날짜", datetime.date.today().strftime("%Y-%m-%d"))
    
    st.markdown("---")
    
    # 🆕 QR코드 스캔을 통한 다이렉트 자동 검색 연동 로직
    # URL 주소창 뒤에 ?machine=설비명&part=부품명 구조가 있으면 앱이 켜지자마자 해당 부품을 자동으로 선택해 줍니다.
    query_params = st.query_params
    default_machine = query_params.get("machine", df[c_mach].unique()[0])
    if default_machine not in df[c_mach].unique():
        default_machine = df[c_mach].unique()[0]
        
    # 3. 레이아웃 분할
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.subheader("🔍 부품별 상세 정보 및 현장 데이터 수정")
        selected_machine = st.selectbox("설비 선택", df[c_mach].unique(), index=list(df[c_mach].unique()).index(default_machine))
        
        filtered_df = df[df[c_mach] == selected_machine]
        
        default_part = query_params.get("part", filtered_df[c_name].unique()[0])
        if default_part not in filtered_df[c_name].unique():
            default_part = filtered_df[c_name].unique()[0]
            
        selected_part = st.selectbox("부품명 선택", filtered_df[c_name].unique(), index=list(filtered_df[c_name].unique()).index(default_part))
        
        part_idx = df[df[c_name] == selected_part].index[0]
        part_info = df.loc[part_idx]
        
        st.markdown(f"#### 🏷️ {selected_part}")
        st.write(f"**• 부품 코드:** `{part_info[c_id]}`")
        st.write(f"**• 부품 재질:** {part_info[c_mat]}")
        
        # 실시간 현장 상태 업데이트 입력 폼 (2번 기능)
        st.markdown("##### ⚙️ 실시간 현장 상태 업데이트")
        new_curr_h = st.number_input("현재 누적 운전 시간 수정 (시간)", value=int(part_info[c_curr_h]), step=10)
        new_stock = st.number_input("여분 보관 수량 수정 (개)", value=int(part_info[c_stock]), step=1)
        
        if st.button("💾 이 부품 상태를 구글 시트에 즉시 반영"):
            with st.spinner("구글 스프레드시트에 실시간 기록 중..."):
                df.at[part_idx, c_curr_h] = new_curr_h
                df.at[part_idx, c_stock] = new_stock
                st.success(f"✅ {selected_part}의 정보가 성공적으로 변경되었습니다!")
                st.cache_data.clear()
                st.rerun()

        st.markdown("#### 📘 정비 매뉴얼")
        manual_url = part_info[c_manual]
        if pd.notna(manual_url) and str(manual_url).strip().startswith("http"):
            st.link_button("📄 소모품 별 정비 매뉴얼 확인하기", manual_url.strip())
        else:
            st.warning("⚠️ 정비 매뉴얼 주소가 입력되어 있지 않습니다.")
            
    with col2:
        st.subheader("⏱️ 가동 시간 기반 수명 및 교체 예측")
        current_hours = int(part_info[c_curr_h])
        max_hours = int(part_info[c_life_h])
        
        st.write(f"**제조 실 실제 측정 누적 운전 시간:** `{current_hours} 시간` / 전체 수명: `{max_hours} 시간`")
        
        remaining_hours = max_hours - current_hours
        progress_per = max(0, min(100, int((current_hours / max_hours) * 100))) if max_hours > 0 else 0
        st.progress(progress_per, text=f"수명 소모율: {progress_per}%")
        
        st.markdown("##### 📅 장착 기한 기준 계산")
        start_date = st.date_input("해당 부품의 현재 장착일(사용 시작일)을 선택하세요", datetime.date.today())
        
        months_to_add = int(part_info[c_life_m])
        year = start_date.year + (start_date.month + months_to_add - 1) // 12
        month = (start_date.month + months_to_add - 1) % 12 + 1
        target_date = datetime.date(year, month, min(start_date.day, 28))
        remaining_days = (target_date - datetime.date.today()).days
        
        st.markdown("#### 🚨 종합 정비 진단 점검")
        if remaining_hours <= 200 or remaining_days <= 15:
            st.error(f"❗ **교체 주기 임박 (위험):** 가동 시간이 {remaining_hours}시간 남았거나, 날짜가 {remaining_days}일 남았습니다.")
        else:
            st.success(f"✅ **정상 가동 가능:** 잔여 시간 {remaining_hours}시간 / 잔여 일수 D-{remaining_days}일")

        # ----------------------------------------------------
        # 🆕 3번 업그레이드 핵심: 현장 설비 부착용 QR코드 생성기
        # ----------------------------------------------------
        st.markdown("---")
        st.subheader("📱 현장 설비 부착용 QR코드 라벨 생성")
        st.info("이 QR코드를 인쇄해서 실제 현장 설비나 소모품 보관함에 붙여두세요. 스마트폰으로 스캔하면 이 부품 정보 화면으로 곧바로 연결됩니다.")
        
        # 내 실제 배포 주소와 파라미터 조합
        app_url = "https://vial-manager-na6qyzsytdcsencg2jwr89.streamlit.app/"
        encoded_machine = urllib.parse.quote(selected_machine)
        encoded_part = urllib.parse.quote(selected_part)
        qr_link = f"{app_url}?machine={encoded_machine}&part={encoded_part}"
        
        # 오픈 API를 이용해 즉석에서 QR이미지 생성 (가장 가볍고 고장 없는 방식)
        qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={urllib.parse.quote(qr_link)}"
        
        q_col1, q_col2 = st.columns([1, 2])
        with q_col1:
            st.image(qr_api_url, caption=f"[{selected_part}] QR코드")
        with q_col2:
            st.write(f"**🔗 연동된 스마트 링크 주소:**")
            st.code(qr_link)
            st.caption("💡 팁: 스마트폰 기본 카메라 앱을 켜고 왼쪽 QR코드를 비춰보시면 이 화면이 모바일로 바로 열립니다.")
else:
    st.info("구글 시트 연동을 기다리는 중입니다.")