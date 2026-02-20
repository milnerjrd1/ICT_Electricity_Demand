# Limitations Register & "What Would Change Our View"
Version: 2026-02 | Status: Template — populate as model is built

---

## Known Limitations

| ID | Limitation | Affected outputs | Mitigation | What would resolve it |
|---|---|---|---|---|
| LIM-001 | AI/DC demand is highly uncertain — no direct measurement of AI electricity consumption | All DC outputs, especially ai_high/ai_stress scenarios | Wide P10/P90 bands; scenario envelopes; explicit Tier 3 confidence | Hyperscaler energy disclosures at workload level; Epoch AI compute tracking |
| LIM-002 | On-premises DC capacity estimated via proxy (server shipments) | on_premises segment | Tier 3 confidence; wide uncertainty band | Direct survey data (e.g. Gartner DC census) |
| LIM-003 | Sovereign cloud capacity sparse outside EU | sovereign segment, non-EU geos | Proxy from GDP/internet penetration; Tier 2/3 confidence | National DC registries; government procurement data |
| LIM-004 | Device usage profiles from Eurostat (EU only) | devices segment, non-EU geos | Income-group proxy scaling; Tier 2/3 confidence | National ICT usage surveys for US, JP, CN, IN |
| LIM-005 | Network core electricity not directly measurable | core_network product | Proxy from operator disclosures; Tier 3 confidence | Operator energy reporting (e.g. GSMA climate action) |
| LIM-006 | Embodied energy excluded (manufacturing, end-of-life) | All segments | Explicitly out of scope; documented in scope boundaries | Separate lifecycle assessment study |
| LIM-007 | Cryptocurrency mining excluded | — | Explicitly out of scope | Include if client requests |
| LIM-008 | Grid emission factors lag by ~18 months | emissions overlay | Use latest available; note lag in outputs | Real-time grid EF APIs (Electricity Maps) |

---

## "What Would Change Our View"

These are the real-world signals that would cause us to shift between scenarios or revise estimates materially.

### AI/DC Demand
- **Upward revision trigger:** Hyperscaler capex announcements exceed $200bn/yr globally; GPU shipments grow >50% YoY; new frontier model training runs disclosed at >10 TWh
- **Downward revision trigger:** AI efficiency breakthrough (e.g. sparse models, neuromorphic chips) reduces kWh/EFLOP by >50%; hyperscaler utilisation drops below 50%
- **Scenario shift (base → high):** Two or more hyperscalers announce >5 GW new DC capacity in a single quarter
- **Scenario shift (base → low):** AI regulation limits compute growth; major hyperscaler pauses DC expansion

### Sovereignty / Repatriation
- **Upward revision trigger:** EU AI Act enforcement triggers workload repatriation; major data breach drives national cloud mandates
- **Downward revision trigger:** Sovereignty concerns resolved via contractual/technical means; hyperscalers win government cloud contracts

### Grid Constraints
- **Trigger:** Grid connection queues exceed 5 years in IE, NL, GB, SG; power purchase agreements unavailable; DC moratoriums extended

### Efficiency
- **Upward revision trigger:** PUE improvements accelerate beyond 2%/yr industry-wide; liquid cooling adoption >50% of new builds by 2027
