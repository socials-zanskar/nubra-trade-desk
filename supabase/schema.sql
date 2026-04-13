create table if not exists symbols (
    symbol text primary key,
    exchange text not null default 'NSE',
    sector text,
    industry text,
    is_active boolean not null default true,
    source text not null default 'seed',
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists volume_snapshots_latest (
    symbol text primary key references symbols(symbol) on delete cascade,
    scanned_at timestamptz not null,
    candle_time text,
    current_volume double precision,
    average_volume double precision,
    volume_ratio double precision,
    signal_summary text,
    interval text not null,
    lookback_days integer not null,
    raw_json jsonb not null default '{}'::jsonb
);

create table if not exists volume_snapshots_history (
    id bigserial primary key,
    symbol text not null references symbols(symbol) on delete cascade,
    scanned_at timestamptz not null,
    candle_time text,
    current_volume double precision,
    average_volume double precision,
    volume_ratio double precision,
    signal_summary text,
    interval text not null,
    lookback_days integer not null,
    raw_json jsonb not null default '{}'::jsonb
);

create index if not exists idx_volume_history_symbol_scanned_at
    on volume_snapshots_history(symbol, scanned_at desc);

create table if not exists stock_signal_board_latest (
    symbol text primary key references symbols(symbol) on delete cascade,
    scanned_at timestamptz not null,
    ltp double precision,
    volume_ratio double precision,
    current_volume double precision,
    average_volume double precision,
    wall_type text,
    wall_strike double precision,
    wall_proximity_pct double precision,
    bias text,
    signal_grade text not null,
    signal_reason text not null,
    setup_type text not null default 'Scanner',
    confidence double precision not null default 0,
    action_state text not null default 'Cooling',
    regime_alignment text not null default 'Neutral',
    trigger_price double precision,
    invalidation_price double precision,
    first_target double precision,
    why_now text,
    raw_json jsonb not null default '{}'::jsonb
);

create table if not exists stock_signal_board_history (
    id bigserial primary key,
    symbol text not null references symbols(symbol) on delete cascade,
    scanned_at timestamptz not null,
    ltp double precision,
    volume_ratio double precision,
    current_volume double precision,
    average_volume double precision,
    wall_type text,
    wall_strike double precision,
    wall_proximity_pct double precision,
    bias text,
    signal_grade text not null,
    signal_reason text not null,
    setup_type text not null default 'Scanner',
    confidence double precision not null default 0,
    action_state text not null default 'Cooling',
    regime_alignment text not null default 'Neutral',
    trigger_price double precision,
    invalidation_price double precision,
    first_target double precision,
    why_now text,
    raw_json jsonb not null default '{}'::jsonb
);

alter table if exists stock_signal_board_latest add column if not exists setup_type text not null default 'Scanner';
alter table if exists stock_signal_board_latest add column if not exists confidence double precision not null default 0;
alter table if exists stock_signal_board_latest add column if not exists action_state text not null default 'Cooling';
alter table if exists stock_signal_board_latest add column if not exists regime_alignment text not null default 'Neutral';
alter table if exists stock_signal_board_latest add column if not exists trigger_price double precision;
alter table if exists stock_signal_board_latest add column if not exists invalidation_price double precision;
alter table if exists stock_signal_board_latest add column if not exists first_target double precision;
alter table if exists stock_signal_board_latest add column if not exists why_now text;

alter table if exists stock_signal_board_history add column if not exists setup_type text not null default 'Scanner';
alter table if exists stock_signal_board_history add column if not exists confidence double precision not null default 0;
alter table if exists stock_signal_board_history add column if not exists action_state text not null default 'Cooling';
alter table if exists stock_signal_board_history add column if not exists regime_alignment text not null default 'Neutral';
alter table if exists stock_signal_board_history add column if not exists trigger_price double precision;
alter table if exists stock_signal_board_history add column if not exists invalidation_price double precision;
alter table if exists stock_signal_board_history add column if not exists first_target double precision;
alter table if exists stock_signal_board_history add column if not exists why_now text;

create index if not exists idx_stock_signal_history_symbol_scanned_at
    on stock_signal_board_history(symbol, scanned_at desc);

create table if not exists symbol_drilldown_latest (
    symbol text primary key references symbols(symbol) on delete cascade,
    scanned_at timestamptz not null,
    exchange text,
    ltp double precision,
    volume_ratio double precision,
    signal_grade text not null,
    setup_type text not null,
    confidence double precision not null,
    action_state text not null,
    regime_alignment text not null,
    trigger_price double precision,
    invalidation_price double precision,
    first_target double precision,
    primary_note text,
    secondary_note text,
    raw_json jsonb not null default '{}'::jsonb
);

create table if not exists symbol_drilldown_history (
    id bigserial primary key,
    symbol text not null references symbols(symbol) on delete cascade,
    scanned_at timestamptz not null,
    exchange text,
    ltp double precision,
    volume_ratio double precision,
    signal_grade text not null,
    setup_type text not null,
    confidence double precision not null,
    action_state text not null,
    regime_alignment text not null,
    trigger_price double precision,
    invalidation_price double precision,
    first_target double precision,
    primary_note text,
    secondary_note text,
    raw_json jsonb not null default '{}'::jsonb
);

create index if not exists idx_symbol_drilldown_history_symbol_scanned_at
    on symbol_drilldown_history(symbol, scanned_at desc);

create table if not exists index_wall_snapshots_latest (
    index_symbol text primary key,
    exchange text not null,
    expiry text,
    scanned_at timestamptz not null,
    spot_price double precision,
    wall_type text,
    wall_strike double precision,
    wall_open_interest double precision,
    distance_from_current_price_pct double precision,
    bias text,
    raw_json jsonb not null default '{}'::jsonb
);

create table if not exists index_wall_snapshots_history (
    id bigserial primary key,
    index_symbol text not null,
    exchange text not null,
    expiry text,
    scanned_at timestamptz not null,
    spot_price double precision,
    wall_type text,
    wall_strike double precision,
    wall_open_interest double precision,
    distance_from_current_price_pct double precision,
    bias text,
    raw_json jsonb not null default '{}'::jsonb
);

create index if not exists idx_index_wall_history_symbol_scanned_at
    on index_wall_snapshots_history(index_symbol, scanned_at desc);

create table if not exists index_multi_wall_latest (
    index_symbol text not null,
    rank integer not null,
    wall_side text,
    strike double precision not null,
    open_interest double precision,
    distance_from_current_price_pct double precision,
    selected boolean not null default false,
    spot_price double precision,
    scanned_at timestamptz not null,
    raw_json jsonb not null default '{}'::jsonb,
    primary key (index_symbol, rank, strike, wall_side)
);

do $$
begin
    if exists (
        select 1
        from pg_constraint
        where conname = 'index_multi_wall_latest_pkey'
          and conrelid = 'index_multi_wall_latest'::regclass
    ) then
        begin
            alter table index_multi_wall_latest drop constraint index_multi_wall_latest_pkey;
        exception
            when undefined_object then null;
        end;
        alter table index_multi_wall_latest
            add constraint index_multi_wall_latest_pkey
            primary key (index_symbol, rank, strike, wall_side);
    end if;
end
$$;

create table if not exists index_multi_wall_history (
    id bigserial primary key,
    index_symbol text not null,
    rank integer not null,
    wall_side text,
    strike double precision not null,
    open_interest double precision,
    distance_from_current_price_pct double precision,
    selected boolean not null default false,
    spot_price double precision,
    scanned_at timestamptz not null,
    raw_json jsonb not null default '{}'::jsonb
);

create index if not exists idx_index_multi_wall_history_symbol_scanned_at
    on index_multi_wall_history(index_symbol, scanned_at desc);

create table if not exists index_wall_ladder_latest (
    index_symbol text not null,
    exchange text not null,
    expiry text,
    scanned_at timestamptz not null,
    spot_price double precision,
    strike double precision not null,
    call_open_interest double precision,
    put_open_interest double precision,
    call_volume double precision,
    put_volume double precision,
    raw_json jsonb not null default '{}'::jsonb,
    primary key (index_symbol, strike)
);

create table if not exists index_wall_ladder_history (
    id bigserial primary key,
    index_symbol text not null,
    exchange text not null,
    expiry text,
    scanned_at timestamptz not null,
    spot_price double precision,
    strike double precision not null,
    call_open_interest double precision,
    put_open_interest double precision,
    call_volume double precision,
    put_volume double precision,
    raw_json jsonb not null default '{}'::jsonb
);

create index if not exists idx_index_ladder_history_symbol_scanned_at
    on index_wall_ladder_history(index_symbol, scanned_at desc);

create table if not exists watchlists (
    id bigserial primary key,
    slug text not null unique,
    title text not null,
    description text,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists watchlist_items (
    watchlist_id bigint not null references watchlists(id) on delete cascade,
    symbol text not null references symbols(symbol) on delete cascade,
    source text not null default 'manual',
    state text,
    notes_json jsonb not null default '{}'::jsonb,
    added_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    primary key (watchlist_id, symbol)
);

create index if not exists idx_watchlist_items_symbol
    on watchlist_items(symbol);

create table if not exists alert_events (
    id bigserial primary key,
    symbol text references symbols(symbol) on delete cascade,
    scanned_at timestamptz not null,
    event_type text not null,
    title text not null,
    body text not null,
    priority integer not null default 1,
    action_state text,
    confidence double precision,
    raw_json jsonb not null default '{}'::jsonb
);

create index if not exists idx_alert_events_symbol_scanned_at
    on alert_events(symbol, scanned_at desc);

create table if not exists signal_transitions (
    id bigserial primary key,
    symbol text not null references symbols(symbol) on delete cascade,
    scanned_at timestamptz not null,
    previous_state text,
    current_state text not null,
    previous_grade text,
    current_grade text not null,
    previous_confidence double precision,
    current_confidence double precision not null,
    raw_json jsonb not null default '{}'::jsonb
);

create index if not exists idx_signal_transitions_symbol_scanned_at
    on signal_transitions(symbol, scanned_at desc);

create table if not exists sync_runs (
    id bigserial primary key,
    started_at timestamptz not null,
    finished_at timestamptz not null,
    status text not null,
    symbol_source text not null,
    symbol_count integer not null,
    details_json jsonb not null default '{}'::jsonb
);

create table if not exists market_eod_summary (
    trading_day date primary key,
    scanned_at timestamptz not null,
    symbol_source text not null,
    total_signals integer not null default 0,
    priority_signals integer not null default 0,
    top_symbol text references symbols(symbol) on delete set null,
    top_grade text,
    top_volume_ratio double precision,
    top_signal_reason text,
    nifty_bias text,
    nifty_wall_type text,
    nifty_wall_strike double precision,
    sensex_bias text,
    sensex_wall_type text,
    sensex_wall_strike double precision,
    raw_json jsonb not null default '{}'::jsonb
);

create table if not exists stock_eod_leaders (
    trading_day date not null,
    symbol text not null references symbols(symbol) on delete cascade,
    rank integer not null,
    scanned_at timestamptz not null,
    signal_grade text not null,
    signal_reason text not null,
    volume_ratio double precision,
    setup_type text,
    confidence double precision,
    action_state text,
    ltp double precision,
    raw_json jsonb not null default '{}'::jsonb,
    primary key (trading_day, symbol)
);

create index if not exists idx_stock_eod_leaders_day_rank
    on stock_eod_leaders(trading_day desc, rank asc);

create table if not exists instruments (
    symbol text not null,
    display_name text not null,
    exchange text not null,
    ref_id bigint not null,
    tick_size integer not null,
    lot_size integer not null,
    instrument_type text not null default 'STOCK',
    is_active boolean not null default true,
    source text not null default 'seed',
    raw_json jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    primary key (symbol, exchange)
);

create index if not exists idx_instruments_exchange_symbol
    on instruments(exchange, symbol);

create table if not exists stock_taxonomy (
    symbol text not null,
    exchange text not null default 'NSE',
    sector text,
    industry text,
    notes_json jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    primary key (symbol, exchange),
    foreign key (symbol, exchange) references instruments(symbol, exchange) on delete cascade
);

create table if not exists dashboard_universes (
    slug text primary key,
    title text not null,
    description text,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists dashboard_universe_members (
    universe_slug text not null references dashboard_universes(slug) on delete cascade,
    symbol text not null,
    exchange text not null,
    sector text,
    industry text,
    sort_order integer not null default 0,
    is_active boolean not null default true,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    primary key (universe_slug, symbol, exchange),
    foreign key (symbol, exchange) references instruments(symbol, exchange) on delete cascade
);

create index if not exists idx_dashboard_universe_members_universe_sort
    on dashboard_universe_members(universe_slug, sort_order asc, symbol asc);

create table if not exists ohlcv_1m_bars (
    symbol text not null,
    exchange text not null,
    bucket_timestamp timestamptz not null,
    open_price double precision,
    high_price double precision,
    low_price double precision,
    close_price double precision,
    bucket_volume double precision,
    cumulative_volume double precision,
    source text not null default 'historical',
    raw_json jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    primary key (symbol, exchange, bucket_timestamp),
    foreign key (symbol, exchange) references instruments(symbol, exchange) on delete cascade
);

create index if not exists idx_ohlcv_1m_bars_symbol_ts
    on ohlcv_1m_bars(symbol, exchange, bucket_timestamp desc);
