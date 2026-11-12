/*
 * Exact simulation of the constrained QAOA circuit inside the Dicke subspace.
 *
 * The constrained circuit never leaves the plans with exactly k ones, so the
 * state is a vector of C(n, k) complex amplitudes instead of 2^n. Each step
 * mirrors kinship/quantum/circuits.py gate for gate:
 *
 *   start   Dicke state: equal amplitude 1/sqrt(C(n,k)) on every valid plan
 *   cost    RZZ(2 gamma b_ij) per couple link and RZ(2 gamma a_i) per relative,
 *           i.e. the phase exp(-i gamma E(x)) with E the RMS-scaled Ising energy
 *   mixer   XXPlusYYGate(2 beta) on the ring pairs in parity order, which acts
 *           on |01>,|10> as [[cos beta, -i sin beta], [-i sin beta, cos beta]]
 *
 * Bit i of a mask is qubit i, as in the Python code.
 */
(function (root) {
  "use strict";

  function popcount(m) { var c = 0; while (m) { m &= m - 1; c++; } return c; }

  function ringPairs(n) {
    var pairs = [], i;
    if (n < 2) return pairs;
    for (i = 0; i < n - 1; i += 2) pairs.push([i, i + 1]);
    for (i = 1; i < n - 1; i += 2) pairs.push([i, i + 1]);
    if (n > 2) pairs.push([n - 1, 0]);
    return pairs;
  }

  /**
   * problem: { n, k, lam, p[], r[], edges: [{i, j, w, c}] }
   */
  function Sim(problem) {
    var n = problem.n, k = problem.k, i, j, t;
    this.n = n; this.k = k;
    var h = new Float64Array(n);
    for (i = 0; i < n; i++) h[i] = problem.lam * problem.r[i] * problem.p[i];
    var W = [];
    for (i = 0; i < n; i++) W.push(new Float64Array(n));
    problem.edges.forEach(function (e) { var q = e.w * e.c; W[e.i][e.j] += q; W[e.j][e.i] += q; });

    // Ising coefficients exactly as Qubo.ising() and scaled_ising() in Python.
    var a = new Float64Array(n), b = [];
    for (i = 0; i < n; i++) a[i] = -0.5 * h[i];
    for (i = 0; i < n; i++) for (j = i + 1; j < n; j++) {
      var q = W[i][j];
      if (q === 0) continue;
      b.push([i, j, q / 4]);
      a[i] -= q / 4; a[j] -= q / 4;
    }
    var sq = 0, cnt = 0;
    for (i = 0; i < n; i++) if (Math.abs(a[i]) > 1e-12) { sq += a[i] * a[i]; cnt++; }
    b.forEach(function (e) { if (Math.abs(e[2]) > 1e-12) { sq += e[2] * e[2]; cnt++; } });
    this.scale = cnt ? Math.sqrt(sq / cnt) : 1;

    // Valid plans, their objective values and scaled energies.
    var masks = [];
    for (var m = 0; m < (1 << n); m++) if (popcount(m) === k) masks.push(m);
    var N = masks.length, index = new Map();
    masks.forEach(function (mm, s) { index.set(mm, s); });
    var value = new Float64Array(N), energy = new Float64Array(N);
    for (t = 0; t < N; t++) {
      var mk = masks[t], v = 0, E = 0;
      for (i = 0; i < n; i++) {
        var xi = (mk >> i) & 1;
        if (xi) v += h[i];
        E += a[i] * (1 - 2 * xi);
        for (j = i + 1; j < n; j++) if (xi && ((mk >> j) & 1)) v += W[i][j];
      }
      for (var e = 0; e < b.length; e++) {
        var zi = 1 - 2 * ((mk >> b[e][0]) & 1), zj = 1 - 2 * ((mk >> b[e][1]) & 1);
        E += b[e][2] * zi * zj;
      }
      value[t] = v; energy[t] = E / this.scale;
    }
    this.masks = masks; this.N = N; this.value = value; this.energy = energy;
    this.h = h; this.W = W;

    var best = -Infinity, worst = Infinity, mean = 0;
    for (t = 0; t < N; t++) { best = Math.max(best, value[t]); worst = Math.min(worst, value[t]); mean += value[t]; }
    this.best = best; this.worst = worst; this.mean = mean / N;

    // Sorted order (worst to best) for drawing.
    this.order = Array.from({ length: N }, function (_, s) { return s; })
      .sort(function (x, y) { return value[x] - value[y] || masks[x] - masks[y]; });

    // For each ring pair, the index pairs (s with bit a=1,b=0 ; t with the bits swapped).
    this.pairs = ringPairs(n).map(function (pr) {
      var A = pr[0], B = pr[1], ss = [], tt = [];
      for (var s = 0; s < N; s++) {
        var ms = masks[s];
        if (((ms >> A) & 1) === 1 && ((ms >> B) & 1) === 0) {
          ss.push(s); tt.push(index.get(ms ^ (1 << A) ^ (1 << B)));
        }
      }
      return { a: A, b: B, s: Int32Array.from(ss), t: Int32Array.from(tt) };
    });
    this.re = new Float64Array(N); this.im = new Float64Array(N);
    this.reset();
  }

  Sim.prototype.reset = function () {
    var amp = 1 / Math.sqrt(this.N);
    this.re.fill(amp); this.im.fill(0);
    return this;
  };

  Sim.prototype.cost = function (gamma) {
    var re = this.re, im = this.im, E = this.energy;
    for (var s = 0; s < this.N; s++) {
      var ph = -gamma * E[s], c = Math.cos(ph), sn = Math.sin(ph);
      var x = re[s], y = im[s];
      re[s] = x * c - y * sn; im[s] = x * sn + y * c;
    }
    return this;
  };

  /** One XX+YY rotation on ring pair number g. */
  Sim.prototype.mixGate = function (g, beta) {
    var P = this.pairs[g], re = this.re, im = this.im, c = Math.cos(beta), sn = Math.sin(beta);
    for (var u = 0; u < P.s.length; u++) {
      var s = P.s[u], t = P.t[u];
      var xr = re[s], xi = im[s], yr = re[t], yi = im[t];
      // [c, -i sn; -i sn, c] applied to (x, y)
      re[s] = c * xr + sn * yi; im[s] = c * xi - sn * yr;
      re[t] = c * yr + sn * xi; im[t] = c * yi - sn * xr;
    }
    return this;
  };

  Sim.prototype.mixer = function (beta) {
    for (var g = 0; g < this.pairs.length; g++) this.mixGate(g, beta);
    return this;
  };

  /** angles = [gamma_1..gamma_p, beta_1..beta_p], as stored by the Python code. */
  Sim.prototype.run = function (angles) {
    var p = angles.length / 2;
    this.reset();
    for (var l = 0; l < p; l++) { this.cost(angles[l]); this.mixer(angles[p + l]); }
    return this;
  };

  Sim.prototype.probs = function (out) {
    out = out || new Float64Array(this.N);
    for (var s = 0; s < this.N; s++) out[s] = this.re[s] * this.re[s] + this.im[s] * this.im[s];
    return out;
  };

  Sim.prototype.expectation = function () {
    var v = 0;
    for (var s = 0; s < this.N; s++) v += (this.re[s] * this.re[s] + this.im[s] * this.im[s]) * this.value[s];
    return v;
  };

  Sim.prototype.metrics = function () {
    var pr = this.probs(), mean = 0, popt = 0, span = this.best - this.worst;
    for (var s = 0; s < this.N; s++) {
      mean += pr[s] * this.value[s];
      if (this.value[s] >= this.best - 1e-12) popt += pr[s];
    }
    return {
      mean: mean, ratio: mean / this.best, quality: span > 0 ? (mean - this.worst) / span : 1,
      p_opt: popt, random_p_opt: this.optimalCount() / this.N,
    };
  };

  Sim.prototype.optimalCount = function () {
    var c = 0;
    for (var s = 0; s < this.N; s++) if (this.value[s] >= this.best - 1e-12) c++;
    return c;
  };

  Sim.prototype.f = function (angles) { return this.run(angles).expectation(); };

  /** Draw shots from the current state. rnd: function returning [0, 1). */
  Sim.prototype.sample = function (shots, rnd) {
    var pr = this.probs(), cum = new Float64Array(this.N), acc = 0, out = [];
    for (var s = 0; s < this.N; s++) { acc += pr[s]; cum[s] = acc; }
    for (var t = 0; t < shots; t++) {
      var u = rnd() * acc, lo = 0, hi = this.N - 1;
      while (lo < hi) { var mid = (lo + hi) >> 1; if (cum[mid] < u) lo = mid + 1; else hi = mid; }
      out.push(lo);
    }
    return out;
  };

  /**
   * Nelder-Mead maximiser that yields after every iteration, so the page can
   * draw the path the classical optimiser takes.
   */
  function* nelderMead(f, x0, step, maxIter) {
    var d = x0.length, pts = [x0.slice()], i, j;
    for (i = 0; i < d; i++) { var p = x0.slice(); p[i] += step; pts.push(p); }
    var vals = pts.map(function (q) { return -f(q); });
    for (var it = 0; it < maxIter; it++) {
      var idx = vals.map(function (_, q) { return q; }).sort(function (u, v) { return vals[u] - vals[v]; });
      pts = idx.map(function (q) { return pts[q]; }); vals = idx.map(function (q) { return vals[q]; });
      yield { x: pts[0].slice(), value: -vals[0], iter: it };
      if (Math.abs(vals[d] - vals[0]) < 1e-10) break;
      var c = new Array(d).fill(0);
      for (i = 0; i < d; i++) for (j = 0; j < d; j++) c[j] += pts[i][j] / d;
      var move = function (t) { return c.map(function (cj, q) { return cj + t * (pts[d][q] - cj); }); };
      var xr = move(-1), fr = -f(xr);
      if (fr < vals[0]) {
        var xe = move(-2), fe = -f(xe);
        if (fe < fr) { pts[d] = xe; vals[d] = fe; } else { pts[d] = xr; vals[d] = fr; }
      } else if (fr < vals[d - 1]) {
        pts[d] = xr; vals[d] = fr;
      } else {
        var xc = fr < vals[d] ? move(-0.5) : move(0.5), fc = -f(xc);
        if (fc < Math.min(fr, vals[d])) { pts[d] = xc; vals[d] = fc; }
        else {
          for (i = 1; i <= d; i++) {
            pts[i] = pts[i].map(function (v, q) { return pts[0][q] + 0.5 * (v - pts[0][q]); });
            vals[i] = -f(pts[i]);
          }
        }
      }
    }
    var last = vals.indexOf(Math.min.apply(null, vals));
    yield { x: pts[last].slice(), value: -vals[last], iter: maxIter, done: true };
  }

  var api = { Sim: Sim, ringPairs: ringPairs, nelderMead: nelderMead };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.QAOASim = api;
})(typeof window !== "undefined" ? window : this);
