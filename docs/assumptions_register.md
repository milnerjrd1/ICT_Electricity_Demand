# Assumptions Register
Version: 2026-02 | Status: Template — populate as model modules are built

Every parameter used in the model must be documented here.
Full YAML definitions live in `configs/assumptions/`.

---

## Template

| Parameter | Module | Baseline | Range | Distribution | Rationale | Confidence | Owner | Last reviewed |
|---|---|---|---|---|---|---|---|---|
| `param_name` | devices/networks/dc | value | [low, high] | triangular/log-normal/uniform | Source + reasoning | 1/2/3 | — | YYYY-MM-DD |

---

## Data Centre Parameters

| Parameter | Baseline | Range | Distribution | Confidence | Source |
|---|---|---|---|---|---|
| PUE — hyperscale | 1.15 | [1.05, 1.30] | triangular | 1 | Uptime Institute 2024; Google sustainability report |
| PUE — sovereign | 1.30 | [1.15, 1.50] | triangular | 2 | EU CoC for DCs; proxy from colo |
| PUE — colocation | 1.45 | [1.25, 1.70] | triangular | 2 | Uptime Institute survey |
| PUE — on-premises | 1.70 | [1.40, 2.20] | triangular | 2 | Borderstep Germany; Gartner |
| PUE — edge | 1.55 | [1.30, 1.90] | triangular | 3 | Proxy from colo; limited data |
| Utilisation — hyperscale | 0.65 | [0.50, 0.80] | triangular | 1 | Hyperscaler disclosures |
| Utilisation — sovereign | 0.45 | [0.25, 0.65] | triangular | 2 | EU operator proxy |
| Utilisation — colocation | 0.55 | [0.30, 0.75] | triangular | 2 | Uptime Institute |
| Utilisation — on-premises | 0.25 | [0.10, 0.45] | triangular | 2 | Borderstep; Gartner |
| AI compute growth rate | 0.20/yr | [0.08, 0.70] | log-normal | 3 | Epoch AI; Semi Analysis |
| kWh per EFLOP | 0.001 | [0.0005, 0.002] | triangular | 3 | Published training run disclosures |

## Device Parameters

| Parameter | Baseline | Range | Distribution | Confidence | Source |
|---|---|---|---|---|---|
| Laptop lifespan | 5.0 yr | [3.0, 7.0] | triangular | 2 | Eurostat; IDC |
| Laptop active power | 15 W | [8, 25] | triangular | 2 | ENERGY STAR |
| Desktop lifespan | 6.0 yr | [4.0, 9.0] | triangular | 2 | Eurostat; IDC |
| Smartphone lifespan | 3.0 yr | [2.0, 4.5] | triangular | 2 | GSMA |

## Network Parameters

| Parameter | Baseline | Range | Distribution | Confidence | Source |
|---|---|---|---|---|---|
| 5G base station power | 1500 W | [900, 2500] | triangular | 2 | Ericsson/Nokia specs |
| 4G base station power | 800 W | [500, 1200] | triangular | 1 | Established specs |
| Fixed broadband CPE power | 8 W | [4, 15] | triangular | 2 | ENERGY STAR; Ofcom |

---

## Change Log

| Date | Parameter | Old value | New value | Reason | Author |
|---|---|---|---|---|---|
| 2026-02-20 | All | — | Initial values | Phase 0 scaffold | — |
