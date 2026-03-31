# System Overview

## 1. Product Definition

OraTek is an active screening and candidate extraction platform for growth-stock research. The implemented product produces three daily outputs:

1. Market Dashboard
2. RS Radar
3. Today's Watchlist

The application is designed to help the user review market context, locate leading groups, and surface candidate tickers that satisfy one or more scan conditions.

## 2. Active Scope

The active product scope is limited to:

- market environment monitoring
- sector and industry leadership review
- watchlist candidate extraction and ranking
- duplicate ticker highlighting from scan overlap
- data-quality visibility for the current run

## 3. Out-Of-Scope Areas

The active product does not implement:

- entry confirmation
- chart-structure review for execution
- position sizing
- stop placement
- exit management
- portfolio-level risk management

Those topics remain archived research material and are not active application behavior.

## 4. Current End-To-End Workflow

### 4.1 Weekly Universe Discovery

The current implementation builds a weekly universe snapshot with the Finviz screener. The latest snapshot is stored locally and reused until the snapshot TTL expires or a manual refresh is requested.

### 4.2 Daily Data Loading

For the resolved universe, the application loads daily price history from Yahoo Finance. Profile and fundamental fields are primarily sourced from the weekly universe snapshot and filled from Yahoo fallback providers when needed.

### 4.3 Local Filtering

Before scans run, the application applies a local eligible-universe filter based on market cap, average volume, ADR, price, and excluded sectors.

### 4.4 Indicator And Score Calculation

The pipeline calculates the technical indicator stack, benchmark-relative strength, research-oriented scoring layers, and watchlist annotations.

### 4.5 Candidate Extraction

The application executes nine active scan rules. Any ticker that passes at least one scan becomes part of Today's Watchlist.

### 4.6 Duplicate Highlighting

A ticker is marked as a duplicate ticker when it appears in three or more of the nine active scans.

### 4.7 Dashboard Rendering

The three active views consume the same run artifacts:

- Market Dashboard summarizes breadth, performance, factor leadership, and snapshot metrics
- RS Radar summarizes sector and industry ETF leadership plus top RS movers
- Today's Watchlist presents duplicate tickers, scan cards, and earnings context

## 5. Core Design Principles

### 5.1 Code And Config Are Authoritative

The source of truth for current behavior is:

- implementation in `src/` and `app/`
- runtime defaults in `config/default.yaml`

### 5.2 Replaceable Research Logic

Non-public or uncertain logic remains configurable rather than fixed. This includes:

- fundamental scoring details
- industry scoring details
- VCS details
- market condition component tuning
- scan thresholds and sort preferences

### 5.3 Data Lineage Is Product Behavior

Fetch status and source labels are not incidental logging. The product exposes lineage such as `live`, `cache_fresh`, `cache_stale`, `snapshot`, `sample`, and `missing` because data quality is part of the screening workflow.

## 6. Active System Layers

### 6.1 Data Layer

Responsibilities:

- weekly universe discovery
- price/profile/fundamental loading
- cache reuse and stale-cache fallback
- run snapshot persistence

### 6.2 Indicator And Scoring Layer

Responsibilities:

- technical indicator calculation
- SPY-relative strength calculation
- fundamental, industry, hybrid, and VCS scoring

### 6.3 Extraction And Presentation Layer

Responsibilities:

- scan execution
- annotation generation
- duplicate ticker aggregation
- watchlist, market, and radar views

## 7. Current Implementation Stance

The active OraTek product should be understood as a working screener with configurable research formulas. It is not a trade execution engine. The core problem it solves is daily screening and prioritization, not final discretionary trade management.
