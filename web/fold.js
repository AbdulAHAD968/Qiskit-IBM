/*
 * Keeps the page light: supporting detail (tables, method notes, the full
 * results table, the explanation behind each limitation, references) is folded
 * behind a "Show the details" toggle. Nothing is removed; without JavaScript
 * everything stays open. Runs before app.js, so its charts and reveals still work.
 */
(function () {
  "use strict";
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  function fold(nodes, label) {
    nodes = nodes.filter(Boolean);
    if (!nodes.length) return;
    var d = document.createElement("details"), s = document.createElement("summary");
    d.className = "more";
    s.textContent = label;
    d.appendChild(s);
    nodes[0].parentNode.insertBefore(d, nodes[0]);
    nodes.forEach(function (n) { n.classList.remove("reveal"); d.appendChild(n); });
  }
  var q = function (s) { return document.querySelector(s); };

  fold([q("#problem .grid.g3"), q("#problem .wrap > p.small")], "Show the sources and who it serves");
  fold([q("#formulation .formula + p.small"), q("#formulation .grid.mt2"), q("#formulation .card.mt")], "Show the variables, the genetics checks and the test instances");
  fold([q("#method .grid.g2.mt")], "Show the penalty baseline and how hard the problem is");
  fold([q("#tie-note")], "Show the tie-breaking check");
  var table = q("#bench-table");
  if (table) fold([table.closest(".card")], "Show the full results table");
  fold([q("#team .refs")], "Show the references");

  // Each limitation shows its title; the explanation opens on demand.
  $$("#limits .card").forEach(function (card) {
    var h = card.querySelector("h3");
    if (!h) return;
    var d = document.createElement("details"), s = document.createElement("summary");
    d.className = "card limit-fold " + card.className.replace(/\breveal\b/, "");
    s.innerHTML = h.innerHTML;
    d.appendChild(s);
    Array.prototype.slice.call(card.childNodes).forEach(function (n) { if (n !== h) d.appendChild(n); });
    card.parentNode.replaceChild(d, card);
  });
})();
