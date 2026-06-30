import streamlit as st
import pandas as pd
import datetime
import google.generativeai as genai
from PIL import Image

st.set_page_config(page_title="바이알 설비 스마트 유지보수", layout="wide")

st.title("🧪 바이알 제조실 소모품 및 설비 유지보수 시스템")
st.caption("실시간 가동 시간 기준 수명 예측, 재고 현황 및 AI 부품 인식 레이더")

# [보안 설정] Gemini API 키 설정 (AI 사진 인식을 위한 엔진)
GEMINI_API_KEY = st.sidebar.text_input("🔑 Gemini API Key 입력", type="password", value="")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# 1. 구글 시트 연동 설정 (회원님의 진짜 주소 입력 완료)
SHEET_CSV_URL = st.sidebar.text_input(
    "📊 구글 시트 CSV 링크 연결", 
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vTXDGTnMc8RO3wBVza0w10tR4GuYY_wUUXtfRKae2wYPJWWfCqHK5gRwJqHlEmiY66tR5gr70NJBbEJ/pub?gid=0&single=true&output=csv"
)

@st.cache_data(ttl=10) # 빠른 테스트를 위해 새로고침 주기 10초로 단축
def load_data(url):
    try:
        df = pd.read_csv(url)
        # 구글 시트 열 이름의 앞뒤 공백과 띄어쓰기를 완벽히 제거하여 매칭 확률 최대로 상승
        df.columns = df.columns.str.strip().str.replace(' ', '')
        return df
    except Exception as e:
        st.error(f"구글 시트를 불러오는 중 오류가 발생했습니다: {e}")
        return None

df = load_data(SHEET_CSV_URL)

if df is not None:
    # 구글 시트 열 이름을 한글 패치 및 자동 매칭
    # 띄어쓰기 예외 처리를 위해 컬럼 맵핑 진행
    col_mapping = {col: col for col in df.columns}
    
    def get_col(target_name):
        # 띄어쓰기 없는 타겟 명칭과 매칭되는 실제 컬럼명 반환
        for col in df.columns:
            if col == target_name.replace(' ', ''):
                return col
        return df.columns[0] # 없으면 첫번째 열 반환 (에러 방지용 안전장치)

    # 안전하게 열 매칭 진행
    c_id = get_col("부품ID")
    c_mach = get_col("소속설비")
    c_name = get_col("부품명")
    c_mat = get_col("재질")
    c_life_m = get_col("수명(개월)")
    c_life_h = get_col("권장가동수명(시간)")
    c_curr_h = get_col("현재누적운전시간(시간)")
    c_stock = get_col("여분보관수량")
    c_manual = get_col("정비매뉴얼링크")
    c_note = get_col("비고")

    # 탭 메뉴 구성
    tab1, tab2 = st.tabs(["📋 소모품 자산 대시보드", "📷 AI 부품 스캔 레이더"])
    
    with tab1:
        st.markdown("### 📊 현재 제조실 소모품 자산 현황")
        
        # 데이터 정수 변환 및 에러 방지 처리
        df[c_stock] = pd.to_numeric(df[c_stock], errors='coerce').fillna(0).astype(int)
        df[c_curr_h] = pd.to_numeric(df[c_curr_h], errors='coerce').fillna(0).astype(int)
        df[c_life_h] = pd.to_numeric(df[c_life_h], errors='coerce').fillna(0).astype(int)
        df[c_life_m] = pd.to_numeric(df[c_life_m], errors='coerce').fillna(0).astype(int)

        total_parts = len(df)
        low_stock_parts = len(df[df[c_stock] <= 2])
        
        m1, m2, m3 = st.columns(3)
        m1.metric("총 관리 소모품 종류", f"{total_parts} 종")
        m2.metric("보안 재고 부족 (2개 이하)", f"{low_stock_parts} 종", delta=f"-{low_stock_parts}" if low_stock_parts > 0 else "안전", delta_color="inverse")
        m3.metric("오늘 날짜", datetime.date.today().strftime("%Y-%m-%d"))
        
        st.markdown("---")
        col1, col2 = st.columns([1, 1.5])
        
        with col1:
            st.subheader("🔍 부품별 상세 정보 확인")
            selected_machine = st.selectbox("설비 선택", df[c_mach].unique(), key="sb_mach")
            
            filtered_df = df[df[c_mach] == selected_machine]
            selected_part = st.selectbox("부품명 선택", filtered_df[c_name].unique(), key="sb_part")
            
            part_info = filtered_df[filtered_df[c_name] == selected_part].iloc[0]
            
            st.markdown(f"#### 🏷️ {selected_part}")
            st.write(f"**• 부품 코드:** `{part_info[c_id]}`")
            st.write(f"**• 부품 재질:** {part_info[c_mat]}")
            st.write(f"**• 권장 보증 수명:** {part_info[c_life_m]}개월 / {part_info[c_life_h]} 시간")
            
            stock = int(part_info[c_stock])
            if stock <= 2:
                st.error(f"🚨 **여분 보관 수량:** {stock}개 (재고 부족! 즉시 발주 필요)")
            else:
                st.success(f"📦 **여분 보관 수량:** {stock}개 (보안 재고 안전)")
                
            st.markdown("#### 📘 정비 매뉴얼")
            manual_url = part_info[c_manual]
            if pd.notna(manual_url) and str(manual_url).startswith("http"):
                st.link_button("📄 소모품 별 정비 매뉴얼 확인하기", manual_url)
            else:
                st.warning("등록된 정비 매뉴얼 링크가 없거나 주소가 올바르지 않습니다.")
                
        with col2:
            st.subheader("⏱️ 가동 시간 기반 수명 및 교체 예측")
            
            current_hours = int(part_info[c_curr_h])
            max_hours = int(part_info[c_life_h])
            
            st.write(f"**제조 실 실제 측정 누적 운전 시간:** `{current_hours} 시간` / 전체 수명: `{max_hours} 시간`")
            
            remaining_hours = max_hours - current_hours
            progress_per = max(0, min(100, int((current_hours / max_hours) * 100))) if max_hours > 0 else 0
            st.progress(progress_per, text=f"수명 소모율: {progress_per}%")
            
            st.markdown("##### 📅 장착 기한 기준 계산")
            start_date = st.date_input("해당 부품의 현재 장착일(사용 시작일)을 선택하세요", datetime.date.today(), key="dt_start")
            
            months_to_add = int(part_info[c_life_m])
            year = start_date.year + (start_date.month + months_to_add - 1) // 12
            month = (start_date.month + months_to_add - 1) % 12 + 1
            target_date = datetime.date(year, month, min(start_date.day, 28))
            
            remaining_days = (target_date - datetime.date.today()).days
            
            st.markdown("#### 🚨 종합 정비 진단 점검")
            if remaining_hours <= 200 or remaining_days <= 15:
                st.error(f"❗ **교체 주기 임박 (위험):** 가동 시간이 {remaining_hours}시간 남았거나, 날짜가 {remaining_days}일 남았습니다. 예방 정비를 수행하세요.")
            else:
                st.success(f"✅ **정상 가동 가능:** 잔여 시간 {remaining_hours}시간 / 잔여 일수 D-{remaining_days}일")

    with tab2:
        st.header("📷 스마트폰 카메라 부품 스캔")
        st.write("현장에서 부품 사진을 촬영하거나 업로드하면 AI가 재질을 판별하고 데이터베이스에서 일치하는 부품 코드를 매칭합니다.")
        
        if not GEMINI_API_KEY:
            st.warning("⚠️ 사진 인식 기능을 사용하려면 왼쪽 사이드바 창을 열고 'Gemini API Key'를 입력해 주세요.")
        else:
            uploaded_file = st.file_uploader("부품 사진을 찍거나 이미지를 선택하세요", type=["jpg", "jpeg", "png"])
            
            if uploaded_file is not None:
                image = Image.open(uploaded_file)
                st.image(image, caption="촬영된 부품 이미지", width=300)
                
                if st.button("🚀 AI 부품 분석 시작"):
                    with st.spinner("AI가 이미지 분석 및 재질 매칭 중..."):
                        try:
                            parts_list_string = "\n".join([f"- 코드: {r[c_id]}, 이름: {r[c_name]}, 재질: {r[c_mat]}" for _, r in df.iterrows()])
                            
                            prompt = f"""
                            너는 바이알 제조공장(충전기, 캡핑기)의 정비 전문가야.
                            제공된 이미지 속 부품이 아래 공장 데이터베이스 리스트 중 어느 부품과 가장 유사한지 식별해줘.
                            
                            [우리 공장 부품 데이터베이스 리스트]
                            {parts_list_string}
                            
                            반드시 아래 양식으로만 답변을 출력해줘:
                            부품코드: [가장 일치하는 부품 ID]
                            판별재질: [이미지 분석을 통해 파악된 부품의 재질 예: 실리콘, SUS316L, 세라믹 등]
                            판별이유: [간단한 외관적 분석 근거 2줄 이내]
                            """
                            
                            model = genai.GenerativeModel('gemini-1.5-flash')
                            response = model.generate_content([prompt, image])
                            
                            st.success("🤖 AI 분석 결과 완료!")
                            st.text_area("AI 진단서", value=response.text, height=150)
                            
                            for _, row in df.iterrows():
                                if row[c_id] in response.text:
                                    st.info(f"💡 AI가 매칭된 부품을 찾았습니다: **[{row[c_mach]} - {row[c_name]}]**")
                                    break
                        except Exception as e:
                            st.error(f"AI 연동 실패: {e}")
else:
    st.info("👈 구글 시트 주소를 연결해 주세요.")