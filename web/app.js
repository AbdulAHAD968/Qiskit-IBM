/* Kinship Screening with QAOA - website behaviour. No dependencies. */
(function () {
  "use strict";
  var D = window.KINSHIP || {};
  var NS = "http://www.w3.org/2000/svg";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  function el(tag, attrs, parent, text) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs || {}) e.setAttribute(k, attrs[k]);
    if (text != null) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
  }
  function h(tag, cls, parent, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    if (parent) parent.appendChild(e);
    return e;
  }
  function get(path) {
    return path.split(".").reduce(function (o, k) { return o == null ? undefined : o[k]; }, D);
  }
  var F = {
    raw: function (v) { return String(v); },
    int: function (v) { return Math.round(v).toLocaleString("en-US"); },
    n0: function (v) { return v.toFixed(0); },
    n1: function (v) { return v.toFixed(1); },
    n2: function (v) { return v.toFixed(2); },
    n3: function (v) { return v.toFixed(3); },
    pct0: function (v) { return (100 * v).toFixed(0) + "%"; },
    pct1: function (v) { return (100 * v).toFixed(1) + "%"; },
    pct2: function (v) { return (100 * v).toFixed(2) + "%"; },
    date: function (v) { return new Date(v).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" }); }
  };
  function pctSmart(v) { return (100 * v).toFixed(v < 0.001 ? 3 : v < 0.01 ? 2 : v < 0.1 ? 1 : 0) + "%"; }
  function safe(name, fn) { try { fn(); } catch (err) { if (window.console) console.error("[" + name + "]", err); } }

  var NAMES = {
    constrained: "Constrained QAOA", penalty: "Penalty QAOA", field: "Field officer's rule",
    relevance: "Relevance-weighted rule", greedy: "Greedy", annealing: "Simulated annealing",
    random: "Random valid plan", exact: "Exact optimum", decomposed_qaoa: "Decomposition + QAOA"
  };

  /* ---------- text bindings ---------- */
  safe("bind", function () {
    $$("[data-v]").forEach(function (node) {
      var v = get(node.getAttribute("data-v"));
      if (v == null) return;
      var f = F[node.getAttribute("data-f") || "raw"];
      node.textContent = f(v);
    });
  });

  /* ---------- theme ---------- */
  safe("theme", function () {
    var root = document.documentElement;
    try { var saved = localStorage.getItem("kinship-theme"); if (saved) root.setAttribute("data-theme", saved); } catch (e) { /* storage blocked */ }
    $("#theme").addEventListener("click", function () {
      var dark = root.getAttribute("data-theme") === "dark" ||
        (!root.getAttribute("data-theme") && window.matchMedia("(prefers-color-scheme: dark)").matches);
      var next = dark ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("kinship-theme", next); } catch (e) { /* storage blocked */ }
    });
  });

  /* ---------- tooltip ---------- */
  var tipNode = $("#tip");
  function tip(html, evt) {
    tipNode.innerHTML = html;
    tipNode.classList.add("show");
    var pad = 14, w = tipNode.offsetWidth, hh = tipNode.offsetHeight;
    var x = evt.clientX + pad, y = evt.clientY + pad;
    if (x + w > window.innerWidth - 8) x = evt.clientX - w - pad;
    if (y + hh > window.innerHeight - 8) y = evt.clientY - hh - pad;
    tipNode.style.left = Math.max(8, x) + "px";
    tipNode.style.top = Math.max(8, y) + "px";
  }
  function tipHide() { tipNode.classList.remove("show"); }
  function hover(node, htmlFn) {
    node.addEventListener("mousemove", function (e) { tip(htmlFn(), e); });
    node.addEventListener("mouseleave", tipHide);
  }
  function tipRow(key, label, value) {
    return '<div class="row"><span><i class="sw bg-' + key + '"></i>' + label + "</span><span>" + value + "</span></div>";
  }

  /* ---------- charts ---------- */
  function lineChart(host, cfg) {
    if (!host) return;
    var W = cfg.w || 520, H = cfg.h || 300;
    var m = { l: 48, r: cfg.direct === false ? 14 : 104, t: 14, b: 40 };
    var svg = el("svg", { viewBox: "0 0 " + W + " " + H, "class": "chart", role: "img", "aria-label": cfg.label || "" });
    var xs = cfg.x.values, pad = 22;
    var X = function (i) { return m.l + pad + (xs.length === 1 ? 0.5 : i / (xs.length - 1)) * (W - m.l - m.r - 2 * pad); };
    var lo = cfg.y.min, hi = cfg.y.max, log = !!cfg.y.log;
    var T = function (v) { return log ? Math.log(Math.max(v, lo)) / Math.LN10 : v; };
    var Y = function (v) { return m.t + (1 - (T(v) - T(lo)) / (T(hi) - T(lo))) * (H - m.t - m.b); };
    cfg.y.ticks.forEach(function (t) {
      el("line", { "class": "grid", x1: m.l, x2: W - m.r, y1: Y(t), y2: Y(t) }, svg);
      el("text", { "class": "tick", x: m.l - 8, y: Y(t) + 4, "text-anchor": "end" }, svg, cfg.y.fmt(t));
    });
    el("line", { "class": "axis", x1: m.l, x2: W - m.r, y1: H - m.b, y2: H - m.b }, svg);
    xs.forEach(function (v, i) {
      el("text", { "class": "tick", x: X(i), y: H - m.b + 17, "text-anchor": "middle" }, svg, cfg.x.fmt(v));
    });
    el("text", { "class": "alabel", x: (m.l + W - m.r) / 2, y: H - 4, "text-anchor": "middle" }, svg, cfg.x.label);
    var cross = el("line", { "class": "cross", y1: m.t, y2: H - m.b }, svg);
    var labels = [];
    (cfg.refs || []).forEach(function (r) {
      el("line", { "class": "refline stroke-" + r.key, x1: m.l, x2: W - m.r, y1: Y(r.y), y2: Y(r.y) }, svg);
      labels.push({ y: Y(r.y), text: r.short || r.label, cls: "dlabel ref" });
    });
    cfg.series.forEach(function (s) {
      var d = s.values.map(function (v, i) { return (i ? "L" : "M") + X(i).toFixed(1) + " " + Y(v).toFixed(1); }).join("");
      el("path", { "class": "line stroke-" + s.key + (s.dash ? " dash" : ""), d: d }, svg);
      s.values.forEach(function (v, i) {
        if (s.sd) {
          el("line", { "class": "err stroke-" + s.key, x1: X(i), x2: X(i), y1: Y(Math.min(hi, v + s.sd[i])), y2: Y(Math.max(lo, v - s.sd[i])) }, svg);
        }
        var mk = s.square
          ? el("rect", { "class": "mk fill-" + s.key, x: X(i) - 4.5, y: Y(v) - 4.5, width: 9, height: 9, rx: 1.5 }, svg)
          : el("circle", { "class": "mk fill-" + s.key, cx: X(i), cy: Y(v), r: 5 }, svg);
        mk.style.setProperty("--d", (0.5 + i * 0.25) + "s");
      });
      labels.push({ y: Y(s.values[s.values.length - 1]), text: s.short || s.label, cls: "dlabel" });
    });
    if (cfg.direct !== false) {
      labels.sort(function (a, b) { return a.y - b.y; });
      for (var i = 1; i < labels.length; i++) if (labels[i].y - labels[i - 1].y < 14) labels[i].y = labels[i - 1].y + 14;
      var over = labels.length ? labels[labels.length - 1].y - (H - m.b - 2) : 0;
      if (over > 0) labels.forEach(function (l) { l.y -= over; });
      labels.forEach(function (l) { el("text", { "class": l.cls, x: W - m.r + 8, y: l.y + 4 }, svg, l.text); });
    }
    xs.forEach(function (v, i) {
      var half = xs.length > 1 ? (X(1) - X(0)) / 2 : 40;
      var hit = el("rect", { "class": "hit", x: X(i) - half, y: m.t, width: 2 * half, height: H - m.t - m.b }, svg);
      hit.addEventListener("mousemove", function (e) {
        cross.setAttribute("x1", X(i)); cross.setAttribute("x2", X(i)); cross.style.opacity = 1;
        var rows = cfg.series.map(function (s) { return tipRow(s.key, s.label, cfg.y.tip(s.values[i])); });
        (cfg.refs || []).forEach(function (r) { rows.push(tipRow(r.key, r.label, cfg.y.tip(r.y))); });
        tip("<b>" + cfg.x.tip(v) + "</b>" + rows.join(""), e);
      });
      hit.addEventListener("mouseleave", function () { cross.style.opacity = 0; tipHide(); });
    });
    host.appendChild(svg);
    $$(".line:not(.dash)", svg).forEach(function (p) { p.style.setProperty("--len", Math.ceil(p.getTotalLength()) + 4); });
  }

  function stripChart(host, rows, size) {
    if (!host || !rows.length) return;
    var methods = ["random", "field", "relevance", "greedy", "annealing"];
    var W = 520, rowH = 40, m = { l: 150, r: 46, t: 8, b: 34 }, H = m.t + methods.length * rowH + m.b;
    var svg = el("svg", { viewBox: "0 0 " + W + " " + H, "class": "chart", role: "img", "aria-label": "Plan value divided by best plan, by method" });
    var X = function (v) { return m.l + v * (W - m.l - m.r); };
    [0, 0.25, 0.5, 0.75, 1].forEach(function (t) {
      el("line", { "class": t === 1 ? "axis" : "grid", x1: X(t), x2: X(t), y1: m.t, y2: H - m.b }, svg);
      el("text", { "class": "tick", x: X(t), y: H - m.b + 16, "text-anchor": "middle" }, svg, (100 * t) + "%");
    });
    el("text", { "class": "alabel", x: (m.l + W - m.r) / 2, y: H - 3, "text-anchor": "middle" }, svg, "value of the plan / value of the best plan");
    methods.forEach(function (key, j) {
      var yc = m.t + (j + 0.5) * rowH, sum = 0;
      el("text", { "class": "tick", x: m.l - 10, y: yc + 4, "text-anchor": "end", style: "font-size:12px" }, svg, NAMES[key]);
      rows.forEach(function (r, i) {
        var v = r[key + "_ratio"]; sum += v;
        var jitter = (((i * 37 + j * 11) % 17) / 16 - 0.5) * 20;
        var dot = el("circle", { "class": "dot fill-" + key, cx: X(v), cy: yc + jitter, r: 3.8 }, svg);
        dot.style.setProperty("--d", (0.15 * j + 0.012 * i) + "s");
        hover(dot, function () { return "<b>Family " + size + "-" + (r.index < 10 ? "0" : "") + r.index + "</b>" + tipRow(key, NAMES[key], F.pct0(v)); });
      });
      var mean = sum / rows.length;
      el("line", { "class": "meanbar", x1: X(mean), x2: X(mean), y1: yc - 13, y2: yc + 13 }, svg);
      el("text", { "class": "dlabel", x: W - m.r + 8, y: yc + 4 }, svg, F.pct0(mean));
    });
    host.appendChild(svg);
  }

  function tradeoffChart(host, t) {
    if (!host || !t) return;
    var W = 520, H = 330, m = { l: 52, r: 16, t: 12, b: 42 };
    var svg = el("svg", { viewBox: "0 0 " + W + " " + H, "class": "chart", role: "img", "aria-label": "Trade-off between couples found and carriers found" });
    var all = t.cloud.concat(t.front, t.qaoa_front, [t.field, t.relevance]);
    var xs = all.map(function (p) { return p.carriers; }), ys = all.map(function (p) { return p.couples; });
    var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs), y1 = Math.max.apply(null, ys);
    var xp = (x1 - x0) * 0.06, X = function (v) { return m.l + (v - (x0 - xp)) / (x1 - x0 + 2 * xp) * (W - m.l - m.r); };
    var Y = function (v) { return m.t + (1 - v / (y1 * 1.08)) * (H - m.t - m.b); };
    for (var i = 0; i <= 4; i++) {
      var yv = y1 * 1.08 * i / 4;
      el("line", { "class": "grid", x1: m.l, x2: W - m.r, y1: Y(yv), y2: Y(yv) }, svg);
      el("text", { "class": "tick", x: m.l - 8, y: Y(yv) + 4, "text-anchor": "end" }, svg, yv.toFixed(2));
      var xv = x0 + (x1 - x0) * i / 4;
      el("text", { "class": "tick", x: X(xv), y: H - m.b + 16, "text-anchor": "middle" }, svg, xv.toFixed(1));
    }
    el("line", { "class": "axis", x1: m.l, x2: W - m.r, y1: H - m.b, y2: H - m.b }, svg);
    el("text", { "class": "alabel", x: (m.l + W - m.r) / 2, y: H - 4, "text-anchor": "middle" }, svg, "relevance-weighted carriers found (expected)");
    el("text", { "class": "alabel", x: 12, y: (m.t + H - m.b) / 2, "text-anchor": "middle", transform: "rotate(-90 12 " + (m.t + H - m.b) / 2 + ")" }, svg, "at-risk couples found (expected)");
    t.cloud.forEach(function (p, i) {
      var c = el("circle", { "class": "dot fill-random", cx: X(p.carriers), cy: Y(p.couples), r: 2.3 }, svg);
      c.style.setProperty("--d", (i % 40) * 0.01 + "s");
    });
    var front = t.front.slice().sort(function (a, b) { return a.carriers - b.carriers; });
    el("path", { "class": "front", d: front.map(function (p, i) { return (i ? "L" : "M") + X(p.carriers).toFixed(1) + " " + Y(p.couples).toFixed(1); }).join("") }, svg);
    function describe(p) { return tipRow("exact", "Couples found", p.couples.toFixed(3)) + tipRow("exact", "Carriers found", p.carriers.toFixed(2)); }
    front.forEach(function (p) {
      var c = el("circle", { "class": "mk fill-exact", cx: X(p.carriers), cy: Y(p.couples), r: 4.5 }, svg);
      hover(c, function () { return "<b>Exact front plan</b>" + describe(p); });
    });
    t.qaoa_front.forEach(function (p) {
      var c = el("circle", { "class": "ring", cx: X(p.carriers), cy: Y(p.couples), r: 8 }, svg);
      c.setAttribute("pointer-events", "all");
      hover(c, function () { return "<b>Among the QAOA shots</b>" + describe(p); });
    });
    [["field", t.field], ["relevance", t.relevance]].forEach(function (pair) {
      var p = pair[1], cx = X(p.carriers), cy = Y(p.couples);
      var d = el("rect", { "class": "mk fill-" + pair[0], x: cx - 6, y: cy - 6, width: 12, height: 12, transform: "rotate(45 " + cx + " " + cy + ")" }, svg);
      hover(d, function () { return "<b>" + NAMES[pair[0]] + "</b>" + describe(p); });
    });
    host.appendChild(svg);
  }

  function barRows(host, items) {
    if (!host) return;
    items.forEach(function (it, i) {
      var row = h("div", "bar-row", host);
      h("div", "name", row, it.name);
      var track = h("div", "track", row);
      (it.segments || [{ cls: it.cls, share: it.share }]).forEach(function (seg) {
        var f = h("i", "fill bg-" + seg.cls, track);
        f.style.setProperty("--w", (100 * seg.share).toFixed(1) + "%");
        f.style.setProperty("--d", (0.08 * i) + "s");
        f.style.display = "block";
      });
      h("div", "val num", row, it.label);
      if (it.tip) hover(row, function () { return it.tip; });
    });
  }

  /* ---------- pedigree ---------- */
  function shortLabel(label) {
    var two = { "Paternal grandfather": ["Paternal", "grandfather"], "Paternal grandmother": ["Paternal", "grandmother"],
      "Maternal grandfather": ["Maternal", "grandfather"], "Maternal grandmother": ["Maternal", "grandmother"],
      "Great-grandfather": ["Great-", "grandfather"], "Great-grandmother": ["Great-", "grandmother"] };
    if (two[label]) return two[label];
    if (label.indexOf("Wife of") === 0) return ["Wife"];
    if (label.indexOf("Husband of") === 0) return ["Husband"];
    return [label.replace("Paternal", "Pat.").replace("Maternal", "Mat.")];
  }
  var STATUS = { affected: "Affected index child", obligate: "Parent, obligate carrier (not tested)", deceased: "Deceased",
    unavailable: "Absent or declined at this visit", candidate: "Can be tested in this visit" };
  var STAGE = { elder: "elder", married: "married adult", unmarried: "unmarried adult", engaged: "engaged", child: "child" };

  function pedigree(host, demo) {
    var people = demo.people, byId = {};
    people.forEach(function (p) { byId[p.id] = p; });
    var ys = people.map(function (p) { return p.y; }), minY = Math.min.apply(null, ys), maxY = Math.max.apply(null, ys);
    var W = 1000, padX = 46, top = 40, rowH = 122, R = 15, H = top + (maxY - minY) * rowH + 64;
    var px = function (p) { return padX + p.x * (W - 2 * padX); }, py = function (p) { return top + (p.y - minY) * rowH; };
    var svg = el("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": "Family tree with the chosen relatives highlighted" });
    var gLinks = el("g", {}, svg), gCouples = el("g", {}, svg), gPeople = el("g", {}, svg);
    var sibships = {};
    people.forEach(function (p) {
      if (p.father == null || p.mother == null) return;
      var key = p.father + "-" + p.mother;
      (sibships[key] = sibships[key] || []).push(p);
    });
    Object.keys(sibships).forEach(function (key, n) {
      var kids = sibships[key], ids = key.split("-"), f = byId[ids[0]], mo = byId[ids[1]];
      var fx = px(f), mx = px(mo), y = py(f), mid = (fx + mx) / 2, bar = y + rowH * (0.46 + 0.06 * (n % 3));
      var cx = kids.map(px), left = Math.min.apply(null, cx.concat([mid])), right = Math.max.apply(null, cx.concat([mid]));
      var d = "M" + fx + " " + y + "H" + mx + "M" + mid + " " + y + "V" + bar + "M" + left + " " + bar + "H" + right;
      kids.forEach(function (k) { d += "M" + px(k) + " " + bar + "V" + (py(k) - R); });
      el("path", { "class": "lnk", d: d }, gLinks);
    });
    var coupleNodes = [];
    demo.couples.forEach(function (c) {
      var a = byId[c.a], b = byId[c.b], ax = px(a), bx = px(b), ay = py(a), by = py(b), node;
      if (c.kind === "married") {
        node = el("line", { "class": "cp married", x1: ax, y1: ay, x2: bx, y2: by }, gCouples);
      } else {
        var lift = 14 + Math.min(26, Math.abs(bx - ax) * 0.045);
        node = el("path", { "class": "cp " + c.kind, d: "M" + ax + " " + (ay - R) + "Q" + (ax + bx) / 2 + " " + (Math.min(ay, by) - R - lift * 2) + " " + bx + " " + (by - R) }, gCouples);
      }
      node.setAttribute("pointer-events", "stroke");
      hover(node, function () {
        return "<b>" + a.label + " and " + b.label + "</b>" +
          '<div class="row"><span>Link</span><span>' + (c.kind === "potential" ? "possible match" : c.kind) + "</span></div>" +
          '<div class="row"><span>Both carriers</span><span>' + F.pct1(c.w) + "</span></div>" +
          '<div class="row"><span>Link strength</span><span>' + c.strength.toFixed(2) + "</span></div>" +
          '<div class="row"><span>Weight in the objective</span><span>' + (c.in_problem ? c.weight.toFixed(3) : "not in this visit") + "</span></div>";
      });
      coupleNodes.push({ c: c, node: node });
    });
    var personNodes = {};
    people.forEach(function (p) {
      var g = el("g", { "class": "person " + p.status, transform: "translate(" + px(p) + " " + py(p) + ")" }, gPeople);
      g.style.setProperty("--d", (0.12 + 0.18 * (p.y - minY) + 0.5 * p.x * 0.3) + "s");
      if (p.sex === "M") el("rect", { "class": "shape", x: -R, y: -R, width: 2 * R, height: 2 * R, rx: 3 }, g);
      else el("circle", { "class": "shape", r: R }, g);
      if (p.status === "deceased") el("line", { x1: -R - 4, y1: R + 4, x2: R + 4, y2: -R - 4, stroke: "var(--axis)", "stroke-width": 1.5 }, g);
      if (p.qubit != null) el("text", { "class": "pv", y: 4 }, g, p.p.toFixed(2).replace(/^0/, ""));
      shortLabel(p.label).forEach(function (line, i) { el("text", { "class": "pn", y: R + 15 + 12 * i }, g, line); });
      hover(g, function () {
        var html = "<b>" + p.label + "</b><div>" + STATUS[p.status] + "</div>";
        if (p.status !== "affected") html += '<div class="row"><span>Carrier probability</span><span>' + F.pct1(p.p) + "</span></div>";
        if (p.qubit != null) {
          html += '<div class="row"><span>Life stage</span><span>' + STAGE[p.stage] + "</span></div>" +
            '<div class="row"><span>Relevance</span><span>' + p.r.toFixed(1) + "</span></div>" +
            '<div class="row"><span>Qubit</span><span>q' + p.qubit + "</span></div>";
        }
        return html;
      });
      personNodes[p.id] = g;
    });
    host.appendChild(svg);
    $$(".lnk", svg).forEach(function (path) { path.style.setProperty("--len", Math.ceil(path.getTotalLength()) + 4); });
    return {
      setPlan: function (chosen) {
        var set = {};
        chosen.forEach(function (id) { set[id] = true; });
        Object.keys(personNodes).forEach(function (id) { personNodes[id].classList.toggle("picked", !!set[id]); });
        coupleNodes.forEach(function (cn) { cn.node.classList.toggle("both", !!set[cn.c.a] && !!set[cn.c.b]); });
      }
    };
  }

  safe("demo", function () {
    var demo = D.demo;
    if (!demo) { var s = $("#demo"); if (s) s.style.display = "none"; return; }
    var tree = pedigree($("#pedigree"), demo);
    var qaoa = demo.qaoa.filter(function (q) { return q.method === "constrained"; }).pop();
    var penalty = demo.qaoa.filter(function (q) { return q.method === "penalty"; }).pop();
    var plans = [
      { key: "field", color: "--c-field", kind: "Classical rule", title: "Field officer's rule", plan: demo.plans.field,
        note: "Tests the " + demo.k + " people with the highest carrier probability. It ignores who is married or engaged to whom." },
      { key: "relevance", color: "--c-relevance", kind: "Classical rule", title: "Relevance-weighted rule", plan: demo.plans.relevance,
        note: "Ranks people by relevance times carrier probability. Still blind to couples." },
      { key: "greedy", color: "--c-greedy", kind: "Classical heuristic", title: "Greedy", plan: demo.plans.greedy,
        note: "Adds one person at a time by marginal gain. Sees a couple only after its first partner is already picked." },
      { key: "qaoa", color: "--c-constrained", kind: "Quantum, depth " + qaoa.p, title: "Constrained QAOA", plan: qaoa.best,
        note: "Best of 4,096 measured plans. Chance that a single shot is the best plan: " + F.pct1(qaoa.p_opt) + ", against " +
          F.pct1(demo.random.p_opt) + " for a random valid plan. Every shot used exactly " + demo.k + " kits; penalty QAOA managed " +
          F.pct0(penalty.valid_share) + "." },
      { key: "exact", color: "--c-exact", kind: "Exact reference", title: "Exact optimum", plan: demo.plans.exact,
        note: "Brute force over all " + demo.n_feasible + " valid plans. This is the answer every other method is scored against." }
    ];
    var shell = $("#demo-shell"), tabs = $("#plan-tabs"), touched = false, buttons = {};
    function show(key) {
      var item = plans.filter(function (p) { return p.key === key; })[0], plan = item.plan;
      Object.keys(buttons).forEach(function (k) { buttons[k].setAttribute("aria-pressed", k === key ? "true" : "false"); });
      shell.style.setProperty("--plan", "var(" + item.color + ")");
      tree.setPlan(plan.chosen);
      $("#plan-kind").textContent = item.kind;
      $("#plan-title").textContent = item.title;
      $("#plan-ratio").textContent = F.pct0(plan.ratio);
      $("#plan-meter").style.width = (100 * plan.ratio).toFixed(1) + "%";
      $("#plan-kv").innerHTML =
        "<dt>At-risk couples found, expected</dt><dd>" + plan.couples.toFixed(3) + "</dd>" +
        "<dt>Carriers found, relevance-weighted</dt><dd>" + plan.carriers.toFixed(2) + "</dd>" +
        "<dt>Objective value</dt><dd>" + plan.value.toFixed(3) + "</dd>";
      $("#plan-chosen").innerHTML = plan.labels.map(function (l) { return "<li>" + l + "</li>"; }).join("");
      $("#plan-note").textContent = item.note;
    }
    plans.forEach(function (p) {
      var b = h("button", "tab", tabs, p.title);
      b.type = "button";
      b.addEventListener("click", function () { touched = true; show(p.key); });
      buttons[p.key] = b;
    });
    show("field");
    var watcher = new MutationObserver(function () {
      if (!shell.classList.contains("in")) return;
      watcher.disconnect();
      setTimeout(function () { if (!touched) show("qaoa"); }, 2600);
    });
    watcher.observe(shell, { attributes: true, attributeFilter: ["class"] });
  });

  /* ---------- tables and derived numbers ---------- */
  safe("genetics", function () {
    var table = $("#genetics-table");
    if (!table || !D.genetics) return;
    D.genetics.checks.forEach(function (c) {
      var tr = h("tr", "", table);
      h("td", "", tr, c.relation);
      h("td", "", tr, c.textbook + (c.formula ? ' <span class="src">exact: ' + c.formula + "</span>" : ""));
      h("td", "r", tr, c.computed.toFixed(4));
    });
  });

  safe("bench-table", function () {
    var table = $("#bench-table"), rows = D.bench_rows;
    if (!table || !rows) return;
    table.innerHTML = "<tr><th>Size</th><th>Method</th><th class='r'>Depth</th><th class='r'>Quality</th><th class='r'>Value / optimum</th>" +
      "<th class='r'>Best plan per shot</th><th class='r'>Valid shots</th><th class='r'>Shots for 95%</th><th class='r'>Finds the best plan</th></tr>";
    var order = ["random", "field", "relevance", "greedy", "annealing", "constrained", "penalty"];
    ["S", "M"].forEach(function (size) {
      order.forEach(function (method) {
        rows.filter(function (r) { return r.size === size && r.method === method; }).forEach(function (r) {
          var q = r.kind === "quantum", tr = h("tr", "", table);
          h("td", "", tr, '<span class="tag">' + size + "</span> " + r.n + " / " + r.k);
          h("td", "", tr, '<span class="key bg-' + method + '"></span>' + NAMES[method] + (q ? ' <span class="tag q">Qiskit</span>' : ""));
          h("td", "r", tr, r.p == null ? "" : r.p);
          h("td", "r", tr, r.quality.mean.toFixed(3) + (r.quality.std ? " &plusmn; " + r.quality.std.toFixed(3) : ""));
          h("td", "r", tr, F.pct0(r.ratio.mean));
          h("td", "r", tr, r.p_opt ? pctSmart(r.p_opt.mean) : "");
          h("td", "r", tr, r.valid_share ? F.pct0(r.valid_share.mean) : "100%");
          h("td", "r", tr, r.shots_95 && r.shots_95.median != null ? F.int(r.shots_95.median) : "");
          h("td", "r", tr, q ? F.pct0(r.best_sample_optimal_share) : r.optimal_share != null ? F.pct0(r.optimal_share) : "");
        });
      });
    });
  });

  safe("derived", function () {
    var set = function (id, text) { var n = $(id); if (n && text != null) n.textContent = text; };
    if (D.decomposition) {
      var rows = D.decomposition.rows, maxq = Math.max.apply(null, rows.map(function (r) { return r.max_qubits; }));
      var runs = rows.reduce(function (a, r) { return a + r.qaoa_runs; }, 0);
      var allOpt = rows.every(function (r) { return r.decomposed_qaoa.optimal; });
      set("#max-qubits", String(maxq));
      set("#decomp-note", "The couple graph of each network splits into components of at most " + maxq + " people, so no circuit needs more than " +
        maxq + " qubits. QAOA ran on every component with three or more people (" + runs + " runs in total) and a dynamic programme split the kits. " +
        (allOpt ? "All " + rows.length + " networks reached the proven optimum." : "Not every network reached the proven optimum.") +
        " At this component size sampling finds each optimum easily, so this shows the scaling route, not an advantage.");
    }
    if (D.bench) {
      set("#penalty-invalid", F.pct0(1 - D.bench.M.penalty["3"].valid_share.mean));
      var evals = 0;
      ["1", "2", "3"].forEach(function (p) { evals += D.bench.M.constrained[p].evaluations.mean; });
      set("#train-evals", String(Math.round(evals / 10) * 10));
    }
    if (D.gate1 && D.gate1.summary.S.field.tie_break) {
      var ts = D.gate1.summary.S.field.tie_break, tm = D.gate1.summary.M.field.tie_break;
      set("#tie-note", "Robustness check. The field officer's rule breaks ties in carrier probability arbitrarily, and a tie at the cut-off occurs in " +
        ts.families_with_tie + " and " + tm.families_with_tie + " of the " + D.gate1.n_instances + " families. Even with every tie broken in its favour it reaches only " +
        F.pct0(ts.best_ratio.mean) + " and " + F.pct0(tm.best_ratio.mean) + " of the best value and misses the best plan in " +
        F.pct0(ts.best_miss_rate) + " and " + F.pct0(tm.best_miss_rate) + " of the families.");
    }
    if (D.ablation) {
      var pick = function (init) { return D.ablation.summary.filter(function (r) { return r.initial === init && r.p === 3; })[0]; };
      set("#abl-field", pctSmart(pick("field").p_opt.mean));
      set("#abl-dicke", pctSmart(pick("dicke").p_opt.mean));
    }
    if (D.noise) {
      var last = D.noise.series.constrained["1"].slice(-1)[0];
      set("#noise-valid-1", F.pct0(last.valid_share));
    }
    if (D.tradeoff) {
      var t = D.tradeoff;
      set("#tradeoff-note", "The exact front has " + t.front_points.exact + " plans. The " + F.int(t.total_shots) + " QAOA shots contained " +
        t.front_points.qaoa_found + " of them and covered " + F.pct1(t.hypervolume.qaoa_ratio) + " of the front's area. Uniform random sampling of valid plans with the same number of shots covered " +
        F.pct1(t.hypervolume.random_ratio_mean) + " and found " + t.front_points.random_found_mean.toFixed(1) + " on average.");
    }
  });

  /* ---------- result charts ---------- */
  safe("gate1", function () {
    if (!D.gate1) return;
    ["S", "M"].forEach(function (size) {
      stripChart($("#gate1-" + size), D.gate1.rows.filter(function (r) { return r.size === size; }), size);
    });
  });

  safe("depth-charts", function () {
    if (!D.bench) return;
    ["S", "M"].forEach(function (size) {
      var b = D.bench[size], depths = [1, 2, 3];
      var series = function (key, field, scale) {
        return { key: key, label: NAMES[key], short: key === "constrained" ? "Constrained" : "Penalty",
          values: depths.map(function (p) { return scale * b[key][p][field].mean; }),
          sd: field === "quality" ? depths.map(function (p) { return b[key][p][field].std; }) : null };
      };
      var xcfg = { values: depths, label: "QAOA depth p", fmt: function (v) { return "p = " + v; }, tip: function (v) { return "Depth p = " + v; } };
      lineChart($("#quality-" + size), {
        label: "Quality against depth, size " + size, x: xcfg,
        y: { min: 0, max: 1, ticks: [0, 0.25, 0.5, 0.75, 1], fmt: function (v) { return v.toFixed(2); }, tip: function (v) { return v.toFixed(3); } },
        series: [series("constrained", "quality", 1), series("penalty", "quality", 1)],
        refs: [{ key: "random", label: NAMES.random, short: "Random", y: b.random["0"].quality.mean },
               { key: "field", label: NAMES.field, short: "Field rule", y: b.field["0"].quality.mean }]
      });
      var rnd = 100 * b.random["0"].p_opt.mean;
      var vals = [rnd].concat(depths.map(function (p) { return 100 * b.constrained[p].p_opt.mean; }), depths.map(function (p) { return 100 * b.penalty[p].p_opt.mean; }));
      var lo = Math.pow(10, Math.floor(Math.log(Math.min.apply(null, vals)) / Math.LN10));
      var hi = Math.pow(10, Math.ceil(Math.log(Math.max.apply(null, vals)) / Math.LN10));
      var ticks = [];
      for (var t = lo; t <= hi * 1.0001; t *= 10) ticks.push(t);
      lineChart($("#popt-" + size), {
        label: "Chance of the best plan against depth, size " + size, x: xcfg,
        y: { min: lo, max: hi, log: true, ticks: ticks, fmt: function (v) { return (v >= 1 ? v.toFixed(0) : String(+v.toPrecision(1))) + "%"; },
             tip: function (v) { return v.toFixed(v < 0.1 ? 3 : 2) + "%"; } },
        series: [series("constrained", "p_opt", 100), series("penalty", "p_opt", 100)],
        refs: [{ key: "random", label: NAMES.random, short: "Random", y: rnd }]
      });
    });
  });

  safe("hist", function () {
    var host = $("#hist-demo"), demo = D.demo;
    if (!host || !demo) return;
    var hst = demo.histogram, keys = [["random", "random"], ["constrained_p1", "dicke"], ["constrained_p3", "constrained"]];
    var top = 0;
    keys.forEach(function (k) { (hst[k[0]] || []).forEach(function (v) { top = Math.max(top, v); }); });
    var wrap = h("div", "hist", host);
    hst.random.forEach(function (_, i) {
      var bin = h("div", "bin", wrap);
      keys.forEach(function (k, j) {
        if (!hst[k[0]]) return;
        var bar = h("i", "bg-" + k[1], bin);
        bar.style.setProperty("--h", (100 * hst[k[0]][i] / top).toFixed(1) + "%");
        bar.style.setProperty("--d", (0.04 * i + 0.1 * j) + "s");
      });
      hover(bin, function () {
        return "<b>Quality " + hst.edges[i].toFixed(1) + " to " + hst.edges[i + 1].toFixed(1) + "</b>" +
          tipRow("random", "Random valid plan", F.pct1(hst.random[i])) +
          (hst.constrained_p1 ? tipRow("dicke", "Constrained QAOA, p = 1", F.pct1(hst.constrained_p1[i])) : "") +
          (hst.constrained_p3 ? tipRow("constrained", "Constrained QAOA, p = 3", F.pct1(hst.constrained_p3[i])) : "");
      });
    });
  });

  safe("bars", function () {
    if (D.bench) {
      var pm = D.bench.M.penalty;
      barRows($("#valid-bars"), [
        { name: "Constrained, any depth", cls: "constrained", share: 1, label: "100%" },
        { name: "Penalty, p = 1, 16 qubits", cls: "penalty", share: pm["1"].valid_share.mean, label: F.pct0(pm["1"].valid_share.mean) },
        { name: "Penalty, p = 2, 16 qubits", cls: "penalty", share: pm["2"].valid_share.mean, label: F.pct0(pm["2"].valid_share.mean) },
        { name: "Penalty, p = 3, 16 qubits", cls: "penalty", share: pm["3"].valid_share.mean, label: F.pct0(pm["3"].valid_share.mean) }
      ]);
    }
    if (D.circ) {
      var items = [], top = 0;
      ["S", "M"].forEach(function (size) { if (D.circ[size]) top = Math.max(top, D.circ[size].all.constrained["1"].two_qubit, D.circ[size].all.penalty["1"].two_qubit); });
      ["S", "M"].forEach(function (size) {
        var c = D.circ[size];
        if (!c) return;
        var dicke = c.all.dicke_only["0"].two_qubit, cons = c.all.constrained["1"].two_qubit, pen = c.all.penalty["1"].two_qubit, n = c.all.constrained["1"].n;
        items.push({ name: "Constrained, " + n + " qubits", label: String(cons), tip: "<b>" + cons + " CZ gates</b><div>" + dicke + " for the Dicke start state, " + (cons - dicke) + " for one cost and mixer layer</div>",
          segments: [{ cls: "dicke", share: dicke / top }, { cls: "constrained", share: (cons - dicke) / top }] });
        items.push({ name: "Penalty, " + n + " qubits", cls: "penalty", share: pen / top, label: String(pen), tip: "<b>" + pen + " CZ gates</b><div>one ZZ rotation on every pair of qubits</div>" });
      });
      barRows($("#circ-bars"), items);
    }
    if (D.decomposition) {
      var s = D.decomposition.summary;
      barRows($("#decomp-bars"), ["field", "relevance", "greedy", "annealing", "decomposed_qaoa"].map(function (k) {
        return { name: NAMES[k], cls: k === "decomposed_qaoa" ? "constrained" : k, share: s[k].mean, label: F.pct0(s[k].mean) };
      }));
    }
  });

  safe("noise", function () {
    var n = D.noise;
    if (!n) return;
    var levels = n.levels, ser = n.series, depths = Object.keys(ser.constrained).sort();
    function build(field, scale) {
      var out = [];
      ["constrained", "penalty"].forEach(function (key) {
        depths.forEach(function (p, j) {
          out.push({ key: key, label: NAMES[key] + ", p = " + p, dash: j > 0, square: j > 0,
            values: ser[key][p].map(function (r) { return scale * r[field]; }) });
        });
      });
      return out;
    }
    var xcfg = { values: levels, label: "two-qubit gate error", fmt: function (v) { return v === 0 ? "0" : +(100 * v).toFixed(2) + "%"; },
      tip: function (v) { return "Two-qubit error " + (100 * v).toFixed(2) + "%"; } };
    var pctTip = function (v) { return v.toFixed(1) + "%"; };
    lineChart($("#noise-valid"), { direct: false, w: 360, h: 280, x: xcfg, series: build("valid_share", 100),
      y: { min: 0, max: 100, ticks: [0, 25, 50, 75, 100], fmt: function (v) { return v + "%"; }, tip: pctTip } });
    var base = ser.constrained[depths[0]][0];
    lineChart($("#noise-quality"), { direct: false, w: 360, h: 280, x: xcfg, series: build("quality", 1),
      refs: [{ key: "random", label: NAMES.random, y: base.random_quality }],
      y: { min: 0, max: 0.8, ticks: [0, 0.2, 0.4, 0.6, 0.8], fmt: function (v) { return v.toFixed(1); }, tip: function (v) { return v.toFixed(3); } } });
    var all = build("p_opt", 100), top = 0;
    all.forEach(function (s) { s.values.forEach(function (v) { top = Math.max(top, v); }); });
    var step = top > 6 ? 2 : top > 3 ? 1 : 0.5, hi = Math.ceil(top / step) * step, ticks = [];
    for (var t = 0; t <= hi + 1e-9; t += step) ticks.push(+t.toFixed(2));
    lineChart($("#noise-popt"), { direct: false, w: 360, h: 280, x: xcfg, series: all,
      refs: [{ key: "random", label: NAMES.random, y: 100 * base.random_p_opt }],
      y: { min: 0, max: hi, ticks: ticks, fmt: function (v) { return v + "%"; }, tip: function (v) { return v.toFixed(2) + "%"; } } });
  });

  safe("tradeoff", function () { tradeoffChart($("#tradeoff"), D.tradeoff); });

  /* ---------- scroll behaviour ---------- */
  safe("scroll", function () {
    var nav = $("#nav"), bar = $("#progress"), hero = $("#hero");
    function onScroll() {
      var y = window.scrollY || window.pageYOffset, max = document.documentElement.scrollHeight - window.innerHeight;
      bar.style.width = (max > 0 ? 100 * y / max : 0) + "%";
      nav.classList.toggle("on-hero", y < hero.offsetHeight - 70);
      nav.classList.toggle("moved", y > 12);
      nav.classList.toggle("scrolled", y >= hero.offsetHeight - 70);
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    onScroll();
  });

  safe("observers", function () {
    var reveals = $$(".reveal"), counters = $$("[data-count]"), steps = $$(".step"), links = $$(".nav-links a");
    function count(node) {
      var target = parseFloat(node.getAttribute("data-count")), dec = parseInt(node.getAttribute("data-dec") || "0", 10), start = null;
      function frame(ts) {
        if (start == null) start = ts;
        var k = Math.min(1, (ts - start) / 1500), eased = 1 - Math.pow(1 - k, 3), v = target * eased;
        node.textContent = dec ? v.toFixed(dec) : Math.round(v).toLocaleString("en-US");
        if (k < 1) requestAnimationFrame(frame);
      }
      requestAnimationFrame(frame);
    }
    if (!("IntersectionObserver" in window) || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      reveals.forEach(function (n) { n.classList.add("in"); });
      counters.forEach(function (n) { var t = parseFloat(n.getAttribute("data-count")); n.textContent = n.getAttribute("data-dec") ? t.toFixed(1) : t.toLocaleString("en-US"); });
      steps.forEach(function (n) { n.classList.add("active"); });
      $$("#circuit .blk").forEach(function (n) { n.classList.add("active"); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
    }, { threshold: 0.12, rootMargin: "0px 0px -6% 0px" });
    reveals.forEach(function (n) { io.observe(n); });
    var cio = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { count(e.target); cio.unobserve(e.target); } });
    }, { threshold: 0.6 });
    counters.forEach(function (n) { cio.observe(n); });

    var active = { qubits: ["qubits"], dicke: ["qubits", "dicke"], cost: ["qubits", "cost"], mixer: ["qubits", "mixer"],
      measure: ["qubits", "dicke", "cost", "mixer", "measure"] };
    function setStep(key) {
      steps.forEach(function (s) { s.classList.toggle("active", s.getAttribute("data-step") === key); });
      $$("#circuit .blk").forEach(function (b) { b.classList.toggle("active", active[key].indexOf(b.getAttribute("data-blk")) >= 0); });
    }
    if (window.matchMedia("(max-width: 900px)").matches) {
      setStep("measure");
      steps.forEach(function (s) { s.classList.add("active"); });
    } else {
      var sio = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) { if (e.isIntersecting) setStep(e.target.getAttribute("data-step")); });
      }, { rootMargin: "-42% 0px -42% 0px" });
      steps.forEach(function (s) { sio.observe(s); });
      setStep("qubits");
    }

    var map = {};
    links.forEach(function (a) { map[a.getAttribute("href").slice(1)] = a; });
    var nio = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        links.forEach(function (a) { a.classList.remove("active"); });
        var a = map[e.target.id];
        if (a) a.classList.add("active");
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    $$("main section[id]").forEach(function (s) { nio.observe(s); });
  });
})();
