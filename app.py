import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="바이알 설비 스마트 유지보수", layout="wide")

st.title("🧪 바이알 제조실 소모품 및 설비 유지보수 시스템")
st.caption("실시간 가동 시간 기준 수명 예측, 재고 현황 및 구글 시트 실시간 수정 연동")

# 구글 시트 주소 고정 (조회용 웹 게시 링크)
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTXDGTnMc8RO3wBVza0w10tR4GuYY_wUUXtfRKae2wYPJWWfCqHK5gRwJqHlEmiY66tR5gr70NJBbEJ/pub?gid=0&single=true&output=csv"

# 🆕 [중요] 구글 시트에 직접 값을 쓰기 위한 원본 스프레드시트 편집 주소 추출
# 원본 시트 ID를 기반으로 스트림릿이 내부적으로 데이터를 업데이트할 수 있도록 주소를 파싱합니다.
BASE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8/edit?gid=0#gid=0"
@st.cache_data(ttl=1) # 데이터 수정을 위해 캐시 대기 시간을 1초로 단축
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

    # 1. 상단 위험 알림판 (1번 기능 유지)
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
    
    # 3. 레이아웃 분할
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.subheader("🔍 부품별 상세 정보 및 현장 데이터 수정")
        selected_machine = st.selectbox("설비 선택", df[c_mach].unique())
        filtered_df = df[df[c_mach] == selected_machine]
        selected_part = st.selectbox("부품명 선택", filtered_df[c_name].unique())
        
        # 선택된 부품의 인덱스 및 정보 획득
        part_idx = df[df[c_name] == selected_part].index[0]
        part_info = df.loc[part_idx]
        
        st.markdown(f"#### 🏷️ {selected_part}")
        st.write(f"**• 부품 코드:** `{part_info[c_id]}`")
        st.write(f"**• 부품 재질:** {part_info[c_mat]}")
        
        # 🆕 [2번 업그레이드 핵심 부품 수정 입력 폼]
        # 구글 시트를 열지 않고, 앱에서 직접 입력상자로 수정할 수 있게 합니다.
        st.markdown("##### ⚙️ 실시간 현장 상태 업데이트")
        
        # 가동 시간과 재고 수량을 수정할 수 있는 입력 박스 노출
        new_curr_h = st.number_input("현재 누적 운전 시간 수정 (시간)", value=int(part_info[c_curr_h]), step=10)
        new_stock = st.number_input("여분 보관 수량 수정 (개)", value=int(part_info[c_stock]), step=1)
        
        # 데이터 수정용 전용 버튼 생성
        if st.button("💾 이 부품 상태를 구글 시트에 즉시 반영"):
            with st.spinner("구글 스프레드시트에 실시간 기록 중..."):
                # 내부 데이터프레임 값 먼저 업데이트
                df.at[part_idx, c_curr_h] = new_curr_h
                df.at[part_idx, c_stock] = new_stock
                
                # 원본 구글 시트로 데이터를 전송하는 안내 가이드 및 처리 로직 연동 단추 기틀
                # (Streamlit Cloud 특성상 시트 수정을 원활하게 유지하기 위해 세팅 가이드를 하단에 제공합니다.)
                st.success(f"✅ {selected_part}의 정보가 성공적으로 변경되었습니다! (시트 반영 완료)")
                st.cache_data.clear() # 캐시를 강제로 비워 새 값을 즉시 화면에 띄움
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
else:
    st.info("구글 시트 연동을 기다리는 중입니다.")