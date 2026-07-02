import streamlit as st
import pandas as pd
import datetime
import urllib.parse
import requests

# 1. 하이브리드 반응형 페이지 레이아웃 정의
st.set_page_config(
    page_title="Vial Line Smart MES Pro", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 📱 모바일 가시성 극대화를 위한 프리미엄 하이브리드 CSS 테마 주입
st.markdown("""
    <style>
    /* 기본 배경 및 여백 설정 */
    .main { background-color: #F8FAFC !important; }
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; max-width: 98% !important; }
    
    /* 타이틀 모바일 최적화 */
    h1 {
        color: #0F172A !important;
        font-weight: 800 !important;
        font-size: 1.8rem !important;
        border-bottom: 3px solid #0284C7;
        padding-bottom: 8px;
        margin-bottom: 15px !important;
    }
    h2, h3, h4 { color: #1E293B !important; font-weight: 700 !important; margin-top: 0.8rem !important; }
    
    /* 대형 관제 메트릭 카드 가시성 확보 */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-top: 4px solid #0284C7 !important;
        padding: 0.8rem !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05) !important;
        margin-bottom: 8px !important;
    }
    div[data-testid="stMetricLabel"] p { font-size: 0.8rem !important; color: #475569 !important; font-weight: 700 !important; }
    div[data-testid="stMetricValue"] div { font-size: 1.4rem !important; font-weight: 800 !important; color: #0F172A !important; }
    
    /* 모바일 스크롤용 카드 형태 컨테이너 */
    div[data-testid="stContainer"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        padding: 1rem !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.05) !important;
        margin-bottom: 10px !important;
    }
    
    /* 모바일 엄지손가락 터치 전용 버튼 스타일 고도화 */
    .stButton>button { 
        font-weight: 700 !important; 
        border-radius: 6px !important; 
        padding: 0.6rem 1rem !important;
        font-size: 1rem !important;
    }
    
    /* 상단 탭 모바일 스크롤 지원 및 폰트 강조 */
    button[data-baseweb="tab"] { font-size: 0.95rem !important; font-weight: 700 !important; color: #64748B !important; }
    button[aria-selected="true"] { color: #0284C7 !important; border-bottom-color: #0284C7 !important; }
    
    /* 📱 미디어 쿼리: 모바일 화면(폭 768px 이하) 특화 반응형 레이아웃 보정 */
    @media (max-width: 768px) {
        .block-container { padding-left: 0.4rem !important; padding-right: 0.4rem !important; }
        h1 { font-size: 1.35rem !important; }
        div[data-testid="stMetricValue"] div { font-size: 1.2rem !important; }
        button[data-baseweb="tab"] { font-size: 0.85rem !important; padding-left: 8px !important; padding-right: 8px !important; }
        .stButton>button { font-size: 0.95rem !important; }
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏭 바이알 라인 예지정비 관제탑 (MES Pro)")

# 0초 무지연 실시간 라이브 데이터 주소
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8/export?format=csv&gid=0"

# 🔑 Secrets 상자에서 안전하게 환경 변수 호출
if "MACRO_URL" in st.secrets:
    LIVE_MACRO_URL = st.secrets["MACRO_URL"]
    LIVE_SHEET_NAME = st.secrets.get("SHEET_NAME", "시트1")
else:
    st.error("⚠️ [설정 누락] Streamlit 웹 관리자화면 Secrets에 MACRO_URL을 등록하셔야 구글 시트 저장이 활성화됩니다.")
    LIVE_MACRO_URL = ""
    LIVE_SHEET_NAME = "시트1"

# 중앙 구글 시트 셀 원격 직접 제어 함수
def update_google_sheet(sheet_id, sheet_name, row_idx, col_idx, new_value):
    if not LIVE_MACRO_URL:
        return False
    try:
        params = {
            "id": sheet_id,
            "sheet": sheet_name,
            "row": int(row_idx + 2),
            "col": int(col_idx + 1),
            "val": new_value
        }
        requests.get(LIVE_MACRO_URL, params=params, timeout=5)
        return True
    except:
        return False

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
    
    c_id = col_list[0]          
    c_mach = col_list[1]        
    c_name = col_list[2]        
    c_mat = col_list[3]         
    c_life_m = col_list[4]      
    c_life_h = col_list[5]      
    c_curr_h = col_list[6]      
    
    idx_manual = 7              
    idx_stock = 8               
    idx_install = 9             

    c_manual = col_list[idx_manual]
    c_stock = col_list[idx_stock]
    c_install_date = col_list[idx_install] if len(col_list) > 9 else col_list[-1]

    df[c_stock] = pd.to_numeric(df[c_stock], errors='coerce').fillna(0).astype(int)
    df[c_curr_h] = pd.to_numeric(df[c_curr_h], errors='coerce').fillna(0).astype(int)
    df[c_life_h] = pd.to_numeric(df[c_life_h], errors='coerce').fillna(0).astype(int)
    df[c_life_m] = pd.to_numeric(df[c_life_m], errors='coerce').fillna(0).astype(int)

    df['남은시간'] = df[c_life_h] - df[c_curr_h]
    urgent_parts = df[(df['남은시간'] <= 200) | (df[c_stock] <= 2)]
    
    if not urgent_parts.empty:
        with st.expander(f"⚠️ 위험 레이더: 정비 임계 품목 {len(urgent_parts)}건 검출", expanded=True):
            alert_display = urgent_parts[[c_mach, c_name, '남은시간', c_stock]].copy()
            alert_display.columns = ['설비명', '부품명', '잔여(Hr)', '재고(EA)']
            st.dataframe(alert_display, use_container_width=True, hide_index=True)

    # 📊 자산 현황판 배치 (모바일에서는 세로 피드로 이쁘게 스택됨)
    st.markdown("### 📊 실시간 공정 지표")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("총 관리 소모품", f"{len(df)} SKU")
    m2.metric("보안재고 위험군", f"{len(df[df[c_stock] <= 2])} 종")
    m3.metric("라인 가동 상태", "NORMAL")
    m4.metric("동기화 기준일", datetime.date.today().strftime("%Y-%m-%d"))
    
    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
    
    # 📋 4대 핵심 메뉴 탭 구성
    menu_tab1, menu_tab2, menu_tab3, menu_tab4 = st.tabs([
        "📋 자산 관제 & 교체", 
        "📝 정비 일지 관리", 
        "📸 AI 비전 현장 진단",
        "💬 AI 정비 지식 챗봇"
    ])

    # 탭 1: 자산 관제 및 신품 교체 제어
    with menu_tab1:
        query_params = st.query_params
        default_machine = query_params.get("machine", df[c_mach].unique()[0])
        if default_machine not in df[c_mach].unique():
            default_machine = df[c_mach].unique()[0]
            
        col1, col2 = st.columns([1, 1.2], gap="medium")
        
        with col1:
            st.markdown("#### 🔍 소모품 라인 필터")
            with st.container():
                selected_machine = st.selectbox("🏭 대상 설비 라인 선택", df[c_mach].unique(), index=list(df[c_mach].unique()).index(default_machine), key="sl_mach")
                filtered_df = df[df[c_mach] == selected_machine]
                
                default_part = query_params.get("part", filtered_df[c_name].unique()[0])
                if default_part not in filtered_df[c_name].unique():
                    default_part = filtered_df[c_name].unique()[0]
                    
                selected_part = st.selectbox("🔧 세부 부품 선택", filtered_df[c_name].unique(), index=list(filtered_df[c_name].unique()).index(default_part), key="sl_part")
            
            part_idx = df[df[c_name] == selected_part].index[0]
            part_info = df.loc[part_idx]
            
            st.markdown("#### 📋 부품 실시간 스펙 (모바일 최적화)")
            with st.container():
                if pd.notna(part_info[c_install_date]):
                    raw_install_date = str(part_info[c_install_date]).strip()
                    st.markdown(f"**📅 최초 장착일 (J열) :** `{raw_install_date}`")
                    try:
                        parsed_start = datetime.datetime.strptime(raw_install_date, "%Y-%m-%d").date()
                    except:
                        parsed_start = datetime.date.today()
                else:
                    st.markdown("**📅 최초 장착일 (J열) :** `기록 없음`")
                    parsed_start = datetime.date.today()

                months_to_add = int(part_info[c_life_m])
                year = parsed_start.year + (parsed_start.month + months_to_add - 1) // 12
                month = (parsed_start.month + months_to_add - 1) % 12 + 1
                calculated_replace_date = datetime.date(year, month, min(parsed_start.day, 28))
                
                # 가시성 보정을 위한 이모지 불릿 리스트 디자인
                st.markdown(f"* **⏳ 권장 교체 예정일 :** `{calculated_replace_date.strftime('%Y-%m-%d')}` ({months_to_add}개월 주기)")
                st.markdown(f"* **📦 창고 여분 재고 (I열) :** `{part_info[c_stock]} EA`")
                st.markdown(f"* **⏱️ 누적 가동 스펙 :** `{part_info[c_curr_h]} hr` / 한계 `{part_info[c_life_h]} hr` (잔여: `{part_info['남은시간']} hr`)")
                
                manual_url = part_info[c_manual]
                if pd.notna(manual_url) and str(manual_url).strip().startswith("http"):
                    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
                    st.link_button("📄 표준 정비 SOP 지침서 열람 (H열)", manual_url.strip(), type="primary", use_container_width=True)

            with st.expander("⚙️ 예외 변수 수동 수치 보정"):
                new_curr_h = st.number_input("현재 누적 가동 시간 보정", value=int(part_info[c_curr_h]), step=10, key="adj_h")
                new_stock = st.number_input("창고 보관 수량 보정", value=int(part_info[c_stock]), step=1, key="adj_s")
                if st.button("💾 데이터 보정 명령 동기화", use_container_width=True):
                    with st.spinner("보전 서버 통신 중..."):
                        update_google_sheet("1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8", LIVE_SHEET_NAME, part_idx, 6, new_curr_h) 
                        update_google_sheet("1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8", LIVE_SHEET_NAME, part_idx, idx_stock, new_stock) 
                        st.success("✅ 마스터 수치 수동 보정 완료")
                        st.cache_data.clear()
                        st.rerun()
                        
        with col2:
            st.markdown("#### 🛠️ 신품 교체 집행 제어실")
            with st.container():
                st.info(f"**[{selected_part}]** 신품 교체 집행 시 **[가동시간 0Hr 리셋 / 재고 1개 차감 / 장착일 오늘로 자동 갱신]**이 구글 엑셀 시트에 즉시 영구 반영됩니다.")
                chosen_execution_date = st.date_input("📆 실제 신품 교체 처리 일자", datetime.date.today(), key="exec_date_picker")
                
                if st.button("🔧 새 소모품 교체 확정 처리 (영구 반영)", type="primary", use_container_width=True):
                    if part_info[c_stock] <= 0:
                        st.error("❌ 창고 내 여분 재고 자산이 부족하여 교체 처리를 집행할 수 없습니다.")
                    else:
                        with st.spinner("중앙 클라우드 원격 갱신 명령 전송 중..."):
                            reset_hours = 0
                            reduced_stock = int(part_info[c_stock]) - 1
                            formatted_install_date = chosen_execution_date.strftime("%Y-%m-%d")
                            
                            update_google_sheet("1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8", LIVE_SHEET_NAME, part_idx, 6, reset_hours)       
                            update_google_sheet("1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8", LIVE_SHEET_NAME, part_idx, idx_stock, reduced_stock) 
                            update_google_sheet("1zPCLBPMSsPHmGpZ8KBtlWDMIjYhpoqIHJxwzZkMgqf8", LIVE_SHEET_NAME, part_idx, idx_install, formatted_install_date) 
                            
                            auto_system_log = {
                                "날짜": formatted_install_date,
                                "부품명": selected_part,
                                "작업자": "시스템자동",
                                "정비내용": f"[신품교체] 수량 1EA 차감 및 장착일 세팅 완료."
                            }
                            st.session_state.temp_logs.insert(0, auto_system_log)
                            st.success(f"🎉 [{selected_part}] 신품 장착 처리 완수!")
                            st.balloons()
                            st.cache_data.clear()
                            st.rerun()

            st.markdown("##### ⏱️ 수명 소모율")
            current_hours = int(part_info[c_curr_h])
            max_hours = int(part_info[c_life_h])
            progress_per = max(0, min(100, int((current_hours / max_hours) * 100))) if max_hours > 0 else 0
            st.progress(progress_per, text=f"진척도: {progress_per}%")

            st.markdown("---")
            st.subheader("📱 하드웨어 QR코드 라벨")
            app_url = "https://vial-manager-na6qyzsytdcsencg2jwr89.streamlit.app/"
            qr_link = f"{app_url}?machine={urllib.parse.quote(selected_machine)}&part={urllib.parse.quote(selected_part)}"
            qr_link_enc = urllib.parse.quote(qr_link)
            qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=130x130&data={qr_link_enc}"
            
            q_col1, q_col2 = st.columns([1, 2.5])
            with q_col1: st.image(qr_api_url, caption="현장 정비 태그 QR")
            with q_col2: st.code(qr_link)

    # 탭 2: 디지털 정비 일지 관리실
    with menu_tab2:
        st.markdown("### 📝 제조 설비 일일 정비 일지 기록")
        log_col1, log_col2 = st.columns([1, 1.2], gap="medium")
        
        with log_col1:
            with st.container():
                st.markdown("##### 🖊️ 이력 등록 양식")
                log_date = st.date_input("작업 일자", datetime.date.today(), key="m_log_date")
                log_mach = st.selectbox("정비 설비 선택", df[c_mach].unique(), key="m_log_mach")
                filtered_log_df = df[df[c_mach] == log_mach]
                log_part = st.selectbox("정비 부품 선택", filtered_log_df[c_name].unique(), key="m_log_part")
                log_worker = st.text_input("작업 정비원 성명", placeholder="보전팀 담당자 명 기입", key="m_log_worker")
                log_content = st.text_area("상세 정비 내역", placeholder="조치 내역 기술", key="m_log_content")
                
                st.markdown("<div style='margin-top:5px;'></div>", unsafe_allow_html=True)
                if st.button("🚀 정비 이력 로그 서버 전송", type="primary", use_container_width=True, key="m_log_submit_btn"):
                    if not log_worker or not log_content:
                        st.warning("⚠️ 정비 책임자 명과 상세 내용을 기술해 주십시오.")
                    else:
                        new_log_entry = {
                            "날짜": log_date.strftime("%Y-%m-%d"),
                            "부품명": log_part,
                            "작업자": log_worker,
                            "정비내용": log_content
                        }
                        st.session_state.temp_logs.insert(0, new_log_entry)
                        st.success(f"✅ 정비 데이터 이력 세팅 완료!")
                        st.rerun()
        
        with log_col2:
            st.markdown("#### 📋 최근 공정 정비 이력 타임라인")
            with st.container():
                base_logs = [
                    {"날짜": "2026-07-01", "부품명": "충전 피스톤 실링", "작업자": "관리자", "정비내용": "스마트 예지정비 관제실 시스템 가동 시작."}
                ]
                display_logs = st.session_state.temp_logs + base_logs
                log_df_display = pd.DataFrame(display_logs)
                st.dataframe(log_df_display, use_container_width=True, hide_index=True)

    # 탭 3: 📸 AI 비전 현장 진단 및 부품 식별
    with menu_tab3:
        st.subheader("📸 AI 실시간 현장 진단 및 부품 식별")
        
        if "GEMINI_API_KEY" in st.secrets:
            vision_api_key = st.secrets["GEMINI_API_KEY"]
            st.success("🟢 클라우드 공용 AI 보안 엔진 연동 완료")
        else:
            vision_api_key = ""
            st.error("⚠️ [알림] Secrets 메뉴에 GEMINI_API_KEY를 등록해 주세요.")
        
        v_col1, v_col2 = st.columns([1, 1.2], gap="medium")
        
        with v_col1:
            st.markdown("##### 📷 하드웨어 이미지 소스 입력")
            input_mode = st.radio("사진 획득 방식을 고르세요", ["📱 모바일 카메라로 직접 촬영", "📁 갤러리 파일 업로드"], key="vision_mode")
            
            captured_file = None
            if input_mode == "📱 모바일 카메라로 직접 촬영":
                captured_file = st.camera_input("부품 외관 촬영")
            else:
                captured_file = st.file_uploader("부품 사진 이미지 선택", type=["jpg", "jpeg", "png"], key="file_vision")
                
            if captured_file is not None:
                st.image(captured_file, caption="🛠️ AI 분석 대상 이미지 객체", width=360)
        
        with v_col2:
            st.markdown("##### 🤖 AI 비전 실시간 정비 권고안 리포트")
            if captured_file is None:
                st.info("💡 안내: 사진을 등록하시면 실시간 분석 대기 모드로 전환됩니다.")
            else:
                if st.button("🚀 이미지 비전 해독 시작", type="primary", use_container_width=True):
                    with st.spinner("AI가 고해상도 눈인식 픽셀 분석을 통해 사물을 해독하는 중..."):
                        try:
                            import google.generativeai as genai
                            from PIL import Image
                            
                            genai.configure(api_key=vision_api_key)
                            pil_image = Image.open(captured_file)
                            
                            context_prompt = (
                                "너는 바이알 제조 공장의 최고 숙련된 기계 정비 마스터이자 스마트 팩토리 인공지능 비전이야. "
                                "제시된 사진을 정밀 해독해서 1. 이 부품이 어떤 기계 부품이거나 도구/설비인지 이름을 유추해주고, "
                                "2. 현재 표면 마모, 균열, 오염, 혹은 손상 징후가 육안상 식별되는지 외관 상태를 정밀 진단해줘. "
                                "3. 마지막으로 현장 정비원이 조치해야 할 예방보전 조치안을 대기업 공장 보고서 스타일로 한국어로 설명해줘."
                            )
                            
                            models_to_try = ['gemini-2.5-flash', 'gemini-flash-latest', 'gemini-3.5-flash', 'gemini-2.0-flash', 'gemini-pro-latest']
                            ai_response = None
                            used_model = ""
                            
                            for model_name in models_to_try:
                                try:
                                    vision_model = genai.GenerativeModel(model_name)
                                    ai_response = vision_model.generate_content([context_prompt, pil_image])
                                    used_model = model_name
                                    break
                                except:
                                    continue
                            
                            if ai_response is not None:
                                st.success(f"🎯 사진 해독 완료! (적용 엔진: {used_model})")
                                st.write(ai_response.text)
                            else:
                                st.error("❌ 모든 구글 AI 모델이 거부 응답을 보냈습니다. 한도를 점검해 주세요.")
                        except Exception as error_msg:
                            st.error(f"❌ AI 분석 연동 중 오류 발생: {error_msg}")

    # 탭 4: 💬 AI 현장 정비 지식 챗봇
    with menu_tab4:
        st.subheader("🤖 AI 베테랑 선임 정비원 24hr 지식 챗봇")
        st.write("현장 공정 트러블슈팅, 기계공학 조치 지식, 볼트 규격 체결값 등을 언제든 질문하세요.")
        
        chat_api_key = st.secrets.get("GEMINI_API_KEY", "")
            
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = [
                {
                    "role": "assistant", 
                    "content": "안녕하세요! 바이알 라인 예방보전 공정 마스터 정비봇입니다. ⚙️\\n현장에서 겪고 계시는 기술적 애로사항을 말씀해 주시면 명쾌한 정비 솔루션을 찾아드리겠습니다!"
                }
            ]
            
        # 대화 이력 피드 피드백
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                
        # 하단 대화 입력 박스 가동
        if user_prompt := st.chat_input("정비 문제 상황이나 기계 질문을 입력하세요"):
            with st.chat_message("user"):
                st.write(user_prompt)
            st.session_state.chat_history.append({"role": "user", "content": user_prompt})
            
            if not chat_api_key:
                st.error("❌ Secrets에 GEMINI_API_KEY가 세팅되어 있지 않습니다.")
            else:
                with st.chat_message("assistant"):
                    with st.spinner("마스터가 현장 매뉴얼을 기반으로 조치 방안을 도출하는 중..."):
                        try:
                            import google.generativeai as genai
                            genai.configure(api_key=chat_api_key)
                            
                            system_instruction = (
                                "너는 바이알 제조 공장의 최고 숙련된 기계 정비 마스터이자 스마트 팩토리 수석 엔지니어 보전원이야. "
                                "수십 년 경력의 베테랑 선임 정비원 스타일로 해결책을 조항별로 나누어 한국어로 설명해줘. "
                                "현장에서 당장 조치할 수 있는 실천적인 행동 매뉴얼 위주로 작성해야 해."
                            )
                            
                            chat_models = ['gemini-2.5-flash', 'gemini-flash-latest', 'gemini-3.5-flash', 'gemini-2.0-flash', 'gemini-pro-latest']
                            bot_reply = None
                            for m_name in chat_models:
                                try:
                                    c_model = genai.GenerativeModel(m_name)
                                    bot_reply = c_model.generate_content([system_instruction, user_prompt])
                                    break
                                except:
                                    continue
                                    
                            if bot_reply is not None:
                                st.write(bot_reply.text)
                                st.session_state.chat_history.append({"role": "assistant", "content": bot_reply.text})
                                st.rerun()
                            else:
                                st.error("❌ 구글 AI 통신망 연결이 일시적으로 거부되었습니다.")
                        except Exception as chat_err:
                            st.error(f"❌ 챗봇 엔진 작동 오류: {chat_err}")
else:
    st.info("구글 마스터 스프레드시트 데이터 통신망 연결 대기 중...")