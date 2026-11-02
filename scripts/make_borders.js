// Natural Earth 50m (via world-atlas): country borders + coastlines, clipped to a box, as encoded polylines.
const topo = require('topojson-client');
const world = require('world-atlas/countries-50m.json');
const [LAT0, LAT1, LON0, LON1] = [30, 62, -20, 40];   // Europe & Mediterranean (San Diego etc. stay without borders)
function encode(coords) {
  let out = '', plat = 0, plon = 0;
  for (const [lon, lat] of coords) {
    const ilat = Math.round(lat * 1e5), ilon = Math.round(lon * 1e5);
    for (let v of [ilat - plat, ilon - plon]) {
      v = v < 0 ? ~(v << 1) : (v << 1);
      while (v >= 0x20) { out += String.fromCharCode((0x20 | (v & 0x1f)) + 63); v >>= 5; }
      out += String.fromCharCode(v + 63);
    }
    plat = ilat; plon = ilon;
  }
  return out;
}
function clip(lines) {
  const res = [];
  for (const line of lines) {
    let cur = [];
    for (const p of line) {
      const inside = p[1] >= LAT0 && p[1] <= LAT1 && p[0] >= LON0 && p[0] <= LON1;
      if (inside) cur.push(p); else { if (cur.length > 1) res.push(cur); cur = []; }
    }
    if (cur.length > 1) res.push(cur);
  }
  return res;
}
const obj = world.objects.countries;
const borders = topo.mesh(world, obj, (a, b) => a !== b).coordinates;
const coast = topo.mesh(world, obj, (a, b) => a === b).coordinates;
const out = { source: 'Natural Earth 1:50m via world-atlas', borders: clip(borders).map(encode), coast: clip(coast).map(encode) };
require('fs').writeFileSync(process.argv[2], JSON.stringify(out));
console.log('borders', out.borders.length, 'coast', out.coast.length, 'bytes', JSON.stringify(out).length);
