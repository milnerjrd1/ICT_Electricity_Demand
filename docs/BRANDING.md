# Branding & Design System

This document describes the Deloitte-aligned brand tokens, typography conventions, and component
usage rules for the ICT Electricity Demand Model frontend.

---

## 1. Color Tokens

All values are defined in `frontend/src/index.css`. **Never use raw hex values in components** —
always reference a CSS variable or Tailwind token.

### 1.1 Primary palette

| Token | Value | Usage |
|---|---|---|
| `--accent` | `#86BC24` | Primary CTA buttons, active nav, focus rings, accent bars |
| `--accent-hover` | `#76A820` | Button hover state |
| `--accent-active` | `#5F8F17` | Button pressed / active text on light backgrounds |
| `--accent-soft` | `#EAF4D8` | Badge backgrounds, active nav fill, focus shadow |
| `--bg-base` | `#F6F7F9` | Page background |
| `--bg-surface` | `#FFFFFF` | Cards, panels, TopBar, Sidebar |
| `--bg-elevated` | `#FBFBFC` | Hover states, nested panels |
| `--border` | `#E5E7EB` | All dividers and card borders |
| `--border-bright` | `#D0D0CE` | Stronger dividers, scrollbar thumb |
| `--text-primary` | `#0F0B0B` | Headings, body copy |
| `--text-secondary` | `#4B5563` | Supporting text, labels |
| `--text-muted` | `#97999B` | Placeholder, metadata, timestamps |

### 1.2 Secondary palette — charts and categories

Use these **in order** for multi-series charts. Do not use Deloitte green for every series.

| Token | Value | Suggested use |
|---|---|---|
| `--chart-1` | `#0097A9` | Series 1 (teal) |
| `--chart-2` | `#00A3E0` | Series 2 (blue) |
| `--chart-3` | `#0076A8` | Series 3 (deep blue) |
| `--chart-4` | `#75787B` | Series 4 (gray) |
| `--chart-5` | `#007680` | Series 5 (dark teal) |
| `--chart-accent` | `#86BC24` | Selected / primary emphasis only |

Full secondary palette (teal, blue, gray groups) is also available as Tailwind tokens:
`teal-500`, `teal-700`, `blue-300`, `blue-500`, `gray-700`, etc. — see `@theme` block in
`index.css`.

### 1.3 Functional colors (alerts and heatmaps only)

| Token | Value | Meaning |
|---|---|---|
| `--accent-red` | `#DA291C` | Error / danger |
| `--accent-amber` | `#ED8B00` | Warning |
| `--accent-purple` | `#0076A8` | Info (mapped to Deloitte blue) |

> **Rule:** Never use functional colors decoratively. They carry semantic meaning and must only
> appear in error states, alerts, or data heatmaps where the meaning is clear.

### 1.4 Accessibility rules

- **Never use green (`--accent`) for body text on white** — contrast ratio is insufficient.
- Green is for accents, borders, active states, and emphasis only.
- All body text uses `--text-primary` (#0F0B0B) on `--bg-surface` (#FFFFFF) — WCAG AA compliant.
- Secondary text (`--text-secondary` #4B5563 on white) meets WCAG AA for normal text.

---

## 2. Typography

### 2.1 Fonts

| Role | Family | Weights |
|---|---|---|
| Body + headings | Open Sans | 400, 500, 600, 700 |
| Numbers, IDs, code | JetBrains Mono | 400, 500, 600 |

Currently loaded via Google Fonts. To swap to self-hosted or `@fontsource`:

1. Remove the `@import url(...)` line from `index.css`.
2. Install `@fontsource/open-sans` and `@fontsource/jetbrains-mono`.
3. Import both in `main.tsx`.
4. The `--font-sans` and `--font-mono` variables in `:root` will pick up the new families
   automatically — no component changes needed.

### 2.2 Scale

| Element | Size | Weight | Token |
|---|---|---|---|
| Page title (H1) | 20px | 700 | `PageHeader` component |
| Section heading (H2) | 16px | 600 | Inline style |
| Card heading (H3) | 13–14px | 600 | Inline style |
| Body | 14px | 400 | Base (`html`) |
| Label / caption | 11–12px | 400–600 | Inline style |
| Metadata / muted | 10–11px | 400–600 | `--text-muted` |
| Mono data | 11–26px | 400–700 | `--font-mono` |

### 2.3 Rules

- Use **Open Sans 600** for all headings and labels.
- Use **JetBrains Mono** for all numeric data values, IDs, version strings, and code.
- Line height: `1.5` for body; `1.25` for headings.
- Letter spacing: `-0.01em` to `-0.02em` for large headings; `0.02–0.06em` for uppercase labels.

---

## 3. Components

### 3.1 `Card`

```tsx
<Card>...</Card>                        // default: white surface, subtle shadow, gray border
<Card accent="var(--accent)">...</Card> // adds 2px green top border
<Card accent="#0097A9">...</Card>       // teal accent for chart cards
```

- Always white background (`--bg-surface`).
- `boxShadow: '0 1px 4px rgba(0,0,0,0.05)'` — subtle, never dramatic.
- `borderRadius: 8px`.
- `padding: 20px`.

### 3.2 `KpiCard`

```tsx
<KpiCard label="Total TWh" value="847" sub="P50 · 2030" />
```

- Value is rendered in JetBrains Mono, `--text-primary` (not colored).
- Label is uppercase, `--text-muted`.
- Pass `accent` to add a colored top border for visual grouping.

### 3.3 `PageHeader`

```tsx
<PageHeader title="Mission Control" subtitle="Live scenario dashboard" actions={<Button>Run</Button>} />
```

- Renders a 3px green left-border accent bar beside the title.
- Title: 20px, weight 700, `--text-primary`.
- Subtitle: 13px, `--text-secondary`.
- `actions` slot: right-aligned, use `Button` components.

### 3.4 `Button`

| Variant | When to use |
|---|---|
| `primary` | Primary action (Run scenario, Export, Save) |
| `secondary` | Secondary action (Compare, Filter, Reset) |
| `ghost` | Tertiary / low-emphasis (Cancel, Dismiss) |
| `danger` | Destructive actions (Delete, Clear) |

```tsx
<Button variant="primary">Run Scenario</Button>
<Button variant="secondary">Compare</Button>
<Button variant="ghost" size="sm">Cancel</Button>
<Button variant="danger">Delete</Button>
<Button variant="primary" loading>Running...</Button>
```

- Primary: Deloitte green fill, white text.
- Secondary: green border, green text, soft green hover.
- Ghost: gray border, secondary text — use for low-priority actions.
- All buttons: `borderRadius: 6px`, `fontWeight: 600`.

### 3.5 `Badge`

```tsx
<Badge>AI / DC</Badge>                        // default: green accent-soft
<Badge color="#0097A9">Teal category</Badge>  // custom color (hex)
```

- Default: `--accent-soft` background, `--accent-active` text, green border.
- Custom hex: semi-transparent background derived from the hex.
- Use for scenario family tags, status labels, confidence tiers.
- Font: Open Sans (not mono), 11px, weight 600.

### 3.6 Wordmark

The `TopBar` renders a text-based Deloitte wordmark placeholder:
`Deloitte` (Open Sans 700) + a 6px green dot.

To replace with the official SVG logo:
1. Place `deloitte-logo.svg` in `frontend/src/assets/`.
2. In `TopBar.tsx`, replace the wordmark `<div>` with:
   ```tsx
   import deloitteLogo from '../assets/deloitte-logo.svg';
   <img src={deloitteLogo} alt="Deloitte" style={{ height: '22px' }} />
   ```

---

## 4. Shape & Spacing

| Property | Value | Rule |
|---|---|---|
| Border radius (default) | `6px` | Buttons, nav items, badges, inputs |
| Border radius (cards) | `8px` | Cards, panels |
| Border radius (large) | `12px` | Modal overlays only |
| Base spacing unit | `8px` | All padding/margin in multiples of 8 |
| Card padding | `20px` | All `Card` components |
| Page content padding | `24–32px` | Shell layout |
| Section gap | `16–24px` | Between cards in a grid |

---

## 5. Charts & Data Visualisation

- Default chart colors: use `--chart-1` through `--chart-5` in order.
- Use `--chart-accent` (green) **only** for the selected/primary series.
- Grid lines: `--border` (`#E5E7EB`), `strokeDasharray="3 3"`.
- Axis tick text: `--text-secondary`, 10–11px, JetBrains Mono.
- Tooltip: `--bg-surface` background, `--border` border, 11px font.
- Avoid green as the dominant chart color — it should draw the eye to the key series only.

---

## 6. Changing the Brand Later

All brand values are centralised in two places:

1. **`frontend/src/index.css`** — `:root` CSS variables (used by all components) and `@theme`
   Tailwind tokens (used by utility classes).
2. **This document** — usage rules.

To rebrand:
- Change hex values in `index.css` only.
- No component files need editing.
- Run `npm run build` to verify no broken references.
