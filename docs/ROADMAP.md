# Metrics Implementation Roadmap

This roadmap breaks the metrics from [METRICS.md](METRICS.md) into Work Packages for phased implementation. Work Packages are ordered by dependency and value.

---

## Overview

| WP | Name                         | Scope                    | Dependencies |
|----|------------------------------|---------------------------|--------------|
| 1  | Core Value and Activity      | Lot count, market value, avg lot size | None |
| 2  | Price Distribution           | Price spread, median, percentiles     | WP1 |
| 3  | Gear Dimension               | Gear filter and breakdown             | WP1 |
| 4  | Species Sub-Metrics          | Grade, processing, condition parsing  | None |
| 5  | Time-Based Analytics         | WoW, MoM, seasonality, correlation    | WP1, WP2 |
| 6  | Supply-Price Relationship    | Correlation, elasticity               | WP5 |

---

## Work Package 1: Core Value and Activity

**Goal:** Extend the timeseries API and UI with high-value, low-effort metrics.

**Scope:**
- Lot count (number of sales per day)
- Total market value (`Price/KG * Weight` summed per day)
- Average lot size (`total weight / lot count` per day)

**Deliverables:**
- API: Add `lot_count`, `total_value`, `avg_lot_size` to timeseries response
- UI: Display summary stats and optionally chart total value
- Tests: Unit tests for new fields

**Effort:** Small

---

## Work Package 2: Price Distribution and Spread

**Goal:** Improve price analysis with distribution metrics that are less sensitive to outliers.

**Scope:**
- Price range (min and max Price/KG per day)
- Median price
- Percentile prices (P10, P25, P75, P90) optional
- Price standard deviation
- Coefficient of variation (optional)

**Deliverables:**
- API: Add `min_price`, `max_price`, `median_price`, `price_std_dev` to timeseries
- UI: Show price band (min-max) on chart or in summary; optional percentile view
- Tests: Unit tests for new aggregations

**Dependencies:** WP1 (shares timeseries structure)

**Effort:** Small to Medium

---

## Work Package 3: Gear Dimension

**Goal:** Add Gear as a filter and breakdown dimension across the app.

**Scope:**
- Include Gear in database queries
- Gear filter dropdown (multi-select or single)
- Tonnage by gear
- Price by gear
- Lot count by gear
- Gear mix over time (share of total)
- Gear by species (which gears for which species)
- Value by gear x species
- Gear premium (price difference between gear types)

**Deliverables:**
- API: `GET /api/gear` - list distinct gear types
- API: Extend timeseries to accept optional `gear` filter and return gear breakdown
- API: Optional `GET /api/gear-breakdown` for gear x species matrix
- UI: Gear filter control; gear breakdown chart or table
- Tests: Unit tests for gear filtering and aggregations

**Dependencies:** WP1 (lot count, value used in gear breakdowns)

**Effort:** Medium to Large

---

## Work Package 4: Species Sub-Metrics

**Goal:** Parse grade, processing, and condition from Species string and expose price-by-subtype metrics.

**Scope:**
- Extract grade/size (e.g. 1, 4) from Species
- Extract processing (e.g. GUT, WNG) from Species
- Extract condition (e.g. DAM, NELSON) from Species
- Price premium by grade
- Price by processing type
- Price discount by condition

**Deliverables:**
- Shared: Parsing functions for grade, processing, condition (extend `_normalize_species` or add helpers)
- API: Optional filter by grade/processing/condition
- API: Add sub-metrics to timeseries or new endpoint for species breakdown
- UI: Sub-metric selector or separate breakdown view
- Tests: Unit tests for parsing; integration tests for new API

**Dependencies:** None (can run in parallel with WP1-3)

**Effort:** Medium

---

## Work Package 5: Time-Based Analytics

**Goal:** Add period-over-period and seasonal analysis.

**Scope:**
- Week-over-week change (% change vs prior week)
- Month-over-month change (% change vs prior month)
- Seasonality: patterns by day-of-week
- Seasonality: patterns by month
- Rolling correlation (price vs tonnage over configurable window)

**Deliverables:**
- API: Add `wow_change`, `mom_change` to timeseries or new comparison endpoint
- API: Optional `GET /api/seasonality` for day-of-week / month aggregates
- API: Optional `rolling_correlation` in timeseries
- UI: Period comparison summary; seasonality chart
- Tests: Unit tests for WoW/MoM calculation; correlation logic

**Dependencies:** WP1, WP2 (needs daily aggregates)

**Effort:** Medium to Large

---

## Work Package 6: Supply-Price Relationship

**Goal:** Formalise supply-demand analytics.

**Scope:**
- Price-tonnage correlation (over period)
- Supply elasticity (optional, more complex)

**Deliverables:**
- API: Add `price_tonnage_correlation` to timeseries or summary endpoint
- UI: Display correlation; optional scatter plot of price vs tonnage
- Tests: Unit tests for correlation calculation

**Dependencies:** WP5 (builds on time-series structure and may reuse correlation logic)

**Effort:** Small to Medium

---

## Suggested Phasing

**Phase 1 (Quick wins):**
- WP1: Core Value and Activity
- WP2: Price Distribution

**Phase 2 (New dimension):**
- WP3: Gear Dimension

**Phase 3 (Parallel or sequential):**
- WP4: Species Sub-Metrics
- WP5: Time-Based Analytics

**Phase 4 (Advanced):**
- WP6: Supply-Price Relationship

---

## Notes

- WP1 and WP4 have no dependencies and can be started immediately.
- WP3 is the largest change (new dimension, new API, UI updates).
- WP5 and WP6 add analytical depth; WP6 can be deferred if correlation is covered in WP5.
