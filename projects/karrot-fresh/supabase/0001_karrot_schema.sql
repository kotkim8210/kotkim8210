-- ============================================================
-- 당근 농수산물 주문·단골·마진 관리 스키마
-- project: kotkim8210's Project (jjlphqevznrifiholkic, ap-northeast-2)
-- 기존 public 스키마와 충돌하지 않도록 전용 schema "karrot" 사용
-- 적용: Supabase MCP apply_migration(name="karrot_schema") 또는 SQL 에디터에 붙여넣기
-- ============================================================

create schema if not exists karrot;

-- ── 고객/단골 ────────────────────────────────────────────────
create table if not exists karrot.customers (
    id              bigint generated always as identity primary key,
    name            text,
    karrot_nickname text,                       -- 당근 닉네임
    phone           text,
    address         text,
    is_regular      boolean not null default false,  -- 단골 여부
    first_order_at  timestamptz,
    total_orders    integer not null default 0,
    total_spent     numeric(12,0) not null default 0,
    notes           text,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);
comment on table karrot.customers is '고객/단골 명부 — 재구매 추적의 기준';

-- ── 상품(시즌 품목) ──────────────────────────────────────────
create table if not exists karrot.products (
    id           bigint generated always as identity primary key,
    name         text not null,                 -- 예: 성주 참외 3kg
    variety      text,                           -- 품종
    origin       text,                           -- 산지
    grade        text,                           -- 등급(로얄/특/상)
    unit_weight  text,                           -- 3kg(9~11과) 등
    brix         numeric(4,1),                   -- 당도
    season       text,                           -- 제철(예: 5~7월)
    base_price   numeric(12,0) not null default 0,  -- 판매가
    cost_price   numeric(12,0) not null default 0,  -- 원가(산지/위탁)
    status       text not null default 'active',    -- active | sold_out | off_season
    created_at   timestamptz not null default now(),
    updated_at   timestamptz not null default now()
);
comment on table karrot.products is '시즌별 판매 품목 + 원가(마진 계산용)';

-- ── 주문 ────────────────────────────────────────────────────
create table if not exists karrot.orders (
    id             bigint generated always as identity primary key,
    customer_id    bigint references karrot.customers(id) on delete set null,
    channel        text not null default 'delivery',  -- delivery(택배) | meetup(직거래)
    status         text not null default 'received',  -- received | paid | shipped | done | refunded | canceled
    payment_method text,                               -- 당근페이 | 계좌 | 현장
    total_amount   numeric(12,0) not null default 0,
    tracking_no    text,                               -- 운송장
    address        text,
    memo           text,
    ordered_at     timestamptz not null default now(),
    shipped_at     timestamptz,
    done_at        timestamptz
);
comment on table karrot.orders is '주문 헤더';
create index if not exists idx_orders_customer on karrot.orders(customer_id);
create index if not exists idx_orders_status   on karrot.orders(status);

-- ── 주문 품목 ────────────────────────────────────────────────
create table if not exists karrot.order_items (
    id          bigint generated always as identity primary key,
    order_id    bigint not null references karrot.orders(id) on delete cascade,
    product_id  bigint references karrot.products(id) on delete set null,
    qty         integer not null default 1,
    unit_price  numeric(12,0) not null default 0,  -- 판매 단가(주문 시점 스냅샷)
    unit_cost   numeric(12,0) not null default 0,  -- 원가 단가(주문 시점 스냅샷)
    line_total  numeric(12,0) generated always as (unit_price * qty) stored
);
create index if not exists idx_items_order on karrot.order_items(order_id);

-- ── CS/하자 접수 ─────────────────────────────────────────────
create table if not exists karrot.cs_cases (
    id            bigint generated always as identity primary key,
    order_id      bigint references karrot.orders(id) on delete set null,
    type          text not null default 'defect',   -- defect(하자) | refund | exchange
    status        text not null default 'open',     -- open | resolved | rejected
    photos_ok     boolean not null default false,   -- 증빙 3장 제출 여부
    defect_ratio  numeric(5,2),                      -- 불량 과수 비율(%) → 부분환불 근거
    refund_amount numeric(12,0) not null default 0,
    resolution    text,
    received_at   timestamptz not null default now(),
    resolved_at   timestamptz,
    notes         text
);
comment on table karrot.cs_cases is 'CS/하자/환불 접수 — 24시간 규칙·부분환불 추적';

-- ── 제철 재입고 리마인더 ─────────────────────────────────────
create table if not exists karrot.restock_reminders (
    id           bigint generated always as identity primary key,
    product_name text not null,
    season_start date,
    season_peak  date,
    notify_date  date not null,    -- 이 날짜에 "재입고/단골 알림 보내라" 리마인드
    channel      text,             -- 단골알림 | 광고 | 신규게시
    sent         boolean not null default false,
    notes        text,
    created_at   timestamptz not null default now()
);
comment on table karrot.restock_reminders is '제철 시작 전 단골 알림/재게시 리마인더';

-- ── 마진 뷰 (주문별 매출·원가·마진) ──────────────────────────
create or replace view karrot.v_order_margin as
select
    o.id                                   as order_id,
    o.ordered_at,
    o.status,
    o.channel,
    sum(oi.unit_price * oi.qty)            as revenue,
    sum(oi.unit_cost  * oi.qty)            as cost,
    sum((oi.unit_price - oi.unit_cost) * oi.qty)            as gross_margin,
    -- 당근 비즈 결제 수수료 가정 3.3% (기존 마진추적기 기준)
    round(sum(oi.unit_price * oi.qty) * 0.033)             as karrot_fee_est,
    sum((oi.unit_price - oi.unit_cost) * oi.qty)
        - round(sum(oi.unit_price * oi.qty) * 0.033)        as net_margin_est
from karrot.orders o
join karrot.order_items oi on oi.order_id = o.id
group by o.id, o.ordered_at, o.status, o.channel;
comment on view karrot.v_order_margin is '주문별 매출/원가/마진 — 당근 수수료 3.3% 가정 반영';

-- ── updated_at 자동 갱신 트리거 ─────────────────────────────
create or replace function karrot.touch_updated_at()
returns trigger language plpgsql
set search_path = ''   -- 보안 린트 0011: search_path 고정
as $$
begin new.updated_at = now(); return new; end; $$;

drop trigger if exists trg_customers_touch on karrot.customers;
create trigger trg_customers_touch before update on karrot.customers
    for each row execute function karrot.touch_updated_at();
drop trigger if exists trg_products_touch on karrot.products;
create trigger trg_products_touch before update on karrot.products
    for each row execute function karrot.touch_updated_at();

-- ── RLS (개인 단일 운영자 — service_role 전용) ──────────────
-- RLS를 켜되 정책을 두지 않으면 anon/authenticated는 기본 차단되고,
-- 서버 키(service_role)와 Supabase 대시보드만 접근한다.
-- (보안 린트 0024 회피: USING(true) 같은 과도 허용 정책을 쓰지 않음.)
-- 클라이언트 인증 접속이 필요해지면 그때 auth.uid() 기반 정책을 추가한다.
alter table karrot.customers        enable row level security;
alter table karrot.products         enable row level security;
alter table karrot.orders           enable row level security;
alter table karrot.order_items      enable row level security;
alter table karrot.cs_cases         enable row level security;
alter table karrot.restock_reminders enable row level security;
