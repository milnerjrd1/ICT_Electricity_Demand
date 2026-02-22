import Plot from 'react-plotly.js';
import type { OutputRow } from '../../types/schema';

interface Props {
  rows: OutputRow[];
  year: number;
}

const ISO_MAP: Record<string, string> = {
  US: 'USA', DE: 'DEU', GB: 'GBR', IE: 'IRL', NL: 'NLD', SG: 'SGP', JP: 'JPN',
  AE: 'ARE', CN: 'CHN', IN: 'IND', AU: 'AUS', CA: 'CAN', SE: 'SWE', PL: 'POL',
  FR: 'FRA', KR: 'KOR', BR: 'BRA', ZA: 'ZAF', SA: 'SAU', MY: 'MYS',
};

export default function ChoroplethMap({ rows, year }: Props) {
  const yearRows = rows.filter((r) => r.year === year);
  const byGeo: Record<string, number> = {};
  for (const r of yearRows) {
    byGeo[r.geo] = (byGeo[r.geo] ?? 0) + r.kwh_p50 / 1e9;
  }

  const locations: string[] = [];
  const values: number[] = [];
  const text: string[] = [];

  for (const [geo, twh] of Object.entries(byGeo)) {
    const iso3 = ISO_MAP[geo];
    if (!iso3) continue;
    locations.push(iso3);
    values.push(Math.round(twh));
    text.push(`${geo}: ${Math.round(twh).toLocaleString()} TWh`);
  }

  return (
    <Plot
      data={[
        {
          type: 'choropleth',
          locationmode: 'ISO-3',
          locations,
          z: values,
          text,
          hovertemplate: '%{text}<extra></extra>',
          colorscale: [
            [0, '#111827'],
            [0.15, '#1E3A5F'],
            [0.4, '#00D4FF'],
            [0.7, '#10B981'],
            [1.0, '#F59E0B'],
          ],
          colorbar: {
            title: { text: 'TWh', font: { color: '#9CA3AF', size: 11 } },
            tickfont: { color: '#9CA3AF', size: 10, family: 'JetBrains Mono' },
            bgcolor: '#111827',
            bordercolor: '#1E3A5F',
            borderwidth: 1,
            thickness: 12,
          },
          marker: { line: { color: '#1E3A5F', width: 0.5 } },
        } as Plotly.Data,
      ]}
      layout={{
        geo: {
          showframe: false,
          showcoastlines: true,
          coastlinecolor: '#1E3A5F',
          showland: true,
          landcolor: '#1F2937',
          showocean: true,
          oceancolor: '#0A0E1A',
          showlakes: false,
          showcountries: true,
          countrycolor: '#1E3A5F',
          bgcolor: '#0A0E1A',
          projection: { type: 'natural earth' },
        },
        paper_bgcolor: '#0A0E1A',
        plot_bgcolor: '#0A0E1A',
        margin: { t: 0, b: 0, l: 0, r: 0 },
        height: 420,
        font: { color: '#9CA3AF', family: 'Inter' },
      } as Partial<Plotly.Layout>}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: '100%' }}
    />
  );
}
