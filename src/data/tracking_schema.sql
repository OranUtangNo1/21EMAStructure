PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS detection (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hit_date TEXT NOT NULL,
    preset_name TEXT NOT NULL,
    ticker TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'closed')),
    market_env TEXT,
    close_at_hit REAL,
    close_at_1d REAL,
    close_at_5d REAL,
    close_at_10d REAL,
    close_at_20d REAL,
    rs21_at_hit REAL,
    vcs_at_hit REAL,
    atr_at_hit REAL,
    hybrid_score_at_hit REAL,
    duplicate_hit_count INTEGER,
    return_1d REAL,
    return_5d REAL,
    return_10d REAL,
    return_20d REAL,
    max_gain_20d REAL,
    max_drawdown_20d REAL,
    closed_above_ema21_5d INTEGER CHECK (closed_above_ema21_5d IN (0, 1) OR closed_above_ema21_5d IS NULL),
    hit_new_high_20d INTEGER CHECK (hit_new_high_20d IN (0, 1) OR hit_new_high_20d IS NULL),
    entered INTEGER CHECK (entered IN (0, 1) OR entered IS NULL),
    entry_date TEXT,
    entry_price REAL,
    closed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(hit_date, preset_name, ticker)
);

CREATE TABLE IF NOT EXISTS detection_scans (
    detection_id INTEGER NOT NULL REFERENCES detection(id) ON DELETE CASCADE,
    scan_name TEXT NOT NULL,
    PRIMARY KEY (detection_id, scan_name)
);

CREATE TABLE IF NOT EXISTS detection_filters (
    detection_id INTEGER NOT NULL REFERENCES detection(id) ON DELETE CASCADE,
    filter_name TEXT NOT NULL,
    PRIMARY KEY (detection_id, filter_name)
);

CREATE TABLE IF NOT EXISTS scan_hits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hit_date TEXT NOT NULL,
    ticker TEXT NOT NULL,
    scan_name TEXT NOT NULL,
    kind TEXT,
    UNIQUE(hit_date, ticker, scan_name)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_detection_active_unique
ON detection(preset_name, ticker)
WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_detection_active_lookup
ON detection(preset_name, ticker, status);

CREATE INDEX IF NOT EXISTS idx_detection_market_env
ON detection(market_env, status);

CREATE INDEX IF NOT EXISTS idx_detection_hit_date
ON detection(hit_date);

CREATE INDEX IF NOT EXISTS idx_detection_status
ON detection(status);

CREATE INDEX IF NOT EXISTS idx_scan_hits_ticker
ON scan_hits(ticker, hit_date);

CREATE INDEX IF NOT EXISTS idx_scan_hits_scan
ON scan_hits(scan_name, hit_date);

DROP VIEW IF EXISTS v_detection_detail;
CREATE VIEW v_detection_detail AS
SELECT
    d.id AS detection_id,
    d.hit_date,
    d.preset_name,
    d.ticker,
    d.status,
    d.market_env,
    d.close_at_hit,
    d.close_at_1d,
    d.close_at_5d,
    d.close_at_10d,
    d.close_at_20d,
    d.rs21_at_hit,
    d.vcs_at_hit,
    d.atr_at_hit,
    d.hybrid_score_at_hit,
    d.duplicate_hit_count,
    d.return_1d,
    d.return_5d,
    d.return_10d,
    d.return_20d,
    d.max_gain_20d,
    d.max_drawdown_20d,
    d.closed_above_ema21_5d,
    d.hit_new_high_20d,
    d.entered,
    d.entry_date,
    d.entry_price,
    d.closed_at,
    d.created_at,
    (
        SELECT GROUP_CONCAT(ordered.scan_name, ', ')
        FROM (
            SELECT ds.scan_name
            FROM detection_scans ds
            WHERE ds.detection_id = d.id
            ORDER BY ds.scan_name
        ) ordered
    ) AS hit_scans,
    (
        SELECT GROUP_CONCAT(ordered.filter_name, ', ')
        FROM (
            SELECT df.filter_name
            FROM detection_filters df
            WHERE df.detection_id = d.id
            ORDER BY df.filter_name
        ) ordered
    ) AS matched_filters
FROM detection d;

DROP VIEW IF EXISTS v_preset_horizon_performance;
CREATE VIEW v_preset_horizon_performance AS
WITH horizon_returns AS (
    SELECT hit_date, preset_name, ticker, status, market_env, 1 AS horizon_days, return_1d AS return_pct
    FROM detection
    WHERE return_1d IS NOT NULL
    UNION ALL
    SELECT hit_date, preset_name, ticker, status, market_env, 5 AS horizon_days, return_5d AS return_pct
    FROM detection
    WHERE return_5d IS NOT NULL
    UNION ALL
    SELECT hit_date, preset_name, ticker, status, market_env, 10 AS horizon_days, return_10d AS return_pct
    FROM detection
    WHERE return_10d IS NOT NULL
    UNION ALL
    SELECT hit_date, preset_name, ticker, status, market_env, 20 AS horizon_days, return_20d AS return_pct
    FROM detection
    WHERE return_20d IS NOT NULL
)
SELECT
    preset_name,
    market_env,
    horizon_days,
    COUNT(*) AS detection_count,
    COUNT(DISTINCT ticker) AS ticker_count,
    SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active_count,
    SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) AS closed_count,
    ROUND(AVG(return_pct), 2) AS avg_return_pct,
    ROUND(MIN(return_pct), 2) AS min_return_pct,
    ROUND(MAX(return_pct), 2) AS max_return_pct,
    ROUND(AVG(CASE WHEN return_pct > 0 THEN 1.0 ELSE 0.0 END), 3) AS win_rate,
    MIN(hit_date) AS first_hit_date,
    MAX(hit_date) AS last_hit_date
FROM horizon_returns
GROUP BY preset_name, market_env, horizon_days;

DROP VIEW IF EXISTS v_preset_scan_performance;
CREATE VIEW v_preset_scan_performance AS
WITH scan_horizon_returns AS (
    SELECT
        d.hit_date,
        d.preset_name,
        d.ticker,
        d.status,
        d.market_env,
        ds.scan_name,
        1 AS horizon_days,
        d.return_1d AS return_pct,
        d.max_gain_20d,
        d.max_drawdown_20d
    FROM detection d
    JOIN detection_scans ds ON ds.detection_id = d.id
    WHERE d.return_1d IS NOT NULL
    UNION ALL
    SELECT
        d.hit_date,
        d.preset_name,
        d.ticker,
        d.status,
        d.market_env,
        ds.scan_name,
        5 AS horizon_days,
        d.return_5d AS return_pct,
        d.max_gain_20d,
        d.max_drawdown_20d
    FROM detection d
    JOIN detection_scans ds ON ds.detection_id = d.id
    WHERE d.return_5d IS NOT NULL
    UNION ALL
    SELECT
        d.hit_date,
        d.preset_name,
        d.ticker,
        d.status,
        d.market_env,
        ds.scan_name,
        10 AS horizon_days,
        d.return_10d AS return_pct,
        d.max_gain_20d,
        d.max_drawdown_20d
    FROM detection d
    JOIN detection_scans ds ON ds.detection_id = d.id
    WHERE d.return_10d IS NOT NULL
    UNION ALL
    SELECT
        d.hit_date,
        d.preset_name,
        d.ticker,
        d.status,
        d.market_env,
        ds.scan_name,
        20 AS horizon_days,
        d.return_20d AS return_pct,
        d.max_gain_20d,
        d.max_drawdown_20d
    FROM detection d
    JOIN detection_scans ds ON ds.detection_id = d.id
    WHERE d.return_20d IS NOT NULL
)
SELECT
    preset_name,
    scan_name,
    market_env,
    horizon_days,
    COUNT(*) AS detection_count,
    COUNT(DISTINCT ticker) AS ticker_count,
    SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active_count,
    SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) AS closed_count,
    ROUND(AVG(return_pct), 2) AS avg_return_pct,
    ROUND(MIN(return_pct), 2) AS min_return_pct,
    ROUND(MAX(return_pct), 2) AS max_return_pct,
    ROUND(AVG(CASE WHEN return_pct > 0 THEN 1.0 ELSE 0.0 END), 3) AS win_rate,
    ROUND(AVG(CASE WHEN horizon_days = 20 THEN max_gain_20d END), 2) AS avg_max_gain_20d,
    ROUND(AVG(CASE WHEN horizon_days = 20 THEN max_drawdown_20d END), 2) AS avg_max_drawdown_20d,
    MIN(hit_date) AS first_hit_date,
    MAX(hit_date) AS last_hit_date
FROM scan_horizon_returns
GROUP BY preset_name, scan_name, market_env, horizon_days;

DROP VIEW IF EXISTS v_preset_summary;
CREATE VIEW v_preset_summary AS
SELECT
    preset_name,
    market_env,
    COUNT(*) AS detection_count,
    ROUND(AVG(return_5d), 2) AS avg_return_5d,
    ROUND(AVG(return_20d), 2) AS avg_return_20d,
    ROUND(AVG(CASE WHEN return_5d > 0 THEN 1.0 ELSE 0.0 END), 3) AS win_rate_5d,
    ROUND(AVG(CASE WHEN return_20d > 0 THEN 1.0 ELSE 0.0 END), 3) AS win_rate_20d,
    ROUND(AVG(max_gain_20d), 2) AS avg_max_gain,
    ROUND(AVG(max_drawdown_20d), 2) AS avg_max_drawdown
FROM detection
WHERE status = 'closed'
GROUP BY preset_name, market_env;

DROP VIEW IF EXISTS v_scan_combo_performance;
CREATE VIEW v_scan_combo_performance AS
SELECT
    sub.preset_name,
    sub.scan_combo,
    COUNT(*) AS detection_count,
    ROUND(AVG(sub.return_5d), 2) AS avg_return_5d,
    ROUND(AVG(sub.return_20d), 2) AS avg_return_20d,
    ROUND(AVG(CASE WHEN sub.return_20d > 0 THEN 1.0 ELSE 0.0 END), 3) AS win_rate_20d,
    ROUND(AVG(sub.max_drawdown_20d), 2) AS avg_max_drawdown
FROM (
    SELECT
        d.id,
        d.preset_name,
        d.return_5d,
        d.return_20d,
        d.max_drawdown_20d,
        (
            SELECT GROUP_CONCAT(ordered.scan_name, ', ')
            FROM (
                SELECT ds2.scan_name
                FROM detection_scans ds2
                WHERE ds2.detection_id = d.id
                ORDER BY ds2.scan_name
            ) ordered
        ) AS scan_combo
    FROM detection d
    WHERE d.status = 'closed'
) sub
GROUP BY sub.preset_name, sub.scan_combo;

DROP VIEW IF EXISTS v_preset_overlap;
CREATE VIEW v_preset_overlap AS
SELECT
    d.hit_date,
    d.ticker,
    GROUP_CONCAT(d.preset_name, ', ') AS hit_presets,
    COUNT(DISTINCT d.preset_name) AS preset_count
FROM detection d
WHERE d.hit_date = (SELECT MAX(hit_date) FROM detection)
GROUP BY d.hit_date, d.ticker
HAVING preset_count >= 2;
