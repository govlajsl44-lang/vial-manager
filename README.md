# KGC Smart MRO — 완성본 배포 안내

모바일 우선 · 엔터프라이즈 인터페이스. **Supabase 인증/DB + Google Gemini**가 브라우저에서 직접 동작하는
단일 HTML 웹앱입니다. 별도 백엔드 서버가 필요 없습니다.

## 구성 파일
- `KGC Smart MRO (standalone).html` — 완성된 앱(모든 폰트·이미지 내장). 이 파일 하나면 실행됩니다.
- `streamlit_app.py` — 현재 쓰시는 Streamlit에 그대로 얹어 실행하는 래퍼.
- `requirements.txt` — Streamlit 실행 의존성.

## 실행 방법 (3가지 중 택1)

### 1) 그냥 파일 열기 (가장 간단)
`KGC Smart MRO (standalone).html` 을 브라우저에서 더블클릭 → 바로 로그인 화면.

### 2) Streamlit (현재 스택 유지)
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```
> 두 파일(`streamlit_app.py`, `KGC Smart MRO (standalone).html`)을 같은 폴더에 두세요.
> Streamlit Community Cloud에 올리면 사내/외부 공유 URL이 생깁니다.

### 3) 정적 호스팅 (권장 — 가장 가볍고 빠름)
Netlify / Vercel / GitHub Pages / Supabase Storage 등에 HTML 파일만 업로드.
서버·파이썬 불필요, 모바일에서도 그대로 동작.

## 설정
- **Supabase**: URL/anon(publishable) 키는 앱에 내장되어 있습니다. 키 교체 시 HTML 상단
  `SUPA_URL` / `SUPA_KEY` 값을 바꾸세요.
- **Gemini API 키**: 앱 실행 후 `더보기 → 내 정보 → Gemini API 키` 또는 AI 진단 화면의
  "등록" 버튼에서 입력 (브라우저 localStorage에 저장).

## 보안 체크리스트 (중요)
- anon 키가 브라우저에 노출되므로 Supabase **RLS(행 수준 보안) 정책**을 반드시 설정하세요.
  (예: 사용자는 본인 factory/team 행만 select/insert 가능하도록)
- 회원가입 시 이메일 인증 여부는 Supabase Auth 설정을 따릅니다.
- Gemini 키도 브라우저에 노출됩니다. 사내용/한도 제한 키를 쓰고, 장기적으로는
  서버(엣지 함수) 프록시 경유를 권장합니다.

## 권한 규칙 (구현됨)
- 이메일에 `admin`/`master` 포함 → 마스터 관리자(전체 공장·설비 열람).
- 팀 = `시설에너지 관리팀` → 통합 관제 센터 접근(본인 공장 전체 설비 상태·정비요청 대응).
- 그 외 일반 사용자 → 본인 **공장 + 팀** 설비만. 설비 라우팅은 공장 선택 없이 라인→기기부터 시작.
