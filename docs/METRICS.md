# Possible Metrics from Brixham Market Data

This document lists metrics that could be derived from the `market_data.brixham` table. The app currently uses Date, Species, Price/KG, and Weight. The table also includes Gear, Location (always Brixham), and id.

## Table Schema

| Column    | Type         | Description                    |
|-----------|--------------|--------------------------------|
| id        | int(11)      | Primary key, auto-increment    |
| Species   | varchar(255) | Fish species with grade/format |
| Gear      | varchar(45)  | Fishing gear type              |
| Weight    | decimal(12,2)| Tonnage (kg)                   |
| Price/KG  | decimal(12,2)| Price per kilogram             |
| Date      | date         | Market date                    |
| Location  | varchar(25)  | Landing or sale location (always Brixham in this dataset) |

---

## Metrics from Core Columns (Date, Species, Price/KG, Weight)

### Value and Aggregation

| Metric              | Formula                     | Description                                       |
|---------------------|-----------------------------|---------------------------------------------------|
| Total market value  | `SUM(Price/KG * Weight)`    | Total value of fish sold per day/species/period   |
| Average price       | `AVG(Price/KG)`             | Mean price per kg (currently used)                |
| Total tonnage       | `SUM(Weight)`               | Total weight sold (currently used)                |
| Median price        | `MEDIAN(Price/KG)`          | Less skewed than mean when outliers exist         |
| Percentile prices   | P10, P25, P75, P90          | Price distribution quartiles/deciles              |

### Spread and Volatility

| Metric                    | Description                                       |
|---------------------------|---------------------------------------------------|
| Price range               | Min and max Price/KG per day                      |
| Price standard deviation  | Volatility of prices within a period              |
| Coefficient of variation  | `std dev / mean` for price or weight              |

### Activity

| Metric      | Description                                    |
|-------------|------------------------------------------------|
| Lot count   | Number of sales/lots per day, species, or period |
| Avg lot size| `SUM(Weight) / COUNT(*)` per grouping          |

### Time-Based

| Metric                   | Description                                       |
|--------------------------|---------------------------------------------------|
| Week-over-week change    | Percent change in price or tonnage vs prior week  |
| Month-over-month change  | Percent change vs prior month                     |
| Seasonality              | Patterns by day-of-week or month                  |
| Rolling correlation      | Price vs tonnage correlation over a window        |

### Supply-Price Relationship

| Metric              | Description                                       |
|---------------------|---------------------------------------------------|
| Price-tonnage correlation | Correlation between daily price and daily tonnage |
| Supply elasticity   | How price responds to supply changes              |

---

## Metrics from Parsed Species String

The Species field embeds structured data, e.g.:

- `SOLE 4 - GUT Gutted - A`
- `4 SOLE 1 - GUT Gutted - A`
- `DAM SOLE 1 - GUT Gutted - A`
- `TH WING 1 - WNG Winged - A`

Parsable elements:

| Element     | Examples        | Possible metrics                              |
|-------------|-----------------|-----------------------------------------------|
| Grade/size  | 1, 4            | Price premium by grade; avg price per grade   |
| Processing  | GUT, WNG        | Price difference (gutted vs winged vs whole)  |
| Condition   | DAM, NELSON     | Price discount for damaged/non-standard lots  |
| Size prefix | 4, DAM, SL      | Size or condition modifiers                   |

---

## Metrics from Gear Column

| Metric               | Description                                       |
|----------------------|---------------------------------------------------|
| Tonnage by gear      | Total weight per gear type                        |
| Price by gear        | Average Price/KG per gear type                    |
| Gear mix over time   | Share of each gear in total tonnage over time     |
| Gear by species      | Which gears are used for which species            |
| Lot count by gear    | Number of sales per gear type                     |
| Gear premium         | Price difference between gear types (e.g. hook vs trawl) |

---

## Location Column

Location is always Brixham in this dataset, so it does not vary and is not useful as a dimension for comparison. Location-based metrics (tonnage by location, price by location, etc.) would only be relevant if data from multiple ports or markets were combined.

---

## Metrics from id Column

| Metric       | Description                                    |
|--------------|------------------------------------------------|
| Lot count    | `COUNT(id)` or `COUNT(*)` per grouping         |
| Unique lots  | Deduplication when combining data sources      |

---

## Cross-Dimensional Metrics

| Metric                  | Description                                           |
|-------------------------|-------------------------------------------------------|
| Gear premium by species | Price difference between gears for the same species   |
| Value by gear x species | Total value (`Price/KG * Weight`) by gear and species |
| High-value combinations | Top gear-species combinations by total value          |

---

## Suggested Priorities

High-value additions to implement first:

1. **Lot count** - Number of sales per day (simple, useful for activity)
2. **Total market value** - `Price/KG * Weight` summed
3. **Gear breakdown** - Filter or compare by gear type
4. **Price spread** - Min/max Price/KG per day
5. **Average lot size** - Weight per lot
6. **Species sub-metrics** - Parse grade/processing for price-by-grade analysis
