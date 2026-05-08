# 내가 직접 해야 할 설정 작업

코드 구현은 Claude가 자동으로 합니다. 아래는 **외부 서비스 계정/설정**이 필요해서 직접 하셔야 하는 작업입니다.

---

## 1. Supabase 프로젝트 생성

1. https://supabase.com 접속 → 로그인 → **New project** 생성
2. 프로젝트 이름: `portfolog` (아무 이름이나 가능)
3. 생성 완료 후 **Settings → API** 메뉴로 이동
4. 아래 값 복사해서 `.env` 파일에 붙여넣기:
   - `SUPABASE_URL` = Project URL (예: `https://xxxxxxxxxxxx.supabase.co`)
   - `SUPABASE_SERVICE_KEY` = `service_role` key (secret)
   - `SUPABASE_JWT_SECRET` = Settings → API → JWT Settings → JWT Secret

---

## 2. Supabase에서 DB 스키마 실행

1. Supabase 대시보드 → **SQL Editor** → New query
2. `supabase/schema.sql` 파일 내용 전체 복사 후 붙여넣기
3. **Run** 클릭
4. Table Editor에서 `profiles`, `sessions`, `payments` 테이블 생성 확인

---

## 3. Google Cloud Console에서 OAuth 앱 만들기

1. https://console.cloud.google.com 접속
2. 새 프로젝트 생성 (또는 기존 프로젝트 선택)
3. **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
4. Application type: **Web application**
5. **Authorized redirect URIs** 에 추가:
   ```
   https://xxxxxxxxxxxx.supabase.co/auth/v1/callback
   ```
   (xxxxxxxxxxxx는 본인 Supabase 프로젝트 ref)
6. 생성 후 **Client ID**와 **Client Secret** 복사해두기

---

## 4. Supabase에서 Google OAuth 연동

1. Supabase 대시보드 → **Authentication → Providers → Google**
2. **Enable** 토글 ON
3. 위에서 복사한 Google Client ID / Client Secret 입력
4. **Save** 클릭

---

## 5. Toss Payments 개발자 계정 & 테스트 키 발급

1. https://developers.tosspayments.com 접속 → 로그인 (또는 회원가입)
2. **내 상점 → API 키** 메뉴
3. 테스트 키 2개 복사:
   - `TOSS_CLIENT_KEY` = 클라이언트 키 (`test_ck_...`)
   - `TOSS_SECRET_KEY` = 시크릿 키 (`test_sk_...`)
4. `.env` 파일에 붙여넣기

---

## 6. .env 파일 최종 확인

아래 형식으로 모든 값이 채워져 있는지 확인:

```
ANTHROPIC_API_KEY=sk-ant-...

SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
SUPABASE_JWT_SECRET=...

TOSS_CLIENT_KEY=test_ck_...
TOSS_SECRET_KEY=test_sk_...

APP_URL=http://localhost:8000
```

---

## 7. Railway 배포 시 (나중에)

1. https://railway.app → GitHub 연동 → 이 레포 선택
2. **Variables** 탭에서 `.env`의 모든 변수 동일하게 입력
3. `APP_URL`은 Railway에서 발급받은 도메인으로 변경
4. Supabase Google OAuth → Authorized redirect URIs에 Railway 도메인도 추가:
   ```
   https://your-app.railway.app/auth/callback
   ```
5. Google Cloud Console → Authorized redirect URIs에도 동일하게 추가

---

## 순서 요약

```
1. Supabase 프로젝트 생성 + .env 값 복사
2. Supabase SQL Editor에서 schema.sql 실행
3. Google Cloud Console에서 OAuth 앱 생성
4. Supabase에 Google OAuth 연동
5. Toss Payments 테스트 키 발급 + .env에 입력
6. uvicorn main:app --reload 로 로컬 테스트
```
