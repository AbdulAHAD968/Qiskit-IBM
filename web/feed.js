/*
 * Two small live components.
 *   #feed    shots from the depth-3 circuit, measured live: each shot is a row
 *            of qubits (1 = test this relative), with its share of the best
 *            plan, and a running count of how often the best plan comes up.
 *   Results  the headline numbers count up when they come into view.
 * Both stay still for visitors who ask for reduced motion.
 */
(function () {
  "use strict";
  var REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var K = window.KINSHIP, D = K && K.demo;

  // ------------------------------------------------------------ shot feed
  var host = document.getElementById("feed-rows");
  if (host && D && window.QAOASim) {
    var tq = null;
    (D.qaoa || []).forEach(function (q) { if (q.method === "constrained" && q.p === 3) tq = q; });
    var sim = new window.QAOASim.Sim({
      n: D.n, k: D.k, lam: D.lam,
      p: D.candidates.map(function (c) { return c.p; }),
      r: D.candidates.map(function (c) { return c.r; }),
      edges: D.edges,
    });
    if (tq) sim.run(tq.angles);
    var probs = sim.probs(), seed = 4242, shots = 0, hits = 0, MAX = 7;
    var rnd = function () { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
    var randomPick = sim.optimalCount() / sim.N;
    var $ = function (id) { return document.getElementById(id); };
    $("feed-random").textContent = (randomPick * 100).toFixed(2) + "%";

    var shoot = function (animate) {
      var u = rnd(), acc = 0, s;
      for (s = 0; s < sim.N - 1; s++) { acc += probs[s]; if (acc >= u) break; }
      var mask = sim.masks[s], best = sim.value[s] >= sim.best - 1e-12;
      shots++; if (best) hits++;
      var row = document.createElement("div");
      row.className = "feed-row" + (best ? " best" : "") + (animate ? " enter" : "");
      var bits = document.createElement("span"); bits.className = "feed-bits";
      var names = [];
      for (var q = 0; q < D.n; q++) {
        var on = (mask >> q) & 1, b = document.createElement("i");
        b.className = on ? "on" : "";
        b.title = D.candidates[q].label;
        bits.appendChild(b);
        if (on) names.push(D.candidates[q].label);
      }
      var label = document.createElement("span"); label.className = "feed-names"; label.textContent = names.join(", ");
      var val = document.createElement("span"); val.className = "feed-val";
      val.textContent = best ? "best plan" : Math.round((sim.value[s] / sim.best) * 100) + "%";
      var no = document.createElement("span"); no.className = "feed-no"; no.textContent = "#" + shots;
      row.appendChild(no); row.appendChild(bits); row.appendChild(label); row.appendChild(val);
      host.insertBefore(row, host.firstChild);
      while (host.children.length > MAX) host.removeChild(host.lastChild);
      $("feed-shots").textContent = shots.toLocaleString("en-US");
      $("feed-hits").textContent = (hits / shots * 100).toFixed(1) + "%";
      $("feed-meter").style.width = Math.min(100, (hits / shots) / 0.12 * 100) + "%";
    };
    for (var i = 0; i < MAX; i++) shoot(false);
    if (!REDUCED) {
      var timer = null, visible = false;
      var run = function () { if (visible && !document.hidden) shoot(true); };
      var io = new IntersectionObserver(function (es) {
        es.forEach(function (e) {
          visible = e.isIntersecting;
          if (visible && !timer) timer = setInterval(run, 550);
          if (!visible && timer) { clearInterval(timer); timer = null; }
        });
      }, { threshold: 0.2 });
      io.observe(document.getElementById("feed"));
    }
  }

  // ---------------------------------------------------- count-up numbers
  if (!REDUCED && "IntersectionObserver" in window) {
    var nums = Array.prototype.slice.call(document.querySelectorAll("#results .stat .v"));
    var cio = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (!e.isIntersecting) return;
        cio.unobserve(e.target);
        var node = e.target.querySelector("span") || e.target;
        var text = node.firstChild && node.firstChild.nodeType === 3 ? node.firstChild : null;
        if (!text) return;
        var raw = text.nodeValue.trim(), m = raw.match(/^([0-9.,]+)(.*)$/);
        if (!m) return;
        var target = parseFloat(m[1].replace(/,/g, "")), dec = (m[1].split(".")[1] || "").length, rest = m[2], t0 = null;
        var step = function (ts) {
          if (t0 == null) t0 = ts;
          var k = Math.min(1, (ts - t0) / 1300), v = target * (1 - Math.pow(1 - k, 3));
          text.nodeValue = v.toFixed(dec) + rest;
          if (k < 1) requestAnimationFrame(step); else text.nodeValue = raw;
        };
        requestAnimationFrame(step);
      });
    }, { threshold: 0.6 });
    setTimeout(function () { nums.forEach(function (n) { cio.observe(n); }); }, 300);
  }
})();
