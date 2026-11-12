/*
 * The Results page as a dashboard: four headline numbers, then one topic at a
 * time behind tabs, with the long notes folded. Runs after app.js has drawn
 * the charts and filled the notes; it only moves nodes, so every chart keeps
 * its data. Without JavaScript all topics stay visible.
 */
(function () {
  "use strict";
  var wrap = document.querySelector("#results .wrap");
  if (!wrap) return;
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var kids = Array.prototype.slice.call(wrap.children);
  var stats = $(".grid.g4", wrap);
  var start = kids.indexOf(stats);
  if (start < 0) return;

  function owner(sel) {
    var el = $(sel, wrap);
    while (el && el.parentElement !== wrap) el = el.parentElement;
    return el;
  }
  function heading(text) {
    return kids.filter(function (k) { return k.tagName === "H3" && k.textContent.indexOf(text) === 0; })[0];
  }
  var TOPICS = [
    { label: "Against simple rules", from: heading("Is the problem trivial") },
    { label: "QAOA against random", from: heading("QAOA against random") },
    { label: "Kit limit and cost", from: owner("#hist-demo") },
    { label: "Under noise", from: heading("Under noise") },
    { label: "Trade-off and scaling", from: owner("#tradeoff") },
    { label: "Full table", from: owner("#bench-table") },
  ].filter(function (t) { return t.from; });
  if (TOPICS.length < 2) return;

  var bar = document.createElement("div");
  bar.className = "dash-tabs";
  bar.setAttribute("role", "tablist");
  bar.setAttribute("aria-label", "Result topics");
  wrap.insertBefore(bar, TOPICS[0].from);

  var panels = TOPICS.map(function (t, i) {
    var panel = document.createElement("div");
    panel.className = "dash-panel";
    panel.id = "dash-" + i;
    panel.setAttribute("role", "tabpanel");
    var next = TOPICS[i + 1] ? TOPICS[i + 1].from : null;
    var node = t.from;
    wrap.insertBefore(panel, node);
    while (node && node !== next) {
      var after = node.nextElementSibling;
      if (node.tagName === "H3" && node.classList.contains("mt2")) node.classList.add("dash-hide");
      panel.appendChild(node);
      node = after;
    }
    var b = document.createElement("button");
    b.type = "button";
    b.className = "dash-tab";
    b.setAttribute("role", "tab");
    b.setAttribute("aria-controls", panel.id);
    b.textContent = t.label;
    b.addEventListener("click", function () { select(i); });
    bar.appendChild(b);
    return panel;
  });

  // Long notes under the charts open on demand.
  ["#tradeoff-note", "#decomp-note"].forEach(function (sel) { foldNote($(sel, wrap)); });
  Array.prototype.forEach.call(wrap.querySelectorAll(".dash-panel > p.small, .chart-card > p.src:not([id])"), foldNote);
  function foldNote(p) {
    if (!p || !p.parentNode || p.closest("details")) return;
    var d = document.createElement("details"), s = document.createElement("summary");
    d.className = "more note";
    s.textContent = "Read the note";
    d.appendChild(s);
    p.parentNode.insertBefore(d, p);
    p.classList.remove("reveal");
    d.appendChild(p);
  }

  function select(i) {
    panels.forEach(function (p, j) { p.hidden = j !== i; });
    Array.prototype.forEach.call(bar.children, function (b, j) {
      b.setAttribute("aria-selected", String(j === i));
      b.tabIndex = j === i ? 0 : -1;
    });
    // charts animate in when they become visible
    Array.prototype.forEach.call(panels[i].querySelectorAll(".reveal"), function (n) { n.classList.add("in"); });
    window.dispatchEvent(new Event("resize"));
  }
  bar.addEventListener("keydown", function (e) {
    var cur = Array.prototype.indexOf.call(bar.children, document.activeElement);
    if (cur < 0) return;
    var to = e.key === "ArrowRight" ? cur + 1 : e.key === "ArrowLeft" ? cur - 1 : null;
    if (to == null) return;
    to = (to + panels.length) % panels.length;
    select(to); bar.children[to].focus(); e.preventDefault();
  });
  select(0);
})();
