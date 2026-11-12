/* Section 6: run the constrained QAOA circuit live, on the instance of section 4. */
(function () {
  "use strict";
  var K = window.KINSHIP, D = K && K.demo;
  if (!D || !window.QAOASim || !document.getElementById("lab")) return;

  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var $ = function (s) { return document.querySelector(s); };
  // The visit being planned: which of the family's testable relatives are available, and how many kits.
  var V = { avail: D.candidates.map(function (c, q) { return q; }), k: D.k, custom: false };
  var problem, sim, calc, N, labels, trained, randomPopt, ampMax, bestRank, pen, penTrained;

  /** Build the optimisation instance for the current visit and tune its circuit. */
  function loadInstance() {
    var pos = new Map();
    V.avail.forEach(function (q, i) { pos.set(q, i); });
    problem = {
      n: V.avail.length, k: V.k, lam: D.lam,
      p: V.avail.map(function (q) { return D.candidates[q].p; }),
      r: V.avail.map(function (q) { return D.candidates[q].r; }),
      edges: D.edges.filter(function (e) { return pos.has(e.i) && pos.has(e.j); })
        .map(function (e) { return { i: pos.get(e.i), j: pos.get(e.j), w: e.w, c: e.c }; }),
    };
    sim = new QAOASim.Sim(problem);     // the state on screen
    calc = new QAOASim.Sim(problem);    // scratch copy for the landscape, the optimiser and the plan
    N = sim.N;
    labels = V.avail.map(function (q) { return D.candidates[q].label; });
    V.custom = !(V.avail.length === D.n && V.k === D.k);
    trained = {};
    if (!V.custom) {
      (D.qaoa || []).forEach(function (q) { if (q.method === "constrained") trained[q.p] = q; });
    } else {
      var L = QAOASim.tuneLadder(calc, 3);
      [1, 2, 3].forEach(function (p) {
        var m = calc.run(L[p].angles).metrics();
        trained[p] = { angles: L[p].angles, p_opt: m.p_opt, ratio: m.ratio, quality: m.quality, evals: L[p].evals, browser: true };
      });
    }
    pen = new QAOASim.PenaltySim(problem);
    penTrained = {};
    if (!V.custom) {
      (D.qaoa || []).forEach(function (q) { if (q.method === "penalty") penTrained[q.p] = q; });
    } else {
      var LP = QAOASim.tuneLadder(pen, 3);
      [1, 2, 3].forEach(function (p) { penTrained[p] = { angles: LP[p].angles, browser: true }; });
    }
    randomPopt = sim.optimalCount() / N;
    ampMax = (function () {
      var m = 1 / Math.sqrt(N);
      [1, 2, 3].forEach(function (p) {
        if (!trained[p]) return;
        calc.run(trained[p].angles);
        for (var s = 0; s < N; s++) m = Math.max(m, Math.hypot(calc.re[s], calc.im[s]));
      });
      return m * 1.08;
    })();
    bestRank = sim.order.map(function (s) { return sim.value[s] >= sim.best - 1e-12; });
  }
  loadInstance();
  var G_RANGE = [-1.5, 1.5], B_RANGE = [0, Math.PI];

  var S = {
    p: 3, angles: trained[3] ? trained[3].angles.slice() : [0.3, 0.7, 0.55, 0.47, 0.61, 0.33],
    op: 0, frac: 1, playing: false, optimising: false, source: "qiskit", evals: 0,
    path: [], interacted: false, tally: new Map(), shots: 0,
  };

  // ---------------------------------------------------------------- helpers
  function pct(x, d) {
    if (x == null || !isFinite(x)) return "–";
    d = d == null ? (x < 0.01 ? 2 : 1) : d;
    return (x * 100).toFixed(d) + "%";
  }
  function planNames(mask) {
    var out = [];
    for (var i = 0; i < sim.n; i++) if ((mask >> i) & 1) out.push(labels[i]);
    return out;
  }
  function ops(p) {
    var list = [{ type: "start" }];
    for (var l = 0; l < p; l++) { list.push({ type: "cost", l: l }); list.push({ type: "mix", l: l }); }
    return list;
  }
  // mulberry32 by Tommy Ettinger (2017, public domain): a small seeded generator, so the shots repeat.
  function mulberry(seed) {
    return function () {
      seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
      var t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  var rnd = mulberry(20261112);

  /** Bring the simulator to the state after operation `op`, with the last one applied by `frac`. */
  function evolve() {
    var p = S.p, list = ops(p);
    sim.reset();
    for (var i = 1; i <= S.op && i < list.length; i++) {
      var f = i === S.op ? S.frac : 1, o = list[i];
      if (o.type === "cost") sim.cost(f * S.angles[o.l]);
      else sim.mixer(f * S.angles[p + o.l]);
    }
  }
  function atEnd() { return S.op === ops(S.p).length - 1 && S.frac >= 1; }
  function isTrained() {
    var t = trained[S.p];
    if (!t) return false;
    for (var i = 0; i < t.angles.length; i++) if (Math.abs(t.angles[i] - S.angles[i]) > 1e-9) return false;
    return true;
  }

  // ---------------------------------------------------------- amplitude chart
  var ampCanvas = $("#lab-amp"), ampCtx = ampCanvas.getContext("2d");

  function sizeCanvas(c) {
    var dpr = Math.min(window.devicePixelRatio || 1, 2), w = c.clientWidth, h = c.clientHeight;
    if (c.width !== Math.round(w * dpr) || c.height !== Math.round(h * dpr)) {
      c.width = Math.round(w * dpr); c.height = Math.round(h * dpr);
    }
    return { w: w, h: h, dpr: dpr };
  }

  function drawAmp() {
    var dim = sizeCanvas(ampCanvas), ctx = ampCtx, w = dim.w, h = dim.h;
    ctx.setTransform(dim.dpr, 0, 0, dim.dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    var top = 10, bottom = h - 16, H = bottom - top, bw = w / N;
    var cur = 0;
    for (var s = 0; s < N; s++) cur = Math.max(cur, Math.hypot(sim.re[s], sim.im[s]));
    var ymax = Math.max(ampMax, cur * 1.05);
    // grid
    ctx.strokeStyle = "rgba(158,197,244,0.10)"; ctx.lineWidth = 1;
    for (var g = 1; g <= 3; g++) { var gy = bottom - (H * g) / 4; ctx.beginPath(); ctx.moveTo(0, gy + 0.5); ctx.lineTo(w, gy + 0.5); ctx.stroke(); }
    // bars
    for (var r = 0; r < N; r++) {
      var t = sim.order[r], re = sim.re[t], im = sim.im[t];
      var a = Math.hypot(re, im), hh = (a / ymax) * H;
      var hue = ((Math.atan2(im, re) * 180) / Math.PI + 210 + 360) % 360;
      ctx.fillStyle = "hsl(" + hue.toFixed(0) + " 78% " + (bestRank[r] ? 66 : 60) + "%)";
      var x0 = r * bw, gap = bw > 3 ? 0.6 : 0.2;
      ctx.fillRect(x0 + gap / 2, bottom - hh, Math.max(bw - gap, 0.6), hh);
    }
    // the start state, which is also a random valid pick
    var uy = bottom - (1 / Math.sqrt(N) / ymax) * H;
    ctx.setLineDash([5, 5]); ctx.strokeStyle = "rgba(238,243,250,0.55)"; ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.moveTo(0, uy); ctx.lineTo(w, uy); ctx.stroke(); ctx.setLineDash([]);
    ctx.font = "12px Inter, Segoe UI, system-ui, sans-serif"; ctx.fillStyle = "rgba(238,243,250,0.75)";
    ctx.textAlign = "left"; ctx.fillText("start state = random valid pick", 6, uy - 6);
    // baseline and best-plan marker
    ctx.strokeStyle = "rgba(158,197,244,0.35)"; ctx.beginPath(); ctx.moveTo(0, bottom + 0.5); ctx.lineTo(w, bottom + 0.5); ctx.stroke();
    for (var b = 0; b < N; b++) if (bestRank[b]) {
      var cx = (b + 0.5) * bw;
      ctx.fillStyle = "#f2b33d"; ctx.beginPath(); ctx.moveTo(cx, bottom + 3); ctx.lineTo(cx - 5, bottom + 11); ctx.lineTo(cx + 5, bottom + 11); ctx.closePath(); ctx.fill();
      ctx.textAlign = "right"; ctx.fillText("best plan", cx - 8, bottom + 12);
    }
    if (hoverRank != null) {
      ctx.strokeStyle = "rgba(255,255,255,0.8)"; ctx.lineWidth = 1;
      ctx.strokeRect(hoverRank * bw, top, bw, H);
    }
  }

  // tooltip, shared with the rest of the site
  var tipNode = $("#tip"), hoverRank = null;
  function showTip(html, e) {
    if (!tipNode) return;
    tipNode.innerHTML = html; tipNode.classList.add("show");
    var x = e.clientX + 16, y = e.clientY + 16, r = tipNode.getBoundingClientRect();
    if (x + r.width > window.innerWidth - 8) x = e.clientX - r.width - 16;
    if (y + r.height > window.innerHeight - 8) y = e.clientY - r.height - 16;
    tipNode.style.left = x + "px"; tipNode.style.top = y + "px";
  }
  function hideTip() { if (tipNode) tipNode.classList.remove("show"); }
  ampCanvas.addEventListener("pointermove", function (e) {
    var rect = ampCanvas.getBoundingClientRect(), r = Math.floor(((e.clientX - rect.left) / rect.width) * N);
    if (r < 0 || r >= N) return;
    hoverRank = r;
    var s = sim.order[r], prob = sim.re[s] * sim.re[s] + sim.im[s] * sim.im[s];
    showTip("<b>" + planNames(sim.masks[s]).join(", ") + "</b>" +
      '<div class="row"><span>Value / best plan</span><span>' + pct(sim.value[s] / sim.best, 0) + "</span></div>" +
      '<div class="row"><span>Chance per shot</span><span>' + pct(prob, 2) + "</span></div>" +
      '<div class="row"><span>Rank</span><span>' + (N - r) + " of " + N + "</span></div>", e);
    drawAmp();
  });
  ampCanvas.addEventListener("pointerleave", function () { hoverRank = null; hideTip(); drawAmp(); });

  // ------------------------------------------------------------- step chips
  var stagesEl = $("#lab-stages");
  function buildStages() {
    stagesEl.innerHTML = "";
    ops(S.p).forEach(function (o, i) {
      var b = document.createElement("button");
      b.type = "button"; b.className = "stage " + o.type;
      b.innerHTML = '<i class="fill"></i><span>' +
        (o.type === "start" ? "Dicke start" : o.type === "cost" ? "Cost, layer " + (o.l + 1) : "Mixer, layer " + (o.l + 1)) + "</span>";
      b.addEventListener("click", function () { stop(); S.interacted = true; S.op = i; S.frac = 1; update(); });
      stagesEl.appendChild(b);
    });
  }
  function paintStages() {
    Array.prototype.forEach.call(stagesEl.children, function (b, i) {
      var fill = b.querySelector(".fill");
      b.classList.toggle("done", i < S.op || (i === S.op && S.frac >= 1));
      b.classList.toggle("now", i === S.op);
      fill.style.width = (i < S.op ? 100 : i === S.op ? S.frac * 100 : 0) + "%";
    });
  }

  var caption = $("#lab-caption");
  function captionText() {
    var o = ops(S.p)[S.op], m = sim.metrics();
    if (o.type === "start") return "The circuit starts in the Dicke state: every plan with exactly " + sim.k + " kits, all with the same amplitude. Measuring now is the same as a random valid pick.";
    if (o.type === "cost") return "Cost layer " + (o.l + 1) + ": one ZZ rotation per couple link and one Z rotation per relative. No bar changes height. Each plan's phase turns by an amount set by its value, so the colours fan out from the worst plans to the best.";
    if (atEnd()) return "After " + S.p + (S.p === 1 ? " layer" : " layers") + ", one shot is the best plan " + pct(m.p_opt) + " of the time, against " + pct(randomPopt, 2) + " for a random valid pick. No shot ever uses more or fewer than " + sim.k + " kits.";
    return "Mixer, layer " + (o.l + 1) + ": XX+YY rotations swap a tested and an untested relative, so plans one swap apart interfere. The phase pattern from the cost layer turns into height: good plans grow, bad plans shrink, and the number of kits stays at " + sim.k + ".";
  }

  // --------------------------------------------------------------- readouts
  function paintReadouts() {
    var m = sim.metrics(), x = m.p_opt / randomPopt;
    $("#lab-popt").textContent = pct(m.p_opt, 2);
    $("#lab-vs").textContent = x > 1.05 ? x.toFixed(1) + "× a random valid pick (" + pct(randomPopt, 2) + ")" : x < 0.95 ? "below a random valid pick (" + pct(randomPopt, 2) + ")" : "same as a random valid pick";
    $("#lab-meter").style.width = Math.min(100, m.quality * 100) + "%";
    $("#lab-ratio").textContent = pct(m.ratio, 0) + " of the best plan";
    $("#lab-quality").textContent = m.quality.toFixed(3);
    var t = trained[S.p], check = $("#lab-check");
    if (!atEnd()) check.textContent = "Readouts follow the state at the highlighted step of the circuit.";
    else if (isTrained() && t.browser) check.innerHTML = "This visit was tuned in your browser with the recipe of the Python code (a grid, then warm starts for each depth; Nelder-Mead in place of COBYLA), in " + t.evals + " circuit evaluations. For the full family the same recipe gives Qiskit's numbers exactly.";
    else if (isTrained()) check.innerHTML = "Check against Qiskit: these are the angles COBYLA found with the Aer Estimator for depth " + S.p + ". Qiskit's statevector gives " + pct(t.p_opt, 2) + "; this page gives <b>" + pct(m.p_opt, 2) + "</b>.";
    else if (S.source === "tuned") check.innerHTML = "Tuned in your browser by Nelder-Mead in " + S.evals + " circuit evaluations: " + pct(m.ratio, 0) + " of the best value per shot. " + (t && t.browser ? "The full tuning recipe" : "Qiskit's COBYLA") + " reached " + pct(t ? t.ratio : NaN, 0) + " at this depth.";
    else check.textContent = "Your angles. The " + (t && t.browser ? "tuned" : "Qiskit") + " angles give " + pct(t ? t.p_opt : NaN, 2) + " for depth " + S.p + ".";
    $("#lab-kits-label").textContent = "Shots that break the " + sim.k + "-kit limit";
    $("#lab-trained").textContent = V.custom ? "Use the tuned angles" : "Use Qiskit's angles";
  }

  // -------------------------------------------------------------- landscape
  var land = $("#lab-land"), landCtx = land.getContext("2d");
  var GX = 90, GY = 56, img = document.createElement("canvas"), imgCtx = img.getContext("2d");
  img.width = GX; img.height = GY;
  var landVals = new Float64Array(GX * GY), landJob = 0, landReady = false;
  var stops = [[6, 17, 31], [20, 52, 99], [42, 120, 214], [134, 182, 239], [255, 236, 179]];
  function cmap(t) {
    t = Math.max(0, Math.min(1, t)) * (stops.length - 1);
    var i = Math.min(Math.floor(t), stops.length - 2), f = t - i, a = stops[i], b = stops[i + 1];
    return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f];
  }
  function gammaAt(ix) { return G_RANGE[0] + ((ix + 0.5) / GX) * (G_RANGE[1] - G_RANGE[0]); }
  function betaAt(iy) { return B_RANGE[1] - ((iy + 0.5) / GY) * (B_RANGE[1] - B_RANGE[0]); }
  function computeLandscape() {
    var job = ++landJob, row = 0, base = S.angles.slice(), p = S.p;
    landReady = false;
    $("#lab-land-sub").textContent = p === 1
      ? "Expected value for every pair of angles. Click or drag to move them; brighter is better."
      : "Expected value as the first-layer angles change, with layers 2 to " + p + " held where they are. Click or drag to move them; brighter is better.";
    function chunk() {
      if (job !== landJob) return;
      var t0 = performance.now(), th = base.slice();
      while (row < GY && performance.now() - t0 < 10) {
        for (var ix = 0; ix < GX; ix++) {
          th[0] = gammaAt(ix); th[p] = betaAt(row);
          landVals[row * GX + ix] = calc.f(th);
        }
        row++;
      }
      paintLandImage(row);
      if (row < GY) requestAnimationFrame(chunk);
      else landReady = true;
      drawLand();
    }
    requestAnimationFrame(chunk);
  }
  function paintLandImage(rows) {
    var data = imgCtx.createImageData(GX, GY), lo = Infinity, hi = -Infinity, i;
    for (i = 0; i < GX * rows; i++) { lo = Math.min(lo, landVals[i]); hi = Math.max(hi, landVals[i]); }
    if (!(hi > lo)) { lo = sim.worst; hi = sim.best; }
    for (i = 0; i < GX * rows; i++) {
      var c = cmap(Math.pow((landVals[i] - lo) / (hi - lo), 1.6));
      data.data[i * 4] = c[0]; data.data[i * 4 + 1] = c[1]; data.data[i * 4 + 2] = c[2]; data.data[i * 4 + 3] = 255;
    }
    for (var j = GX * rows; j < GX * GY; j++) data.data[j * 4 + 3] = 0;
    imgCtx.putImageData(data, 0, 0);
  }
  function toLand(g, b, w, h) {
    return [((g - G_RANGE[0]) / (G_RANGE[1] - G_RANGE[0])) * w, ((B_RANGE[1] - b) / (B_RANGE[1] - B_RANGE[0])) * h];
  }
  function drawLand() {
    var dim = sizeCanvas(land), ctx = landCtx, w = dim.w, h = dim.h;
    ctx.setTransform(dim.dpr, 0, 0, dim.dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "#06111f"; ctx.fillRect(0, 0, w, h);
    ctx.imageSmoothingEnabled = true; ctx.drawImage(img, 0, 0, w, h);
    ctx.font = "11px Inter, Segoe UI, system-ui, sans-serif"; ctx.fillStyle = "rgba(238,243,250,0.55)";
    ctx.textAlign = "left"; ctx.fillText(G_RANGE[0].toFixed(1), 4, h - 5);
    ctx.textAlign = "right"; ctx.fillText("+" + G_RANGE[1].toFixed(1), w - 4, h - 5);
    ctx.fillText("π", w - 4, 13);
    var p = S.p;
    if (S.path.length > 1) {
      ctx.strokeStyle = "rgba(255,255,255,0.9)"; ctx.lineWidth = 1.6; ctx.beginPath();
      S.path.forEach(function (q, i) { var xy = toLand(q[0], q[1], w, h); if (i) ctx.lineTo(xy[0], xy[1]); else ctx.moveTo(xy[0], xy[1]); });
      ctx.stroke();
    }
    var t = trained[p];
    if (t) {
      var txy = toLand(t.angles[0], t.angles[p], w, h);
      ctx.strokeStyle = "#f2b33d"; ctx.lineWidth = 2; ctx.beginPath();
      ctx.moveTo(txy[0], txy[1] - 7); ctx.lineTo(txy[0] + 7, txy[1]); ctx.lineTo(txy[0], txy[1] + 7); ctx.lineTo(txy[0] - 7, txy[1]); ctx.closePath(); ctx.stroke();
      ctx.fillStyle = "#f2b33d"; ctx.textAlign = "left"; ctx.fillText("Qiskit", txy[0] + 10, txy[1] + 4);
    }
    var xy = toLand(S.angles[0], S.angles[p], w, h);
    ctx.fillStyle = "#fff"; ctx.strokeStyle = "#06111f"; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.arc(xy[0], xy[1], 6.5, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    if (!landReady) { ctx.fillStyle = "rgba(238,243,250,0.7)"; ctx.textAlign = "left"; ctx.fillText("computing the landscape…", 8, 16); }
  }
  function setFromLand(e) {
    var rect = land.getBoundingClientRect();
    var fx = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    var fy = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
    S.angles[0] = G_RANGE[0] + fx * (G_RANGE[1] - G_RANGE[0]);
    S.angles[S.p] = B_RANGE[1] - fy * (B_RANGE[1] - B_RANGE[0]);
    userMoved();
  }
  var dragging = false;
  land.tabIndex = 0;
  land.addEventListener("pointerdown", function (e) { stopAll(); dragging = true; land.setPointerCapture(e.pointerId); setFromLand(e); });
  land.addEventListener("pointermove", function (e) { if (dragging) setFromLand(e); });
  land.addEventListener("pointerup", function () { dragging = false; });
  land.addEventListener("keydown", function (e) {
    var dg = { ArrowLeft: -0.03, ArrowRight: 0.03 }[e.key], db = { ArrowUp: 0.03, ArrowDown: -0.03 }[e.key];
    if (dg == null && db == null) return;
    e.preventDefault(); stopAll();
    if (dg) S.angles[0] = Math.max(G_RANGE[0], Math.min(G_RANGE[1], S.angles[0] + dg));
    if (db) S.angles[S.p] = Math.max(B_RANGE[0], Math.min(B_RANGE[1], S.angles[S.p] + db));
    userMoved();
  });

  // ---------------------------------------------------------------- sliders
  var slidersEl = $("#lab-sliders");
  function buildSliders() {
    slidersEl.innerHTML = "";
    for (var l = 0; l < S.p; l++) {
      [["γ", l, G_RANGE], ["β", S.p + l, B_RANGE]].forEach(function (spec) {
        var wrap = document.createElement("label"); wrap.className = "slider";
        wrap.innerHTML = "<span>" + spec[0] + "<sub>" + (l + 1) + "</sub></span>" +
          '<input type="range" min="' + spec[2][0] + '" max="' + spec[2][1].toFixed(4) + '" step="0.005">' +
          "<output></output>";
        var input = wrap.querySelector("input"), idx = spec[1];
        input.setAttribute("aria-label", (spec[0] === "γ" ? "gamma " : "beta ") + (l + 1));
        input.dataset.idx = idx;
        input.addEventListener("input", function () { stopAll(); S.angles[idx] = parseFloat(input.value); userMoved(true); });
        input.addEventListener("change", function () { if (idx !== 0 && idx !== S.p) computeLandscape(); });
        slidersEl.appendChild(wrap);
      });
    }
  }
  function paintSliders() {
    Array.prototype.forEach.call(slidersEl.querySelectorAll("input"), function (input) {
      var v = S.angles[+input.dataset.idx];
      if (document.activeElement !== input) input.value = v;
      input.nextElementSibling.textContent = v.toFixed(3);
    });
  }

  // ----------------------------------------------------------- measurement
  var bitsEl = $("#lab-bits");
  function buildBits() {
    bitsEl.innerHTML = "";
    for (var i = 0; i < sim.n; i++) {
      var b = document.createElement("div"); b.className = "bit"; b.title = labels[i];
      b.innerHTML = "0<small>q" + i + "</small>"; bitsEl.appendChild(b);
    }
  }
  function showBits(mask) {
    Array.prototype.forEach.call(bitsEl.children, function (b, i) {
      var on = (mask >> i) & 1;
      b.className = "bit" + (on ? " on" : "");
      b.firstChild.nodeValue = on ? "1" : "0";
      void b.offsetWidth; b.classList.add("flash");
    });
  }
  function resetTally() {
    S.tally = new Map(); S.shots = 0;
    $("#lab-tally").innerHTML = ""; $("#lab-shot-plan").textContent = "No shots yet.";
    showBits(0);
    Array.prototype.forEach.call(bitsEl.children, function (b) { b.classList.remove("flash"); });
  }
  function measure(shots) {
    S.interacted = true; stopAll();
    var draws = sim.sample(shots, rnd), bestIdx = -1;
    draws.forEach(function (s) {
      S.tally.set(s, (S.tally.get(s) || 0) + 1);
      if (bestIdx < 0 || sim.value[s] > sim.value[bestIdx]) bestIdx = s;
    });
    S.shots += shots;
    var shown = shots === 1 ? draws[0] : bestIdx, isBest = sim.value[shown] >= sim.best - 1e-12;
    showBits(sim.masks[shown]);
    $("#lab-shot-plan").innerHTML = (shots === 1 ? "This shot tests " : "Best of these " + shots + " shots tests ") +
      planNames(sim.masks[shown]).join(", ") + ": " +
      (isBest ? '<span class="best">the best plan.</span>' : pct(sim.value[shown] / sim.best, 0) + " of the best plan's value.");
    var rows = Array.from(S.tally.entries()).sort(function (a, b) { return b[1] - a[1] || sim.value[b[0]] - sim.value[a[0]]; }).slice(0, 5);
    var bestHits = 0;
    S.tally.forEach(function (c, s) { if (sim.value[s] >= sim.best - 1e-12) bestHits += c; });
    var max = rows.length ? rows[0][1] : 1;
    $("#lab-tally").innerHTML = '<div class="lab-sub" style="margin:0">' + S.shots + (S.shots === 1 ? " shot" : " shots") +
      " so far, " + S.tally.size + " different plans. The best plan came up " + bestHits + " times (" + pct(bestHits / S.shots, 1) + ").</div>" +
      rows.map(function (r) {
        var best = sim.value[r[0]] >= sim.best - 1e-12;
        return '<div class="tally-row' + (best ? " best" : "") + '"><span class="tl" title="' + planNames(sim.masks[r[0]]).join(", ") + '">' +
          (best ? "Best plan: " : "") + planNames(sim.masks[r[0]]).join(", ") + '</span><span class="tb"><i style="width:' +
          ((r[1] / max) * 100).toFixed(1) + '%"></i></span><span class="tc">' + r[1] + "</span></div>";
      }).join("");
  }
  $("#lab-shot1").addEventListener("click", function () { measure(1); });
  $("#lab-shot100").addEventListener("click", function () { measure(100); });

  // ------------------------------------------------------------- the loop
  var lastKey = "";
  function update() {
    evolve();
    var key = S.p + "|" + S.op + "|" + S.frac.toFixed(4) + "|" + S.angles.join(",");
    if (key !== lastKey && S.shots) resetTally();
    lastKey = key;
    drawAmp(); paintStages(); paintReadouts(); paintSliders(); drawLand();
    caption.textContent = captionText();
  }
  function userMoved(fromSlider) {
    S.interacted = true; S.source = "user"; S.path = [];
    S.op = ops(S.p).length - 1; S.frac = 1;
    if (!fromSlider) paintSliders();
    update();
  }

  var raf = 0;
  function stop() { if (raf) cancelAnimationFrame(raf); raf = 0; S.playing = false; playBtn.querySelector("span").textContent = "Play the circuit"; }
  function stopAll() { stop(); S.optimising = false; }
  var playBtn = $("#lab-play");
  function play() {
    stopAll();
    var list = ops(S.p);
    if (reduce) { S.op = list.length - 1; S.frac = 1; update(); return; }
    S.playing = true; S.op = 0; S.frac = 1;
    playBtn.querySelector("span").textContent = "Playing…";
    var stepMs = 1300, t0 = performance.now() + 500;
    function frame(now) {
      var t = Math.max(0, now - t0), i = Math.floor(t / stepMs) + 1, f = (t % stepMs) / stepMs;
      if (now < t0) { S.op = 0; S.frac = 1; }
      else if (i >= list.length) { S.op = list.length - 1; S.frac = 1; }
      else { S.op = i; S.frac = f < 0.85 ? 0.5 - 0.5 * Math.cos((Math.PI * f) / 0.85) : 1; }
      update();
      if (now >= t0 && i >= list.length) { stop(); return; }
      raf = requestAnimationFrame(frame);
    }
    raf = requestAnimationFrame(frame);
  }
  playBtn.addEventListener("click", function () { S.interacted = true; if (S.playing) { stop(); return; } play(); });

  $("#lab-trained").addEventListener("click", function () {
    stopAll(); S.interacted = true;
    if (trained[S.p]) S.angles = trained[S.p].angles.slice();
    S.source = "qiskit"; S.path = []; S.op = ops(S.p).length - 1; S.frac = 1;
    computeLandscape(); update();
  });
  $("#lab-reset").addEventListener("click", function () { stopAll(); S.interacted = true; S.op = 0; S.frac = 1; update(); });

  $("#lab-opt").addEventListener("click", function () {
    stopAll(); S.interacted = true;
    var p = S.p, x0 = S.source === "user" ? S.angles.slice() : (function () {
      var a = []; for (var l = 0; l < p; l++) a.push(0.1); for (l = 0; l < p; l++) a.push(0.2); return a;
    })();
    var evals = 0, f = function (th) { evals++; return calc.f(th); };
    var it = QAOASim.nelderMead(f, x0, 0.2, 160);
    S.optimising = true; S.path = [[x0[0], x0[p]]]; S.source = "tuned"; S.op = ops(p).length - 1; S.frac = 1;
    var btn = this; btn.disabled = true;
    function step() {
      if (!S.optimising) { btn.disabled = false; return; }
      var r;
      for (var k = 0; k < (reduce ? 400 : 1); k++) { r = it.next(); if (r.done || r.value.done) break; }
      if (r.value) { S.angles = r.value.x.slice(); S.path.push([S.angles[0], S.angles[p]]); }
      S.evals = evals; update();
      if (r.done || (r.value && r.value.done)) { S.optimising = false; btn.disabled = false; if (p > 1) computeLandscape(); return; }
      raf = requestAnimationFrame(step);
    }
    raf = requestAnimationFrame(step);
  });

  var depthBtns = document.querySelectorAll("#lab-depth button");
  function setDepth(p) {
    stopAll(); S.p = p; S.path = []; S.source = "qiskit";
    S.angles = trained[p] ? trained[p].angles.slice() : S.angles;
    S.op = ops(p).length - 1; S.frac = 1;
    Array.prototype.forEach.call(depthBtns, function (b) { b.setAttribute("aria-checked", String(+b.dataset.p === p)); b.tabIndex = +b.dataset.p === p ? 0 : -1; });
    buildStages(); buildSliders(); computeLandscape(); update(); renderCompare();
  }
  Array.prototype.forEach.call(depthBtns, function (b) {
    b.addEventListener("click", function () { S.interacted = true; setDepth(+b.dataset.p); });
  });

  // ------------------------------------------------------ plan today's visit
  var SVGNS = "http://www.w3.org/2000/svg", planSvg = $("#plan-svg"), people = D.people || [];
  var byId = {};
  people.forEach(function (p) { byId[p.id] = p; });
  var qubitOf = {};                      // person id -> index in D.candidates
  D.candidates.forEach(function (c, q) { qubitOf[c.id] = q; });
  var VW = 640, VH = 352;
  function px(p) { return 26 + p.x * (VW - 52); }
  function py(p) { return 26 + p.y * 84; }
  function el(tag, attrs, parent) {
    var n = document.createElementNS(SVGNS, tag);
    for (var a in attrs) n.setAttribute(a, attrs[a]);
    if (parent) parent.appendChild(n);
    return n;
  }
  function shortLabel(label) {
    return label.replace("Paternal ", "P. ").replace("Maternal ", "M. ").replace(/^Husband of .*/, "Husband").replace(/^Wife of .*/, "Wife");
  }
  var pairLinks = [];                    // couple links that count in the objective
  function buildTree() {
    planSvg.innerHTML = "";
    var svg = el("svg", { viewBox: "0 0 " + VW + " " + VH, role: "img", "aria-label": "Family tree. Testable relatives can be switched on or off." }, planSvg);
    var lines = el("g", { class: "t-lines" }, svg), pairs = el("g", {}, svg), nodes = el("g", {}, svg);
    var seen = {};
    people.forEach(function (c) {
      if (c.father == null || c.mother == null) return;
      var f = byId[c.father], m = byId[c.mother], key = c.father + "-" + c.mother;
      var mx = (px(f) + px(m)) / 2, y0 = py(f), yb = y0 + 42;
      if (!seen[key]) { seen[key] = 1; el("line", { x1: px(f), y1: y0, x2: px(m), y2: py(m), class: "t-mar" }, lines); }
      el("path", { d: "M" + mx + " " + y0 + "V" + yb + "H" + px(c) + "V" + (py(c) - 12), class: "t-kin" }, lines);
    });
    pairLinks = [];
    (D.couples || []).forEach(function (cp) {
      if (!cp.in_problem) return;
      var a = byId[cp.a], b = byId[cp.b], d;
      if (cp.kind === "married") d = "M" + px(a) + " " + py(a) + "L" + px(b) + " " + py(b);
      else {
        var x1 = px(a), x2 = px(b), y = py(a) + 33, depth = 14 + Math.abs(x2 - x1) * 0.1;
        d = "M" + x1 + " " + y + "Q" + (x1 + x2) / 2 + " " + (y + depth) + " " + x2 + " " + y;
      }
      var path = el("path", { d: d, class: "t-pair " + cp.kind }, pairs);
      pairLinks.push({ a: qubitOf[cp.a], b: qubitOf[cp.b], node: path, w: cp.w * cp.strength });
    });
    people.forEach(function (p) {
      var q = qubitOf[p.id], cand = q != null;
      var g = el("g", { class: "t-node " + p.status + (p.sex === "F" ? " f" : " m"), transform: "translate(" + px(p) + " " + py(p) + ")" }, nodes);
      if (p.sex === "F") el("circle", { r: 12, class: "shape" }, g);
      else el("rect", { x: -12, y: -12, width: 24, height: 24, rx: 2, class: "shape" }, g);
      if (p.status === "deceased") el("line", { x1: -15, y1: 15, x2: 15, y2: -15, class: "slash" }, g);
      if (cand) {
        el("text", { y: 4, class: "pv" }, g).textContent = p.p.toFixed(2).replace(/^0/, "");
        var t = el("text", { y: 27, class: "pl" }, g); t.textContent = shortLabel(p.label);
        g.setAttribute("tabindex", "0"); g.setAttribute("role", "button"); g.dataset.q = q;
        var toggle = function () { toggleRelative(q); };
        g.addEventListener("click", toggle);
        g.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } });
      } else if (p.role === "father" || p.role === "mother" || p.role === "proband") {
        el("text", { y: 27, class: "pl dim" }, g).textContent = p.role === "proband" ? "Index child" : p.label;
      }
      g.addEventListener("pointerenter", function (e) {
        var note = cand ? (V.avail.indexOf(q) >= 0 ? "Can be tested today. Tap to mark as not available." : "Not available today. Tap to bring back.")
          : p.status === "affected" ? "Affected child: already diagnosed." : p.status === "obligate" ? "Parent of the affected child: a carrier for certain, so no kit is needed."
          : p.status === "deceased" ? "Deceased." : "Not part of this visit.";
        showTip("<b>" + p.label + "</b>" + (p.p != null && p.status !== "affected" ? '<div class="row"><span>Carrier probability</span><span>' + p.p.toFixed(3) + "</span></div>" : "") + "<div>" + note + "</div>", e);
      });
      g.addEventListener("pointermove", function (e) { if (tipNode && tipNode.classList.contains("show")) showTip(tipNode.innerHTML, e); });
      g.addEventListener("pointerleave", hideTip);
    });
  }

  function toggleRelative(q) {
    var i = V.avail.indexOf(q);
    if (i >= 0) { if (V.avail.length <= 2) return; V.avail.splice(i, 1); }
    else { V.avail.push(q); V.avail.sort(function (a, b) { return a - b; }); }
    V.k = Math.max(1, Math.min(V.k, V.avail.length - 1));
    reconfigure();
  }
  $("#kit-minus").addEventListener("click", function () { if (V.k > 1) { V.k--; reconfigure(); } });
  $("#kit-plus").addEventListener("click", function () { if (V.k < Math.min(6, V.avail.length - 1)) { V.k++; reconfigure(); } });
  $("#plan-restore").addEventListener("click", function () {
    V.avail = D.candidates.map(function (c, q) { return q; }); V.k = D.k; reconfigure();
  });

  function reconfigure() {
    stopAll(); S.interacted = true; hideTip();
    loadInstance();
    S.angles = trained[S.p].angles.slice(); S.source = V.custom ? "browser" : "qiskit";
    S.path = []; S.op = ops(S.p).length - 1; S.frac = 1; S.tally = new Map(); S.shots = 0;
    buildBits(); resetTally(); buildStages(); buildSliders(); computeLandscape(); update();
    renderPlan(); renderCompare();
  }

  /** Map a mask of the current instance back to the family's candidate indices. */
  function toFamily(mask) {
    var out = [];
    for (var i = 0; i < sim.n; i++) if ((mask >> i) & 1) out.push(V.avail[i]);
    return out;
  }
  function couplesFound(mask) {
    var v = 0;
    for (var i = 0; i < sim.n; i++) for (var j = i + 1; j < sim.n; j++)
      if (((mask >> i) & 1) && ((mask >> j) & 1)) v += sim.W[i][j];
    return v;
  }
  function valueOf(mask) {
    var v = couplesFound(mask);
    for (var i = 0; i < sim.n; i++) if ((mask >> i) & 1) v += sim.h[i];
    return v;
  }
  function fieldRule() {
    var idx = V.avail.map(function (q, i) { return i; });
    idx.sort(function (a, b) { return problem.p[b] - problem.p[a] || a - b; });
    return idx.slice(0, sim.k).reduce(function (m, i) { return m | (1 << i); }, 0);
  }
  function exactPlan() {
    var best = -Infinity, mask = 0;
    for (var s = 0; s < N; s++) if (sim.value[s] > best + 1e-12) { best = sim.value[s]; mask = sim.masks[s]; }
    return mask;
  }
  function qaoaPlan() {
    var t = trained[3], shots = 4096;
    calc.run(t.angles);
    var draws = calc.sample(shots, mulberry(7)), bestS = draws[0];
    draws.forEach(function (s) { if (calc.value[s] > calc.value[bestS]) bestS = s; });
    return { mask: calc.masks[bestS], shots: shots, p_opt: calc.metrics().p_opt };
  }

  function renderPlan() {
    var exact = exactPlan(), field = fieldRule(), q = qaoaPlan(), best = sim.best;
    var picked = toFamily(q.mask), match = valueOf(q.mask) >= best - 1e-12;
    $("#kit-count").textContent = sim.k;
    $("#kit-minus").disabled = sim.k <= 1;
    $("#kit-plus").disabled = sim.k >= Math.min(6, V.avail.length - 1);
    // the tree
    Array.prototype.forEach.call(planSvg.querySelectorAll(".t-node[data-q]"), function (g) {
      var qq = +g.dataset.q, away = V.avail.indexOf(qq) < 0;
      g.classList.toggle("away", away);
      g.classList.toggle("tested", picked.indexOf(qq) >= 0);
      g.setAttribute("aria-pressed", String(!away));
      g.setAttribute("aria-label", D.candidates[qq].label + (away ? ", not available today" : picked.indexOf(qq) >= 0 ? ", tested in this plan" : ", available"));
    });
    pairLinks.forEach(function (l) {
      var both = picked.indexOf(l.a) >= 0 && picked.indexOf(l.b) >= 0;
      var gone = V.avail.indexOf(l.a) < 0 || V.avail.indexOf(l.b) < 0;
      l.node.classList.toggle("both", both); l.node.classList.toggle("gone", gone);
    });
    // the cards
    function names(mask) { return toFamily(mask).map(function (qq) { return D.candidates[qq].label; }).join(", "); }
    function card(cls, title, mask, extra) {
      var v = valueOf(mask), c = couplesFound(mask);
      return '<div class="pcard ' + cls + '"><div class="pc-head"><b>' + title + '</b><span class="pc-pct num">' + pct(best > 0 ? v / best : 1, 0) + '</span></div>' +
        '<div class="pc-names">' + names(mask) + '</div>' +
        '<div class="pc-meta">' + c.toFixed(3) + " expected at-risk couples found" + (extra || "") + "</div></div>";
    }
    var combos = N.toLocaleString("en-US");
    $("#plan-cards").innerHTML =
      card("qaoa", "Constrained QAOA plan", q.mask,
        '<br>Best of ' + q.shots.toLocaleString("en-US") + " shots at depth 3. One shot is the best plan " + pct(q.p_opt, 1) + " of the time; a random pick, " + pct(randomPopt, 2) + ".") +
      '<div class="pc-verdict ' + (match ? "ok" : "miss") + '">' + (match ? "Matches the exact optimum." : "Below the exact optimum.") + "</div>" +
      card("exact", "Exact optimum", exact, "<br>Brute force over all " + combos + " valid plans.") +
      card("field", "Field officer's rule", field, "<br>The " + sim.k + " highest carrier probabilities.");
  }

  // ------------------------------------------- penalty against constrained
  function renderCompare() {
    if (!pen || !penTrained[S.p]) return;
    var p = S.p, n = sim.n, k = sim.k;
    var pm = pen.run(penTrained[p].angles).metrics();
    var cm = calc.run(trained[p].angles).metrics();
    var conW = new Float64Array(n + 1); conW[k] = 1;
    function bars(id, byW) {
      var host = $(id), max = 0, i;
      for (i = 0; i <= n; i++) max = Math.max(max, byW[i]);
      if (host.children.length !== n + 1) {
        host.innerHTML = "";
        for (i = 0; i <= n; i++) {
          var col = document.createElement("div"); col.className = "cmp-bar" + (i === k ? " ok" : "");
          col.innerHTML = '<span class="cv"></span><i></i><span class="ck">' + i + "</span>";
          host.appendChild(col);
        }
      }
      Array.prototype.forEach.call(host.children, function (col, j) {
        col.classList.toggle("ok", j === k);
        col.querySelector("i").style.height = ((byW[j] / Math.max(max, 1e-9)) * 100).toFixed(1) + "%";
        col.querySelector(".cv").textContent = byW[j] >= 0.01 ? Math.round(byW[j] * 100) + "%" : "";
        col.title = j + (j === 1 ? " kit: " : " kits: ") + pct(byW[j], 1) + " of shots";
      });
    }
    bars("#cmp-pen", pm.byWeight); bars("#cmp-con", conW);
    function kv(id, m, valid) {
      $(id).innerHTML = "<dt>Shots that use exactly " + k + " kits</dt><dd>" + pct(valid, 1) + "</dd>" +
        "<dt>One shot is the best plan</dt><dd>" + pct(m.p_opt, 2) + "</dd>" +
        "<dt>Quality of the valid shots</dt><dd>" + m.quality.toFixed(2) + "</dd>";
    }
    kv("#cmp-pen-kv", pm, pm.valid_share); kv("#cmp-con-kv", cm, 1);
    $("#cmp-pen-gates").textContent = pen.zzCount + " ZZ rotations per layer";
    $("#cmp-con-gates").textContent = problem.edges.length + " ZZ + " + sim.pairs.length + " XY rotations per layer";
    $("#cmp-sub").textContent = 'Standard QAOA cannot hold a rule like "exactly ' + k + ' kits". It starts from every one of the ' +
      (1 << n).toLocaleString("en-US") + " bitstrings and has to learn the rule from a penalty term, which also needs a rotation on every pair of qubits. " +
      "Both circuits are simulated exactly at depth " + p + ", with angles tuned for this visit. Bars show where the shots land, by the number of kits a measured plan uses.";
    var t = penTrained[p];
    $("#cmp-check").innerHTML = t.browser
      ? "Both circuits were tuned in your browser with the same recipe. Shots that break the kit limit are wasted: a field officer cannot use them."
      : "Check against Qiskit: for the penalty circuit at depth " + p + ", Qiskit's statevector gives " + pct(t.valid_share, 1) + " valid shots and " + pct(t.p_opt, 2) +
        " for the best plan; this page gives <b>" + pct(pm.valid_share, 1) + "</b> and <b>" + pct(pm.p_opt, 2) + "</b>.";
  }

  // ---------------------------------------------------------------- start
  buildBits();
  buildTree();
  setDepth(3);
  S.op = 0; S.frac = 1; update();
  renderPlan(); renderCompare();
  if (window.ResizeObserver) new ResizeObserver(function () { drawAmp(); drawLand(); }).observe($("#lab-shell"));
  else window.addEventListener("resize", function () { drawAmp(); drawLand(); });

  // Play once when the section scrolls into view, unless the visitor got there first.
  if ("IntersectionObserver" in window && !reduce) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { io.disconnect(); if (!S.interacted) setTimeout(function () { if (!S.interacted) play(); }, 350); }
      });
    }, { threshold: 0.45 });
    io.observe($("#lab-amp"));
  }
})();
