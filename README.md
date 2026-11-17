# Smart Location Analytics

**Where should a new neighbourhood gourmet shop open? A data-driven answer for Paris.**

Master's thesis (Data Science & Big Data, University of Seville, 2026). An end-to-end geomarketing
pipeline that turns raw short-term-rental data into a ranked list of candidate zones, plus an
interactive dashboard so the client can explore the result without touching code.

**[Open the interactive dashboard](https://anabelen6.github.io/smart-location-analytics/dashboard/paris_dashboard.html)**

![Dashboard](docs/dashboard.png)

## The problem

A client wants to open a gourmet shop aimed at a high-standing, tourist-heavy public. Instead of
choosing a street by intuition, the project ranks zones using five measurable criteria.

## What it does

| Phase | What happens |
|---|---|
| **0. EDA and city choice** | Explores 280k listings and 5.4M reviews across 10 cities. A 0-100 data-quality index (completeness, listings and reviews volume) gives the client a Top 5 of well-supported cities. Paris ranks first. |
| **1. ETL and high-standing score** | Cleans Paris (64,690 → 45,787 listings). Score = 70% scaled price + 30% scaled location rating. Demand comes from recent reviews, excluding 2020 (COVID). |
| **2. Geospatial clustering** | Compares **DBSCAN** and **HDBSCAN** with haversine distance. HDBSCAN is chosen: 200 zones, handles a dense centre and sparse outskirts. |
| **3. Open-data enrichment** | Competition and public-transport access from OpenStreetMap; local income from INSEE Filosofi (200 m grid). |
| **4. Opportunity index and dashboard** | Weighted 0-100 index per zone, reverse-geocoded top 15, and a self-contained HTML dashboard where the client changes the weights live. |

## Opportunity index

| Dimension | Direction | Default weight |
|---|---|---|
| High-standing score | higher is better | 0.30 |
| Cannibalization (gourmet competitors per listing, 400 m) | lower is better | 0.25 |
| Accessibility (distance to nearest transit) | lower is better | 0.15 |
| Income proxy (INSEE) | higher is better | 0.15 |
| Demand per listing | higher is better | 0.15 |

The weights are a reasoned starting point, not fitted: there is no ground truth for "the right
location". The index **ranks** zones; it is not a sales forecast.

## Key results

- DBSCAN suffers from the *chaining effect*: one macro-cluster holds ~68% of clustered listings.
  HDBSCAN gives 200 finer zones (at the cost of 45.5% noise points).
- Best zone: a cluster around Rue du Parc Royal (3e arrondissement), index **80.8**.
- **Robust to the weights:** in 5,000 random weight draws, zone 15 (Square Alboni, 16e) appears
  in the top 10 in 93% of them.
- **Robust to the competition radius:** 13 to 15 of the top 15 zones stay the same with 300, 400 or 500 m.

## Repository structure

```
├── main_v2.ipynb          # full analysis, phase by phase
├── viz_config.py          # chart style and palette used by the notebook
├── requirements.txt
├── data/                  # raw CSVs go here (see data/README.md)
├── output/                # figures and result tables
├── dashboard/
│   ├── template.html
│   └── paris_dashboard.html   # open it in any browser, no server needed
└── docs/                  # screenshots
```

## How to run

```bash
git clone https://github.com/anabelen6/smart-location-analytics.git
cd smart-location-analytics
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# put listings.csv and reviews.csv in data/
jupyter notebook main_v2.ipynb
```

The first run downloads OSM and INSEE data (cached afterwards). Reverse geocoding uses the public
Nominatim service at 1 request per second, so it takes a minute or two.

## Limitations

- INSEE Filosofi does not publish median income at 200 m, so income is a **mean** used as a proxy
  for purchasing power. About 78% of French cells are imputed for confidentiality.
- Demand is inferred from short-term-rental reviews, which describe tourists rather than residents.
- Weights are not statistically tuned; the dashboard
