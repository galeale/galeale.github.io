/* Teaching and public-engagement helpers shared by the homepage and their own pages. */
var Sections = (function () {
  var NS = 'http://www.w3.org/2000/svg';
  var INST = [
    { match: 'Padova', label: 'University of Padova', color: '#3B6FD6' },
    { match: 'Ca’ Foscari', label: 'Ca’ Foscari Venice', color: '#C9741C' },
    { match: 'Polish-Japanese', label: 'PJAIT Warsaw', color: '#22936A' }
  ];
  var GROUPS = [
    { id: 'talks', label: 'Talks for the public', color: '#3B6FD6' },
    { id: 'press', label: 'In the press', color: '#C9741C' },
    { id: 'policy', label: 'Policy and impact', color: '#22936A' }
  ];
  function mk(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text) e.textContent = text; return e; }
  function svg(tag, attrs, parent) { var e = document.createElementNS(NS, tag); for (var k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
  function inst(c) { for (var i = 0; i < INST.length; i++) if (c.institution.indexOf(INST[i].match) > -1) return i; return 0; }

  function courses(ul, list) {
    list.forEach(function (c) {
      var li = mk('li', 'course'), main = mk('div', 'cm');
      main.appendChild(mk('span', 'cn', c.course));
      main.appendChild(mk('span', 'cw', [c.programme, c.institution].filter(Boolean).join(' · ')));
      li.appendChild(main);
      li.appendChild(mk('span', 'cr', c.role + (c.hours ? ', ' + c.hours + ' h' : '')));
      var yrs = mk('span', 'cy'); c.years.forEach(function (y) { yrs.appendChild(mk('span', 'yr', y)); });
      li.appendChild(yrs); ul.appendChild(li);
    });
  }

  /* stacked bars: teaching hours per academic year, by institution */
  function teachingChart(box, list) {
    var years = {};
    list.forEach(function (c) { if (!c.hours) return; c.years.forEach(function (y) { (years[y] = years[y] || [0, 0, 0])[inst(c)] += c.hours; }); });
    var ys = Object.keys(years).sort();
    var max = Math.max.apply(null, ys.map(function (y) { return years[y].reduce(function (a, b) { return a + b; }, 0); }));
    var top = Math.ceil(max / 30) * 30, Wd = 480, Ht = 250, L = 34, R = 10, T = 22, B = 30;
    var s = svg('svg', { viewBox: '0 0 ' + Wd + ' ' + Ht, role: 'img', 'aria-label': 'Teaching hours per academic year: ' + ys.map(function (y) { return y + ' ' + years[y].reduce(function (a, b) { return a + b; }, 0) + ' hours'; }).join(', ') }, null);
    var yScale = function (v) { return T + (Ht - T - B) * (1 - v / top); };
    for (var g = 0; g <= top; g += 30) {
      svg('line', { x1: L, x2: Wd - R, y1: yScale(g), y2: yScale(g), stroke: '#E2E8F0', 'stroke-width': 1 }, s);
      var t = svg('text', { x: L - 6, y: yScale(g) + 4, 'text-anchor': 'end', 'font-size': 11, fill: '#64748B', 'font-family': 'IBM Plex Mono, monospace' }, s); t.textContent = g;
    }
    var slot = (Wd - L - R) / ys.length, bw = Math.min(46, slot * 0.5);
    ys.forEach(function (y, i) {
      var x = L + slot * i + (slot - bw) / 2, acc = 0, tot = years[y].reduce(function (a, b) { return a + b; }, 0);
      var segs = years[y].map(function (h, k) { return { h: h, k: k }; }).filter(function (d) { return d.h > 0; });
      segs.forEach(function (d, j) {
        var y0 = yScale(acc), y1 = yScale(acc + d.h); acc += d.h;
        var last = j === segs.length - 1, h = y0 - y1 - (j ? 2 : 0);
        var r = svg('path', { d: last ? roundTop(x, y1, bw, h, 4) : 'M' + x + ' ' + y1 + 'h' + bw + 'v' + h + 'h' + -bw + 'z', fill: INST[d.k].color }, s);
        svg('title', {}, r).textContent = y + ' · ' + INST[d.k].label + ': ' + d.h + ' h';
      });
      var lab = svg('text', { x: x + bw / 2, y: yScale(tot) - 6, 'text-anchor': 'middle', 'font-size': 12, 'font-weight': 600, fill: '#0F172A', 'font-family': 'IBM Plex Sans, sans-serif' }, s); lab.textContent = tot + ' h';
      var yl = svg('text', { x: x + bw / 2, y: Ht - 10, 'text-anchor': 'middle', 'font-size': 12, fill: '#475569', 'font-family': 'IBM Plex Mono, monospace' }, s); yl.textContent = y;
    });
    box.appendChild(s);
    var leg = mk('div', 'chart-legend');
    INST.forEach(function (it) { var sp = mk('span'); var k = mk('i'); k.style.background = it.color; sp.appendChild(k); sp.appendChild(document.createTextNode(it.label)); leg.appendChild(sp); });
    box.appendChild(leg);
  }
  function roundTop(x, y, w, h, r) {
    r = Math.min(r, h, w / 2);
    return 'M' + x + ' ' + (y + h) + 'V' + (y + r) + 'Q' + x + ' ' + y + ' ' + (x + r) + ' ' + y + 'H' + (x + w - r) + 'Q' + (x + w) + ' ' + y + ' ' + (x + w) + ' ' + (y + r) + 'V' + (y + h) + 'Z';
  }

  function engagementList(box, items, group) {
    items.filter(function (it) { return it.group === group; }).forEach(function (it) {
      var row = mk('div', 'talk');
      row.appendChild(mk('span', 'd', it.date || ''));
      var t = mk(it.url ? 'a' : 'span', 'tt', it.title); if (it.url) t.href = it.url;
      if (it.where) t.appendChild(mk('span', 'w', it.where));
      row.appendChild(t); box.appendChild(row);
    });
  }

  /* dot timeline: one dot per dated item, a row per kind */
  function engagementTimeline(box, items) {
    var dated = items.filter(function (it) { return /^\d{4}$/.test(it.date); });
    var yrs = dated.map(function (it) { return +it.date; });
    var y0 = Math.min.apply(null, yrs), y1 = Math.max.apply(null, yrs);
    var Wd = 480, rowH = 52, L = 8, T = 10, Ht = T + rowH * GROUPS.length + 26, colW = (Wd - L - 8) / (y1 - y0 + 1);
    var s = svg('svg', { viewBox: '0 0 ' + Wd + ' ' + Ht, role: 'img', 'aria-label': 'Public engagement per year: ' + GROUPS.map(function (g) { return dated.filter(function (it) { return it.group === g.id; }).length + ' ' + g.label.toLowerCase(); }).join(', ') });
    GROUPS.forEach(function (g, r) {
      var cy = T + rowH * r + rowH / 2;
      svg('line', { x1: L, x2: Wd - 8, y1: cy, y2: cy, stroke: '#E2E8F0', 'stroke-width': 1 }, s);
      for (var y = y0; y <= y1; y++) {
        var here = dated.filter(function (it) { return it.group === g.id && +it.date === y; });
        here.forEach(function (it, k) {
          var cx = L + colW * (y - y0) + colW / 2 + (k - (here.length - 1) / 2) * 14;
          var c = svg('circle', { cx: cx, cy: cy, r: 5.5, fill: g.color, stroke: '#FFFFFF', 'stroke-width': 2 }, s);
          svg('title', {}, c).textContent = it.date + ' · ' + it.title + (it.where ? ' (' + it.where + ')' : '');
        });
      }
    });
    for (var y = y0; y <= y1; y++) {
      var t = svg('text', { x: L + colW * (y - y0) + colW / 2, y: Ht - 6, 'text-anchor': 'middle', 'font-size': 12, fill: '#475569', 'font-family': 'IBM Plex Mono, monospace' }, s); t.textContent = y;
    }
    box.appendChild(s);
    var leg = mk('div', 'chart-legend');
    GROUPS.forEach(function (g) { var sp = mk('span'); var k = mk('i'); k.style.background = g.color; k.style.borderRadius = '50%'; sp.appendChild(k); sp.appendChild(document.createTextNode(g.label)); leg.appendChild(sp); });
    box.appendChild(leg);
  }

  return { courses: courses, teachingChart: teachingChart, engagementList: engagementList, engagementTimeline: engagementTimeline, GROUPS: GROUPS };
})();
