# Shared Price Schema

## Status

Decision accepted for the modularization refactor.

## Goal

All modules that consume daily price data must share one stable price-history contract.

The initial shared schema intentionally matches the current internal price-history format used by the existing price provider, indicator calculator, compressed tape, and stock-card generator.

## Canonical PriceHistory Shape

`PriceHistory` is a pandas `DataFrame`.

Index:

- `DatetimeIndex`
- daily trading dates
- ascending order
- timezone-naive unless a provider adapter explicitly normalizes before storage

Required columns:

- `open`
- `high`
- `low`
- `close`
- `adjusted_close`
- `volume`

Column rules:

- OHLC and `adjusted_close` values are numeric.
- `volume` is numeric.
- `adjusted_close` must exist.
- If a provider does not supply `adjusted_close`, the ingestion layer must fill it from `close`.
- Business logic must not rely on provider-specific extra columns.

## Metadata Separation

Ticker and source metadata must not be mixed into the row-level price-history DataFrame.

Metadata belongs in a separate record or manifest, including:

- `ticker`
- `provider_symbol`
- `market`
- `currency`
- `source`
- `fetched_at`
- `adjusted`

This keeps indicator, scan, market, radar, and stock-card calculations focused on numeric price history.

## as_of_date Rule

Every historical calculation must slice data before calculation:

```python
history_asof = history.loc[history.index <= as_of_date].copy()
```

No module may calculate an `as_of_date` result from rows after that date.

Output artifacts must record the effective `as_of_date` or latest trade date used for calculation.

## Shared Storage Direction

The shared storage layout is not final, but it must preserve the canonical `PriceHistory` shape.

Initial direction:

```text
shared_data/
  prices/
    US/
      AAPL.parquet
    JP/
      7203.T.parquet
  metadata/
    prices.json
```

The storage format may be Parquet or CSV during transition, but service inputs and outputs must normalize to the canonical `PriceHistory` DataFrame.

## Compatibility Notes

- US tickers can continue using provider symbols such as `AAPL`.
- Japanese equities may use provider symbols such as `7203.T`; display ticker and provider symbol should remain separable in metadata.
- Existing stock-card and compressed-tape behavior should remain compatible because the shared schema matches their current OHLCV expectation.
