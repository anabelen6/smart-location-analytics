# Methodological decision log — TFM Gourmet Geomarketing

> Living document. Every relevant project decision is recorded here with its
> rationale, and kept consistent with `main_v2.ipynb`. It is the basis for
> section 3.3 "Chosen approach" of the TFM report (analyst part and, in
> summarised form, sponsor part). IDs are stable: merged or removed entries
> are listed at the end with a pointer to where their content now lives.

---

## Phase 0 — Initial phase: EDA and city selection

### EDA on the full dataset

**D10. `district` is discarded as a usable variable.**
86.8% nulls in the full dataset, so it is useless for geographic
segmentation (confirms the dataset PDF's warning about inconsistent
geographic granularity). `neighbourhood`, much more complete, is used
wherever neighbourhood level is needed.

**D11. Visual confirmation of the COVID effect (see D8).**
The monthly series of reviews (all cities) shows an abrupt drop in March
2020 and only a partial recovery until the end of the dataset (March 2021).
This supports excluding 2020 from the recent demand window (D8).

**D12. Duplicates are negligible and not treated.**
`reviews.csv` has 160 duplicated `review_id` out of 5.37M rows (<0.01%);
`listings.csv` has no duplicated `listing_id`. The pipeline does not drop
them: the effect on per-listing review counts is negligible.

**D13. Listings without reviews get demand 0, not a null.**
69.2% of listings have at least one review. The rest (new or inactive
listings) get `reviews_total = reviews_recent = 0` after the Phase 1 merge:
a valid value meaning "no observed demand", not a missing value to impute.

### City selection

**D2. City chosen through a data-quality index, not arbitrarily.**
The dataset covers 10 cities with very uneven data quality (completeness
of `review_scores_location` between 45.8% and 75.3%).
Index (0-100) = 40% completeness of `review_scores_location` (key variable
of the score) + 30% listings volume (clustering robustness) + 30% reviews
volume (reliability of demand). Volumes are MinMax-scaled across the 10
cities; completeness enters as its raw share (0-1). Weights set by the
author as a reasoned starting point, not tuned.
Result — Top 5: **Paris (90), Rome (68), New York (64), Sydney (50),
Mexico City (45)**. Left out: Rio de Janeiro, Cape Town, Bangkok, Istanbul
and Hong Kong — mainly for low listings/reviews volume (Cape Town's
completeness, 70.2%, is higher than Sydney's); only Istanbul (45.8%) and
Hong Kong (53.3%) are also clearly weak on completeness.
Note for the report: because completeness is not MinMax-scaled, it only
spans ~12 points of the index while volume spans up to 60, so the ranking
is driven mostly by volume (on completeness alone Rome is first). Sensitivity
check: MinMax-scaling completeness too leaves the same Top 5 with Paris
first (only Sydney and Mexico City swap places), so the choice is robust.
The client (simulated) confirmed **Paris**, the top-ranked city, as the
working city; this also fixed the income source to INSEE (D24).

**D3. No city-name normalisation needed.**
The dataset PDF warns about alias inconsistencies ("Mexico City" spelled
three ways, New York boroughs as separate cities). Checking the real data
found exactly 10 clean `city` values, so no alias mapping is applied and
`filter_city()` is a plain case-insensitive match. Report note: documented
data issues must be checked against the actual data before adding defensive
logic.

---

## Phase 1 — ETL and high-standing score

**D1. Price is scaled within the city, after the city filter.**
`price` is in each country's local currency; scaling it across cities would
mix currencies and bias the score towards currencies with high nominal
values. So the city is filtered first (`filter_city`) and every scaling
step (percentile trim D7, MinMax in the score D5) runs on that city only.
The Phase 0 EDA shows price per city on a log axis for visual comparison
only; no price transformation or scaling happens before the filter.

**D5. High-standing score formula.**
`highstanding_score = 0.70 × price_scaled + 0.30 × review_scores_location_scaled`
(`PRICE_WEIGHT`, `LOCATION_WEIGHT`), both MinMax-scaled 0-1 within the
city. Weighting defined by the client: expensive flat with a good
location, with more weight on price as the main proxy for the guest's
purchasing power.

**D6. Medium/long-term stays excluded.**
Listings with `minimum_nights >= 30` are dropped: they do not match the
short-stay tourist profile relevant to a neighbourhood gourmet shop.

**D7. Price outliers trimmed at the 1st-99th percentile (within the city).**
Prevents loading errors and extreme cases from distorting the MinMax
scaling, which is very sensitive to extreme values. In Paris the range kept
is €25-€500.

**D8. Demand variable: two windows from `reviews.csv`.**
- `reviews_total`: full history (2008-2021), accumulated traction.
- `reviews_recent`: the last `RECENT_YEARS_WINDOW = 3` calendar years
  **excluding 2020** (`COVID_YEAR`), whose drop does not reflect a
  structural change in demand.
The recent window is the one used downstream (zone metrics and the
opportunity index). Limitation for the report: since the data ends in March 2021, the
window is in practice 2019 plus January-March 2021 (≈95% of its reviews
are from 2019).

**D9. Critical nulls are dropped, not imputed.**
Listings without `price`, `review_scores_location`, `latitude` or
`longitude` are removed: they are the core of the score and the clustering,
and imputing them would bias the main result directly.

**D16. Ties at the top of the score — root cause and tie-break.**
In Paris the maximum price after the p1-p99 trim is exactly €500, shared by
41 listings, and `review_scores_location = 10` is very frequent. Result:
**35 listings tie at `highstanding_score = 1.0`**. This is not a bug but a
real low-granularity limitation at the top of the distribution (round
"psychological" prices + the 10-point cap of the location score). The
shortlist is therefore sorted by `highstanding_score`, then
`reviews_recent`, then `review_scores_rating`, so the order within ties has
a business meaning. Mention it in the report as a real data limitation
found during development.

**D28. Threshold-based shortlist (`SCORE_THRESHOLD = 0.90`) instead of a
fixed Top 20.**
The original fixed Top 20 cut through the middle of the 35-listing tie
(D16), leaving out listings indistinguishable from those selected and
making neighbourhood counts depend on an arbitrary cut. A score threshold
avoids this. Thresholds tested: 0.85 → 356, 0.88 → 242, **0.90 → 195
(0.43% of clean Paris listings)**, 0.92 → 171, 0.95 → 92; 0.90 balances
sample size and strictness.
With ~195 listings, per-listing charts are replaced by neighbourhood
aggregates, which answer the business question better:
- `plot_shortlist_by_neighbourhood()`: Temple (21), Luxembourg (19),
  Palais-Bourbon (19), Passy (17) lead.
- `plot_demand_by_neighbourhood()`: Luxembourg leads in recent demand
  despite having fewer listings than Temple — a signal the raw count hides.

---

## Phase 2 — Geospatial clustering

**D17. HDBSCAN chosen over DBSCAN, based on a parameter sweep.**
Both run on the 45,787 clean Paris listings (`df_scored`):
- DBSCAN sweep (`eps` 30/100/200 m × `min_samples` 10/15/20): small `eps`
  labels almost everything as noise; large `eps` merges almost everything
  into one cluster. Best compromise `eps=100m, min_samples=15`: 67 clusters,
  7.3% noise, but **one macro-cluster holds 68% of the clustered listings**
  (28,931) over most of the historic centre — the "chaining effect" of a
  fixed radius in a dense, homogeneous city.
- HDBSCAN sweep (`min_cluster_size` 25/50 × `min_samples` 10/15/20): the
  same macro-cluster appears with high `min_cluster_size`. (25, 10) and
  (50, 15) have similar noise (45.5% vs 45.7%); **(25, 10) is chosen for
  its finer granularity (200 zones vs 80)**. Its largest cluster holds only
  10% of the clustered listings (2,551).
- Cost: more noise (45.5% vs 7.3%). Accepted, because HDBSCAN labels
  intermediate-density areas as noise instead of forcing them into a zone
  that does not represent them.
The DBSCAN sweep is reported as the evidence for the choice, not discarded.
`cluster_hdbscan` is the zone ID used downstream.

**D18. Haversine distance on radians, not Euclidean on degrees.**
One degree of longitude is not the same distance as one degree of latitude
(it shrinks with latitude); Euclidean distance on lat/lon would distort
cluster shapes and sizes. All clustering uses `metric="haversine"` on
coordinates in radians.

**D19. Clustering on all clean listings of the city, not only the shortlist.**
The 195 shortlist listings are too few for density clustering. Phase 2
clusters all clean Paris listings to find market ZONES, and computes
per-zone metrics (`cluster_metrics`: median price, mean location review,
mean high-standing score, aggregated demand, centroid). The shortlist
(listing level) and the zones (area level) are complementary analyses.

---

## Phase 3 — Enrichment with open data (OSM + INSEE)

**D20. OSM data via Overpass, one query per city and tag block, cached.**
`fetch_osm_pois()` sends one query per tag block (competitors,
accessibility) over the city bounding box (never one query per zone): the
smallest lat/lon rectangle containing all clean listings, widened by 0.01°
per side (~1.1 km lat, ~0.7 km lon) so POIs just outside the outermost
listings are not lost; ~12 × 19 km for Paris (the same box bounds the INSEE
Filosofi cells, D24). It caches the response in `cache_osm/`, retries with
backoff and sends an identifiable User-Agent. Paris: 11,785 accessibility
elements and 2,069 gourmet retail competitors (the cached competitor
response, 13,583 elements, predates D37 and also contains restaurants;
`osm_response_to_df()` drops elements whose tags are not in the tag dict).
Competitors (`COMPETITOR_TAGS`): delicatessen, cheese, chocolate,
confectionery, wine and butcher shops (gourmet retail only, see D37).
Accessibility
(`ACCESSIBILITY_TAGS`): train/metro stations, bus stops, parking.

**D21. Competition catchment: 400 m around the zone centroid.**
Competition is measured in a 400 m walking catchment (a few minutes' walk)
around each zone centroid (`COMPETITION_RADIUS_M`). Cannibalization index =
gourmet competitors within 400 m / clean listings within 400 m
(`n_competitors / n_listings_catchment`); a competitor near several zones
counts for all of them. See D40 for why this replaced the original
nearest-centroid assignment. Accessibility uses no radius: it is the
distance from the zone centroid to the nearest transit point
(`dist_to_transit_m`). Adjustable to the "influence" radius the client
considers relevant.

**D40. Competitors counted per catchment, not assigned to the nearest zone.**
The original D21 assigned each competitor to its single nearest zone
centroid and divided by the zone's own `n_listings`. Both parts were
artifacts of the HDBSCAN geometry, not of the market: (a) in the dense
centre, zones are small and close together, so a shop's competition was
credited to only one neighbour; zone 168 (Marais) had 10 gourmet shops
within 400 m but was credited with 1, zone 181 had 25 but was credited
with 0 (old vs new counts correlate only 0.39); (b) the denominator
depended on how far the cluster happened to extend, not on the market
around the shop. Now both numerator and denominator are counted in the
same 400 m catchment, keeping D21's concept (competition relative to the
local tourist market) with a consistent spatial support. Effect on the
index (same weights): Spearman 0.93 with the previous ranking, 12 of the
Top 15 kept (in: 179, 110, 12; out: 2, 26, 109), #1 and #2 unchanged
(zone 168 80.8, zone 15 79.6). Zone 168 stays #1 not because it has little
competition in absolute terms (10 shops) but because its catchment is a
large tourist market (730 listings). Sensitivity note for the report: with
a raw competitor count (no denominator), zone 15 becomes #1 and zone 168
#3, so the #1 depends on whether competition is read in absolute or
relative terms.

**D22. Zone centroids at full precision; cannibalization ties handled by
market size.**
An earlier version of `cluster_metrics()` rounded centroids to 2 decimals
(~1 km), so the 200 zones collapsed onto 80 distinct centroids: every
competitor went to only one of the zones sharing a centroid (120 zones were
left with 0 competitors), and those zones also got identical accessibility,
income and geocoded address. Fixed: centroids keep full precision (only
the displayed metrics are rounded). With the fix, no zone loses its
competitors to a neighbour sharing its centroid; with retail-only
competitors (D37), 1,261 are assigned and 11 zones have none (superseded
by the catchment count of D40, where every zone has at least 1).
Report note: a good example of how a presentation detail (rounding)
silently distorted a spatial join; all Phase 3-4 results were re-run.
The cannibalization chart keeps two safeguards for ties: (a) tie-break by
descending `n_listings` (with equal competition, the larger tourist market
wins); (b) a lollipop chart with point size = `n_listings`.

**D24. Income from INSEE Filosofi (not INE), mean per cell as proxy.**
The initial plan named the INE, but that is Spain's statistics agency and
does not cover any Top 5 city. With Paris confirmed (D2), income comes from
**INSEE Filosofi**, "Revenus, pauvreté et niveau de vie - Données carroyées
2019 et 2021" (data.gouv.fr, parquet, EPSG:3035), read with `duckdb` and
reprojected with `pyproj`. 4,091 cells fall in the Paris bounding box.
Columns used: `idcar_200m` (cell id encoding the SW corner in EPSG:3035
metres), `ind` (population), `ind_snv` (SUM of winsorised standards of
living), `i_est_200` (imputation flag: cells with <11 tax households are
aggregated with neighbours; ~78-79% of French cells, but only ~0.6% on
average in the Paris zones, where population density is high).
Limitation for the report: Filosofi at 200 m does NOT publish median
income; only a **mean** per cell can be derived (`ind_snv / ind`), used as
`income_proxy`, a proxy for purchasing power, not a real median.
Vintage: the notebook uses the **2019** file (`FILOSOFI_URL`, resource
b480cead…, `carreaux-200m-met-3035.parquet`), which matches the recent
demand window (mostly 2019, D8); the 2021 file is also available. The
filtered cells are cached in `cache_insee/` so data.gouv.fr is queried once.

**D26. Filosofi cell → zone radius: 300 m (not 400 m as in D21).**
Cells are 200 m per side; 300 m from the centroid captures the containing
cell plus immediate neighbours without diluting the local signal. Cells in
the radius are averaged (simple mean), and the number of cells used
(`n_filosofi_cells`) and the share imputed (`income_pct_imputed`) are
reported as a confidence indicator per zone (median 7 cells per zone; no
zone above the 70% imputation alert threshold in Paris).

**D37. Competitors are gourmet retail only; restaurants are excluded.**
The client's business is a take-away gourmet shop (retail), not dining, so
its direct competition is other gourmet shops, not restaurants.
`amenity=restaurant` was removed from `COMPETITOR_TAGS`. It mattered a
lot: restaurants were 85% of the competitor POIs (11,514 of 13,583) and
dominated the cannibalization index, and hence the opportunity ranking.
With retail only, zone 168 (Marais, 3e) becomes #1.

---

## Phase 4 — Opportunity index, geocoding and dashboard

**D34. Opportunity index: 5 MinMax-scaled dimensions with explicit,
untuned weights.**
`opportunity_index` (0-100) combines, per zone:

| Dimension | Variable | Direction | Weight |
|---|---|---|---|
| High-standing score | `highstanding_score_mean` | higher is better | 0.30 |
| Cannibalization | `cannibalization_index` | inverted | 0.25 |
| Accessibility | `dist_to_transit_m` | inverted | 0.15 |
| Income | `income_proxy` | higher is better | 0.15 |
| Demand | `demand_per_listing` | higher is better | 0.15 |

- All components are MinMax-scaled 0-1 before weighting, so none dominates
  by its natural scale (€/year, index, metres, reviews). Inverted
  components use `1 - scaled` so higher always means better. Missing values
  are filled with the median and the row is flagged (`is_complete`).
- Score and cannibalization keep the highest weights because they are the
  two hard requirements of the brief (upscale positioning, avoid saturated
  zones); the other three are supporting signals weighted equally.
- The weights are a reasoned starting point, NOT tuned: there is no
  ground-truth "correct opportunity" to fit them to. The dashboard (D39)
  lets the client change them and see the ranking react.
- Demand was added as the 5th dimension because it is the only signal of
  observed behaviour (the other four are structural). A first version used
  the zone's total recent reviews, which mechanically rewarded the largest
  zones (the largest cluster jumped to #1 on volume alone, despite lower
  demand per listing). It is therefore measured **per listing**
  (`reviews_recent_total / n_listings`): intensity of interest per unit of
  supply, not raw volume. Check with the total instead: zone 53 (1,971
  listings) jumps from #28 to #2, on volume alone.
- Effect of adding demand (4 vs 5 dimensions, same data): the #1 is stable
  (**zone 168**, 86.3 → 79.9/100) and 2 of the Top 15 zones change; zone 15
  rises to #2 (78.3) thanks to its demand per listing. The ranking's top is
  robust to this change. (Values before D40; after it: 80.8 and 79.6.)

**D32. Reverse geocoding with Nominatim, for presentation only.**
`geocode_top_zones()` turns the centroids of the Top 15 zones (the same
15 shown in the opportunity ranking chart) into real
addresses for the client, through `reverse_geocode()` (Nominatim, max. 1
req/s via `RATE_LIMIT_SECONDS = 1.1`, identifiable User-Agent; results
cached in `cache_osm/nominatim_reverse.json`; `geocode_fn` is injectable
for testing). Nominatim is **not** an input of
the opportunity index: the index uses 5 dimensions from 3 sources (Airbnb:
score and demand; OSM: cannibalization and accessibility; INSEE: income).

**D38. The predictive model is removed; the project's model is the
clustering plus the opportunity index.**
The Phase 4 regression (Linear Regression vs Random Forest) predicted
`expected_revenue_proxy = price_median × 0.65 × 0.08 × n_listings`, a
simulated target with uncalibrated constants (there is no revenue data for
a shop that does not exist yet). Because `n_listings` multiplies the
target and `reviews_recent_total` correlates 0.98 with it, the models only
recovered the formula (R² ≈ 0.99, 93% of the importance on those two
variables); without any size variable the R² dropped below 0, and
dividing the target by `n_listings` just turned it into the median price,
which the high-standing score already contains (correlation 0.93). With no
observed target (sales, commercial rents, footfall) a supervised model
cannot be built honestly for this brief, so it was removed rather than kept
as a result the client might read as a revenue forecast. The project's
model is unsupervised: HDBSCAN zones (D17) ranked by the opportunity index
(D34). Report: mention it briefly as a discarded approach.

**D39. Interactive HTML dashboard as the client deliverable.**
The last notebook section exports the zone results
(`output/paris_dashboard_data.json`) and embeds them in
`dashboard/template.html`, producing `dashboard/paris_dashboard.html`: a
single self-contained file (no server, no internet, no map tiles; the
city is drawn from the listings themselves and zones as the convex hull
of their listings). The client adjusts the 5 weights of the index and the
map and Top 15 update live, with each zone's position change against the
default weights; a zone card shows its raw values, how it compares with
the rest of the zones and each criterion's contribution. The browser uses
the same formula as `build_opportunity_index()`; with `DEFAULT_WEIGHTS`
it reproduces the notebook index exactly. Addresses exist only for the 15
default top zones (Nominatim, D32); other zones show their Airbnb
neighbourhood. HTML was chosen over Tableau: the whole deliverable is
generated from the notebook and needs no licence or manual build.

---

## Project conventions

**D35. Everything in English; decision log renamed to `DECISIONS.md`.**
All project material is written in **English**: notebook markdown cells,
code, comments, docstrings, printed output and this log (translated from
Spanish and renamed from `DECISIONES.md`, keeping the D-numbering).
Existing Spanish text in the notebook is legacy and is translated when the
corresponding cell is edited. Exception for figures: see D36.

**D36. Figures in Spanish (exception to D35).**
The TFM report is written in Spanish, so every figure that goes into it
(plot titles, axis labels, legends, colorbars and annotations) is in
**Spanish**. Dataset variable / column names shown in figures (e.g. feature
names in the importance plot) are kept as-is, since they are the dataset's
identifiers and are referenced by those names in the report. Established
technical terms used in the report (listings, reviews, shortlist, score
high-standing) are kept. Everything else (code, notebook markdown, printed
output, this log) stays in English as per D35.

**D15. Palette: navy blue / teal; red reserved for real alerts.**
Centralised in `viz_config.py` (`PALETTE`, `SEQUENTIAL_CMAP`); all figures
consume it. Orange-red (`PALETTE["alert"]`) is used ONLY for real warnings
(nulls >30%, high cannibalization, heavily imputed income) so it keeps its
semantic value.

**D14. Shared config module named `viz_config.py`.**
`config.py` collided with the PyPI `config` package present in some
Anaconda installations (`ImportError`), so the module is `viz_config.py`.

---

## Known limitations and constraints (for the recommendations section)

- The dataset ends in March 2021: it does not reflect post-pandemic tourism
  patterns, and the recent demand window is mostly 2019 (D8).
- No reliable open data on street-level pedestrian flow; proxies are used
  instead (listing density, recent reviews, access to transport).
- Opening costs are out of scope (no reliable open data on commercial rents
  by zone) — joint decision with the client.
- No observed outcome (sales, footfall, commercial rents) is available, so
  zones are ranked, not forecast: the index prioritises zones and is not a
  sales prediction (D38).
- Income is a mean per 200 m cell, not a median (D24); the Filosofi
  vintage (2019) predates the end of the Airbnb data by ~1 year.

---

## Merged or removed entries

| ID | Status | Where its content is now |
|---|---|---|
| D3b | Removed | Superseded by D35 |
| D4 | Merged | D1 (within-city scaling) |
| D20 (original) | Rewritten | "No internet in the dev environment" no longer applies: Overpass data was fetched and cached; D20 now documents the access design |
| D23 | Merged | D24 (INE → INSEE); Paris confirmation moved to D2 |
| D25 | Removed | INSEE integration now runs end to end on real data; mock tests no longer exist |
| D27 | Merged | D28 (motivation for the threshold) |
| D28b | Removed | Report-editing note, not a methodological decision |
| D29 | Merged | D34 (original 4-dimension index and weights) |
| D33 | Removed | Report-editing note, not a methodological decision |
| D33b | Merged | D32 (Nominatim is not an index source) |
| D34b | Merged | D34 (effect of adding demand, recomputed after the D22 fix) |
| D30 | Removed | Simulated revenue target; model removed (D38) |
| D31 | Removed | Leakage finding that motivated removing the model (D38) |
