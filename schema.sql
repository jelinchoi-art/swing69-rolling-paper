create extension if not exists pgcrypto;

create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  nickname text not null check (char_length(nickname) between 1 and 20),
  message text not null check (char_length(message) between 1 and 120),
  icon text not null default '🍁',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  is_hidden boolean not null default false,
  page integer null check (page in (1, 2)),
  x integer null,
  y integer null,
  w integer null,
  h integer null,
  font_pt numeric null check (font_pt between 14 and 28),
  locked boolean not null default false
);

create index if not exists messages_created_at_idx on public.messages(created_at);

-- This app uses the service-role key only on the Streamlit server.
-- Do not expose the service-role key in client-side code or public files.
