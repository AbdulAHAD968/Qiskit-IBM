/*
 * Scroll scenes. A scene is a tall section with a sticky, full-screen stage.
 * Its scroll position becomes a progress value p in [0, 1], eased every frame,
 * which switches the caption steps (data-at="from,to") and redraws the canvas.
 *
 *   #hero   the family of section 4: the tree, then every carrier probability,
 *           then the field officer's plan against the plan the circuit measured
 *   #flow   the constrained QAOA circuit itself, run by web/qaoa-sim.js as you
 *           scroll: Dicke start, three cost and mixer layers, measurement
 */
(function () {
  "use strict";
  var K = window.KINSHIP, D = K && K.demo;
  if (!D) return;
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var clamp = function (x, a, b) { return Math.min(b == null ? 1 : b, Math.max(a || 0, x)); };
  var seg = function (p, a, b) { return clamp((p - a) / (b - a)); };
  var ease = function (t) { return t * t * (3 - 2 * t); };
  var lerp = function (a, b, t) { return a + (b - a) * t; };
  var REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var narrow = function () { return window.innerWidth <= 860; };
  var C = { ink: "#141413", body: "#3d3d3a", mut: "#6c6a64", hair: "#d9d1c6", card: "#efe9de", canvas: "#faf9f5",
    coral: "#c2613f", teal: "#2a8c7a", amber: "#c0811f" };
  var DC = { ink: "#faf9f5", mut: "#a09d96", hair: "#3a3733", card: "#252320", coral: "#e08a6c", teal: "#5db8a6", amber: "#e8a55a" };
  var SANS = "500 12px Inter, sans-serif", SERIF = "'Cormorant Garamond', Garamond, serif";

  function txt(ctx, s, x, y, col, font, align) {
    ctx.fillStyle = col; ctx.font = font || SANS; ctx.textAlign = align || "left"; ctx.textBaseline = "middle"; ctx.fillText(s, x, y);
  }

  // ---------------------------------------------------------------- engine
  var scenes = [];
  function scene(id, def) {
    var el = document.getElementById(id);
    if (!el) return;
    var cv = $(".stage > canvas", el);
    scenes.push(Object.assign({ el: el, cv: cv, ctx: cv ? cv.getContext("2d") : null, top: 0, h: 0, p: 0, tp: 0, W: 0, H: 0,
      dirty: true, steps: $$(".beat", el), cache: null }, def));
  }
  function measure(reset) {
    var y = window.scrollY, d = Math.min(window.devicePixelRatio || 1, 2);
    scenes.forEach(function (s) {
      var r = s.el.getBoundingClientRect();
      s.top = r.top + y; s.h = r.height;
      if (s.cv) {
        var st = s.cv.parentElement, W = st.clientWidth, H = st.clientHeight;
        if (reset) s.cache = null;
        if (W !== s.W || H !== s.H) {
          s.W = W; s.H = H; s.cv.width = W * d; s.cv.height = H * d;
          s.ctx.setTransform(d, 0, 0, d, 0, 0); s.cache = null; s.dirty = true;
        }
      }
    });
  }
  var last = performance.now(), force = true;
  function frame(now) {
    var dt = clamp((now - last) / 1000, 0, 0.05), y = window.scrollY, vh = window.innerHeight;
    last = now;
    var k = REDUCED ? 1 : 1 - Math.exp(-dt * 8);
    scenes.forEach(function (s) {
      var span = s.h - vh;
      s.tp = span > 0 ? clamp((y - s.top) / span) : 0;
      var moved = Math.abs(s.tp - s.p) > 1e-4;
      s.p = moved ? s.p + (s.tp - s.p) * k : s.tp;
      if (!(y + vh > s.top - 200 && y < s.top + s.h + 200)) return;
      s.steps.forEach(function (st) {
        var ab = st.dataset.at.split(",").map(Number);
        st.classList.toggle("on", s.tp >= ab[0] && s.tp < ab[1]);
      });
      if (moved || s.dirty || s.live || force) {
        s.dirty = false;
        if (s.ctx) {
          s.ctx.clearRect(0, 0, s.W, s.H);
          if (!s.cache && s.build) s.cache = s.build(s.W, s.H);
          try { s.draw(s.ctx, s.W, s.H, s.p, now / 1000, s.cache); } catch (err) { console.error(err); }
        }
      }
    });
    force = false;
    requestAnimationFrame(frame);
  }

  // ------------------------------------------------------- hero: the family
  var people = D.people || [], byId = {};
  people.forEach(function (p) { byId[p.id] = p; });
  var exact = (D.plans && D.plans.exact && D.plans.exact.chosen) || [];
  var field = (D.plans && D.plans.field && D.plans.field.chosen) || [];
  var gens = people.reduce(function (m, p) { return Math.max(m, p.y); }, 0) || 3;

  var T0 = performance.now();
  scene("hero", {
    live: true,
    build: function (W, H) {
      var m = narrow();
      // Fit the tree between the title and the captions as they are laid out on this screen.
      var stage = $("#hero .stage"), ttl = $("#hero .ttl"), low = $("#hero .lower");
      var top = H * 0.385, bottom = H * 0.675;
      if (stage && ttl && low) {
        var sr = stage.getBoundingClientRect();
        top = ttl.getBoundingClientRect().bottom - sr.top + (m ? 34 : 46);
        bottom = low.getBoundingClientRect().top - sr.top - (m ? 70 : 96);   // room for the match curves and the verdict
      }
      var h = Math.max(90, bottom - top);
      var w = m ? W - 44 : Math.min(W * 0.72, Math.max(560, h * 4.2));
      var R = { x: (W - w) / 2, y: top, w: w, h: h };
      var pos = {};
      people.forEach(function (p) { pos[p.id] = { x: R.x + p.x * R.w, y: R.y + (p.y / gens) * R.h }; });
      return { R: R, pos: pos, s: Math.max(7, Math.min(15, R.w / 62)) };
    },
    draw: function (ctx, W, H, p, t, G) {
      // The tree draws itself once on load; carrier shading and the plans follow the scroll.
      var intro = REDUCED ? 1 : ease(clamp((performance.now() - T0) / 2600));
      var pos = G.pos, s = G.s, draw = Math.max(intro, ease(seg(p, 0.0, 0.18))), shade = ease(seg(p, 0.33, 0.58));
      var showField = seg(p, 0.64, 0.7) * (1 - seg(p, 0.8, 0.84)), showPlan = seg(p, 0.82, 0.88);
      // lines of descent
      ctx.lineWidth = 1.3; ctx.strokeStyle = C.hair;
      var seen = {};
      people.forEach(function (c) {
        if (c.father == null || c.mother == null) return;
        var f = pos[c.father], m = pos[c.mother], ch = pos[c.id], key = c.father + "-" + c.mother;
        var g = seg(draw, (c.y - 1) / gens, c.y / gens);
        if (g <= 0) return;
        if (!seen[key]) {
          seen[key] = 1;
          ctx.beginPath(); ctx.moveTo(f.x, f.y); ctx.lineTo(lerp(f.x, m.x, Math.min(1, g * 2)), lerp(f.y, m.y, Math.min(1, g * 2))); ctx.stroke();
        }
        var mx = (f.x + m.x) / 2, yb = f.y + (ch.y - f.y) * 0.5;
        ctx.beginPath(); ctx.moveTo(mx, f.y);
        ctx.lineTo(mx, lerp(f.y, yb, Math.min(1, g * 3)));
        if (g > 0.33) ctx.lineTo(lerp(mx, ch.x, Math.min(1, (g - 0.33) * 3)), yb);
        if (g > 0.66) ctx.lineTo(ch.x, lerp(yb, ch.y - s, (g - 0.66) * 3));
        ctx.stroke();
      });
      // possible matches, and the couples a plan tests in full
      var plan = showPlan > 0 ? exact : showField > 0 ? field : [];
      var planA = showPlan > 0 ? showPlan : showField;
      (D.couples || []).forEach(function (cp) {
        if (!cp.in_problem) return;
        var a = pos[cp.a], b = pos[cp.b];
        if (!a || !b) return;
        var both = plan.indexOf(cp.a) >= 0 && plan.indexOf(cp.b) >= 0;
        ctx.save();
        ctx.globalAlpha = seg(p, 0.12, 0.2);
        ctx.strokeStyle = both ? C.coral : "rgba(194,97,63,0.4)";
        ctx.lineWidth = both ? 1.5 + 2.5 * planA : 1.3;
        if (!both) ctx.setLineDash(cp.kind === "potential" ? [2, 5] : []);
        ctx.beginPath();
        if (cp.kind === "married") { ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); }
        else { var y = a.y + s + 6, dep = 12 + Math.abs(b.x - a.x) * 0.12; ctx.moveTo(a.x, y); ctx.quadraticCurveTo((a.x + b.x) / 2, y + dep, b.x, y); }
        ctx.stroke(); ctx.restore();
      });
      // people
      people.forEach(function (q) {
        var P = pos[q.id], appear = seg(draw, q.y / (gens + 1), (q.y + 0.8) / (gens + 1));
        if (appear <= 0) return;
        var r = s * (0.6 + 0.4 * ease(appear)), cand = q.qubit != null, gone = q.status === "deceased" || q.status === "unavailable";
        ctx.save();
        ctx.globalAlpha = appear * (gone ? 0.45 : 1);
        var path = function () {
          ctx.beginPath();
          if (q.sex === "F") ctx.arc(P.x, P.y, r, 0, Math.PI * 2);
          else ctx.rect(P.x - r, P.y - r, 2 * r, 2 * r);
        };
        path(); ctx.fillStyle = C.canvas; ctx.fill();
        // carrier probability as a fill from the bottom, the way pedigrees shade carriers
        var level = q.status === "affected" ? 1 : (q.p || 0) * shade;
        if (q.status === "obligate") level = Math.max(level, shade);
        if (level > 0) {
          ctx.save(); path(); ctx.clip();
          ctx.fillStyle = q.status === "affected" ? C.ink : "rgba(194,97,63,0.55)";
          ctx.fillRect(P.x - r, P.y + r - 2 * r * level, 2 * r, 2 * r * level);
          ctx.restore();
        }
        if (q.status === "affected") { path(); ctx.fillStyle = C.ink; ctx.fill(); }
        var tested = plan.indexOf(q.id) >= 0;
        path();
        ctx.lineWidth = tested ? 2.6 : 1.5;
        ctx.strokeStyle = tested ? (showPlan > 0 ? C.coral : C.teal) : gone ? C.mut : C.ink;
        if (gone) ctx.setLineDash([3, 3]);
        ctx.stroke(); ctx.setLineDash([]);
        if (tested) {
          ctx.globalAlpha = appear * planA;
          ctx.beginPath(); ctx.arc(P.x, P.y, r + 6, 0, Math.PI * 2);
          ctx.strokeStyle = showPlan > 0 ? C.coral : C.teal; ctx.lineWidth = 1.5; ctx.stroke();
          ctx.globalAlpha = appear;
        }
        if (cand && shade > 0.05 && G.R.w > 520) {
          ctx.globalAlpha = appear * shade;
          txt(ctx, q.p.toFixed(2).replace(/^0/, ""), P.x, P.y - r - 9, C.mut, "500 10.5px Inter, sans-serif", "center");
        }
        if (q.status === "affected" && G.R.w > 420) {
          ctx.globalAlpha = appear;
          txt(ctx, "affected child", P.x, P.y + r + 13, C.ink, "500 11px Inter, sans-serif", "center");
        }
        ctx.restore();
      });
      // the verdict of the plan on screen
      if (planA > 0.05) {
        var label = showPlan > 0 ? "Constrained QAOA: " + D.plans.exact.couples.toFixed(3) + " expected at-risk couples, the exact optimum"
          : "Field officer's rule: " + D.plans.field.couples.toFixed(3) + " expected at-risk couples";
        ctx.globalAlpha = planA;
        txt(ctx, label, W / 2, G.R.y + G.R.h + s + 66, showPlan > 0 ? C.coral : C.teal, "500 15px Inter, sans-serif", "center");
        ctx.globalAlpha = 1;
      }
    },
  });

  // -------------------------------------------------- flow: the circuit, run
  var Q = window.QAOASim, trained = null;
  (D.qaoa || []).forEach(function (q) { if (q.method === "constrained" && q.p === 3) trained = q; });
  if (Q && trained) {
    var sim = new Q.Sim({
      n: D.n, k: D.k, lam: D.lam,
      p: D.candidates.map(function (c) { return c.p; }),
      r: D.candidates.map(function (c) { return c.r; }),
      edges: D.edges,
    });
    var ang = trained.angles, P3 = ang.length / 2, N = sim.N;
    var bestRank = sim.order.map(function (s) { return sim.value[s] >= sim.best - 1e-12; });
    var ampMax = (function () { sim.run(ang); var m = 0; for (var s = 0; s < N; s++) m = Math.max(m, Math.hypot(sim.re[s], sim.im[s])); return m * 1.08; })();
    /** Apply the circuit up to a fraction u of its 2p operations. */
    var evolve = function (u) {
      sim.reset();
      var ops = 2 * P3, x = u * ops;
      for (var i = 0; i < ops; i++) {
        var f = clamp(x - i);
        if (f <= 0) break;
        var l = Math.floor(i / 2);
        if (i % 2 === 0) sim.cost(f * ang[l]); else sim.mixer(f * ang[P3 + l]);
      }
    };
    scene("flow", {
      build: function (W, H) {
        var m = narrow();
        return { R: m ? { x: 20, y: H * 0.44, w: W - 40, h: H * 0.4 } : { x: W * 0.47, y: H * 0.2, w: W * 0.46, h: H * 0.56 } };
      },
      draw: function (ctx, W, H, p, t, G) {
        var R = G.R, u = ease(seg(p, 0.14, 0.84)), meas = seg(p, 0.86, 0.95);
        evolve(u);
        var bw = R.w / N, base = R.y + R.h, popt = 0;
        // grid and reference line
        ctx.fillStyle = DC.hair;
        for (var g = 1; g <= 3; g++) ctx.fillRect(R.x, base - (R.h * g) / 4, R.w, 1);
        for (var r = 0; r < N; r++) {
          var s = sim.order[r], re = sim.re[s], im = sim.im[s], a = Math.hypot(re, im), hh = (a / ampMax) * R.h;
          if (bestRank[r]) popt += re * re + im * im;
          var hue = ((Math.atan2(im, re) * 180) / Math.PI + 380) % 360;
          ctx.fillStyle = "hsl(" + hue.toFixed(0) + " 62% " + (bestRank[r] ? 70 : 62) + "%)";
          ctx.fillRect(R.x + r * bw + 0.3, base - hh, Math.max(bw - 0.6, 0.6), hh);
        }
        var uy = base - (1 / Math.sqrt(N) / ampMax) * R.h;
        ctx.setLineDash([5, 5]); ctx.strokeStyle = "rgba(250,249,245,0.55)"; ctx.lineWidth = 1.2;
        ctx.beginPath(); ctx.moveTo(R.x, uy); ctx.lineTo(R.x + R.w, uy); ctx.stroke(); ctx.setLineDash([]);
        txt(ctx, "start: every plan equally likely", R.x + 4, uy - 9, DC.mut, "500 11.5px Inter, sans-serif");
        ctx.fillStyle = DC.hair; ctx.fillRect(R.x, base, R.w, 1);
        txt(ctx, "worst plan", R.x, base + 16, DC.mut, "500 12px Inter, sans-serif");
        txt(ctx, "best plan", R.x + R.w, base + 16, DC.amber, "500 12px Inter, sans-serif", "right");
        // the step the circuit is on
        var ops = 2 * P3, x = u * ops, i = Math.min(ops - 1, Math.floor(x));
        var label = u <= 0 ? "Dicke state" : u >= 1 ? "after 3 layers" : (i % 2 === 0 ? "cost layer " : "mixer ") + (Math.floor(i / 2) + 1);
        txt(ctx, label, R.x, R.y - 34, DC.ink, "500 13px Inter, sans-serif");
        // progress through the circuit
        var tw = Math.min(R.w, 360);
        for (var j = 0; j < ops; j++) {
          var cx = R.x + (j / ops) * tw, wv = tw / ops - 4, f = clamp(x - j);
          ctx.fillStyle = DC.hair; ctx.fillRect(cx, R.y - 18, wv, 4);
          ctx.fillStyle = j % 2 === 0 ? DC.coral : DC.teal; ctx.fillRect(cx, R.y - 18, wv * f, 4);
        }
        // live readout
        txt(ctx, (popt * 100).toFixed(2) + "%", R.x + R.w, R.y - 34, DC.ink, "500 " + Math.min(48, R.w * 0.1) + "px Inter, sans-serif", "right");
        txt(ctx, "chance one shot is the best plan", R.x + R.w, R.y - 4, DC.mut, "500 12px Inter, sans-serif", "right");
        // measurement: shots land on plans
        if (meas > 0) {
          var rnd = (function (seed) { return function () { seed = (seed * 16807) % 2147483647; return seed / 2147483647; }; })(11);
          var probs = sim.probs(), cum = [], acc = 0;
          for (var rr = 0; rr < N; rr++) { acc += probs[sim.order[rr]]; cum.push(acc); }
          var shots = Math.floor(meas * 160);
          for (var k = 0; k < shots; k++) {
            var v = rnd() * acc, lo = 0;
            while (lo < N - 1 && cum[lo] < v) lo++;
            var px = R.x + (lo + 0.5) * bw, py = base + 34 + (k % 8) * 5;
            ctx.fillStyle = bestRank[lo] ? DC.amber : "rgba(250,249,245,0.55)";
            ctx.beginPath(); ctx.arc(px, py, 1.8, 0, Math.PI * 2); ctx.fill();
          }
          ctx.globalAlpha = meas;
          txt(ctx, "160 shots: amber ones are the best plan", R.x, base + 84, DC.mut, "500 12px Inter, sans-serif");
          ctx.globalAlpha = 1;
        }
      },
    });
  }

  // ----------------------------------------------------------------- start
  var rz;
  window.addEventListener("resize", function () { clearTimeout(rz); rz = setTimeout(function () { measure(true); force = true; }, 120); });
  window.addEventListener("load", function () { measure(true); force = true; });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { measure(true); force = true; });
  measure();
  requestAnimationFrame(frame);
  // Layout above a scene can change after charts render; re-measure now and then.
  setInterval(measure, 2000);
})();
