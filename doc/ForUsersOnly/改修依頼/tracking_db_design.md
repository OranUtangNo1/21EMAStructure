# トラッキング DB 設計書

作成日: 2026-04-17

---

## 1. 目的

プリセットが検出したティッカーのその後のパフォーマンスを追跡し、裁量エントリの精度向上に資するフィードバックループを構築する。

### 1.1 解決する問題

- 検出ティッカーの蓄積量が増加し、CSV ベースの管理が煩雑化している
- 検出レコードと追跡結果が別ファイルに分離しており、突合処理が複雑
- 過去データの横断クエリ（期間別、プリセット別、スキャン組み合わせ別）に毎回複数ファイルの結合が必要
- 検出時のコンテキスト（どのスキャンがヒットしたか、市場環境は何か）が記録されておらず、事後分析の解像度が低い

### 1.2 設計方針

- Python 標準ライブラリの `sqlite3` を使用し、外部依存を追加しない
- DB ファイル 1 つで完結するサーバーレス構成
- テーブルは正規化し、JSON カラムを排除する
- 集計はマテリアライズドテーブルではなく VIEW で提供する（年間想定データ量 約 11,250 行で十分高速）
- 将来の AI インポートや統計処理は `pd.read_sql()` で直接アクセスする前提

---

## 2. データソースの再編

### 2.1 DB に統合する既存出力

| 既存出力 | 現在の形式 | DB での扱い |
|---|---|---|
| `data_runs/preset_effectiveness/events.csv` | 日次 CSV | `detection` テーブルの INSERT 時カラムに統合 |
| `data_runs/preset_effectiveness/outcomes.csv` | 日次 CSV | `detection` テーブルの後日 UPDATE カラムに統合 |
| `data_runs/scan_hits/` | 日次 CSV | `scan_hits` テーブルに置換 |
| `data_runs/preset_exports/`（重複ヒット要約） | 日次 CSV | `v_preset_overlap` VIEW で導出、独立テーブル不要 |
| `data_runs/preset_exports/`（プリセット別詳細） | 日次 CSV | `detection` + `detection_scans` から導出、独立テーブル不要 |

### 2.2 ファイルのまま残す既存出力

| 既存出力 | 理由 | 推奨変更 |
|---|---|---|
| `data_runs/watchlist/` | 数十〜数百カラムの幅広スナップショット。DB 化するとスキーマ管理コストが利益を上回る | parquet 化を推奨 |
| `data_runs/universe_snapshots/` | 同上 | parquet 化を推奨 |

---

## 3. DB ファイル構成

```
tracking.db           ← SQLite3 データベースファイル（単一ファイル）

テーブル (4)
├── detection           ← 検出レコード本体
├── detection_scans     ← 検出時にヒットしたスキャン（正規化）
├── detection_filters   ← 検出時にヒットしたアノテーションフィルタ（正規化）
└── scan_hits           ← 全スキャンの生ヒット（プリセット適用前）

VIEW (3)
├── v_preset_summary            ← プリセット × 環境別の成績集計
├── v_scan_combo_performance    ← スキャン組み合わせ別の成績集計
└── v_preset_overlap            ← プリセット横断の重複ヒット要約

インデックス (6)
├── idx_detection_active_lookup
├── idx_detection_market_env
├── idx_detection_hit_date
├── idx_detection_status
├── idx_scan_hits_ticker
└── idx_scan_hits_scan
```

---

## 4. テーブル定義

### 4.1 `detection`

検出レコードの本体。旧 `events.csv` と `outcomes.csv` を 1 テーブルに統合する。

```sql
CREATE TABLE detection (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 検出コンテキスト（検出日に INSERT）
    hit_date              TEXT    NOT NULL,
    preset_name           TEXT    NOT NULL,
    ticker                TEXT    NOT NULL,
    status                TEXT    NOT NULL DEFAULT 'active',
    market_env            TEXT,
    close_at_hit          REAL,
    rs21_at_hit           REAL,
    vcs_at_hit            REAL,
    atr_at_hit            REAL,
    hybrid_score_at_hit   REAL,
    duplicate_hit_count   INTEGER,

    -- パフォーマンストラッキング（後日 UPDATE）
    return_1d             REAL,
    return_5d             REAL,
    return_10d            REAL,
    return_20d            REAL,
    max_gain_20d          REAL,
    max_drawdown_20d      REAL,
    closed_above_ema21_5d BOOLEAN,
    hit_new_high_20d      BOOLEAN,

    -- 裁量エントリログ（手動 or 外部ツールで UPDATE）
    entered               BOOLEAN,
    entry_date            TEXT,
    entry_price           REAL,

    -- ライフサイクル管理
    closed_at             TEXT,
    created_at            TEXT    NOT NULL DEFAULT (datetime('now')),

    UNIQUE(hit_date, preset_name, ticker)
);
```

#### カラム詳細

**検出コンテキスト（INSERT 時に確定）**

| カラム | 型 | 説明 |
|---|---|---|
| `hit_date` | TEXT | 検出日。`YYYY-MM-DD` 形式 |
| `preset_name` | TEXT | 検出プリセット名 |
| `ticker` | TEXT | ティッカーシンボル |
| `status` | TEXT | `'active'` または `'closed'`。デフォルト `'active'` |
| `market_env` | TEXT | 検出日の市場環境ラベル |
| `close_at_hit` | REAL | 検出日の終値 |
| `rs21_at_hit` | REAL | 検出日の RS21 |
| `vcs_at_hit` | REAL | 検出日の VCS スコア |
| `atr_at_hit` | REAL | 検出日の ATR |
| `hybrid_score_at_hit` | REAL | 検出日の hybrid score |
| `duplicate_hit_count` | INTEGER | プリセット内でのスキャンヒット数 |

**パフォーマンストラッキング（後日 UPDATE で埋める）**

| カラム | 型 | 説明 |
|---|---|---|
| `return_1d` | REAL | 検出翌日の騰落率（%） |
| `return_5d` | REAL | 5 営業日後の騰落率（%） |
| `return_10d` | REAL | 10 営業日後の騰落率（%） |
| `return_20d` | REAL | 20 営業日後の騰落率（%） |
| `max_gain_20d` | REAL | 20 営業日以内の最大上昇率（%） |
| `max_drawdown_20d` | REAL | 20 営業日以内の最大ドローダウン（%） |
| `closed_above_ema21_5d` | BOOLEAN | 5 日後に 21EMA より上で引けているか |
| `hit_new_high_20d` | BOOLEAN | 20 日以内に新高値をつけたか |

**裁量エントリログ（任意、手動または外部ツールで UPDATE）**

| カラム | 型 | 説明 |
|---|---|---|
| `entered` | BOOLEAN | 裁量でエントリしたか。未記録時は NULL |
| `entry_date` | TEXT | エントリ日。`YYYY-MM-DD` 形式 |
| `entry_price` | REAL | エントリ価格 |

**ライフサイクル管理**

| カラム | 型 | 説明 |
|---|---|---|
| `closed_at` | TEXT | `status` が `'closed'` に遷移した日付 |
| `created_at` | TEXT | レコード作成日時。自動設定 |

#### UNIQUE 制約

`UNIQUE(hit_date, preset_name, ticker)` により、同一日・同一プリセット・同一ティッカーの重複 INSERT を DB レベルで防止する。

### 4.2 `detection_scans`

検出時にヒットしたスキャンの正規化テーブル。1 つの detection レコードに対し、ヒットしたスキャンの数だけ行が生成される。

```sql
CREATE TABLE detection_scans (
    detection_id  INTEGER NOT NULL REFERENCES detection(id) ON DELETE CASCADE,
    scan_name     TEXT    NOT NULL,
    PRIMARY KEY (detection_id, scan_name)
);
```

#### 使用例

Base Breakout で VCS 52 High, Pocket Pivot, 97 Club の 3 スキャンにヒットした場合、detection_scans に 3 行が INSERT される。

```
detection_id=42, scan_name='VCS 52 High'
detection_id=42, scan_name='Pocket Pivot'
detection_id=42, scan_name='97 Club'
```

### 4.3 `detection_filters`

検出時にヒットしたアノテーションフィルタの正規化テーブル。構造は `detection_scans` と同一。

```sql
CREATE TABLE detection_filters (
    detection_id  INTEGER NOT NULL REFERENCES detection(id) ON DELETE CASCADE,
    filter_name   TEXT    NOT NULL,
    PRIMARY KEY (detection_id, filter_name)
);
```

### 4.4 `scan_hits`

プリセット適用前の、全スキャンの生ヒット記録。旧 `data_runs/scan_hits/` の日次 CSV を置換する。

```sql
CREATE TABLE scan_hits (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    hit_date  TEXT    NOT NULL,
    ticker    TEXT    NOT NULL,
    scan_name TEXT    NOT NULL,
    kind      TEXT,
    UNIQUE(hit_date, ticker, scan_name)
);
```

#### `detection_scans` との関係

| テーブル | 意味 | 粒度 |
|---|---|---|
| `scan_hits` | プリセット適用前の全スキャン生ヒット | 全ティッカー × 全スキャン |
| `detection_scans` | プリセット経由で検出された際にヒットしていたスキャン | プリセット検出ティッカーのみ |

両者を JOIN することで「スキャンにはヒットしたがプリセットには拾われなかった銘柄のその後」を分析可能。

---

## 5. インデックス定義

```sql
-- detection: Active レコードの存在チェック（毎回の起動で全検出ティッカーに対して実行）
CREATE INDEX idx_detection_active_lookup ON detection(preset_name, ticker, status);

-- detection: 市場環境別の集計クエリ
CREATE INDEX idx_detection_market_env ON detection(market_env, status);

-- detection: 日付範囲の集計クエリ
CREATE INDEX idx_detection_hit_date ON detection(hit_date);

-- detection: status による絞り込み
CREATE INDEX idx_detection_status ON detection(status);

-- scan_hits: ティッカー別のヒット履歴検索
CREATE INDEX idx_scan_hits_ticker ON scan_hits(ticker, hit_date);

-- scan_hits: スキャン別のヒット傾向分析
CREATE INDEX idx_scan_hits_scan ON scan_hits(scan_name, hit_date);
```

---

## 6. VIEW 定義

### 6.1 `v_preset_summary`

プリセット × 市場環境別の成績集計。Closed レコードのみを対象とする。

```sql
CREATE VIEW v_preset_summary AS
SELECT
    preset_name,
    market_env,
    COUNT(*)                                              AS detection_count,
    ROUND(AVG(return_5d), 2)                              AS avg_return_5d,
    ROUND(AVG(return_20d), 2)                             AS avg_return_20d,
    ROUND(AVG(CASE WHEN return_5d  > 0 THEN 1.0 ELSE 0.0 END), 3) AS win_rate_5d,
    ROUND(AVG(CASE WHEN return_20d > 0 THEN 1.0 ELSE 0.0 END), 3) AS win_rate_20d,
    ROUND(AVG(max_gain_20d), 2)                           AS avg_max_gain,
    ROUND(AVG(max_drawdown_20d), 2)                       AS avg_max_drawdown
FROM detection
WHERE status = 'closed'
GROUP BY preset_name, market_env;
```

### 6.2 `v_scan_combo_performance`

スキャン組み合わせ別の成績集計。同一 detection に紐づくスキャン群をソート済み文字列として結合し、組み合わせパターンとして扱う。

```sql
CREATE VIEW v_scan_combo_performance AS
SELECT
    sub.preset_name,
    sub.scan_combo,
    COUNT(*)                                              AS detection_count,
    ROUND(AVG(sub.return_5d), 2)                          AS avg_return_5d,
    ROUND(AVG(sub.return_20d), 2)                         AS avg_return_20d,
    ROUND(AVG(CASE WHEN sub.return_20d > 0 THEN 1.0 ELSE 0.0 END), 3) AS win_rate_20d,
    ROUND(AVG(sub.max_drawdown_20d), 2)                   AS avg_max_drawdown
FROM (
    SELECT
        d.id,
        d.preset_name,
        d.return_5d,
        d.return_20d,
        d.max_drawdown_20d,
        GROUP_CONCAT(ds.scan_name, ', ') AS scan_combo
    FROM detection d
    JOIN detection_scans ds ON d.id = ds.detection_id
    WHERE d.status = 'closed'
    GROUP BY d.id
) sub
GROUP BY sub.preset_name, sub.scan_combo;
```

### 6.3 `v_preset_overlap`

プリセット横断の重複ヒット要約。直近の hit_date に対し、どの銘柄がどのプリセットで検出されたかを集約する。旧 `preset_exports` の重複ヒット要約 CSV を置換する。

```sql
CREATE VIEW v_preset_overlap AS
SELECT
    d.hit_date,
    d.ticker,
    GROUP_CONCAT(d.preset_name, ', ') AS hit_presets,
    COUNT(DISTINCT d.preset_name)     AS preset_count
FROM detection d
WHERE d.hit_date = (SELECT MAX(hit_date) FROM detection)
GROUP BY d.ticker
HAVING preset_count >= 2;
```

---

## 7. レコード管理ルール

### 7.1 登録判定

パイプライン実行時、プリセットが検出したティッカーごとに以下を判定する。

```
[preset_name, ticker] の組について:
  detection テーブルに status = 'active' のレコードが存在するか?
    → 存在する: INSERT をスキップ（同一セットアップのトレース中）
    → 存在しない: 新規 INSERT
```

この判定により、Active 中の同一 `[preset_name, ticker]` ペアが重複登録されることはない。Closed 済みの同一ペアが再検出された場合は、新しい `hit_date` で新規レコードが作成される。

#### 実装例（Python）

```python
import sqlite3

def should_register(conn: sqlite3.Connection, preset_name: str, ticker: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM detection WHERE preset_name = ? AND ticker = ? AND status = 'active' LIMIT 1",
        (preset_name, ticker),
    )
    return cur.fetchone() is None
```

### 7.2 パフォーマンス更新

起動時の価格取得フェーズで、Active レコードのパフォーマンスカラムを更新する。

```
1. SELECT id, ticker, hit_date, close_at_hit FROM detection WHERE status = 'active'
   → Active ティッカーのみが価格取得の対象
2. 取得した価格データから各ホライズンのリターン、max_gain、max_drawdown を計算
3. UPDATE detection SET return_1d = ?, return_5d = ?, ... WHERE id = ?
```

#### 各カラムの計算定義

| カラム | 計算 |
|---|---|
| `return_Nd` | `((close_at_N / close_at_hit) - 1.0) * 100.0` |
| `max_gain_20d` | `((max(high[hit_date+1 : hit_date+20]) / close_at_hit) - 1.0) * 100.0` |
| `max_drawdown_20d` | `((min(low[hit_date+1 : hit_date+20]) / close_at_hit) - 1.0) * 100.0` |
| `closed_above_ema21_5d` | `close_at_5d > ema21_at_5d` |
| `hit_new_high_20d` | `max(high[hit_date+1 : hit_date+20]) > high_20d_at_hit` |

### 7.3 ライフサイクル遷移

```
パフォーマンス更新の後:
  hit_date から 20 営業日以上経過した Active レコードを Closed に遷移する

  UPDATE detection
  SET status = 'closed', closed_at = :today
  WHERE status = 'active'
    AND hit_date <= :date_20_business_days_ago
```

遷移後、当該レコードは以後の価格取得対象から除外される。パフォーマンスカラムは全て埋まった状態で確定する。

### 7.4 scan_hits の登録

スキャン実行フェーズで、全スキャンの生ヒットを `scan_hits` に INSERT する。`UNIQUE(hit_date, ticker, scan_name)` 制約により、同日同一ヒットの重複は DB レベルで防止される。

```python
def insert_scan_hits(conn: sqlite3.Connection, hit_date: str, hits: list[dict]):
    conn.executemany(
        "INSERT OR IGNORE INTO scan_hits (hit_date, ticker, scan_name, kind) VALUES (?, ?, ?, ?)",
        [(hit_date, h["ticker"], h["scan_name"], h.get("kind")) for h in hits],
    )
    conn.commit()
```

---

## 8. パイプライン統合

### 8.1 処理フロー

```
パイプライン起動
│
├─ 1. データ取得・指標計算・スコアリング（既存、変更なし）
│
├─ 2. スキャン実行
│   ├─ ScanRunner.run() → hits, watchlist（既存、変更なし）
│   └─ scan_hits テーブルへ INSERT                    ← 新規
│
├─ 3. プリセット適用・検出
│   ├─ WatchlistViewModelBuilder（既存、変更なし）
│   └─ detection テーブルへの登録判定・INSERT          ← 新規
│       ├─ detection_scans への INSERT
│       └─ detection_filters への INSERT
│
├─ 4. 価格取得（Active ティッカー分）
│   └─ detection テーブルのパフォーマンスカラム UPDATE  ← 新規（既存 CSV 更新を置換）
│
├─ 5. ライフサイクル遷移
│   └─ 20 営業日超過 Active → Closed                  ← 新規（既存 CSV 管理を置換）
│
├─ 6. ファイル出力（変更なし）
│   ├─ watchlist スナップショット（ファイル継続）
│   └─ universe スナップショット（ファイル継続）
│
└─ 終了
```

### 8.2 DB 接続管理

```python
import sqlite3
from pathlib import Path

DB_PATH = Path("data_runs/tracking.db")

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
```

`PRAGMA journal_mode=WAL`: 書き込み中の読み取りを安全にする。パイプライン実行中に別プロセスで分析クエリを走らせる場合に有効。

`PRAGMA foreign_keys=ON`: `detection_scans` / `detection_filters` の外部キー制約を有効化。`ON DELETE CASCADE` を機能させるために必須。

### 8.3 初期化

DB ファイルが存在しない場合、初回起動時にスキーマを自動作成する。

```python
def initialize_db(conn: sqlite3.Connection):
    schema_path = Path("sql/schema.sql")
    conn.executescript(schema_path.read_text())
```

`sql/schema.sql` に §4〜§6 の CREATE TABLE / CREATE INDEX / CREATE VIEW を全て記述する。

---

## 9. 分析クエリ例

### 9.1 プリセット別の直近 90 日成績

```sql
SELECT
    preset_name,
    COUNT(*)                                              AS n,
    ROUND(AVG(return_20d), 2)                             AS avg_r20,
    ROUND(AVG(CASE WHEN return_20d > 0 THEN 1.0 ELSE 0.0 END), 3) AS wr20,
    ROUND(AVG(max_drawdown_20d), 2)                       AS avg_mdd
FROM detection
WHERE status = 'closed'
  AND hit_date >= date('now', '-90 days')
GROUP BY preset_name
ORDER BY wr20 DESC;
```

### 9.2 市場環境別のプリセット成績比較

```sql
SELECT
    preset_name,
    market_env,
    COUNT(*)                                              AS n,
    ROUND(AVG(return_20d), 2)                             AS avg_r20,
    ROUND(AVG(CASE WHEN return_20d > 0 THEN 1.0 ELSE 0.0 END), 3) AS wr20
FROM detection
WHERE status = 'closed'
GROUP BY preset_name, market_env
ORDER BY preset_name, wr20 DESC;
```

### 9.3 スキャンにはヒットしたがプリセットに拾われなかった銘柄の追跡

```sql
SELECT
    sh.ticker,
    sh.scan_name,
    sh.hit_date,
    d.id AS detection_id
FROM scan_hits sh
LEFT JOIN detection d
    ON sh.ticker = d.ticker
    AND sh.hit_date = d.hit_date
WHERE sh.hit_date >= date('now', '-30 days')
  AND d.id IS NULL
ORDER BY sh.hit_date DESC, sh.ticker;
```

### 9.4 裁量エントリ判断の振り返り

```sql
SELECT
    CASE
        WHEN entered = 1 THEN 'Entered'
        ELSE 'Not entered'
    END AS decision,
    COUNT(*)                                              AS n,
    ROUND(AVG(return_20d), 2)                             AS avg_r20,
    ROUND(AVG(CASE WHEN return_20d > 0 THEN 1.0 ELSE 0.0 END), 3) AS wr20,
    ROUND(AVG(max_gain_20d), 2)                           AS avg_max_gain,
    ROUND(AVG(max_drawdown_20d), 2)                       AS avg_mdd
FROM detection
WHERE status = 'closed'
  AND entered IS NOT NULL
GROUP BY decision;
```

### 9.5 特定スキャン組み合わせの成績

```sql
SELECT *
FROM v_scan_combo_performance
WHERE preset_name = 'Base Breakout'
ORDER BY detection_count DESC;
```

---

## 10. 既存 CSV 出力の廃止判断

| 既存出力 | 置換先 | 廃止可否 |
|---|---|---|
| `preset_effectiveness/events.csv` | `detection` テーブル INSERT | 廃止 |
| `preset_effectiveness/outcomes.csv` | `detection` テーブル UPDATE | 廃止 |
| `scan_hits/` 日次 CSV | `scan_hits` テーブル | 廃止 |
| `preset_exports/` 重複ヒット要約 | `v_preset_overlap` VIEW | 廃止 |
| `preset_exports/` プリセット別詳細 | `detection` + `detection_scans` から導出 | 廃止 |
| `watchlist/` スナップショット | ファイル継続 | 廃止しない（parquet 化推奨） |
| `universe_snapshots/` | ファイル継続 | 廃止しない（parquet 化推奨） |

---

## 11. 将来の拡張余地

### 11.1 `entered` カラムの自動化

現状は手動 UPDATE を想定するが、将来的にブローカー API やトレードログとの連携により、エントリ有無の自動記録が可能。`entry_date` / `entry_price` カラムが初期スキーマに含まれているため、スキーマ変更なしで対応可能。

### 11.2 Market Environment 連動によるプリセット自動制御

`v_preset_summary` の `market_env` 別成績を参照し、成績が悪い環境ではプリセットを自動 disable する機構。detection テーブルに `market_env` が記録されているため、判断に必要なデータは既に蓄積される構造になっている。

### 11.3 scan_hits の長期保持とデータ量管理

`scan_hits` は全スキャン × 全ティッカーの生ヒットを記録するため、`detection` より増加ペースが速い。年間数万〜数十万行になり得る。パフォーマンスが問題になった場合は、N 日以前のレコードをアーカイブテーブルに移動するか、古いデータを DELETE する運用ルールを検討する。現時点では SQLite のパフォーマンス上限に達しない見込み。
