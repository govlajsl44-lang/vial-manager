import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="바이알 설비 부품 관리", layout="wide")

st.title("🧪 바이알 설비 부품 교체 주기 관리 시스템")
st.caption("충전기 및 캡핑기 부품의 재질 정보와 예상 교체 주기를 확인합니다.")

# 1. 샘플 데이터 설정
if "parts_db" not in st.session_state:
    st.session_state.parts_db = [
        {
            "ID": "V-FILL-001",
            "설비": "바이알 충전기",
            "부품명": "충전 피스톤 실링 (O-링)",
            "재질": "실리콘 (Silicone)",
            "주기": 6,
            "비고": "고온 멸균(SIP) 후 손상 주의",
        },
        {
            "ID": "V-FILL-002",
            "설비": "바이알 충전기",
            "부품명": "세라믹 로터리 밸브",
            "재질": "세라믹 (Ceramic)",
            "주기": 24,
            "비고": "마모 상태 정기 점검 필요",
        },
        {
            "ID": "V-CAP-001",
            "설비": "바이알 캡핑기",
            "부품명": "캡핑 헤드 플런저",
            "재질": "SUS316L",
            "주기": 12,
            "비고": "스프링 장력 저하 확인 필요",
        },
        {
            "ID": "V-CAP-002",
            "설비": "바이알 캡핑기",
            "부품명": "고무 가이드 롤러",
            "재질": "폴리우레탄",
            "주기": 3,
            "비고": "마찰로 인한 마모가 빠른 편",
        },
    ]

df = pd.DataFrame(st.session_state.parts_db)

# 2. UI 레이아웃 균등 분할
col1, col2 = st.columns([1, 2])

with col1:
    st.header("🔍 부품 선택")
    selected_machine = st.selectbox("설비 선택", df["설비"].unique())

    # 선택한 설비에 해당하는 부품 필터링
    filtered_df = df[df["설비"] == selected_machine]
    selected_part_name = st.selectbox("부품명 선택", filtered_df["부품명"].unique())

    # 선택된 부품 상세 정보 추출
    part_info = filtered_df[filtered_df["부품명"] == selected_part_name].iloc[0]

    st.markdown("---")
    st.markdown(f"**🔢 부품 코드:** `{part_info['ID']}`")
    st.markdown(f"**🧪 재질 정보:** {part_info['재질']}")
    st.markdown(f"**📅 표준 교체 주기:** {part_info['주기']}개월")
    st.info(f"💡 **비고:** {part_info['비고']}")

with col2:
    st.header("⏱️ 교체 주기 계산기")

    # 사용 시작일 입력 받기
    start_date = st.date_input(
        "⚙️ 해당 부품의 현재 사용 시작일(장착일)을 선택하세요", datetime.date.today()
    )

    # 예상 교체일 계산 (월 단위 추가)
    months_to_add = int(part_info["주기"])

    # 간단한 월 가산 로직
    year = start_date.year + (start_date.month + months_to_add - 1) // 12
    month = (start_date.month + months_to_add - 1) % 12 + 1
    day = min(
        start_date.day,
        [
            31,
            29
            if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
            else 28,
            31,
            30,
            31,
            30,
            31,
            31,
            30,
            31,
            30,
            31,
        ][month - 1],
    )
    target_date = datetime.date(year, month, day)

    # 남은 D-Day 계산
    today = datetime.date.today()
    remaining_days = (target_date - today).days

    # 결과 시각화
    st.subheader("📊 교체 예측 결과")

    cc1, cc2 = st.columns(2)
    cc1.metric(label="예상 교체일", value=target_date.strftime("%Y년 %m월 %d일"))

    if remaining_days < 0:
        cc2.metric(
            label="상태",
            value=f"교체 지연 ({abs(remaining_days)}일 경과)",
            delta="-경고",
            delta_color="inverse",
        )
        st.error("🚨 즉시 부품을 교체해야 합니다! 교체 주기가 지났습니다.")
    elif remaining_days <= 15:
        cc2.metric(
            label="남은 기간",
            value=f"D-{remaining_days}일",
            delta="-위험",
            delta_color="inverse",
        )
        st.warning("⚠️ 교체 임박! 15일 이내에 새 부품 교체를 준비하세요.")
    else:
        cc2.metric(label="남은 기간", value=f"D-{remaining_days}일", delta="안전")
        st.success("✅ 현재 정상 사용 가능 기간입니다.")
