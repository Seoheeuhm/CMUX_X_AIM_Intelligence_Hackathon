-- ============================================================
-- Portfolog DB Schema — Supabase SQL Editor에서 실행
-- ============================================================

-- 1. profiles — auth.users 확장 (plan, gen_count 추적)
CREATE TABLE IF NOT EXISTS public.profiles (
  id             UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email          TEXT        NOT NULL,
  name           TEXT,
  avatar_url     TEXT,
  plan           TEXT        NOT NULL DEFAULT 'free' CHECK (plan IN ('free', 'pro')),
  gen_count      INTEGER     NOT NULL DEFAULT 0,
  gen_limit      INTEGER     NOT NULL DEFAULT 3,
  gen_reset_at   TIMESTAMPTZ,
  pro_expires_at TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all_profiles" ON public.profiles USING (auth.role() = 'service_role');

-- 신규 Google 로그인 시 profiles 행 자동 생성
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  INSERT INTO public.profiles (id, email, name, avatar_url)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.email),
    NEW.raw_user_meta_data->>'avatar_url'
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- 2. sessions — 인메모리 dict 대체 (JSONB)
CREATE TABLE IF NOT EXISTS public.sessions (
  id         TEXT        PRIMARY KEY,
  user_id    UUID        REFERENCES public.profiles(id) ON DELETE SET NULL,
  data       JSONB       NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '24 hours'
);

ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all_sessions" ON public.sessions USING (auth.role() = 'service_role');

-- 3. payments — Toss 결제 기록
CREATE TABLE IF NOT EXISTS public.payments (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        UUID        NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  order_id       TEXT        UNIQUE NOT NULL,
  payment_key    TEXT,
  amount         INTEGER     NOT NULL,
  status         TEXT        NOT NULL DEFAULT 'pending'
                             CHECK (status IN ('pending','confirmed','failed','cancelled')),
  paid_at        TIMESTAMPTZ,
  pro_expires_at TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all_payments" ON public.payments USING (auth.role() = 'service_role');
