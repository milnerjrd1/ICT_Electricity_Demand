# Data Catalogue
Version: 2026-02 | Status: Template — populate as sources are acquired

Every data source used in the model must be documented here before ingestion.

---

## Template

| Field | Description |
|---|---|
| Source ID | Unique identifier used in gold tables (e.g. `iea_2024`) |
| Name | Full source name |
| URL | Access URL |
| License | Free / Paid / Restricted |
| Coverage | Geographies and segments covered |
| Update frequency | Annual / Quarterly / Irregular |
| Format | CSV / Excel / API / PDF |
| Confidence tier | 1 / 2 / 3 |
| Loader | `src/data/loader_<name>.py` |
| Gold table | Table name in DuckDB |
| Limitations | Known gaps, caveats |
| Last ingested | YYYY-MM-DD |

---

## Sources

### IEA — Grid Emission Factors
| Field | Value |
|---|---|
| Source ID | `iea_ef_2024` |
| Name | IEA CO2 Emissions from Fuel Combustion |
| URL | https://www.iea.org/data-and-statistics |
| License | Paid (IEA subscription) / Free summary data |
| Coverage | Global; annual by country |
| Update frequency | Annual |
| Format | Excel |
| Confidence tier | 1 |
| Loader | `src/data/loader_iea.py` |
| Gold table | `grid_ef` |
| Limitations | Lag of ~18 months; provisional data for latest year |
| Last ingested | — |

### IEA — Electricity Prices
| Field | Value |
|---|---|
| Source ID | `iea_prices_2024` |
| Name | IEA Energy Prices |
| URL | https://www.iea.org/data-and-statistics |
| License | Paid |
| Coverage | OECD countries; industry and residential |
| Update frequency | Annual |
| Format | Excel |
| Confidence tier | 1 |
| Loader | `src/data/loader_iea.py` |
| Gold table | `electricity_prices` |
| Limitations | Non-OECD coverage limited; use Ember/EIA as fallback |
| Last ingested | — |

### ITU — Network Infrastructure
| Field | Value |
|---|---|
| Source ID | `itu_2024` |
| Name | ITU World Telecommunication/ICT Indicators Database |
| URL | https://www.itu.int/en/ITU-D/Statistics |
| License | Free (registration required) |
| Coverage | Global; subscriber counts, base stations |
| Update frequency | Annual |
| Format | Excel |
| Confidence tier | 1 (Tier 1 geos) / 2 (Tier 2) / 3 (Tier 3) |
| Loader | `src/data/loader_itu.py` |
| Gold table | `networks` |
| Limitations | Lag of ~12 months; base station counts incomplete for some markets |
| Last ingested | — |

### UN Comtrade — Device Shipments
| Field | Value |
|---|---|
| Source ID | `comtrade_2024` |
| Name | UN Comtrade Database (HS codes 8471, 8517, 8443, 8528) |
| URL | https://comtradeplus.un.org/ |
| License | Free (API rate limits apply) |
| Coverage | Global; trade flows as shipment proxy |
| Update frequency | Annual / Quarterly |
| Format | CSV (bulk download) |
| Confidence tier | 2 (proxy — trade ≠ shipments exactly) |
| Loader | `src/data/loader_trade.py` |
| Gold table | `devices` |
| Limitations | Trade data ≠ domestic production; re-export distortion; use IDC as primary if licensed |
| Last ingested | — |

### DC Byte / Uptime Institute — DC Capacity
| Field | Value |
|---|---|
| Source ID | `dc_byte_2024` |
| Name | DC Byte Colocation and Hyperscale Capacity Database |
| URL | https://www.dc-byte.com/ |
| License | Paid |
| Coverage | Global; MW by DC type and geography |
| Update frequency | Quarterly |
| Format | Excel / API |
| Confidence tier | 1 (hyperscale) / 2 (colo) / 3 (on-prem) |
| Loader | `src/data/loader_dc_byte.py` |
| Gold table | `datacentres` |
| Limitations | On-premises capacity estimated; edge DCs sparse |
| Last ingested | — |

### Eurostat — ICT Usage Surveys
| Field | Value |
|---|---|
| Source ID | `eurostat_ict_2024` |
| Name | Eurostat ICT Usage in Households and by Individuals |
| URL | https://ec.europa.eu/eurostat/data/database |
| License | Free |
| Coverage | EU27 + EEA; household device ownership and usage |
| Update frequency | Annual |
| Format | CSV (bulk download) |
| Confidence tier | 1 |
| Loader | `src/data/loader_eurostat.py` |
| Gold table | `devices` |
| Limitations | EU only; non-EU countries require proxy scaling |
| Last ingested | — |

### Borderstep / BNetzA — Germany Calibration
| Field | Value |
|---|---|
| Source ID | `borderstep_2024` |
| Name | Borderstep Institut — Rechenzentren und KI in Deutschland |
| URL | https://www.borderstep.de/ |
| License | Free (published reports) |
| Coverage | Germany; DC electricity consumption by type |
| Update frequency | Annual |
| Format | PDF (manual extraction) |
| Confidence tier | 1 |
| Loader | Manual extraction → `data/raw/germany/` |
| Gold table | `datacentres` |
| Limitations | Germany only; primary calibration anchor |
| Last ingested | — |
