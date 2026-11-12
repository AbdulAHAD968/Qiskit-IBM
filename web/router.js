/*
 * Pages. The site is one file, shown as five pages with tabs at the top:
 *   #/          Overview       the story: the family, the problem, the circuit as you scroll
 *   #/plan      Plan a visit   the live planner and circuit, as a dashboard
 *   #/results   Results        every measured comparison
 *   #/method    How it works   formulation, live plan, method, architecture
 *   #/about     Limits & team  what did not work, ethics, reproduce, credits
 * A link to any section id (for example #ref3) opens the page that holds it.
 * Without JavaScript every section stays on one long page.
 */
(function () {
  "use strict";
  var PAGES = [
    { id: "", label: "Overview", sections: ["hero", "problem", "pairs", "flow"] },
    { id: "plan", label: "Plan a visit", sections: ["lab"] },
    { id: "results", label: "Results", sections: ["results"] },
    { id: "method", label: "How it works", sections: ["formulation", "demo", "method", "architecture"] },
    { id: "about", label: "Limits and team", sections: ["limits", "team"] },
  ];
  var pageOf = {};
  PAGES.forEach(function (p) { p.sections.forEach(function (s) { pageOf[s] = p; }); });
  var all = Object.keys(pageOf).map(function (id) { return document.getElementById(id); }).filter(Boolean);
  if (!all.length) return;
  document.documentElement.classList.add("paged");

  // Tabs replace the section links in the top bar.
  var links = document.querySelector(".nav-links");
  if (links) {
    links.innerHTML = "";
    PAGES.forEach(function (p) {
      var a = document.createElement("a");
      a.href = "#/" + p.id;
      a.textContent = p.label;
      a.dataset.page = p.id;
      links.appendChild(a);
    });
  }

  // A short "next page" link closes every page, so the story keeps moving.
  PAGES.forEach(function (p, i) {
    var next = PAGES[i + 1];
    var lastId = p.sections[p.sections.length - 1], last = document.getElementById(lastId);
    if (!next || !last) return;
    var band = document.createElement("div");
    band.className = "next-page";
    band.innerHTML = '<div class="wrap"><span>Next</span><a href="#/' + next.id + '"></a></div>';
    band.querySelector("a").textContent = next.label;
    last.parentNode.insertBefore(band, last.nextSibling);
    band.dataset.page = p.id;
  });

  var current = null;
  function show(page, target) {
    if (current !== page) {
      current = page;
      all.forEach(function (el) { el.hidden = pageOf[el.id] !== page; });
      Array.prototype.forEach.call(document.querySelectorAll(".next-page"), function (b) { b.hidden = b.dataset.page !== page.id; });
      Array.prototype.forEach.call(document.querySelectorAll(".nav-links a"), function (a) {
        a.classList.toggle("active", a.dataset.page === page.id);
        if (a.dataset.page === page.id) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
      });
      document.title = (page.id ? page.label + " · " : "") + "Kinship Screening with QAOA";
      // Canvases and scroll triggers measure again now that this page is visible.
      setTimeout(function () {
        window.dispatchEvent(new Event("resize"));
        if (window.ScrollTrigger) window.ScrollTrigger.refresh();
      }, 30);
    }
    var y = 0;
    if (target) y = target.getBoundingClientRect().top + window.scrollY - 76;
    window.scrollTo(0, Math.max(0, y));
  }
  function route() {
    var h = decodeURIComponent(location.hash.slice(1));
    if (h === "" || h.charAt(0) === "/") {
      var id = h.slice(1), page = PAGES.filter(function (p) { return p.id === id; })[0] || PAGES[0];
      show(page, null);
      return;
    }
    var el = document.getElementById(h);
    var sec = el && el.closest("main > section, main > div");
    var pg = sec && pageOf[sec.id];
    if (pg) show(pg, el);
  }
  window.addEventListener("hashchange", route);
  // The brand returns to the overview.
  var brand = document.querySelector(".brand");
  if (brand) brand.setAttribute("href", "#/");
  route();
})();
