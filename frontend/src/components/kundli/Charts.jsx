export const ABBR = { Sun: "Su", Moon: "Mo", Mars: "Ma", Mercury: "Me", Jupiter: "Ju", Venus: "Ve", Saturn: "Sa", Rahu: "Ra", Ketu: "Ke" };
const tag = (p) => `${ABBR[p.name]}${p.retrograde && !["Rahu", "Ketu"].includes(p.name) ? "(R)" : ""}`;

// fixed house positions of the North Indian diamond chart on a 300x300 board
const NORTH = [[150, 72], [75, 34], [34, 75], [75, 150], [34, 225], [75, 266], [150, 228], [225, 266], [266, 225], [225, 150], [266, 75], [225, 34]];
const NUM = [[150, 128], [75, 12], [12, 75], [128, 150], [12, 225], [75, 290], [150, 172], [225, 290], [288, 225], [172, 150], [288, 75], [225, 12]];

export function NorthChart({ chart, testid = "chart-north" }) {
  const byHouse = (h) => chart.planets.filter((p) => p.house === h).map(tag);
  return (
    <svg data-testid={testid} viewBox="0 0 300 300" role="img" aria-label="North Indian birth chart" className="w-full max-w-[340px] mx-auto">
      <rect x="1" y="1" width="298" height="298" fill="#111B32" stroke="#D4AF37" strokeWidth="1.5" />
      <path d="M1 1L299 299M299 1L1 299M150 1L299 150L150 299L1 150Z" fill="none" stroke="#D4AF37" strokeOpacity=".7" strokeWidth="1" />
      {chart.houses.map((h, i) => (
        <g key={h.house}>
          <text x={NUM[i][0]} y={NUM[i][1] + 4} textAnchor="middle" fontSize="10" fill="#B9C2D3">{h.sign_index + 1}</text>
          {i === 0 && <text x="150" y="100" textAnchor="middle" fontSize="10" fill="#F4D675">Asc</text>}
          {byHouse(h.house).map((t, j, a) => (
            <text key={t} x={NORTH[i][0]} y={NORTH[i][1] + (j - (a.length - 1) / 2) * 12 + 4} textAnchor="middle" fontSize="11" fontWeight="600" fill="#F8F7F2">{t}</text>
          ))}
        </g>
      ))}
    </svg>
  );
}

// South Indian chart: signs fixed, Pisces top-left, clockwise
const SOUTH = [[0, 1], [0, 2], [0, 3], [1, 3], [2, 3], [3, 3], [3, 2], [3, 1], [3, 0], [2, 0], [1, 0], [0, 0]];
const SHORT = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir", "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"];

export function SouthChart({ chart, label = "RASHI" }) {
  const asc = chart.ascendant.sign_index;
  return (
    <div data-testid="chart-south" role="img" aria-label="South Indian birth chart" className="grid grid-cols-4 grid-rows-4 aspect-square w-full max-w-[340px] mx-auto border border-amber-400 bg-[#111B32] text-[11px]">
      {SOUTH.map(([r, c], s) => (
        <div key={s} style={{ gridRow: r + 1, gridColumn: c + 1 }} className={`border border-amber-400/50 p-1 flex flex-col ${s === asc ? "bg-amber-400/10" : ""}`}>
          <span className="text-[10px] text-muted-foreground">{SHORT[s]}{s === asc && <span className="ml-1 text-amber-200">Asc</span>}</span>
          <span className="font-semibold leading-tight text-foreground">{chart.planets.filter((p) => p.sign_index === s).map(tag).join(" ")}</span>
        </div>
      ))}
      <div style={{ gridRow: "2 / 4", gridColumn: "2 / 4" }} className="flex items-center justify-center font-display text-xs tracking-[0.14em] text-amber-200/80">{label}</div>
    </div>
  );
}
