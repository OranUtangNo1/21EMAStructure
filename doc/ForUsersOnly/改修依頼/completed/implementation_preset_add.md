## プリセット1: 50SMA Defense

```yaml
preset_name: 50SMA Defense
selected_scan_names: [50SMA Reclaim, Pullback Quality scan, Volume Accumulation, Pocket Pivot]
selected_annotation_filters: [Trend Base]
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: grouped_threshold
  required_scans: [50SMA Reclaim]
  optional_groups:
    - group_name: Pullback Quality
      scans: [Pullback Quality scan]
      min_hits: 1
    - group_name: Demand Confirmation
      scans: [Volume Accumulation, Pocket Pivot]
      min_hits: 1
preset_status: enabled
```

```
50SMAリクレイムイベント（50SMA Reclaim）
  + 直前の押し目が秩序的だった証拠（PB Quality）
  + 出来高面の需要確認（Volume Accum or Pocket Pivot）
```

PB QualityをGroup化する理由：PB Qualityの`atr_50sma_zone 0.75-3.5`と50SMA Reclaimの`atr_50sma_zone 0.0-1.0`は検出タイミングが異なる。PB Qualityが数日前に発火し（押し目中）、50SMA Reclaimが当日発火する（リクレイム日）。同日ヒットは`atr_50sma_zone ≈ 0.75-1.0`の狭い重複帯でのみ成立するため、requiredにすると候補が過度に制限される。

---

## プリセット2: Power Gap Pullback

```yaml
preset_name: Power Gap Pullback
selected_scan_names: [Pullback Quality scan, 21EMA Pattern H, 21EMA Pattern L, Reclaim scan, Volume Accumulation, Pocket Pivot]
selected_annotation_filters: [Recent Power Gap, Trend Base]
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: grouped_threshold
  required_scans: [Pullback Quality scan]
  optional_groups:
    - group_name: Reentry Trigger
      scans: [21EMA Pattern H, 21EMA Pattern L, Reclaim scan]
      min_hits: 1
    - group_name: Demand Confirmation
      scans: [Volume Accumulation, Pocket Pivot]
      min_hits: 1
preset_status: enabled
```

```
ギャップ後の押し目品質を保証（PB Quality）
  + 21EMAパターンまたはリクレイムによるリエントリトリガー
  + 出来高面の需要回帰
  × アノテーション「Recent Power Gap」でギャップ文脈をフィルター
  × アノテーション「Trend Base」でトレンド環境を限定
```

ギャップの検出をスキャン層ではなくアノテーション層に置くことで、PB Quality + トリガー + 需要のDuplicate構造は既存の押し目系プリセットと同一パターンを保つ。`Recent Power Gap`アノテーションが「最近10%以上のギャップアップがあり、20営業日以内」の銘柄だけに候補を絞る。

---

## プリセット3: RS Breakout Setup

```yaml
preset_name: RS Breakout Setup
selected_scan_names: [RS New High, VCS 52 High, Pocket Pivot, 4% bullish, PP Count]
selected_annotation_filters: [Trend Base]
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: grouped_threshold
  required_scans: [RS New High, VCS 52 High]
  optional_groups:
    - group_name: Breakout Event
      scans: [Pocket Pivot, 4% bullish, PP Count]
      min_hits: 1
preset_status: enabled
```

```
RS線が52週新高値 + 価格はまだ高値ではない（RS New High）
  + 52週高値圏でボラティリティが収縮（VCS 52 High）
  + ブレイクアウトイベントまたは蓄積の証拠（PP / 4% bullish / PP Count）
```

RS New HighとVCS 52 Highを両方requiredにする根拠：RS New Highの`dist_from_52w_high -30%〜-5%`とVCS 52 Highの`dist_from_52w_high ≥ -20%`は`-20%〜-5%`で重複する。この重複帯は「52週高値から5-20%以内でボラが収縮し、かつRS線が新高値」という最も高品質な候補に限定される。両方を通過する銘柄は少ないが、出現時の意味が極めて強い。