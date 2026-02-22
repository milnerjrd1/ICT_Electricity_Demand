import { useState } from 'react';
import { Card } from '../components/ui/Card';
import { PageHeader } from '../components/ui/PageHeader';

type Family = 'all' | 'ai_dc' | 'sovereignty' | 'grid' | 'efficiency';

interface Param {
  key: string; label: string; description: string;
  baseline: string; value: string; direction: 'up' | 'down' | 'neutral';
}
interface PlacementShare {
  hyperscale: number; sovereign: number; colocation: number;
  on_premises: number; edge: number;
}
interface Source { ref: string; detail: string; }
interface ScenarioDef {
  id: string; family: Family; label: string; color: string;
  tagline: string; narrative: string; interpretation: string;
  keyDrivers: string[]; watchFor: string[];
  params: Param[]; placement: PlacementShare;
  placementDelta: Partial<PlacementShare>; specialNotes?: string[];
  sources: Source[];
}

const SCENARIOS: ScenarioDef[] = [
  {
    id: 'ai_base', family: 'ai_dc', label: 'AI Base', color: '#3B82F6',
    tagline: 'Central trajectory — calibrated to historical hyperscale growth rates',
    narrative: 'The reference scenario against which all others are compared. AI compute demand grows at 20%/yr, consistent with observed hyperscale capacity additions 2020–2024. PUE improves at 2%/yr. Device lifespans and network efficiency are unchanged from the 2024 baseline. Hyperscale share grows slowly as colocation and on-premises decline.',
    interpretation: 'Use AI Base as your anchor. If a policy or technology intervention moves outcomes materially below this line, it is meaningful. If outcomes cluster near AI Base across scenarios, the variable being tested has low sensitivity. This is the best-estimate central case — neither optimistic nor pessimistic.',
    keyDrivers: [
      '20%/yr AI compute demand growth (consistent with 2020–2024 hyperscale capex)',
      '2%/yr PUE improvement (industry average, IEA 2023)',
      'Hyperscale share rising slowly from 45% to ~55% by 2035',
      'Device and network parameters at 2024 baseline',
    ],
    watchFor: [
      'DC electricity share of total ICT — if it exceeds 50% before 2030, AI growth is dominating',
      'Divergence from AI Low/High narrows after 2030 as efficiency gains compound',
      'Germany calibration anchor: model output should be within ±15% of Borderstep/BNetzA estimates',
    ],
    params: [
      { key: 'ai_growth_rate', label: 'AI Compute Growth', description: 'Annual growth in AI compute demand', baseline: '20%/yr', value: '20%/yr', direction: 'neutral' },
      { key: 'pue_improvement_rate', label: 'PUE Improvement', description: 'Annual reduction in Power Usage Effectiveness', baseline: '2%/yr', value: '2%/yr', direction: 'neutral' },
      { key: 'utilisation_multiplier', label: 'DC Utilisation', description: 'Multiplier on baseline DC utilisation rate', baseline: '1.0x', value: '1.0x', direction: 'neutral' },
      { key: 'ai_kwh_per_eflop', label: 'AI Energy Intensity', description: 'kWh consumed per EFLOP of AI compute', baseline: '0.001', value: '0.001', direction: 'neutral' },
      { key: 'avg_lifespan_multiplier', label: 'Device Lifespan', description: 'Multiplier on average device lifespan', baseline: '1.0x', value: '1.0x', direction: 'neutral' },
      { key: 'power_efficiency_factor', label: 'Network Efficiency', description: 'Multiplier on network equipment power draw', baseline: '1.0x', value: '1.0x', direction: 'neutral' },
    ],
    placement: { hyperscale: 0.45, sovereign: 0.15, colocation: 0.25, on_premises: 0.10, edge: 0.05 },
    placementDelta: { hyperscale: 0.01, sovereign: 0.005, colocation: -0.005, on_premises: -0.01, edge: 0.0 },
    sources: [
      { ref: 'IEA-DC-2024', detail: '20%/yr AI compute growth and 2%/yr PUE improvement calibrated to IEA Data Centres and Data Transmission Networks (2024), tracking global DC electricity at ~460 TWh in 2022 with rapid AI-driven growth.' },
      { ref: 'BORDERSTEP-2023', detail: 'Germany calibration anchor: Borderstep Institut, Rechenzentren in Deutschland 2023 — total German DC electricity ~18 TWh; used as Tier 1 validation target (±15%).' },
      { ref: 'SYNERGY-Q4-2024', detail: 'Hyperscale placement share (45%) derived from Synergy Research Group Q4 2024 — hyperscale operators account for ~45% of global DC capacity.' },
      { ref: 'GOOGLE-ESR-2024', detail: 'Google Environmental Report 2024 reports average PUE of 1.10 across its fleet; used to anchor the 2%/yr improvement assumption for best-in-class operators.' },
      { ref: 'FRAUNHOFER-ISI-2020', detail: 'Fraunhofer ISI (2020) — baseline device and network electricity parameters for Germany, extrapolated globally.' },
    ],
  },
  {
    id: 'ai_low', family: 'ai_dc', label: 'AI Low', color: '#10B981',
    tagline: 'Conservative AI adoption — efficiency gains outpace demand growth',
    narrative: 'AI compute demand grows at only 8%/yr — closer to conventional cloud workload growth than the AI boom of 2022–2024. PUE improves at 4%/yr, devices last longer, and network equipment is more efficient. ICT electricity demand grows, but at a pace grid operators can manage.',
    interpretation: 'The soft-landing case. AI still grows at 8%/yr but efficiency improvements prevent runaway demand. Compare against AI Base to isolate the AI demand premium — the additional electricity attributable to the current pace of AI scaling.',
    keyDrivers: [
      '8%/yr AI compute growth (conventional cloud-like trajectory)',
      '4%/yr PUE improvement (achievable with liquid cooling adoption)',
      '10% lower DC utilisation than baseline',
      'Better energy intensity per EFLOP (0.0008 vs 0.001) — newer hardware mix',
      'Longer device lifespans (+10%) and more efficient network equipment (−5%)',
    ],
    watchFor: [
      'Convergence with AI Base after 2030 as efficiency gains compound',
      'Devices and networks may become the dominant ICT electricity consumers in this scenario',
      'Low scenario is the floor for plausible near-term outcomes absent major disruption',
    ],
    params: [
      { key: 'ai_growth_rate', label: 'AI Compute Growth', description: 'Annual growth in AI compute demand', baseline: '20%/yr', value: '8%/yr', direction: 'down' },
      { key: 'pue_improvement_rate', label: 'PUE Improvement', description: 'Annual reduction in Power Usage Effectiveness', baseline: '2%/yr', value: '4%/yr', direction: 'up' },
      { key: 'utilisation_multiplier', label: 'DC Utilisation', description: 'Multiplier on baseline DC utilisation rate', baseline: '1.0x', value: '0.90x', direction: 'down' },
      { key: 'ai_kwh_per_eflop', label: 'AI Energy Intensity', description: 'kWh consumed per EFLOP of AI compute', baseline: '0.001', value: '0.0008', direction: 'down' },
      { key: 'avg_lifespan_multiplier', label: 'Device Lifespan', description: 'Multiplier on average device lifespan', baseline: '1.0x', value: '1.1x', direction: 'up' },
      { key: 'power_efficiency_factor', label: 'Network Efficiency', description: 'Multiplier on network equipment power draw', baseline: '1.0x', value: '0.95x', direction: 'down' },
    ],
    placement: { hyperscale: 0.45, sovereign: 0.12, colocation: 0.27, on_premises: 0.11, edge: 0.05 },
    placementDelta: { hyperscale: 0.005, sovereign: 0.002, colocation: 0.0, on_premises: -0.005, edge: -0.002 },
    sources: [
      { ref: 'IEA-DC-2024', detail: '8%/yr AI compute growth reflects the lower end of IEA projections, consistent with inference efficiency improvements dominating over new training demand.' },
      { ref: 'UPTIME-PUE-2023', detail: '4%/yr PUE improvement: Uptime Institute Global DC Survey 2023 reports average PUE of 1.58 globally; best-in-class at 1.2–1.3, implying 4%/yr is achievable with liquid cooling rollout.' },
      { ref: 'CIRCULAR-ECONOMY-EC-2021', detail: 'Device lifespan +10%: EU Ecodesign Regulation (EU) 2021/341 mandates minimum 5–7 year spare parts availability; modelled as 10% lifespan extension vs 2024 baseline.' },
      { ref: 'ERICSSON-MOBILITY-2024', detail: 'Network efficiency −5%: Ericsson Mobility Report 2024 projects 15–20% energy efficiency improvement per bit by 2029 for RAN equipment; −5% is a conservative near-term estimate.' },
    ],
  },
  {
    id: 'ai_high', family: 'ai_dc', label: 'AI High', color: '#EF4444',
    tagline: 'Accelerated AI build-out — hyperscale capacity doubles by 2030',
    narrative: 'AI compute demand grows at 40%/yr — roughly double the baseline rate, consistent with the most aggressive analyst forecasts for AI infrastructure investment through 2027. PUE improvement slows to 1%/yr as demand outpaces engineering capacity. Hyperscale share rises rapidly.',
    interpretation: 'The continued-boom scenario. 40%/yr AI compute growth is within the range of observed 2023–2024 hyperscale capex. Use it to stress-test grid capacity planning and understand the upper bound of near-term DC electricity demand.',
    keyDrivers: [
      '40%/yr AI compute growth (consistent with 2023–2024 hyperscale capex)',
      '1%/yr PUE improvement — demand outpaces efficiency engineering',
      '15% higher DC utilisation than baseline',
      'Slightly worse energy intensity per EFLOP (0.0012) — rapid hardware scaling',
      'Faster device refresh (−5% lifespan) and higher network load (+5%)',
    ],
    watchFor: [
      'Data centre share of total ICT electricity may exceed 60% by 2030',
      'Grid constraint scenarios become binding — cross-reference with Grid Constrained',
      'Emissions trajectory diverges sharply from AI Low — the scenario spread is the policy-relevant range',
      'Hyperscale share approaches 60%+ by 2035',
    ],
    params: [
      { key: 'ai_growth_rate', label: 'AI Compute Growth', description: 'Annual growth in AI compute demand', baseline: '20%/yr', value: '40%/yr', direction: 'up' },
      { key: 'pue_improvement_rate', label: 'PUE Improvement', description: 'Annual reduction in Power Usage Effectiveness', baseline: '2%/yr', value: '1%/yr', direction: 'down' },
      { key: 'utilisation_multiplier', label: 'DC Utilisation', description: 'Multiplier on baseline DC utilisation rate', baseline: '1.0x', value: '1.15x', direction: 'up' },
      { key: 'ai_kwh_per_eflop', label: 'AI Energy Intensity', description: 'kWh consumed per EFLOP of AI compute', baseline: '0.001', value: '0.0012', direction: 'up' },
      { key: 'avg_lifespan_multiplier', label: 'Device Lifespan', description: 'Multiplier on average device lifespan', baseline: '1.0x', value: '0.95x', direction: 'down' },
      { key: 'power_efficiency_factor', label: 'Network Efficiency', description: 'Multiplier on network equipment power draw', baseline: '1.0x', value: '1.05x', direction: 'up' },
    ],
    placement: { hyperscale: 0.50, sovereign: 0.18, colocation: 0.22, on_premises: 0.07, edge: 0.03 },
    placementDelta: { hyperscale: 0.02, sovereign: 0.01, colocation: -0.01, on_premises: -0.015, edge: -0.005 },
    sources: [
      { ref: 'GOLDMAN-AI-2024', detail: '40%/yr AI compute growth: Goldman Sachs AI Infrastructure Investment Outlook (2024) projects hyperscale AI capex growing at 40–50%/yr through 2027, implying equivalent compute demand growth.' },
      { ref: 'MSFT-ANNUAL-2024', detail: 'Microsoft FY2024 Annual Report: capex of $55.7bn, up 75% YoY, predominantly for AI infrastructure — corroborates 40%+ annual AI capacity growth.' },
      { ref: 'META-CAPEX-2024', detail: 'Meta Q4 2024 earnings: 2025 capex guidance of $60–65bn, up from $38bn in 2024 — a 60%+ increase driven entirely by AI infrastructure.' },
      { ref: 'IEA-DC-2024', detail: 'PUE improvement slowing to 1%/yr: IEA notes rapid DC expansion is outpacing efficiency engineering in high-growth markets.' },
    ],
  },
  {
    id: 'ai_stress', family: 'ai_dc', label: 'AI Stress', color: '#7C3AED',
    tagline: 'Extreme AI demand — unconstrained compute growth, grid constraints bind',
    narrative: 'A tail-risk stress test probing the upper bound of plausible ICT electricity demand. AI compute grows at 70%/yr. PUE improvement is minimal (0.5%/yr), DC utilisation is 30% above baseline, and hardware scaling outpaces efficiency. This is not a forecast.',
    interpretation: 'Use to answer: what is the worst credible case for ICT electricity demand? Not intended as a planning baseline. If AI Stress outcomes are within grid capacity, that is reassuring. If not, that identifies the need for demand-side constraints or major grid investment.',
    keyDrivers: [
      '70%/yr AI compute growth — extreme but not impossible given 2023 investment trajectories',
      '0.5%/yr PUE improvement — engineering capacity overwhelmed by demand',
      '30% higher DC utilisation than baseline',
      'Worst energy intensity per EFLOP (0.0015) — rapid scaling with mixed hardware vintage',
      'Hyperscale dominates at 55%+ and growing at 3%/yr',
    ],
    watchFor: [
      'Total ICT electricity may approach or exceed 10% of global electricity by 2035',
      'Data centre share of ICT electricity likely exceeds 70%',
      'Treat outputs as an upper bound, not a central estimate',
      'In practice, grid limits would dampen this trajectory before 2030',
    ],
    params: [
      { key: 'ai_growth_rate', label: 'AI Compute Growth', description: 'Annual growth in AI compute demand', baseline: '20%/yr', value: '70%/yr', direction: 'up' },
      { key: 'pue_improvement_rate', label: 'PUE Improvement', description: 'Annual reduction in Power Usage Effectiveness', baseline: '2%/yr', value: '0.5%/yr', direction: 'down' },
      { key: 'utilisation_multiplier', label: 'DC Utilisation', description: 'Multiplier on baseline DC utilisation rate', baseline: '1.0x', value: '1.30x', direction: 'up' },
      { key: 'ai_kwh_per_eflop', label: 'AI Energy Intensity', description: 'kWh consumed per EFLOP of AI compute', baseline: '0.001', value: '0.0015', direction: 'up' },
      { key: 'avg_lifespan_multiplier', label: 'Device Lifespan', description: 'Multiplier on average device lifespan', baseline: '1.0x', value: '0.90x', direction: 'down' },
      { key: 'power_efficiency_factor', label: 'Network Efficiency', description: 'Multiplier on network equipment power draw', baseline: '1.0x', value: '1.10x', direction: 'up' },
    ],
    placement: { hyperscale: 0.55, sovereign: 0.20, colocation: 0.18, on_premises: 0.05, edge: 0.02 },
    placementDelta: { hyperscale: 0.03, sovereign: 0.015, colocation: -0.02, on_premises: -0.02, edge: -0.005 },
    sources: [
      { ref: 'EPOCH-AI-2024', detail: '70%/yr AI compute growth: Epoch AI, Trends in Machine Learning Hardware (2024) documents training compute doubling every ~6 months (2020–2024), implying ~150%/yr growth; 70%/yr is a moderated stress-test value.' },
      { ref: 'SEMANALYSIS-2024', detail: 'SemiAnalysis, AI Datacenter Energy Dilemma (2024): projects AI-specific DC power demand reaching 96 GW by 2030 under aggressive scaling — consistent with the AI Stress trajectory.' },
      { ref: 'IEA-DC-2024', detail: 'IEA (2024) notes that under high-AI scenarios, global DC electricity could reach 1,000 TWh by 2026 — the AI Stress scenario is calibrated to be consistent with this upper bound.' },
      { ref: 'GRID-QUEUE-NESO-2024', detail: 'NESO 2024 Connection Queue data: 750+ GW in the GB queue, of which ~40 GW is DC-related — evidence that grid limits would bind before 2030 in this scenario.' },
    ],
    specialNotes: [
      'Stress test only — do not use as a planning baseline.',
      'In practice, grid constraints would dampen this trajectory before 2030.',
    ],
  },
  {
    id: 'sovereignty_push', family: 'sovereignty', label: 'Sovereignty Push', color: '#F59E0B',
    tagline: 'Workload repatriation to national clouds — distributed, less efficient DC footprint',
    narrative: 'Driven by data localisation regulations and EU digital sovereignty policy, workloads migrate from hyperscale public cloud to sovereign cloud and on-premises infrastructure. By 2030, 20% of hyperscale workloads are repatriated. Sovereign and on-premises infrastructure is less PUE-optimised, and AI energy intensity is higher due to less specialised hardware.',
    interpretation: 'Answers: what is the electricity cost of digital sovereignty? Because sovereign and on-premises infrastructure is less efficient than hyperscale, the same compute workload consumes more electricity when repatriated. Compare against AI Base to isolate the sovereignty premium.',
    keyDrivers: [
      'Hyperscale share falls from 45% to ~35% by 2024, declining further at −2%/yr',
      'Sovereign cloud share rises from 15% to 30% by 2024, growing at +2.5%/yr',
      '20% of hyperscale workloads repatriated to sovereign infrastructure by 2030',
      'PUE improvement slows to 1.5%/yr — sovereign infra less optimised than hyperscale',
      'AI energy intensity 20% worse than baseline (0.0012 vs 0.001 kWh/EFLOP)',
    ],
    watchFor: [
      'Total ICT electricity may be 5–15% higher than AI Base by 2030 due to efficiency penalty',
      'Geographic distribution of demand shifts — more distributed, less concentrated in Tier 1 DC hubs',
      'Emissions impact depends heavily on grid mix in sovereign cloud locations',
    ],
    params: [
      { key: 'ai_growth_rate', label: 'AI Compute Growth', description: 'Annual growth in AI compute demand', baseline: '20%/yr', value: '20%/yr', direction: 'neutral' },
      { key: 'pue_improvement_rate', label: 'PUE Improvement', description: 'Annual reduction in Power Usage Effectiveness', baseline: '2%/yr', value: '1.5%/yr', direction: 'down' },
      { key: 'utilisation_multiplier', label: 'DC Utilisation', description: 'Multiplier on baseline DC utilisation rate', baseline: '1.0x', value: '1.05x', direction: 'up' },
      { key: 'ai_kwh_per_eflop', label: 'AI Energy Intensity', description: 'kWh consumed per EFLOP of AI compute', baseline: '0.001', value: '0.0012', direction: 'up' },
      { key: 'avg_lifespan_multiplier', label: 'Device Lifespan', description: 'Multiplier on average device lifespan', baseline: '1.0x', value: '1.0x', direction: 'neutral' },
      { key: 'power_efficiency_factor', label: 'Network Efficiency', description: 'Multiplier on network equipment power draw', baseline: '1.0x', value: '1.0x', direction: 'neutral' },
    ],
    placement: { hyperscale: 0.35, sovereign: 0.30, colocation: 0.22, on_premises: 0.10, edge: 0.03 },
    placementDelta: { hyperscale: -0.02, sovereign: 0.025, colocation: 0.005, on_premises: -0.005, edge: -0.005 },
    sources: [
      { ref: 'EU-AIACT-2024', detail: 'EU AI Act (Regulation 2024/1689), in force August 2024: imposes data governance and localisation requirements on high-risk AI systems, driving demand for EU-based sovereign cloud infrastructure.' },
      { ref: 'EUCS-2024', detail: 'EU Cloud Services Cybersecurity Scheme (EUCS) draft 2024: proposed EU Sovereign tier requires data processing exclusively within EU by EU-controlled entities — primary regulatory driver for the sovereignty scenario.' },
      { ref: 'GAIA-X-2024', detail: 'Gaia-X Association, Data Spaces Business Alliance Report 2024: estimates 20–30% of European enterprise cloud workloads could migrate to sovereign infrastructure by 2030 under current regulatory trajectory.' },
      { ref: 'UPTIME-PUE-2023', detail: 'PUE penalty for sovereign infra: Uptime Institute 2023 reports average PUE of 1.58 for enterprise/on-premises DCs vs ~1.2 for hyperscale — sovereign infrastructure is structurally less efficient.' },
      { ref: 'BORDERSTEP-2023', detail: 'Borderstep 2023 notes ~60% of German DC capacity is still enterprise/colocation, not hyperscale — consistent with the sovereignty scenario distribution.' },
    ],
    specialNotes: [
      'Repatriation fraction by 2030: 20% of hyperscale workloads moved to sovereign infrastructure.',
      'Relevant for EU AI Act, GDPR enforcement, and national cloud strategy analysis.',
    ],
  },
  {
    id: 'grid_constrained', family: 'grid', label: 'Grid Constrained', color: '#6B7280',
    tagline: 'Grid limits bind from 2027 — DC expansion slows in key markets',
    narrative: 'From 2027, electricity grid constraints limit data centre expansion in Ireland, the Netherlands, Great Britain, and Singapore. AI growth slows to 15%/yr as power availability becomes the binding constraint. PUE improvement accelerates slightly as operators are forced to extract more compute per watt.',
    interpretation: 'The most policy-relevant near-term scenario. Grid connection queues in Ireland and the Netherlands are already multi-year. Demand falls below AI Base — not because AI adoption slows, but because physical infrastructure cannot be built fast enough.',
    keyDrivers: [
      'Grid constraint onset: 2027 in IE, NL, GB, SG',
      'AI growth slows to 15%/yr — power availability is the binding constraint',
      'PUE improvement accelerates to 2.5%/yr under grid pressure',
      'DC utilisation 15% below baseline — constrained markets cannot fill capacity',
    ],
    watchFor: [
      'Demand shifts geographically — constrained markets lose share to US, DE, SE, PL',
      'After 2027, the gap between Grid Constrained and AI Base widens — this is the grid premium',
      'Phase 0 model applies constraint uniformly; Phase 1 will apply market-specific capacity caps',
    ],
    params: [
      { key: 'ai_growth_rate', label: 'AI Compute Growth', description: 'Annual growth in AI compute demand', baseline: '20%/yr', value: '15%/yr', direction: 'down' },
      { key: 'pue_improvement_rate', label: 'PUE Improvement', description: 'Annual reduction in Power Usage Effectiveness', baseline: '2%/yr', value: '2.5%/yr', direction: 'up' },
      { key: 'utilisation_multiplier', label: 'DC Utilisation', description: 'Multiplier on baseline DC utilisation rate', baseline: '1.0x', value: '0.85x', direction: 'down' },
      { key: 'ai_kwh_per_eflop', label: 'AI Energy Intensity', description: 'kWh consumed per EFLOP of AI compute', baseline: '0.001', value: '0.0009', direction: 'down' },
      { key: 'avg_lifespan_multiplier', label: 'Device Lifespan', description: 'Multiplier on average device lifespan', baseline: '1.0x', value: '1.05x', direction: 'up' },
      { key: 'power_efficiency_factor', label: 'Network Efficiency', description: 'Multiplier on network equipment power draw', baseline: '1.0x', value: '0.90x', direction: 'down' },
    ],
    placement: { hyperscale: 0.40, sovereign: 0.15, colocation: 0.28, on_premises: 0.12, edge: 0.05 },
    placementDelta: { hyperscale: 0.005, sovereign: 0.005, colocation: 0.0, on_premises: -0.005, edge: -0.005 },
    sources: [
      { ref: 'EIRGRID-2024', detail: 'EirGrid, Tomorrow\'s Energy Scenarios Ireland 2024: DC electricity reached 21% of national consumption in 2023; EirGrid imposed a moratorium on new large DC connections in the Dublin area since 2022.' },
      { ref: 'TENNET-2024', detail: 'TenneT, Dutch Grid Capacity Report 2024: grid congestion affects >80% of the Netherlands; ACM reports multi-year connection queues for DCs in Noord-Holland and Utrecht provinces.' },
      { ref: 'NESO-2024', detail: 'NESO, Electricity Ten Year Statement 2024: identifies DC load growth as a primary driver of transmission reinforcement need in SE England; connection timelines of 5–10 years for large sites.' },
      { ref: 'EMA-SG-2024', detail: 'Energy Market Authority Singapore, Singapore Energy Statistics 2024: DC moratorium lifted in 2022 after 2-year pause; new capacity subject to PUE and carbon intensity caps — effective constraint from 2027 modelled here.' },
      { ref: 'IEA-DC-2024', detail: 'IEA (2024) identifies grid connection constraints as the primary near-term bottleneck for DC expansion in Europe and Asia-Pacific.' },
    ],
    specialNotes: [
      'Constraint onset year: 2027. Constrained markets: IE, NL, GB, SG.',
      'Phase 0 applies constraint as a uniform demand dampener. Phase 1 will apply market-specific capacity caps.',
    ],
  },
  {
    id: 'efficiency_breakthrough', family: 'efficiency', label: 'Efficiency Breakthrough', color: '#06B6D4',
    tagline: 'Rapid PUE and hardware efficiency gains — demand grows far below baseline',
    narrative: 'Engineering progress dramatically outpaces demand growth. PUE improves at 6%/yr via liquid cooling and AI-optimised chip architectures. AI energy intensity halves relative to baseline (0.0005 kWh/EFLOP). Network equipment becomes 20% more efficient. AI compute growth is unchanged — the efficiency gains are purely on the supply side.',
    interpretation: 'Answers: how much can technology alone reduce ICT electricity demand, holding AI growth constant? Compare against AI Base to isolate the efficiency dividend. Relevant for assessing hardware efficiency standards and DC energy performance regulations.',
    keyDrivers: [
      '6%/yr PUE improvement — liquid cooling, AI-optimised design, best-in-class operations',
      'AI energy intensity halved: 0.0005 kWh/EFLOP (next-gen accelerators, custom ASICs)',
      '20% improvement in network equipment power efficiency',
      'Device lifespans +15% — longer refresh cycles reduce operational energy',
      'AI growth unchanged at 20%/yr — efficiency gains are supply-side only',
    ],
    watchFor: [
      'By 2030, total ICT electricity may be 20–35% below AI Base despite identical AI growth',
      'Data centre share of ICT electricity may fall as DC efficiency outpaces device/network improvement',
      'Jevons paradox risk: cheaper compute may induce more demand — not modelled here',
    ],
    params: [
      { key: 'ai_growth_rate', label: 'AI Compute Growth', description: 'Annual growth in AI compute demand', baseline: '20%/yr', value: '20%/yr', direction: 'neutral' },
      { key: 'pue_improvement_rate', label: 'PUE Improvement', description: 'Annual reduction in Power Usage Effectiveness', baseline: '2%/yr', value: '6%/yr', direction: 'up' },
      { key: 'utilisation_multiplier', label: 'DC Utilisation', description: 'Multiplier on baseline DC utilisation rate', baseline: '1.0x', value: '0.95x', direction: 'down' },
      { key: 'ai_kwh_per_eflop', label: 'AI Energy Intensity', description: 'kWh consumed per EFLOP of AI compute', baseline: '0.001', value: '0.0005', direction: 'down' },
      { key: 'avg_lifespan_multiplier', label: 'Device Lifespan', description: 'Multiplier on average device lifespan', baseline: '1.0x', value: '1.15x', direction: 'up' },
      { key: 'power_efficiency_factor', label: 'Network Efficiency', description: 'Multiplier on network equipment power draw', baseline: '1.0x', value: '0.80x', direction: 'down' },
    ],
    placement: { hyperscale: 0.50, sovereign: 0.12, colocation: 0.25, on_premises: 0.08, edge: 0.05 },
    placementDelta: { hyperscale: 0.015, sovereign: 0.005, colocation: -0.005, on_premises: -0.01, edge: -0.005 },
    sources: [
      { ref: 'GOOGLE-ESR-2024', detail: 'Google Environmental Report 2024: average fleet PUE of 1.10; liquid-cooled TPU pods achieve PUE <1.05. 6%/yr improvement from a global average of ~1.58 is aggressive but technically achievable at scale.' },
      { ref: 'UPTIME-PUE-2023', detail: 'Uptime Institute 2023: global average PUE 1.58; top quartile 1.2–1.3. The gap between average and best-in-class implies 6%/yr improvement is the upper bound of what engineering can deliver.' },
      { ref: 'EPOCH-AI-2024', detail: 'AI energy intensity halved (0.0005 kWh/EFLOP): Epoch AI documents ~2× compute efficiency improvement per generation of AI accelerators (2020–2024); 0.0005 reflects two hardware generations of improvement.' },
      { ref: 'ERICSSON-MOBILITY-2024', detail: 'Network efficiency −20%: Ericsson Mobility Report 2024 projects 15–20% energy efficiency improvement per bit by 2029 for RAN equipment; −20% represents the upper end of this range.' },
      { ref: 'EU-ECODESIGN-2021', detail: 'Device lifespan +15%: EU Ecodesign Regulation (EU) 2021/341 and Right to Repair Directive (2024) mandate extended spare parts availability; modelled as 15% lifespan extension vs 2024 baseline.' },
    ],
    specialNotes: [
      'Jevons paradox (cheaper compute inducing more demand) is not modelled — outputs are a lower bound.',
      'PUE of 6%/yr is aggressive but achievable with liquid cooling at scale.',
    ],
  },
];

interface GlobalRef { key: string; authors: string; title: string; publisher: string; year: number; url?: string; }
const GLOBAL_REFS: GlobalRef[] = [
  { key: 'IEA-DC-2024', authors: 'International Energy Agency', title: 'Data Centres and Data Transmission Networks', publisher: 'IEA, Paris', year: 2024, url: 'https://www.iea.org/energy-system/buildings/data-centres-and-data-transmission-networks' },
  { key: 'BORDERSTEP-2023', authors: 'Hintemann, R. & Hinterholzer, S.', title: 'Rechenzentren in Deutschland: Bestandsaufnahme 2023', publisher: 'Borderstep Institut für Innovation und Nachhaltigkeit', year: 2023, url: 'https://www.borderstep.de/publikationen/' },
  { key: 'FRAUNHOFER-ISI-2020', authors: 'Fraunhofer ISI', title: 'Entwicklung des IKT-bedingten Strombedarfs in Deutschland', publisher: 'Fraunhofer Institut für System- und Innovationsforschung ISI', year: 2020, url: 'https://www.isi.fraunhofer.de' },
  { key: 'UPTIME-PUE-2023', authors: 'Uptime Institute', title: 'Global Data Center Survey Results 2023', publisher: 'Uptime Institute LLC', year: 2023, url: 'https://uptimeinstitute.com/research-publications' },
  { key: 'SYNERGY-Q4-2024', authors: 'Synergy Research Group', title: 'Hyperscale Data Center Count and Capacity — Q4 2024', publisher: 'Synergy Research Group', year: 2024, url: 'https://www.srgresearch.com' },
  { key: 'GOOGLE-ESR-2024', authors: 'Google LLC', title: 'Google Environmental Report 2024', publisher: 'Alphabet Inc.', year: 2024, url: 'https://sustainability.google/reports/google-2024-environmental-report/' },
  { key: 'GOLDMAN-AI-2024', authors: 'Goldman Sachs Global Investment Research', title: 'AI Infrastructure: Power and Beyond', publisher: 'Goldman Sachs', year: 2024 },
  { key: 'MSFT-ANNUAL-2024', authors: 'Microsoft Corporation', title: 'Annual Report FY2024', publisher: 'Microsoft Corporation', year: 2024, url: 'https://www.microsoft.com/investor/reports/ar24/' },
  { key: 'META-CAPEX-2024', authors: 'Meta Platforms Inc.', title: 'Q4 2024 Earnings Release and 2025 Capex Guidance', publisher: 'Meta Platforms Inc.', year: 2024, url: 'https://investor.fb.com' },
  { key: 'EPOCH-AI-2024', authors: 'Epoch AI', title: 'Trends in Machine Learning Hardware', publisher: 'Epoch AI Research', year: 2024, url: 'https://epochai.org/research' },
  { key: 'SEMANALYSIS-2024', authors: 'SemiAnalysis', title: 'AI Datacenter Energy Dilemma — Race to the Top', publisher: 'SemiAnalysis LLC', year: 2024, url: 'https://www.semianalysis.com' },
  { key: 'GRID-QUEUE-NESO-2024', authors: 'National Energy System Operator (NESO)', title: 'Electricity Ten Year Statement 2024', publisher: 'NESO, UK', year: 2024, url: 'https://www.neso.energy/publications' },
  { key: 'EIRGRID-2024', authors: 'EirGrid', title: "Tomorrow's Energy Scenarios Ireland 2024", publisher: 'EirGrid Group', year: 2024, url: 'https://www.eirgridgroup.com/the-grid/tomorrow' },
  { key: 'TENNET-2024', authors: 'TenneT TSO B.V.', title: 'Grid Capacity Report — Netherlands 2024', publisher: 'TenneT', year: 2024, url: 'https://www.tennet.eu/nl/nieuws-en-publicaties/publicaties' },
  { key: 'NESO-2024', authors: 'National Energy System Operator (NESO)', title: 'Electricity Ten Year Statement 2024', publisher: 'NESO, UK', year: 2024, url: 'https://www.neso.energy/publications' },
  { key: 'EMA-SG-2024', authors: 'Energy Market Authority Singapore', title: 'Singapore Energy Statistics 2024', publisher: 'EMA, Singapore', year: 2024, url: 'https://www.ema.gov.sg/singapore-energy-statistics' },
  { key: 'EU-AIACT-2024', authors: 'European Parliament and Council', title: 'Regulation (EU) 2024/1689 — Artificial Intelligence Act', publisher: 'Official Journal of the European Union', year: 2024, url: 'https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689' },
  { key: 'EUCS-2024', authors: 'ENISA', title: 'EU Cloud Services Cybersecurity Scheme (EUCS) — Candidate Scheme v3', publisher: 'European Union Agency for Cybersecurity (ENISA)', year: 2024, url: 'https://www.enisa.europa.eu/publications/eucs-cloud-scheme' },
  { key: 'GAIA-X-2024', authors: 'Gaia-X Association AISBL', title: 'Data Spaces Business Alliance: European Data Sovereignty Report 2024', publisher: 'Gaia-X Association', year: 2024, url: 'https://gaia-x.eu/news-publications' },
  { key: 'ERICSSON-MOBILITY-2024', authors: 'Ericsson', title: 'Ericsson Mobility Report November 2024', publisher: 'Telefonaktiebolaget LM Ericsson', year: 2024, url: 'https://www.ericsson.com/en/reports-and-papers/mobility-report' },
  { key: 'CIRCULAR-ECONOMY-EC-2021', authors: 'European Commission', title: 'Ecodesign Regulation (EU) 2021/341 — Sustainable Products', publisher: 'Official Journal of the European Union', year: 2021, url: 'https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32021R0341' },
  { key: 'EU-ECODESIGN-2021', authors: 'European Commission', title: 'Ecodesign Regulation (EU) 2021/341 and Right to Repair Directive (2024)', publisher: 'Official Journal of the European Union', year: 2021, url: 'https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32021R0341' },
];

const FAMILY_FILTER_KEYS: Family[] = ['all', 'ai_dc', 'sovereignty', 'grid', 'efficiency'];
const FAMILY_LABELS: Record<Family, string> = {
  all: 'All', ai_dc: 'AI / Data Centre', sovereignty: 'Sovereignty', grid: 'Grid', efficiency: 'Efficiency',
};
const DIRECTION_ICON: Record<string, string> = { up: '▲', down: '▼', neutral: '—' };
const DIRECTION_COLOR: Record<string, string> = { up: '#EF4444', down: '#10B981', neutral: 'var(--text-muted)' };
const PLACEMENT_KEYS: (keyof PlacementShare)[] = ['hyperscale', 'sovereign', 'colocation', 'on_premises', 'edge'];
const PLACEMENT_LABELS: Record<keyof PlacementShare, string> = {
  hyperscale: 'Hyperscale', sovereign: 'Sovereign Cloud', colocation: 'Colocation',
  on_premises: 'On-Premises', edge: 'Edge',
};
const PLACEMENT_COLORS: Record<keyof PlacementShare, string> = {
  hyperscale: '#3B82F6', sovereign: '#F59E0B', colocation: '#10B981', on_premises: '#8B5CF6', edge: '#06B6D4',
};

function PlacementBar({ placement, delta }: { placement: PlacementShare; delta: Partial<PlacementShare> }) {
  return (
    <div>
      <div style={{ display: 'flex', height: '10px', borderRadius: '4px', overflow: 'hidden', marginBottom: '10px' }}>
        {PLACEMENT_KEYS.map((k) => (
          <div
            key={k}
            style={{ width: `${placement[k] * 100}%`, background: PLACEMENT_COLORS[k] }}
            title={`${PLACEMENT_LABELS[k]}: ${(placement[k] * 100).toFixed(0)}%`}
          />
        ))}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
        {PLACEMENT_KEYS.map((k) => {
          const d = delta[k] ?? 0;
          return (
            <div key={k} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '2px', background: PLACEMENT_COLORS[k], flexShrink: 0 }} />
              <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{PLACEMENT_LABELS[k]}</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)' }}>
                {(placement[k] * 100).toFixed(0)}%
              </span>
              {d !== 0 && (
                <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: d > 0 ? '#EF4444' : '#10B981' }}>
                  {d > 0 ? '+' : ''}{(d * 100).toFixed(1)}%/yr
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ParamTable({ params }: { params: Param[] }) {
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
      <thead>
        <tr style={{ borderBottom: '1px solid var(--border)' }}>
          {['Parameter', 'Description', 'Baseline', 'This scenario', ''].map((h) => (
            <th key={h} style={{ padding: '6px 8px', textAlign: 'left', fontSize: '10px',
              fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
              {h.toUpperCase()}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {params.map((p) => (
          <tr key={p.key} style={{ borderBottom: '1px solid var(--border)' }}>
            <td style={{ padding: '7px 8px', fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>{p.label}</td>
            <td style={{ padding: '7px 8px', color: 'var(--text-secondary)' }}>{p.description}</td>
            <td style={{ padding: '7px 8px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{p.baseline}</td>
            <td style={{ padding: '7px 8px', fontFamily: 'var(--font-mono)', fontWeight: 600,
              color: p.direction === 'neutral' ? 'var(--text-primary)' : p.direction === 'up' ? '#EF4444' : '#10B981' }}>
              {p.value}
            </td>
            <td style={{ padding: '7px 8px', textAlign: 'center', fontSize: '11px', color: DIRECTION_COLOR[p.direction] }}>
              {DIRECTION_ICON[p.direction]}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ScenarioCard({ scenario, expanded, onToggle }: {
  scenario: ScenarioDef; expanded: boolean; onToggle: () => void;
}) {
  return (
    <div style={{ border: `1px solid ${scenario.color}55`, borderLeft: `3px solid ${scenario.color}`,
      borderRadius: '8px', background: 'var(--bg-surface)', overflow: 'hidden' }}>
      <button
        onClick={onToggle}
        style={{ width: '100%', background: 'none', border: 'none', cursor: 'pointer',
          padding: '18px 20px', textAlign: 'left', display: 'flex', alignItems: 'flex-start', gap: '14px' }}
      >
        <div style={{ width: '10px', height: '10px', borderRadius: '50%',
          background: scenario.color, flexShrink: 0, marginTop: '3px' }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)' }}>{scenario.label}</span>
            <span style={{ fontSize: '10px', fontWeight: 600, letterSpacing: '0.1em',
              color: scenario.color, background: `${scenario.color}18`,
              padding: '2px 7px', borderRadius: '10px', textTransform: 'uppercase' }}>
              {FAMILY_LABELS[scenario.family]}
            </span>
            {scenario.id === 'ai_stress' && (
              <span style={{ fontSize: '10px', fontWeight: 600, letterSpacing: '0.08em',
                color: '#F59E0B', background: '#F59E0B18', padding: '2px 7px', borderRadius: '10px' }}>
                STRESS TEST
              </span>
            )}
          </div>
          <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            {scenario.tagline}
          </p>
        </div>
        <span style={{ fontSize: '11px', color: 'var(--text-muted)', flexShrink: 0, marginTop: '3px' }}>
          {expanded ? '▲' : '▼'}
        </span>
      </button>

      {expanded && (
        <div style={{ padding: '0 20px 24px', borderTop: '1px solid var(--border)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginTop: '20px' }}>
            <div>
              <h4 style={{ margin: '0 0 8px', fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)',
                letterSpacing: '0.1em', textTransform: 'uppercase' }}>How it is built</h4>
              <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                {scenario.narrative}
              </p>
            </div>
            <div>
              <h4 style={{ margin: '0 0 8px', fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)',
                letterSpacing: '0.1em', textTransform: 'uppercase' }}>How to interpret it</h4>
              <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                {scenario.interpretation}
              </p>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginTop: '20px' }}>
            <div>
              <h4 style={{ margin: '0 0 8px', fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)',
                letterSpacing: '0.1em', textTransform: 'uppercase' }}>Key drivers</h4>
              <ul style={{ margin: 0, paddingLeft: '16px' }}>
                {scenario.keyDrivers.map((d, i) => (
                  <li key={i} style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: '2px' }}>{d}</li>
                ))}
              </ul>
            </div>
            <div>
              <h4 style={{ margin: '0 0 8px', fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)',
                letterSpacing: '0.1em', textTransform: 'uppercase' }}>Watch for</h4>
              <ul style={{ margin: 0, paddingLeft: '16px' }}>
                {scenario.watchFor.map((w, i) => (
                  <li key={i} style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: '2px' }}>{w}</li>
                ))}
              </ul>
            </div>
          </div>

          {scenario.specialNotes && (
            <div style={{ marginTop: '16px', padding: '12px 14px', background: '#F59E0B10',
              border: '1px solid #F59E0B44', borderRadius: '6px' }}>
              <span style={{ fontSize: '10px', fontWeight: 700, color: '#F59E0B',
                letterSpacing: '0.1em', textTransform: 'uppercase' }}>Notes</span>
              <ul style={{ margin: '6px 0 0', paddingLeft: '16px' }}>
                {scenario.specialNotes.map((n, i) => (
                  <li key={i} style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>{n}</li>
                ))}
              </ul>
            </div>
          )}

          <div style={{ marginTop: '20px' }}>
            <h4 style={{ margin: '0 0 10px', fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)',
              letterSpacing: '0.1em', textTransform: 'uppercase' }}>Parameter values vs baseline</h4>
            <div style={{ border: '1px solid var(--border)', borderRadius: '6px', overflow: 'hidden' }}>
              <ParamTable params={scenario.params} />
            </div>
          </div>

          <div style={{ marginTop: '20px' }}>
            <h4 style={{ margin: '0 0 10px', fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)',
              letterSpacing: '0.1em', textTransform: 'uppercase' }}>
              DC workload placement (2024 baseline + annual drift)
            </h4>
            <PlacementBar placement={scenario.placement} delta={scenario.placementDelta} />
          </div>

          <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid var(--border)' }}>
            <h4 style={{ margin: '0 0 10px', fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)',
              letterSpacing: '0.1em', textTransform: 'uppercase' }}>Sources &amp; evidence base</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {scenario.sources.map((s) => {
                const meta = GLOBAL_REFS.find((r) => r.key === s.ref);
                return (
                  <div key={s.ref} style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700,
                      color: 'var(--accent-cyan)', background: 'rgba(0,212,255,0.08)',
                      padding: '2px 6px', borderRadius: '4px', flexShrink: 0, whiteSpace: 'nowrap',
                      marginTop: '1px' }}>
                      [{s.ref}]
                    </span>
                    <div>
                      {meta && (
                        <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '2px' }}>
                          <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{meta.authors}</span>
                          {' '}({meta.year}).{' '}
                          {meta.url
                            ? <a href={meta.url} target="_blank" rel="noreferrer"
                                style={{ color: 'var(--accent-cyan)', textDecoration: 'none', fontStyle: 'italic' }}>
                                {meta.title}
                              </a>
                            : <em>{meta.title}</em>
                          }.
                          {' '}{meta.publisher}.
                        </div>
                      )}
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                        {s.detail}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function ScenarioGuide() {
  const [familyFilter, setFamilyFilter] = useState<Family>('all');
  const [expandedId, setExpandedId] = useState<string | null>('ai_base');

  const visible = SCENARIOS.filter((s) => familyFilter === 'all' || s.family === familyFilter);

  return (
    <div style={{ maxWidth: '960px' }}>
      <PageHeader
        title="Scenario Guide"
        subtitle="How each scenario is built, what drives it, and how to interpret results in context"
      />

      <Card style={{ marginBottom: '20px' }}>
        <h3 style={{ margin: '0 0 8px', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
          How to use this guide
        </h3>
        <p style={{ margin: '0 0 12px', fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.7 }}>
          Each scenario is a self-consistent set of parameter assumptions that shapes the demand trajectory produced by the model.
          Scenarios are not forecasts — they are structured what-if questions. The model generates P10/P50/P90 uncertainty bands
          within each scenario; the scenario spread represents structural uncertainty about which future we are heading toward.
        </p>
        <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', borderTop: '1px solid var(--border)', paddingTop: '12px' }}>
          {[
            { label: 'AI Base', note: 'always run first as your anchor' },
            { label: 'AI Low / High', note: 'bound the AI demand premium' },
            { label: 'AI Stress', note: 'upper-bound stress test only' },
            { label: 'Sovereignty / Grid / Efficiency', note: 'structural alternatives' },
          ].map(({ label, note }) => (
            <div key={label} style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{label}</span>
              {' — '}{note}
            </div>
          ))}
        </div>
      </Card>

      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '16px', alignItems: 'center' }}>
        {FAMILY_FILTER_KEYS.map((f) => (
          <button
            key={f}
            onClick={() => setFamilyFilter(f)}
            style={{ padding: '5px 12px', borderRadius: '6px', fontSize: '12px', fontWeight: 500,
              cursor: 'pointer', border: '1px solid var(--border)',
              background: familyFilter === f ? 'var(--accent-cyan)' : 'var(--bg-surface)',
              color: familyFilter === f ? '#000' : 'var(--text-secondary)',
              transition: 'all 0.15s' }}
          >
            {FAMILY_LABELS[f]}
          </button>
        ))}
        <span style={{ marginLeft: 'auto', fontSize: '11px', color: 'var(--text-muted)' }}>
          {visible.length} scenario{visible.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {visible.map((s) => (
          <ScenarioCard
            key={s.id}
            scenario={s}
            expanded={expandedId === s.id}
            onToggle={() => setExpandedId(expandedId === s.id ? null : s.id)}
          />
        ))}
      </div>

      <Card style={{ marginTop: '32px' }}>
        <h3 style={{ margin: '0 0 4px', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
          Full Reference List
        </h3>
        <p style={{ margin: '0 0 16px', fontSize: '11px', color: 'var(--text-secondary)' }}>
          All sources cited across scenarios. {GLOBAL_REFS.length} references.
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
          {GLOBAL_REFS.map((r, i) => (
            <div key={r.key} style={{ display: 'flex', gap: '12px', alignItems: 'flex-start',
              padding: '10px 0', borderBottom: i < GLOBAL_REFS.length - 1 ? '1px solid var(--border)' : 'none' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700,
                color: 'var(--accent-cyan)', background: 'rgba(0,212,255,0.08)',
                padding: '2px 6px', borderRadius: '4px', flexShrink: 0, whiteSpace: 'nowrap',
                marginTop: '1px' }}>
                [{r.key}]
              </span>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{r.authors}</span>
                {' '}({r.year}).{' '}
                {r.url
                  ? <a href={r.url} target="_blank" rel="noreferrer"
                      style={{ color: 'var(--accent-cyan)', textDecoration: 'none', fontStyle: 'italic' }}>
                      {r.title}
                    </a>
                  : <em>{r.title}</em>
                }.
                {' '}<span style={{ color: 'var(--text-muted)' }}>{r.publisher}.</span>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
