import type { Map as MLMap } from "maplibre-gl";

// Each flag is drawn on a 20×13 "design grid"; each cell is PX×PX actual pixels.
// pixelRatio=PX tells MapLibre to treat the image as PX-density, so it renders at 20×13 CSS px.
const PX = 3;
const GW = 20;
const GH = 13;
const IW = GW * PX; // 60
const IH = GH * PX; // 39

type RGB = [number, number, number];

function hex(h: string): RGB {
  const n = parseInt(h.replace("#", ""), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

type FlagDef =
  | { t: "h3"; c: [string, string, string] }   // horizontal tricolor
  | { t: "v3"; c: [string, string, string] }   // vertical tricolor
  | { t: "h2"; c: [string, string] }            // horizontal bicolor
  | { t: "v2"; c: [string, string] }            // vertical bicolor
  | { t: "q4"; c: [string, string, string, string] } // 4 quadrants TL/TR/BL/BR
  | { t: "plain"; c: string }                   // solid color
  | { t: "circle"; bg: string; dot: string }   // solid bg + center ellipse (Japan, Palau…)
  | { t: "cross"; bg: string; cross: string }  // Nordic cross

// ISO 3166-1 alpha-3 → flag definition
const FLAGS: Record<string, FlagDef> = {
  // South America
  ARG: { t: "h3", c: ["#74acdf", "#ffffff", "#74acdf"] },
  URY: { t: "h3", c: ["#ffffff", "#74acdf", "#ffffff"] },
  BRA: { t: "plain", c: "#009c3b" },
  CHL: { t: "h2", c: ["#0039a6", "#d52b1e"] },
  PRY: { t: "h3", c: ["#d52b1e", "#ffffff", "#0038a8"] },
  BOL: { t: "h3", c: ["#d52b1e", "#f9e300", "#007a3d"] },
  COL: { t: "h3", c: ["#fcd116", "#003087", "#ce1126"] },
  VEN: { t: "h3", c: ["#cf142b", "#003087", "#009a44"] },
  ECU: { t: "h3", c: ["#ffda00", "#003087", "#ce1126"] },
  PER: { t: "v3", c: ["#d91023", "#ffffff", "#d91023"] },

  // Europe
  RUS: { t: "h3", c: ["#ffffff", "#0039a6", "#cc0000"] },
  DEU: { t: "h3", c: ["#000000", "#dd0000", "#ffce00"] },
  NLD: { t: "h3", c: ["#ae1c28", "#ffffff", "#21468b"] },
  ESP: { t: "h3", c: ["#aa151b", "#f1bf00", "#aa151b"] },
  GRC: { t: "h3", c: ["#0d5eaf", "#ffffff", "#0d5eaf"] },
  ITA: { t: "v3", c: ["#009246", "#ffffff", "#ce2b37"] },
  FRA: { t: "v3", c: ["#002395", "#ffffff", "#ed2939"] },
  PRT: { t: "v3", c: ["#006600", "#006600", "#ff0000"] },
  IRL: { t: "v3", c: ["#169b62", "#ffffff", "#ff883e"] },
  BEL: { t: "v3", c: ["#000000", "#fcd116", "#ef3340"] },
  LUX: { t: "h3", c: ["#ef3340", "#ffffff", "#00a1de"] },
  AUT: { t: "h3", c: ["#ed2939", "#ffffff", "#ed2939"] },
  CHE: { t: "plain", c: "#ff0000" },
  SRB: { t: "h3", c: ["#c6363c", "#0c4076", "#ffffff"] },
  HRV: { t: "h3", c: ["#ff0000", "#ffffff", "#0000ff"] },
  SVN: { t: "h3", c: ["#003da5", "#ffffff", "#dd1c1a"] },
  POL: { t: "h2", c: ["#ffffff", "#dc143c"] },
  CZE: { t: "v3", c: ["#003399", "#ffffff", "#cc0000"] },
  SVK: { t: "h3", c: ["#ffffff", "#0b4ea2", "#ee1c25"] },
  UKR: { t: "h2", c: ["#005bbb", "#ffd500"] },
  BLR: { t: "h2", c: ["#cf101a", "#009000"] },
  LTU: { t: "h3", c: ["#fdb913", "#006a44", "#c1272d"] },
  LVA: { t: "h3", c: ["#9e3039", "#ffffff", "#9e3039"] },
  EST: { t: "h3", c: ["#0072ce", "#000000", "#ffffff"] },
  NOR: { t: "cross", bg: "#ef2b2d", cross: "#002868" },
  SWE: { t: "cross", bg: "#006aa7", cross: "#fecc02" },
  FIN: { t: "cross", bg: "#ffffff", cross: "#003580" },
  DNK: { t: "cross", bg: "#c60c30", cross: "#ffffff" },
  ISL: { t: "cross", bg: "#003897", cross: "#dc1c2d" },
  GBR: { t: "plain", c: "#012169" },
  MLT: { t: "v2", c: ["#ffffff", "#cf142b"] },
  CYP: { t: "plain", c: "#ffffff" },
  MNE: { t: "plain", c: "#d4af37" },
  MKD: { t: "plain", c: "#ce2028" },
  ALB: { t: "plain", c: "#e41e20" },
  BIH: { t: "plain", c: "#002395" },
  ROU: { t: "v3", c: ["#002b7f", "#fcd116", "#ce1126"] },
  BGR: { t: "h3", c: ["#ffffff", "#00966e", "#d62612"] },
  HUN: { t: "h3", c: ["#ce2939", "#ffffff", "#477050"] },

  // North America & Caribbean
  USA: { t: "h2", c: ["#b22234", "#ffffff"] },
  CAN: { t: "v3", c: ["#ff0000", "#ffffff", "#ff0000"] },
  MEX: { t: "v3", c: ["#006847", "#ffffff", "#ce1126"] },
  CUB: { t: "h3", c: ["#002a8f", "#ffffff", "#cc0000"] },
  DOM: { t: "q4", c: ["#002d62", "#cf142b", "#cf142b", "#002d62"] },
  JAM: { t: "plain", c: "#000000" },
  HTI: { t: "h2", c: ["#00209f", "#d21034"] },
  TTO: { t: "plain", c: "#ce1126" },
  BRB: { t: "v3", c: ["#00267f", "#ffc726", "#00267f"] },
  BLZ: { t: "plain", c: "#003f87" },
  GTM: { t: "v3", c: ["#4997d0", "#ffffff", "#4997d0"] },
  HND: { t: "h3", c: ["#0073cf", "#ffffff", "#0073cf"] },
  CRI: { t: "h3", c: ["#002b7f", "#e60000", "#002b7f"] },
  NIC: { t: "h3", c: ["#1a48c3", "#ffffff", "#1a48c3"] },
  SLV: { t: "h3", c: ["#0f47af", "#ffffff", "#0f47af"] },
  PAN: { t: "q4", c: ["#ffffff", "#d21034", "#002395", "#ffffff"] },
  ATG: { t: "plain", c: "#ce1126" },
  VCT: { t: "v3", c: ["#009e60", "#f4d000", "#009e60"] },
  BHS: { t: "h3", c: ["#00778b", "#ffc72c", "#00778b"] },
  SGP: { t: "h2", c: ["#ef3340", "#ffffff"] },

  // Africa & Atlantic islands
  LBR: { t: "h2", c: ["#bf0a30", "#ffffff"] },
  GHA: { t: "h3", c: ["#006b3f", "#fcd116", "#ce1126"] },
  SEN: { t: "v3", c: ["#00853f", "#fdef42", "#e31b23"] },
  NGA: { t: "v3", c: ["#008751", "#ffffff", "#008751"] },
  CIV: { t: "v3", c: ["#f77f00", "#ffffff", "#009a44"] },
  CMR: { t: "v3", c: ["#007a5e", "#ce1126", "#fcd116"] },
  GAB: { t: "h3", c: ["#009e60", "#fcd116", "#003189"] },
  MOZ: { t: "h3", c: ["#009a44", "#ffffff", "#ffca28"] },
  AGO: { t: "h2", c: ["#cc0000", "#000000"] },
  ZAF: { t: "h3", c: ["#007a4d", "#000000", "#de3831"] },
  EGY: { t: "h3", c: ["#ce1126", "#ffffff", "#000000"] },
  MAR: { t: "plain", c: "#c1272d" },
  DZA: { t: "v2", c: ["#006233", "#ffffff"] },
  TUN: { t: "circle", bg: "#e70013", dot: "#ffffff" },

  // Pacific & Asia
  CHN: { t: "plain", c: "#de2910" },
  JPN: { t: "circle", bg: "#ffffff", dot: "#bc002d" },
  KOR: { t: "plain", c: "#ffffff" },
  TWN: { t: "plain", c: "#fe0000" },
  HKG: { t: "plain", c: "#de2110" },
  IDN: { t: "h2", c: ["#ce1126", "#ffffff"] },
  MYS: { t: "h2", c: ["#cc0001", "#ffffff"] },
  PHL: { t: "h2", c: ["#0038a8", "#ce1126"] },
  THA: { t: "h3", c: ["#a51931", "#ffffff", "#2d2a4a"] },
  VNM: { t: "plain", c: "#da251d" },
  MMR: { t: "h3", c: ["#fecb00", "#34b233", "#ea2839"] },
  IND: { t: "h3", c: ["#ff9933", "#ffffff", "#138808"] },
  BGD: { t: "circle", bg: "#006a4e", dot: "#f42a41" },
  PAK: { t: "plain", c: "#01411c" },
  AUS: { t: "plain", c: "#00008b" },
  NZL: { t: "plain", c: "#00008b" },

  // Pacific island registries (common vessel flags)
  MHL: { t: "plain", c: "#003893" },
  PLW: { t: "circle", bg: "#4aadd6", dot: "#ffde00" },
  FSM: { t: "plain", c: "#75b2dd" },
  KIR: { t: "plain", c: "#ce1126" },
  TUV: { t: "plain", c: "#009fca" },
  NRU: { t: "plain", c: "#002b7f" },
  COK: { t: "plain", c: "#012169" },
  TON: { t: "plain", c: "#c10000" },
  VUT: { t: "plain", c: "#009543" },
  WSM: { t: "plain", c: "#ce1126" },

  // Middle East
  SAU: { t: "plain", c: "#006c35" },
  ARE: { t: "v3", c: ["#00732f", "#ffffff", "#000000"] },
  IRN: { t: "h3", c: ["#239f40", "#ffffff", "#da0000"] },
  TUR: { t: "circle", bg: "#e30a17", dot: "#ffffff" },
  QAT: { t: "v2", c: ["#8d1b3d", "#ffffff"] },
  BHR: { t: "v2", c: ["#ce1126", "#ffffff"] },
  KWT: { t: "h3", c: ["#007a3d", "#ffffff", "#ce1126"] },
  ISR: { t: "h2", c: ["#ffffff", "#003399"] },
  JOR: { t: "h3", c: ["#007a3d", "#ffffff", "#000000"] },
};

function renderFlag(def: FlagDef): { width: number; height: number; data: Uint8ClampedArray } {
  const data = new Uint8ClampedArray(IW * IH * 4);

  const block = (gx: number, gy: number, rgb: RGB) => {
    for (let dy = 0; dy < PX; dy++) {
      for (let dx = 0; dx < PX; dx++) {
        const i = ((gy * PX + dy) * IW + (gx * PX + dx)) * 4;
        data[i] = rgb[0]; data[i + 1] = rgb[1]; data[i + 2] = rgb[2]; data[i + 3] = 255;
      }
    }
  };

  const fill = (gx0: number, gy0: number, gx1: number, gy1: number, color: string) => {
    const rgb = hex(color);
    for (let gy = gy0; gy < gy1; gy++)
      for (let gx = gx0; gx < gx1; gx++)
        block(gx, gy, rgb);
  };

  switch (def.t) {
    case "h3": {
      const h1 = Math.floor(GH / 3), h2 = Math.floor(2 * GH / 3);
      fill(0, 0, GW, h1, def.c[0]);
      fill(0, h1, GW, h2, def.c[1]);
      fill(0, h2, GW, GH, def.c[2]);
      break;
    }
    case "v3": {
      const w1 = Math.floor(GW / 3), w2 = Math.floor(2 * GW / 3);
      fill(0, 0, w1, GH, def.c[0]);
      fill(w1, 0, w2, GH, def.c[1]);
      fill(w2, 0, GW, GH, def.c[2]);
      break;
    }
    case "h2": {
      const h1 = Math.floor(GH / 2);
      fill(0, 0, GW, h1, def.c[0]);
      fill(0, h1, GW, GH, def.c[1]);
      break;
    }
    case "v2": {
      const w1 = Math.floor(GW / 2);
      fill(0, 0, w1, GH, def.c[0]);
      fill(w1, 0, GW, GH, def.c[1]);
      break;
    }
    case "q4": {
      const cx = Math.floor(GW / 2), cy = Math.floor(GH / 2);
      fill(0, 0, cx, cy, def.c[0]);
      fill(cx, 0, GW, cy, def.c[1]);
      fill(0, cy, cx, GH, def.c[2]);
      fill(cx, cy, GW, GH, def.c[3]);
      break;
    }
    case "plain":
      fill(0, 0, GW, GH, def.c);
      break;
    case "circle": {
      fill(0, 0, GW, GH, def.bg);
      const cx = Math.floor(GW / 2), cy = Math.floor(GH / 2);
      const rx = 4, ry = 3;
      const dotRgb = hex(def.dot);
      for (let gy = 0; gy < GH; gy++)
        for (let gx = 0; gx < GW; gx++) {
          const dx = gx - cx, dy = gy - cy;
          if ((dx * dx) / (rx * rx) + (dy * dy) / (ry * ry) <= 1) block(gx, gy, dotRgb);
        }
      break;
    }
    case "cross": {
      fill(0, 0, GW, GH, def.bg);
      const crossRgb = hex(def.cross);
      // Nordic cross: vertical bar slightly left of center, horizontal bar at mid
      const vx = 5, vy = Math.floor(GH / 2);
      for (let gy = 0; gy < GH; gy++)
        for (let gx = vx - 1; gx <= vx + 1; gx++)
          if (gx >= 0 && gx < GW) block(gx, gy, crossRgb);
      for (let gx = 0; gx < GW; gx++)
        for (let gy = vy - 1; gy <= vy + 1; gy++)
          if (gy >= 0 && gy < GH) block(gx, gy, crossRgb);
      break;
    }
  }

  // 1-pixel black border
  const black: RGB = [0, 0, 0];
  for (let gx = 0; gx < GW; gx++) { block(gx, 0, black); block(gx, GH - 1, black); }
  for (let gy = 0; gy < GH; gy++) { block(0, gy, black); block(GW - 1, gy, black); }

  return { width: IW, height: IH, data };
}

export function registerFlagImages(map: MLMap) {
  for (const [code, def] of Object.entries(FLAGS)) {
    const id = `flag-${code}`;
    if (!map.hasImage(id)) {
      map.addImage(id, renderFlag(def), { pixelRatio: PX });
    }
  }
}
