-- ══════════════════════════════════════
--  RecallAI — Supabase Schema
-- ══════════════════════════════════════

-- 1. Cards table: كل بطاقة مولّدة من PDF
create table if not exists cards (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid references auth.users(id) on delete cascade,
  topic        text not null,          -- اسم الـ PDF / الموضوع
  question     text not null,
  options      jsonb not null,         -- ["A","B","C","D"]
  correct_index int not null,
  created_at   timestamptz default now()
);

-- 2. Reviews table: سجل المراجعات (SM-2)
create table if not exists reviews (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid references auth.users(id) on delete cascade,
  card_id       uuid references cards(id) on delete cascade,
  ease_factor   float default 2.5,     -- معامل السهولة (SM-2)
  interval_days int default 1,         -- عدد الأيام للمراجعة القادمة
  due_date      date default current_date,
  repetitions   int default 0,         -- عدد مرات الإجابة الصحيحة المتتالية
  last_quality  int default -1,        -- آخر تقييم (0-5)
  updated_at    timestamptz default now()
);

-- Row Level Security
alter table cards   enable row level security;
alter table reviews enable row level security;

create policy "user owns cards"   on cards   for all using (auth.uid() = user_id);
create policy "user owns reviews" on reviews for all using (auth.uid() = user_id);
