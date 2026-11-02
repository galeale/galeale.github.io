/* Draggable force-directed network of papers. Data: data/papers.json + data/citations.csv. */
(function () {
  var NS = 'http://www.w3.org/2000/svg';
  var graph = document.getElementById('graph'), svg = document.getElementById('svg'), tip = document.getElementById('tip');
  var VW = 1000, aspect = 0.5, alpha = 0.6, drag = null, running = false;
  var P, E, T = {}, N = [], sel = 0, theme = null, els = {};

  function el(tag, attrs, parent) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function parseCSV(text) {
    var out = {}, lines = text.split(/\r?\n/).slice(1);
    lines.forEach(function (l) { var m = l.match(/^([^,]+),(\d*)/); if (m && m[2]) out[m[1]] = +m[2]; });
    return out;
  }
  function radius(p) { return (14 + 6 * Math.log10(p.c || 12)) / 2; }

  function tick(a) {
    var VH = VW * aspect, i, j, A, B, dx, dy, d2, d, f, min;
    for (i = 0; i < N.length; i++) {
      A = N[i];
      for (j = i + 1; j < N.length; j++) {
        B = N[j]; dx = B.x - A.x; dy = B.y - A.y; d2 = dx * dx + dy * dy;
        if (d2 < 1) { dx = 0.5; dy = 0.5; d2 = 0.5; }
        d = Math.sqrt(d2); f = 70 * a / d;
        A.vx -= dx / d * f; A.vy -= dy / d * f; B.vx += dx / d * f; B.vy += dy / d * f;
        min = A.r + B.r + 4;
        if (d < min) { var push = (min - d) / d * 0.35; A.x -= dx * push; A.y -= dy * push; B.x += dx * push; B.y += dy * push; }
      }
    }
    E.forEach(function (e) {
      A = N[e[0]]; B = N[e[1]]; dx = B.x - A.x; dy = B.y - A.y; d = Math.sqrt(dx * dx + dy * dy) || 1;
      var L = e[3] ? 170 : 55, s = e[3] ? 0.02 : 0.06 + 0.25 * e[2], k = (d - L) / d * a * s;
      A.vx += dx * k; A.vy += dy * k; B.vx -= dx * k; B.vy -= dy * k;
    });
    for (i = 0; i < N.length; i++) {
      A = N[i]; var t = T[P[i].theme];
      A.vx += (t.ax * VW - A.x) * 0.035 * a; A.vy += (t.ay * VH - A.y) * 0.035 * a;
      if (A.fx !== null) { A.x = A.fx; A.y = A.fy; A.vx = A.vy = 0; continue; }
      A.vx *= 0.6; A.vy *= 0.6; A.x += A.vx; A.y += A.vy;
      A.x = Math.max(A.r + 6, Math.min(VW - A.r - 6, A.x));
      A.y = Math.max(A.r + 6, Math.min(VH - A.r - 6, A.y));
    }
  }

  function render() {
    E.forEach(function (e, i) {
      var l = els.edges[i], A = N[e[0]], B = N[e[1]];
      l.setAttribute('x1', A.x); l.setAttribute('y1', A.y); l.setAttribute('x2', B.x); l.setAttribute('y2', B.y);
    });
    N.forEach(function (n, i) { els.nodes[i].setAttribute('transform', 'translate(' + n.x.toFixed(1) + ' ' + n.y.toFixed(1) + ')'); });
    var VH = VW * aspect;
    els.labels.forEach(function (lab) {
      var sx = 0, c = 0, top = 1e9;
      P.forEach(function (p, i) { if (p.theme === lab.id) { sx += N[i].x; c++; top = Math.min(top, N[i].y - N[i].r); } });
      lab.el.setAttribute('x', Math.max(110, Math.min(VW - 110, sx / c)));
      lab.el.setAttribute('y', Math.max(16, top - 14));
    });
    if (!tip.hidden && tip._i !== undefined) placeTip(tip._i);
  }

  function styleAll() {
    E.forEach(function (e, i) {
      var l = els.edges[i], pa = P[e[0]], pb = P[e[1]];
      var touch = sel === e[0] || sel === e[1];
      var dim = theme && pa.theme !== theme && pb.theme !== theme;
      l.setAttribute('stroke', e[3] ? (touch ? '#E2E8F0' : '#64748B') : T[pa.theme].color);
      l.setAttribute('stroke-width', e[3] ? 1.5 : (1 + 2.5 * e[2]).toFixed(1));
      if (e[3]) l.setAttribute('stroke-dasharray', '5 5');
      l.setAttribute('opacity', dim ? 0.08 : (touch ? 0.95 : (e[3] ? 0.7 : 0.4)));
    });
    P.forEach(function (p, i) {
      var g = els.nodes[i], t = T[p.theme];
      g.setAttribute('opacity', !theme || theme === p.theme ? 1 : 0.18);
      g._ring.setAttribute('stroke', sel === i ? '#F8FAFC' : 'none');
    });
    els.labels.forEach(function (lab) { lab.el.setAttribute('opacity', theme && theme !== lab.id ? 0.2 : 0.9); });
    var bs = document.querySelectorAll('#legend button');
    bs.forEach(function (b) { b.setAttribute('aria-pressed', String((b.dataset.theme || null) === theme)); });
    var p = P[sel], t = T[p.theme];
    var k = document.getElementById('p-theme'); k.textContent = t.label; k.style.color = t.color;
    document.getElementById('p-title').textContent = p.t;
    document.getElementById('p-authors').textContent = p.au.join(', ') + (p.etal ? ', et al.' : '');
    document.getElementById('p-meta').textContent = p.v + ' · ' + p.yr + (p.c ? ' · cited by ' + p.c.toLocaleString('en-US') : '');
    document.getElementById('p-link').href = 'https://scholar.google.com/scholar?q=' + encodeURIComponent('"' + p.t + '"');
  }

  function placeTip(i) {
    var n = N[i], r = graph.getBoundingClientRect(), sx = r.width / VW, sy = r.height / (VW * aspect);
    var x = n.x * sx, y = n.y * sy;
    tip.style.left = x + 'px'; tip.style.top = y + 'px';
    var hx = n.x > VW * 0.78 ? 'calc(-100% + 22px)' : (n.x < VW * 0.22 ? '-22px' : '-50%');
    tip.style.transform = 'translate(' + hx + ', ' + (y < 70 ? '26px' : 'calc(-100% - 26px)') + ')';
  }

  function kick(a) {
    alpha = Math.max(alpha, a);
    if (running) return;
    running = true;
    (function loop() {
      tick(alpha); if (!drag) alpha *= 0.975; render();
      if (alpha > 0.004 || drag) requestAnimationFrame(loop); else running = false;
    })();
  }

  function toLocal(ev) {
    var r = graph.getBoundingClientRect();
    return [(ev.clientX - r.left) / r.width * VW, (ev.clientY - r.top) / r.height * VW * aspect];
  }

  function build() {
    P.forEach(function (p, i) { p._i = i; });
    svg.setAttribute('viewBox', '0 0 ' + VW + ' ' + VW * aspect);
    var gE = el('g', {}, svg), gL = el('g', {}, svg), gN = el('g', {}, svg);
    els.edges = E.map(function () { return el('line', { 'stroke-linecap': 'round' }, gE); });
    els.labels = Object.keys(T).map(function (id) {
      var t = el('text', { 'class': 'label', fill: T[id].color, 'text-anchor': 'middle' }, gL);
      t.textContent = T[id].label; return { id: id, el: t };
    });
    els.nodes = P.map(function (p, i) {
      var t = T[p.theme], g = el('g', { 'class': 'node', tabindex: 0, role: 'button', 'aria-label': p.t + ', ' + p.yr }, gN);
      el('circle', { r: 22, fill: 'transparent' }, g); // touch target
      g._ring = el('circle', { 'class': 'ring', r: N[i].r + 3, fill: 'none', 'stroke-width': 3 }, g);
      el('circle', { r: p.pre ? N[i].r - 1.5 : N[i].r, fill: p.pre ? '#0F172A' : t.color, stroke: p.pre ? t.color : '#0F172A', 'stroke-width': p.pre ? 3 : 2 }, g);
      g.addEventListener('pointerdown', function (ev) {
        if (ev.button !== 0) return;
        g.setPointerCapture(ev.pointerId); g.style.cursor = 'grabbing';
        drag = { i: i, moved: false, x0: ev.clientX, y0: ev.clientY };
        tip.hidden = true; kick(0.3);
      });
      g.addEventListener('pointermove', function (ev) {
        if (!drag || drag.i !== i) return;
        if (Math.abs(ev.clientX - drag.x0) + Math.abs(ev.clientY - drag.y0) > 3) drag.moved = true;
        var q = toLocal(ev); N[i].fx = q[0]; N[i].fy = q[1]; alpha = Math.max(alpha, 0.3);
      });
      var end = function () {
        if (!drag || drag.i !== i) return;
        N[i].fx = N[i].fy = null; g.style.cursor = '';
        sel = i; drag = null; styleAll(); kick(0.25);
      };
      g.addEventListener('pointerup', end); g.addEventListener('pointercancel', end);
      g.addEventListener('pointerenter', function (ev) {
        if (drag || ev.pointerType === 'touch') return;
        tip.textContent = p.t + ' (' + p.yr + ')'; tip._i = i; tip.hidden = false; placeTip(i);
      });
      g.addEventListener('pointerleave', function () { if (tip._i === i) tip.hidden = true; });
      g.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); sel = i; styleAll(); } });
      g.addEventListener('focus', function () { sel = i; styleAll(); });
      return g;
    });
    var lg = document.getElementById('legend');
    function chip(label, color, count, id) {
      var b = document.createElement('button'); b.type = 'button'; if (id) b.dataset.theme = id;
      if (color) { var d = document.createElement('span'); d.className = 'dot'; d.style.background = color; b.appendChild(d); }
      b.appendChild(document.createTextNode(label));
      var n = document.createElement('span'); n.className = 'n'; n.textContent = count; b.appendChild(n);
      b.addEventListener('click', function () {
        theme = id && theme !== id ? id : null;
        if (theme) { var best = P.filter(function (p) { return p.theme === theme; }).sort(function (a, b) { return (b.c || 0) - (a.c || 0); })[0]; sel = best._i; }
        styleAll();
      });
      lg.appendChild(b);
    }
    chip('All', null, P.length, null);
    Object.keys(T).forEach(function (id) { chip(T[id].label, T[id].color, P.filter(function (p) { return p.theme === id; }).length, id); });
  }

  function resize() {
    var r = graph.getBoundingClientRect();
    if (!r.width) return;
    var a = r.height / r.width;
    if (Math.abs(a - aspect) > 0.01) {
      var k = a / aspect; N.forEach(function (n) { n.y *= k; }); aspect = a;
      svg.setAttribute('viewBox', '0 0 ' + VW + ' ' + VW * aspect);
      kick(0.4);
    }
  }

  Promise.all([
    fetch('data/papers.json').then(function (r) { return r.json(); }),
    fetch('data/citations.csv').then(function (r) { return r.ok ? r.text() : ''; }).catch(function () { return ''; })
  ]).then(function (res) {
    var D = res[0], C = parseCSV(res[1]);
    P = D.papers; E = D.edges;
    D.themes.forEach(function (t) { T[t.id] = t; });
    P.forEach(function (p) { if (C[p.key]) p.c = C[p.key]; });
    sel = P.reduce(function (b, p, i) { return (p.c || 0) > (P[b].c || 0) ? i : b; }, 0);
    var r = graph.getBoundingClientRect(); if (r.width) aspect = r.height / r.width;
    var seed = 11, rnd = function () { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; };
    N = P.map(function (p) { var t = T[p.theme]; return { x: t.ax * VW + (rnd() - 0.5) * 120, y: t.ay * VW * aspect + (rnd() - 0.5) * 90, vx: 0, vy: 0, r: radius(p), fx: null, fy: null }; });
    for (var i = 0; i < 220; i++) tick(1 - i / 260);
    build(); styleAll(); render();
    if (window.ResizeObserver) new ResizeObserver(resize).observe(graph);
    kick(0.3);
  });
})();
