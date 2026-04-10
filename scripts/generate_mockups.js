const fs = require("fs");
const path = require("path");

const outDir = path.join(process.cwd(), "mockups");
fs.mkdirSync(outDir, { recursive: true });

const palette = {
  bg0: "#08131f",
  bg2: "#11293c",
  panel: "#10263a",
  panel2: "#143149",
  line: "#234a68",
  text: "#e8f1f8",
  muted: "#88a3bb",
  cyan: "#2ed3b7",
  blue: "#57b6ff",
  amber: "#f8b84e",
  red: "#ff6b6b",
  green: "#24c48e",
  white: "#ffffff",
};

function wrap(title, body) {
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg width="1600" height="900" viewBox="0 0 1600 900" xmlns="http://www.w3.org/2000/svg">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1600" y2="900" gradientUnits="userSpaceOnUse">
<stop stop-color="${palette.bg0}"/><stop offset="1" stop-color="${palette.bg2}"/>
</linearGradient>
<linearGradient id="hero" x1="0" y1="0" x2="1" y2="1">
<stop stop-color="#113052"/><stop offset="1" stop-color="#0D6C73"/>
</linearGradient>
</defs>
<rect width="1600" height="900" fill="url(#bg)"/>
<circle cx="1270" cy="110" r="220" fill="#0d6c73" opacity="0.08"/>
<circle cx="140" cy="760" r="240" fill="#1f63a3" opacity="0.08"/>
<text x="56" y="64" fill="${palette.white}" font-size="18" font-family="Arial">Nubra x Streamlit Concept</text>
<text x="56" y="112" fill="${palette.text}" font-size="34" font-weight="700" font-family="Arial">${title}</text>
${body}
</svg>`;
}

function panel(x, y, w, h, label, inner = "") {
  return `<rect x="${x}" y="${y}" rx="26" width="${w}" height="${h}" fill="${palette.panel}" stroke="${palette.line}"/>
<text x="${x + 22}" y="${y + 34}" fill="${palette.text}" font-size="22" font-weight="700" font-family="Arial">${label}</text>${inner}`;
}

function metric(x, y, w, h, label, value, accent) {
  return `<rect x="${x}" y="${y}" rx="20" width="${w}" height="${h}" fill="${palette.panel2}" stroke="${palette.line}"/>
<text x="${x + 20}" y="${y + 30}" fill="${palette.muted}" font-size="16" font-family="Arial">${label}</text>
<text x="${x + 20}" y="${y + 72}" fill="${accent}" font-size="34" font-weight="700" font-family="Arial">${value}</text>`;
}

function table(x, y, w, rowH, headers, rows) {
  const colW = w / headers.length;
  let out = `<rect x="${x}" y="${y}" rx="18" width="${w}" height="${rowH * (rows.length + 1) + 20}" fill="${palette.panel2}" stroke="${palette.line}"/>`;
  headers.forEach((h, i) => {
    out += `<text x="${x + 18 + i * colW}" y="${y + 34}" fill="${palette.muted}" font-size="15" font-family="Arial">${h}</text>`;
  });
  rows.forEach((row, r) => {
    const yy = y + 24 + rowH * (r + 1);
    out += `<line x1="${x + 16}" y1="${yy - 18}" x2="${x + w - 16}" y2="${yy - 18}" stroke="${palette.line}"/>`;
    row.forEach((cell, i) => {
      const fill = typeof cell === "object" ? cell.fill : palette.text;
      const text = typeof cell === "object" ? cell.text : cell;
      out += `<text x="${x + 18 + i * colW}" y="${yy}" fill="${fill}" font-size="16" font-family="Arial">${text}</text>`;
    });
  });
  return out;
}

function spark(x, y, values, color, w = 260, h = 74) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const step = w / (values.length - 1);
  const pts = values.map((v, i) => `${x + i * step},${y + h - ((v - min) / range) * h}`).join(" ");
  const cy = y + h - ((values[values.length - 1] - min) / range) * h;
  return `<polyline points="${pts}" fill="none" stroke="${color}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
<circle cx="${x + w}" cy="${cy}" r="5" fill="${color}"/>`;
}

function bars(x, y, vals, colors, w = 280, h = 110) {
  const bw = (w - 20) / vals.length;
  return vals.map((v, i) => {
    const bh = h * v;
    return `<rect x="${x + i * (bw + 6)}" y="${y + h - bh}" width="${bw}" height="${bh}" rx="8" fill="${colors[i % colors.length]}"/>`;
  }).join("");
}

const files = [];

files.push({
  name: "01-landing-overview.svg",
  title: "Signal Discovery Dashboard",
  body: `<rect x="56" y="150" rx="28" width="1488" height="210" fill="url(#hero)" opacity="0.96"/>
<text x="90" y="220" fill="${palette.white}" font-size="48" font-weight="700" font-family="Arial">Find meaningful market signals, not just raw market data.</text>
<text x="90" y="268" fill="${palette.text}" font-size="24" font-family="Arial">Volume spikes, breakout confirmation, OI walls, live watchlists, and symbol drilldowns powered by Nubra.</text>
<rect x="92" y="302" rx="14" width="220" height="44" fill="${palette.cyan}"/>
<text x="125" y="331" fill="#082132" font-size="18" font-weight="700" font-family="Arial">Open Signal Dashboard</text>
${metric(56, 394, 280, 120, "Core engine", "Volume spikes", palette.cyan)}
${metric(354, 394, 280, 120, "Context engine", "OI walls", palette.blue)}
${metric(652, 394, 280, 120, "Hosting", "Streamlit", palette.amber)}
${metric(950, 394, 280, 120, "Mode", "Demo / BYOC", palette.green)}
${panel(56, 548, 720, 290, "User Value",
table(78, 588, 676, 48, ["Module", "Useful output", "Why users care"], [
["Volume Tracker", "Abnormal volume now", "Discover movers early"],
["Breakout Filter", "Volume + price combo", "Remove weak noise"],
["OI Context", "Support / resistance", "Know what blocks the move"],
["Watchlist", "Live alerts", "Track your names fast"],
]))}
${panel(808, 548, 736, 290, "Recommended V1",
`<text x="832" y="606" fill="${palette.text}" font-size="20" font-family="Arial">• Shared demo mode using Streamlit secrets</text>
<text x="832" y="648" fill="${palette.text}" font-size="20" font-family="Arial">• Optional bring-your-own Nubra credentials later</text>
<text x="832" y="690" fill="${palette.text}" font-size="20" font-family="Arial">• Read-only product with live-ish scans and drilldowns</text>
<text x="832" y="742" fill="${palette.cyan}" font-size="26" font-weight="700" font-family="Arial">Build a useful signal product, not a vanity dashboard.</text>`)}`
});

files.push({
  name: "02-market-pulse.svg",
  title: "Market Pulse",
  body: `${metric(56, 150, 250, 108, "Volume leaders", "14", palette.green)}
${metric(326, 150, 250, 108, "Breakout confirmed", "6", palette.cyan)}
${metric(596, 150, 250, 108, "Wall near spot", "9", palette.amber)}
${metric(866, 150, 250, 108, "Strong bullish", "4", palette.blue)}
${metric(1136, 150, 250, 108, "Updated", "09:42 IST", palette.text)}
${panel(56, 290, 908, 550, "Signal Heat",
`<text x="80" y="332" fill="${palette.muted}" font-size="16" font-family="Arial">Cross-market signal density</text>
${spark(92, 382, [44,48,46,55,58,63,62,68,72,70], palette.cyan, 340, 130)}
${spark(470, 382, [71,67,66,60,58,53,56,51,48,45], palette.red, 340, 130)}
<text x="92" y="540" fill="${palette.text}" font-size="18" font-family="Arial">Momentum pressure</text>
<text x="470" y="540" fill="${palette.text}" font-size="18" font-family="Arial">Resistance pressure</text>
<rect x="92" y="580" rx="20" width="834" height="218" fill="${palette.panel2}" stroke="${palette.line}"/>
${bars(126, 646, [0.52,0.68,0.44,0.78,0.33,0.71,0.63,0.57], [palette.cyan, palette.blue, palette.amber, palette.green], 760, 120)}`)}
${panel(994, 290, 550, 550, "Priority Tape",
table(1018, 338, 502, 54, ["Symbol", "Signal", "Bias"], [
["NIFTY", { text: "Put wall near", fill: palette.green }, "Bullish"],
["RELIANCE", { text: "4.1x volume", fill: palette.cyan }, "Momentum"],
["BANKNIFTY", { text: "Call wall near", fill: palette.red }, "Bearish"],
["HDFCBANK", { text: "Clustered walls", fill: palette.amber }, "Compression"],
["INFY", { text: "No breakout", fill: palette.muted }, "Neutral"],
]))}`
});

files.push({
  name: "03-volume-spike-tracker.svg",
  title: "Volume Spike Tracker",
  body: `${panel(56, 150, 420, 690, "Tracker Controls",
`<rect x="80" y="206" rx="16" width="372" height="60" fill="${palette.panel2}" stroke="${palette.line}"/>
<text x="100" y="244" fill="${palette.text}" font-size="18" font-family="Arial">Watchlist: NIFTY50 Momentum</text>
<rect x="80" y="286" rx="16" width="176" height="54" fill="${palette.panel2}" stroke="${palette.line}"/>
<text x="100" y="320" fill="${palette.text}" font-size="18" font-family="Arial">Lookback: 10</text>
<rect x="276" y="286" rx="16" width="176" height="54" fill="${palette.panel2}" stroke="${palette.line}"/>
<text x="296" y="320" fill="${palette.text}" font-size="18" font-family="Arial">Interval: 5m</text>
<rect x="80" y="360" rx="16" width="190" height="48" fill="${palette.cyan}"/>
<text x="116" y="390" fill="#082132" font-size="18" font-weight="700" font-family="Arial">Run Tracker</text>
<text x="82" y="470" fill="${palette.muted}" font-size="18" font-family="Arial">What makes it useful</text>
<text x="82" y="510" fill="${palette.text}" font-size="19" font-family="Arial">• Highest abnormal volume</text>
<text x="82" y="544" fill="${palette.text}" font-size="19" font-family="Arial">• Same-slot comparison</text>
<text x="82" y="578" fill="${palette.text}" font-size="19" font-family="Arial">• Watchlist-first workflow</text>
<text x="82" y="612" fill="${palette.text}" font-size="19" font-family="Arial">• Easy user alerts</text>`)}
${panel(504, 150, 1040, 690, "Ranked Live Spikes",
table(530, 206, 988, 72, ["symbol", "candle_time", "current_volume", "average_volume", "volume_ratio"], [
["ADANIENT", "2026-04-09 09:30 IST", "4,230,000", "1,040,000", { text: "4.06", fill: palette.cyan }],
["ABB", "2026-04-09 09:30 IST", "2,870,000", "920,000", { text: "3.12", fill: palette.green }],
["RELIANCE", "2026-04-09 09:30 IST", "8,540,000", "3,330,000", { text: "2.56", fill: palette.amber }],
["TCS", "2026-04-09 09:30 IST", "1,210,000", "540,000", { text: "2.24", fill: palette.blue }],
]) + `<text x="530" y="612" fill="${palette.muted}" font-size="16" font-family="Arial">Promote only meaningful spikes, not absolute volume leaders alone.</text>${bars(540, 650, [0.93,0.72,0.58,0.51,0.46,0.42,0.38], [palette.cyan, palette.blue, palette.amber, palette.green], 720, 120)}`)}`
});

files.push({
  name: "04-breakout-confirmation.svg",
  title: "Breakout Confirmation",
  body: `${metric(56, 150, 260, 104, "Selected", "RELIANCE", palette.text)}
${metric(334, 150, 260, 104, "Volume ratio", "2.56x", palette.cyan)}
${metric(612, 150, 260, 104, "Price status", "Above high", palette.green)}
${metric(890, 150, 260, 104, "Wall bias", "PUT support", palette.amber)}
${metric(1168, 150, 260, 104, "Signal grade", "A-", palette.blue)}
${panel(56, 290, 930, 548, "Signal Chart",
`<rect x="84" y="338" rx="18" width="874" height="450" fill="${palette.panel2}" stroke="${palette.line}"/>
${spark(110, 408, [42,44,43,45,47,46,49,52,55,58,56,61,64,66], palette.blue, 780, 240)}
<line x1="172" y1="620" x2="870" y2="620" stroke="${palette.red}" stroke-dasharray="10 10"/>
<line x1="172" y1="674" x2="870" y2="674" stroke="${palette.green}" stroke-dasharray="10 10"/>
<text x="880" y="624" fill="${palette.red}" font-size="16" font-family="Arial">Call wall</text>
<text x="880" y="678" fill="${palette.green}" font-size="16" font-family="Arial">Put wall</text>
${bars(126, 690, [0.25,0.35,0.32,0.44,0.61,0.48,0.67,0.74,0.69,0.82], [palette.cyan], 700, 70)}`)}
${panel(1018, 290, 526, 548, "Decision Card",
`<text x="1042" y="350" fill="${palette.text}" font-size="20" font-family="Arial">• Volume is far above normal baseline</text>
<text x="1042" y="398" fill="${palette.text}" font-size="20" font-family="Arial">• Price is clearing a recent high</text>
<text x="1042" y="446" fill="${palette.text}" font-size="20" font-family="Arial">• Nearest dominant wall is supportive</text>
<text x="1042" y="520" fill="${palette.cyan}" font-size="24" font-weight="700" font-family="Arial">This is the key “useful” page for users.</text>
<rect x="1042" y="586" rx="16" width="206" height="48" fill="${palette.cyan}"/>
<text x="1090" y="616" fill="#082132" font-size="18" font-weight="700" font-family="Arial">Add Alert</text>`)}`
});

files.push({
  name: "05-oi-walls-summary.svg",
  title: "OI Walls Summary",
  body: `${panel(56, 150, 470, 690, "Scanner Controls",
`<rect x="80" y="200" rx="16" width="422" height="64" fill="${palette.panel2}" stroke="${palette.line}"/>
<text x="100" y="238" fill="${palette.text}" font-size="20" font-family="Arial">Symbols: NIFTY, BANKNIFTY, RELIANCE, HDFCBANK</text>
<rect x="80" y="286" rx="16" width="202" height="56" fill="${palette.panel2}" stroke="${palette.line}"/>
<text x="100" y="320" fill="${palette.text}" font-size="18" font-family="Arial">Exchange: NSE</text>
<rect x="300" y="286" rx="16" width="202" height="56" fill="${palette.panel2}" stroke="${palette.line}"/>
<text x="320" y="320" fill="${palette.text}" font-size="18" font-family="Arial">Normalize: Off</text>
<rect x="80" y="364" rx="16" width="170" height="48" fill="${palette.cyan}"/>
<text x="110" y="394" fill="#082132" font-size="18" font-weight="700" font-family="Arial">Run Scan</text>`)}
${panel(556, 150, 988, 690, "Result Grid",
table(580, 208, 940, 88, ["Stock", "LTP", "Wall Type", "Wall Strike", "Strength", "Proximity", "Bias"], [
["NIFTY", "24,180.15", { text: "PUT", fill: palette.green }, "24,100", "7.2 L", "0.33%", "Bullish"],
["BANKNIFTY", "53,460.45", { text: "CALL", fill: palette.red }, "53,500", "9.8 L", "0.07%", "Bearish"],
["RELIANCE", "2,987.40", { text: "PUT", fill: palette.green }, "2,950", "4.1 L", "1.25%", "Bullish"],
["HDFCBANK", "1,715.20", { text: "CALL", fill: palette.red }, "1,720", "3.7 L", "0.28%", "Bearish"],
["INFY", "1,546.10", { text: "PUT", fill: palette.green }, "1,540", "2.8 L", "0.39%", "Bullish"],
]))}`
});

files.push({
  name: "06-multi-wall-explorer.svg",
  title: "Multi-Wall Explorer",
  body: `${metric(56, 150, 260, 104, "Selected symbol", "BANKNIFTY", palette.text)}
${metric(334, 150, 260, 104, "Current LTP", "53,460.45", palette.blue)}
${metric(612, 150, 260, 104, "Nearest wall", "CALL 53,500", palette.red)}
${metric(890, 150, 260, 104, "Cluster spread", "0.78%", palette.amber)}
${metric(1168, 150, 260, 104, "Expiry", "2026-04-30", palette.cyan)}
${panel(56, 290, 746, 550, "Wall Ladder",
table(84, 340, 690, 72, ["symbol", "ltp", "wall_side", "rank", "strike", "oi", "dist_pct", "selected"], [
["BANKNIFTY", "53460.45", { text: "CALL", fill: palette.red }, "1", "53500", "9.8 L", "0.07", "yes"],
["BANKNIFTY", "53460.45", { text: "PUT", fill: palette.green }, "1", "53300", "8.9 L", "0.30", "no"],
["BANKNIFTY", "53460.45", { text: "CALL", fill: palette.red }, "2", "53600", "7.1 L", "0.26", "no"],
["BANKNIFTY", "53460.45", { text: "PUT", fill: palette.green }, "2", "53200", "6.8 L", "0.49", "no"],
]))}
${panel(832, 290, 712, 550, "Visual Context",
`<rect x="860" y="342" rx="18" width="656" height="192" fill="${palette.panel2}" stroke="${palette.line}"/>
<line x1="900" y1="438" x2="1476" y2="438" stroke="${palette.line}" stroke-width="2"/>
<rect x="1110" y="386" width="22" height="104" rx="10" fill="${palette.red}"/>
<rect x="1022" y="402" width="22" height="88" rx="10" fill="${palette.amber}"/>
<rect x="938" y="420" width="22" height="70" rx="10" fill="${palette.green}"/>
<line x1="1160" y1="360" x2="1160" y2="500" stroke="${palette.blue}" stroke-dasharray="8 8"/>
<text x="1130" y="352" fill="${palette.blue}" font-size="15" font-family="Arial">LTP</text>`)}`
});

files.push({
  name: "07-symbol-drilldown.svg",
  title: "Symbol Drilldown",
  body: `<rect x="56" y="150" rx="26" width="1488" height="110" fill="url(#hero)"/>
<text x="88" y="214" fill="${palette.white}" font-size="38" font-weight="700" font-family="Arial">RELIANCE</text>
<text x="320" y="214" fill="${palette.text}" font-size="24" font-family="Arial">Bullish wall bias with 2.56x volume and price near breakout zone</text>
${panel(56, 292, 930, 548, "Price + Signal Overlay",
`<rect x="84" y="338" rx="18" width="874" height="450" fill="${palette.panel2}" stroke="${palette.line}"/>
${spark(110, 408, [42,44,43,45,47,46,49,52,55,58,56,61,64,66], palette.blue, 780, 240)}
${bars(126, 690, [0.25,0.35,0.32,0.44,0.61,0.48,0.67,0.74,0.69,0.82], [palette.cyan], 700, 70)}`)}
${panel(1018, 292, 526, 548,
"Story Card",
`<text x="1042" y="350" fill="${palette.text}" font-size="20" font-family="Arial">• Supportive wall below spot</text>
<text x="1042" y="398" fill="${palette.text}" font-size="20" font-family="Arial">• Stronger-than-normal participation</text>
<text x="1042" y="446" fill="${palette.text}" font-size="20" font-family="Arial">• Clear user narrative in plain English</text>
<text x="1042" y="520" fill="${palette.cyan}" font-size="24" font-weight="700" font-family="Arial">Best demo screen for stakeholders.</text>`)}`
});

files.push({
  name: "08-live-watchlist.svg",
  title: "Live Watchlist and Alerts",
  body: `${panel(56, 150, 540, 690, "Watchlist Setup",
`<rect x="80" y="250" rx="16" width="490" height="58" fill="${palette.panel2}" stroke="${palette.line}"/>
<text x="100" y="287" fill="${palette.text}" font-size="18" font-family="Arial">Symbols: NIFTY, RELIANCE, HDFCBANK, INFY, TCS</text>
<rect x="80" y="334" rx="16" width="230" height="48" fill="${palette.cyan}"/>
<text x="124" y="364" fill="#082132" font-size="18" font-weight="700" font-family="Arial">Save Watchlist</text>
<rect x="80" y="430" rx="20" width="490" height="370" fill="${palette.panel2}" stroke="${palette.line}"/>
<text x="106" y="518" fill="${palette.text}" font-size="20" font-family="Arial">• Wall proximity &lt; 0.50%</text>
<text x="106" y="560" fill="${palette.text}" font-size="20" font-family="Arial">• volume_ratio &gt; 2.00</text>
<text x="106" y="602" fill="${palette.text}" font-size="20" font-family="Arial">• Bullish + breakout alignment</text>`)}
${panel(628, 150, 916, 690, "Alert Feed",
table(652, 206, 868, 74, ["Time", "Symbol", "Alert", "Priority"], [
["09:31", "NIFTY", "Put wall within 0.33%", { text: "High", fill: palette.green }],
["09:33", "RELIANCE", "Volume ratio crossed 2.5x", { text: "High", fill: palette.cyan }],
["09:35", "BANKNIFTY", "Call wall tightening", { text: "Medium", fill: palette.amber }],
["09:38", "HDFCBANK", "Support cluster", { text: "Watch", fill: palette.blue }],
["09:41", "INFY", "Signal faded", { text: "Low", fill: palette.muted }],
]))}`
});

files.push({
  name: "09-comparison-lab.svg",
  title: "Comparison Lab",
  body: `${panel(56, 150, 1488, 690, "Cross-Symbol Comparison",
`<text x="80" y="204" fill="${palette.text}" font-size="22" font-family="Arial">Compare wall distance, breakout ratio, and signal quality across a basket.</text>
${metric(84, 242, 220, 96, "Symbols", "6", palette.text)}
${metric(324, 242, 220, 96, "Bullish", "4", palette.green)}
${metric(564, 242, 220, 96, "Bearish", "2", palette.red)}
${metric(804, 242, 220, 96, "Avg ratio", "2.14x", palette.cyan)}
${metric(1044, 242, 220, 96, "Closest wall", "BANKNIFTY", palette.amber)}
${metric(1284, 242, 220, 96, "Best combo", "RELIANCE", palette.blue)}
<rect x="84" y="374" rx="18" width="680" height="404" fill="${palette.panel2}" stroke="${palette.line}"/>
<rect x="796" y="374" rx="18" width="720" height="404" fill="${palette.panel2}" stroke="${palette.line}"/>
${bars(118, 468, [0.78,0.62,0.54,0.47,0.38,0.29], [palette.green, palette.red, palette.cyan, palette.amber], 610, 200)}
${spark(830, 438, [18,22,25,24,29,31,35,37,41,40,46,44], palette.blue, 610, 160)}`)}`
});

files.push({
  name: "10-hosting-and-access.svg",
  title: "Hosting and Access Strategy",
  body: `${panel(56, 150, 472, 690, "Option A: Demo Mode",
`<text x="80" y="210" fill="${palette.text}" font-size="20" font-family="Arial">Shared read-only showcase using Streamlit secrets.</text>
<text x="80" y="262" fill="${palette.text}" font-size="19" font-family="Arial">1. App owner stores Nubra credentials</text>
<text x="80" y="304" fill="${palette.text}" font-size="19" font-family="Arial">2. Visitors use the app immediately</text>
<text x="80" y="346" fill="${palette.text}" font-size="19" font-family="Arial">3. Fastest path to launch</text>
<text x="80" y="430" fill="${palette.cyan}" font-size="28" font-weight="700" font-family="Arial">Recommended phase 1</text>`)}
${panel(564, 150, 472, 690, "Option B: Bring Your Own Nubra Session",
`<text x="588" y="210" fill="${palette.text}" font-size="20" font-family="Arial">User enters credentials for that session only.</text>
<text x="588" y="262" fill="${palette.text}" font-size="19" font-family="Arial">1. Better user isolation</text>
<text x="588" y="304" fill="${palette.text}" font-size="19" font-family="Arial">2. More UX friction</text>
<text x="588" y="346" fill="${palette.text}" font-size="19" font-family="Arial">3. Good second-phase feature</text>`)}
${panel(1072, 150, 472, 690, "Option C: App Login",
`<text x="1096" y="210" fill="${palette.text}" font-size="20" font-family="Arial">Use Streamlit OIDC only to gate access.</text>
<text x="1096" y="262" fill="${palette.text}" font-size="19" font-family="Arial">1. Great for internal or partner users</text>
<text x="1096" y="304" fill="${palette.text}" font-size="19" font-family="Arial">2. Nubra auth still separate</text>
<text x="1096" y="346" fill="${palette.text}" font-size="19" font-family="Arial">3. Good if you want a private portal</text>`)}`
});

for (const file of files) {
  fs.writeFileSync(path.join(outDir, file.name), wrap(file.title, file.body), "utf8");
}

console.log(`Created ${files.length} mockups in ${outDir}`);
