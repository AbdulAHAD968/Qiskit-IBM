/* Section 6: run the constrained QAOA circuit live, on the instance of section 4. */
(function () {
  "use strict";
  var K = window.KINSHIP, D = K && K.demo;
  if (!D || !window.QAOASim || !document.getElementById("lab")) return;

  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var $ = function (s) { return document.querySelector(s); };
  var problem = {
    n: D.n, k: D.k, lam: D.lam,
    p: D.candidates.map(function (c) { return c.p; }),
    r: D.candidates.map(function (c) { return c.r; }),
    edges: D.edges,
  };
  var sim = new QAOASim.Sim(problem);     // the state on screen
  var calc = new QAOASim.Sim(problem);    // scratch copy for the landscape and the optimiser
  var N = sim.N, labels = D.candidates.map(function (c) { return c.label; });
  var trained = {};
  (D.qaoa || []).forEach(function (q) { if (q.method === "constrained") trained[q.p] = q; });
  var randomPopt = sim.optimalCount() / N;
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
    for (var i = 0; i < D.n; i++) if ((mask >> i) & 1) out.push(labels[i]);
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
  var ampMax = (function () {
    var m = 1 / Math.sqrt(N);
    [1, 2, 3].forEach(function (p) {
      if (!trained[p]) return;
      sim.run(trained[p].angles);
      for (var s = 0; s < N; s++) m = Math.max(m, Math.hypot(sim.re[s], sim.im[s]));
    });
    return m * 1.08;
  })();
  var bestRank = sim.order.map(function (s) { return sim.value[s] >= sim.best - 1e-12; });

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
    if (o.type === "start") return "The circuit starts in the Dicke state: every plan with exactly " + D.k + " kits, all with the same amplitude. Measuring now is the same as a random valid pick.";
    if (o.type === "cost") return "Cost layer " + (o.l + 1) + ": one ZZ rotation per couple link and one Z rotation per relative. No bar changes height. Each plan's phase turns by an amount set by its value, so the colours fan out from the worst plans to the best.";
    if (atEnd()) return "After " + S.p + (S.p === 1 ? " layer" : " layers") + ", one shot is the best plan " + pct(m.p_opt) + " of the time, against " + pct(randomPopt, 2) + " for a random valid pick. No shot ever uses more or fewer than " + D.k + " kits.";
    return "Mixer, layer " + (o.l + 1) + ": XX+YY rotations swap a tested and an untested relative, so plans one swap apart interfere. The phase pattern from the cost layer turns into height: good plans grow, bad plans shrink, and the number of kits stays at " + D.k + ".";
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
    else if (isTrained()) check.innerHTML = "Check against Qiskit: these are the angles COBYLA found with the Aer Estimator for depth " + S.p + ". Qiskit's statevector gives " + pct(t.p_opt, 2) + "; this page gives <b>" + pct(m.p_opt, 2) + "</b>.";
    else if (S.source === "tuned") check.innerHTML = "Tuned in your browser by Nelder-Mead in " + S.evals + " circuit evaluations: " + pct(m.ratio, 0) + " of the best value per shot. Qiskit's COBYLA reached " + pct(t ? t.ratio : NaN, 0) + " at this depth.";
    else check.textContent = "Your angles. Qiskit's trained angles give " + pct(t ? t.p_opt : NaN, 2) + " for depth " + S.p + ".";
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
    for (var i = 0; i < D.n; i++) {
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
    buildStages(); buildSliders(); computeLandscape(); update();
  }
  Array.prototype.forEach.call(depthBtns, function (b) {
    b.addEventListener("click", function () { S.interacted = true; setDepth(+b.dataset.p); });
  });

  // ---------------------------------------------------------------- start
  buildBits();
  setDepth(3);
  S.op = 0; S.frac = 1; update();
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
