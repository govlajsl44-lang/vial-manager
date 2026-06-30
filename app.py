import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="바이알 설비 스마트 유지보수", layout="wide")

st.title("🧪 바이알 제조실 소모품 및 설비 유지보수 시스템")
st.caption("실시간 가동 시간 기준 수명 예측, 재고 현황 및 정비 매뉴얼 조회")

# 1. 구글 시트 연동 설정 (웹에 게시된 CSV URL 입력)
# 테스트를 위해 주소를 직접 고정하거나 화면에서 입력받을 수 있습니다.
# 반드시 주소 양옆에 따옴표(")가 있어야 에러가 안 납니다!
SHEET_CSV_URL = st.sidebar.text_input(
    "📊 구글 시트 CSV 링크 연결", 
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vTXDGTnMc8R03wBVza0w10tR4GuyY_wUUxtFRKae2wYPJWWfCqHK5gRwJQhLEmiY66tR5gr70NJBbEJ/pub?gid=0&single=true&output=csv"
)

@st.cache_data(ttl=60) # 1분마다 데이터 새로고침 허용
def load_data(url):
    try:
        df = pd.read_csv(url)
        # 공백 제거 및 기본 클리닝
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"구글 시트를 불러오는 중 오류가 발생했습니다. 주소를 확인해주세요. 에러: {e}")
        return None

df = load_data(SHEET_CSV_URL)

if df is not None:
    # 2. 상단 요약 대시보드 (전체 소모품 현황 및 여분 보관 수량 안전 자산 체크)
    st.markdown("### 📊 현재 제조실 소모품 자산 현황")
    total_parts = len(df)
    low_stock_parts = len(df[df['여분 보관 수량'] <= 2]) # 2개 이하인 경우 부족으로 간주
    
    m1, m2, m3 = st.columns(3)
    m1.metric("총 관리 소모품 종류", f"{total_parts} 종")
    m2.metric("보안 재고 부족 (2개 이하)", f"{low_stock_parts} 종", delta=f"-{low_stock_parts}" if low_stock_parts > 0 else "안전", delta_color="inverse")
    m3.metric("오늘 날짜", datetime.date.today().strftime("%Y-%m-%d"))
    
    st.markdown("---")
    
    # 3. 메인 기능 레이아웃 분할
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.subheader("🔍 부품별 상세 정보 확인")
        selected_machine = st.selectbox("설비 선택", df["소속 설비"].unique())
        
        filtered_df = df[df["소속 설비"] == selected_machine]
        selected_part = st.selectbox("부품명 선택", filtered_df["부품명"].unique())
        
        part_info = filtered_df[filtered_df["부품명"] == selected_part].iloc[0]
        
        # 부품 기본 스펙 카드 배치
        st.markdown(f"#### 🏷️ {selected_part}")
        st.write(f"**• 부품 코드:** `{part_info['부품 ID']}`")
        st.write(f"**• 부품 재질:** {part_info['재질']}")
        st.write(f"**• 권장 보증 수명:** {part_info['수명(개월)']}개월 / {part_info['권장 가동 수명(시간)']} 시간")
        
        # 여분 보관 수량 표시 시각화
        stock = int(part_info['여분 보관 수량'])
        if stock <= 2:
            st.error(f"🚨 **여분 보관 수량:** {stock}개 (재고 부족! 즉시 발주 필요)")
        else:
            st.success(f"📦 **여분 보관 수량:** {stock}개 (보안 재고 안전)")
            
        # 정비 매뉴얼 버튼 제공
        st.markdown("#### 📘 정비 매뉴얼")
        manual_url = part_info['정비 매뉴얼 링크']
        if pd.notna(manual_url) and str(manual_url).startswith("http"):
            st.link_button("📄 소모품 별 정비 매뉴얼 확인하기", manual_url)
        else:
            st.warning("등록된 정비 매뉴얼 링크가 유효하지 않거나 없습니다.")
            
    with col2:
        st.subheader("⏱️ 가동 시간 기반 수명 및 교체 예측")
        
        # 실제 가동 시간 확인 및 입력 수정 바 구현
        current_hours = int(part_info['현재 누적 운전 시간(시간)'])
        max_hours = int(part_info['권장 가동 수명(시간)'])
        
        st.write(f"**제조 실 실제 측정 누적 운전 시간:** `{current_hours} 시간` / 전체 수명: `{max_hours} 시간`")
        
        # 수명 잔여 진행률 시각화
        remaining_hours = max_hours - current_hours
        progress_per = max(0, min(100, int((current_hours / max_hours) * 100)))
        
        st.progress(progress_per, text=f"수명 소모율: {progress_per}%")
        
        # 날짜 기준 추가 연산 대시보드
        st.markdown("##### 📅 장착 기한 기준 계산")
        start_date = st.date_input("해당 부품의 현재 장착일(사용 시작일)을 선택하세요", datetime.date.today())
        
        months_to_add = int(part_info['수명(개월)'])
        year = start_date.year + (start_date.month + months_to_add - 1) // 12
        month = (start_date.month + months_to_add - 1) % 12 + 1
        day = min(start_date.day, 28) # 날짜 마감 예외처리 단순화
        target_date = datetime.date(year, month, day)
        
        remaining_days = (target_date - datetime.date.today()).days
        
        # 최종 정비 판단
        st.markdown("#### 🚨 종합 정비 진단 점검")
        
        # 조건 1: 시간 마모도 판정, 조건 2: 달력 기준 판정
        if remaining_hours <= 200 or remaining_days <= 15:
            st.error(f"❗ **교체 주기 임박 (위험):** 가동 시간이 {remaining_hours}시간 남았거나, 날짜가 {remaining_days}일 남았습니다. 예방 정비를 수행하세요.")
        else:
            st.success(f"✅ **정상 가동 가능:** 잔여 시간 {remaining_hours}시간 / 잔여 일수 D-{remaining_days}일")

else:
    st.info("👈 구글 시트에서 '웹에 게시(CSV)'를 진행한 후 해당 URL 주소를 사이드바에 입력해 주세요.")
