# Proxy Rulebook
Version: 2026-02 | Status: Template — populate as data gaps are identified

Every proxy rule must have: rationale, scaling logic, confidence impact, and owner.

---

## Template

| Rule ID | Gap | Proxy Method | Scaling Logic | Confidence Impact | Rationale | Owner |
|---|---|---|---|---|---|---|
| `PRX-001` | Description of gap | What we use instead | How we scale | Tier drop (e.g. 1→2) | Why this is reasonable | — |

---

## Active Proxy Rules

### PRX-001 — Tier 2/3 DC capacity from Tier 1 anchors
| Field | Value |
|---|---|
| Gap | DC capacity data unavailable or unreliable for Tier 2/3 geographies |
| Proxy method | Scale from nearest Tier 1 anchor using GDP-PPP and internet penetration |
| Scaling logic | `capacity_proxy = capacity_anchor × (gdp_ppp_target / gdp_ppp_anchor) × (inet_pen_target / inet_pen_anchor)` |
| Confidence impact | Tier 1 → Tier 2 (adds ±15% uncertainty) |
| Rationale | DC capacity correlates with economic activity and digital adoption; validated against Germany→Netherlands |
| Owner | — |

### PRX-002 — Non-EU device usage from Eurostat
| Field | Value |
|---|---|
| Gap | Device usage hours and power state profiles unavailable outside EU |
| Proxy method | Apply EU average profiles with income-group adjustment |
| Scaling logic | `usage_proxy = usage_eu_avg × income_adjustment_factor(geo)` |
| Confidence impact | Tier 1 → Tier 2 for high-income non-EU; Tier 2 → Tier 3 for middle/low-income |
| Rationale | Usage patterns correlate with income; OECD countries cluster near EU averages |
| Owner | — |

### PRX-003 — Tier 3 regional aggregate electricity demand
| Field | Value |
|---|---|
| Gap | No reliable country-level data for Tier 3 geographies |
| Proxy method | Regional aggregate scaled from population and GDP-PPP per capita |
| Scaling logic | `kwh_region = Σ_countries [population × gdp_ppp_per_cap × ict_intensity_factor]` |
| Confidence impact | Always Tier 3; uncertainty band ≥ ±35% |
| Rationale | ICT electricity intensity correlates with income level; validated at regional level against IEA totals |
| Owner | — |

### PRX-004 — On-premises DC capacity
| Field | Value |
|---|---|
| Gap | On-premises DC capacity not tracked by DC Byte or Uptime Institute |
| Proxy method | Scale from server shipment data (IDC/Gartner) using average rack density |
| Scaling logic | `on_prem_mw = server_shipments × avg_power_per_server_kw / 1000 × avg_lifespan_years` |
| Confidence impact | Tier 2 → Tier 3 (high uncertainty in server-to-MW conversion) |
| Rationale | Server shipments are the best available proxy; Borderstep Germany used for calibration |
| Owner | — |

---

## Pending Proxy Rules (to be defined)

- [ ] PRX-005 — AI workload share of DC electricity (no direct measurement)
- [ ] PRX-006 — Edge DC capacity (very sparse data globally)
- [ ] PRX-007 — Network core electricity (operator disclosures only)
- [ ] PRX-008 — Sovereign cloud capacity outside EU
