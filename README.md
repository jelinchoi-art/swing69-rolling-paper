# 스윙피버 린디합 69기 — A3 양면 롤링페이퍼 Streamlit 앱

친구들에게 초대 링크를 배포하면 메시지를 수집하고, 관리자는 메시지 수정/삭제/숨김/위치 조정 후 A3 양면 PDF를 내려받을 수 있는 앱입니다.

## 핵심 기능

- 참여 코드가 있어야 메시지 작성 가능
- 닉네임 + 메시지 + 작은 기호 입력
- 메시지 110자 제한, 50~80자 권장
- 앞면 16명 + 나머지 뒷면 자동 배치
- 기본 본문 17pt, 자동 축소 최저 15pt
- 관리자만 메시지 수정/삭제/숨김 가능
- 관리자만 페이지·X/Y 위치·카드 폭·글씨 크기 조정 가능
- 수동 조정 후 겹침 감지
- A3 300dpi 앞/뒤 PNG 및 2페이지 PDF 다운로드
- 배경 디자인 포함: `assets/front_bg.png`, `assets/back_bg.png`

## 1. Supabase 만들기

1. https://supabase.com 에서 새 프로젝트 생성
2. SQL Editor에서 `schema.sql` 전체 실행
3. Project Settings → API에서 아래 두 값을 확인
   - Project URL
   - `service_role` key

**service_role key는 절대 GitHub에 올리지 마세요.** Streamlit Secrets에만 저장합니다.

## 2. GitHub에 업로드

이 폴더 전체를 새 GitHub 저장소에 올립니다.

`.streamlit/secrets.toml` 파일은 만들지 말고, 예시 파일인 `.streamlit/secrets.toml.example`만 올리세요.

## 3. Streamlit Community Cloud 배포

1. https://share.streamlit.io 에 로그인
2. GitHub 저장소 선택
3. Main file path: `app.py`
4. Advanced settings → Secrets에 아래 입력

```toml
SUPABASE_URL = "https://xxxxx.supabase.co"
SUPABASE_SERVICE_KEY = "여기에_service_role_key"
ADMIN_PASSWORD = "관리자만아는긴비밀번호"
PARTICIPANT_CODE = "SWING69"
```

5. Deploy

`packages.txt`가 `fonts-nanum`을 설치하므로 A3 이미지/PDF에서 한글을 렌더링할 수 있습니다.

## 4. 친구들에게 배포하는 주소

두 방식 중 하나를 쓰면 됩니다.

### A. 참여 코드 직접 입력

그냥 앱 주소를 배포합니다.

`https://앱주소.streamlit.app`

친구들이 `PARTICIPANT_CODE`를 입력해야 입장합니다.

### B. 링크에 초대코드 포함 — 더 편함

`https://앱주소.streamlit.app/?invite=SWING69`

링크를 가진 사람은 별도 코드 입력 없이 바로 작성 화면에 들어갑니다.

> 링크가 외부로 전달되면 그 사람도 작성할 수 있으므로, 필요하면 `PARTICIPANT_CODE`를 바꿔 재배포하세요.

## 5. 관리자 주소

`https://앱주소.streamlit.app/?mode=admin`

`ADMIN_PASSWORD`로 로그인합니다.

관리자 화면에서 할 수 있는 일:

- 등록 문구 수정
- 닉네임 수정
- 최종본에서 임시 숨김
- 영구 삭제
- 앞/뒤 페이지 이동
- X/Y 위치 조정
- 카드 폭 조정
- 본문 글씨 크기 15~22pt 조정
- 모든 메시지 자동 재배치
- 겹침/공간초과 감지
- A3 PDF/PNG 다운로드

## 6. 레이아웃 원칙

- 앞면: 사진/타이틀을 살리면서 좌우 빈 공간과 하단에 약 16개 메시지를 자동 배치
- 뒷면: 서호&유진 사진을 유지하면서 좌우 상단 + 하단 4열 영역에 나머지 메시지를 자동 배치
- 30~40명 기준으로 설계
- 글씨는 자동배치에서 최대한 17pt 유지, 공간이 부족할 때만 15pt까지 축소
- 15pt 미만으로는 자동 축소하지 않음
- 긴 메시지가 너무 많으면 관리자 화면에서 ‘공간 초과’ 경고가 표시됨

## 7. 출력 권장

최종 PDF는 A3 세로 2페이지입니다.

- 용지: A3 (297 × 420 mm)
- 출력 배율: 실제 크기 / 100%
- 해상도: 300dpi 기준 3508 × 4961 px
- 양면 출력 시 인쇄소에서 앞뒤 방향을 시안 확인 후 출력

## 보안 메모

- GitHub에는 비밀번호·참여코드·Supabase service role key를 직접 적지 않습니다.
- Streamlit Cloud의 Secrets에만 저장하세요.
- 참가자는 데이터베이스를 직접 호출하지 않고 Streamlit 서버를 통해 제출합니다.
- 관리 기능은 별도 관리자 비밀번호로 보호됩니다.
