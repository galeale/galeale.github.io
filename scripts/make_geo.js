// Map background for cycling.html: world borders + coastlines (Natural Earth) and the towns near my rides (GeoNames).
// Usage, from the repository root:
//   npm install world-atlas@2.0.2 topojson-client@3.1.0 all-the-cities@3.1.0
//   node scripts/make_geo.js
// Writes data/borders.json and data/places.json; also private/cities1000.json for build_trips.py.
const fs = require('fs');
const topo = require('topojson-client');
const cities = require('all-the-cities');

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
function decode(str) {
  let i = 0, lat = 0, lon = 0; const out = [];
  while (i < str.length) {
    for (let k = 0; k < 2; k++) {
      let b, shift = 0, res = 0;
      do { b = str.charCodeAt(i++) - 63; res |= (b & 0x1f) << shift; shift += 5; } while (b >= 0x20);
      const v = (res & 1) ? ~(res >> 1) : (res >> 1);
      if (k === 0) lat += v; else lon += v;
    }
    out.push([lat / 1e5, lon / 1e5]);
  }
  return out;
}

// --- borders: whole world at 1:110m, Europe and the Mediterranean at 1:50m
const w110 = require('world-atlas/countries-110m.json'), w50 = require('world-atlas/countries-50m.json');
const BOX = [34, 62, -12, 32]; // lat0, lat1, lon0, lon1 covered at 1:50m
const inBox = p => p[1] >= BOX[0] && p[1] <= BOX[1] && p[0] >= BOX[2] && p[0] <= BOX[3];
function split(lines, keepInside) {
  const res = [];
  for (const line of lines) {
    let cur = [];
    for (const p of line) {
      if (inBox(p) === keepInside) cur.push(p);
      else { if (cur.length > 1) res.push(cur); cur = keepInside ? [] : [p]; }
    }
    if (cur.length > 1) res.push(cur);
  }
  return res;
}
const mesh = (w, f) => topo.mesh(w, w.objects.countries, f).coordinates;
const out = {
  source: 'Natural Earth (1:110m world, 1:50m Europe) via world-atlas',
  borders: [...split(mesh(w110, (a, b) => a !== b), false), ...split(mesh(w50, (a, b) => a !== b), true)].map(encode),
  coast: [...split(mesh(w110, (a, b) => a === b), false), ...split(mesh(w50, (a, b) => a === b), true)].map(encode),
};
fs.writeFileSync('data/borders.json', JSON.stringify(out));

// --- towns within 10 km of any ride, ranked by population for the zoom-dependent labels
const D = JSON.parse(fs.readFileSync('data/cycling-data.json', 'utf8'));
const cell = 0.1, grid = new Set();
for (const k of ['commute', 'conference', 'other']) {
  for (const t of D.tracks[k]) for (const [la, lo] of decode(typeof t === 'string' ? t : t.p)) {
    for (let a = -1; a <= 1; a++) for (let b = -1; b <= 1; b++) grid.add(Math.floor(la / cell + a) + ':' + Math.floor(lo / cell + b));
  }
}
const near = c => grid.has(Math.floor(c.loc.coordinates[1] / cell) + ':' + Math.floor(c.loc.coordinates[0] / cell));
const tier = p => p >= 500000 ? 1 : p >= 100000 ? 2 : p >= 30000 ? 3 : 4;
const places = cities.filter(c => c.population >= 8000 && c.featureCode !== 'PPLX' && near(c))
  .sort((a, b) => b.population - a.population)
  .map(c => [c.name, +c.loc.coordinates[1].toFixed(3), +c.loc.coordinates[0].toFixed(3), tier(c.population)]);
fs.writeFileSync('data/places.json', JSON.stringify(places));
fs.mkdirSync('private', { recursive: true });
fs.writeFileSync('private/cities1000.json', JSON.stringify(cities.filter(x => x.population >= 1000)
  .map(x => [x.name, +x.loc.coordinates[1].toFixed(4), +x.loc.coordinates[0].toFixed(4), x.population, x.featureCode, x.country])));
console.log('borders', out.borders.length, 'coast', out.coast.length, 'bytes', JSON.stringify(out).length, '| places', places.length,
  'tiers', [1, 2, 3, 4].map(t => places.filter(p => p[3] === t).length));
