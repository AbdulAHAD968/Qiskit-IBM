/*
 * Scroll-driven motion: Lenis smooth scrolling and GSAP ScrollTrigger scenes.
 *
 * Progressive enhancement only. If GSAP fails to load, or the visitor asks for
 * reduced motion, nothing here runs and the page keeps its plain behaviour
 * (CSS reveals from app.js). Every scene is tied to what it explains.
 *
 *   1. intro       the family tree draws itself, generation by generation
 *   2. hero        the hero recedes as the problem panel slides over it
 *   3. formula     each term is underlined in reading order as you scroll
 *   4. pair risk   the wrong answer, 26%, is struck through as it passes
 *   5. circuit     a playhead runs through the circuit in step with the text
 *   6. lab         the live circuit panel rises into place
 *   7. results     headline numbers settle in at different speeds
 */
(function () {
  "use strict";
  var gsap = window.gsap, ST = window.ScrollTrigger;
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!gsap || !ST || reduce) return;
  gsap.registerPlugin(ST);
  document.documentElement.classList.add("has-motion");

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  /** Hand an element over from the CSS reveal to GSAP. */
  function claim(els) { els.forEach(function (el) { el.classList.remove("reveal", "left", "right", "zoom"); }); return els; }

  // ------------------------------------------------------------ smooth scroll
  var lenis = null;
  if (window.Lenis && !window.matchMedia("(pointer: coarse)").matches) {
    lenis = new window.Lenis({ lerp: 0.1, smoothWheel: true });
    lenis.on("scroll", ST.update);
    gsap.ticker.add(function (t) { lenis.raf(t * 1000); });
    gsap.ticker.lagSmoothing(0);
    // In-page links go through Lenis so they glide instead of jumping.
    document.addEventListener("click", function (e) {
      var a = e.target.closest && e.target.closest('a[href^="#"]');
      if (!a) return;
      var id = a.getAttribute("href");
      var target = id.length > 1 && document.getElementById(id.slice(1));
      if (!target) return;
      e.preventDefault();
      lenis.scrollTo(target, { offset: id === "#top" ? 0 : -70, duration: 1.2 });
      history.replaceState(null, "", id);
    });
  }

  // 1 and 2 (the hero) are now the #hero scroll scene in web/scenes.js.

  function nodeY(n) {
    var y = n.getAttribute("y") || n.getAttribute("cy") || 0;
    return parseFloat(y);
  }

  // ------------------------------------------------------- 3. formula
  var formula = $("#formulation .formula");
  if (formula) {
    var terms = $$(".t1, .t2, .st", formula);
    terms.forEach(function (t) { t.classList.add("ink-line"); });
    gsap.to(terms, {
      backgroundSize: "100% 3px", ease: "none", stagger: 0.5,
      scrollTrigger: { trigger: formula, start: "top 80%", end: "bottom 40%", scrub: 0.5 },
    });
  }

  // ----------------------------------------------------- 4. pair risk
  $$(".big-compare .strike").forEach(function (el) {
    el.classList.remove("strike");
    el.classList.add("strike-live");
    var bar = document.createElement("i");
    bar.className = "strike-bar";
    el.appendChild(bar);
    gsap.fromTo(bar, { scaleX: 0 }, {
      scaleX: 1, ease: "none",
      scrollTrigger: { trigger: el, start: "top 78%", end: "top 48%", scrub: 0.4 },
    });
    gsap.to(el, { color: "var(--muted)", ease: "none", scrollTrigger: { trigger: el, start: "top 70%", end: "top 48%", scrub: true } });
  });

  // ------------------------------------------------------ 5. circuit playhead
  var circuit = $("#circuit"), scrolly = $("#scrolly");
  if (circuit && scrolly && window.matchMedia("(min-width: 901px)").matches) {
    var NS = "http://www.w3.org/2000/svg";
    var head = document.createElementNS(NS, "line");
    head.setAttribute("class", "playhead");
    head.setAttribute("y1", "26"); head.setAttribute("y2", "326");
    head.setAttribute("x1", "40"); head.setAttribute("x2", "40");
    circuit.appendChild(head);
    gsap.fromTo(head, { attr: { x1: 40, x2: 40 } }, {
      attr: { x1: 600, x2: 600 }, ease: "none",
      scrollTrigger: { trigger: scrolly, start: "top 30%", end: "bottom 70%", scrub: 0.4 },
    });
  }

  // ------------------------------------------------------------- 6. lab
  var labShell = $("#lab-shell");
  if (labShell) {
    claim([labShell]);
    gsap.fromTo(labShell, { y: 90, scale: 0.94, opacity: 0.4 }, {
      y: 0, scale: 1, opacity: 1, ease: "none",
      scrollTrigger: { trigger: "#lab", start: "top 85%", end: "top 15%", scrub: 0.5 },
    });
  }

  // ---------------------------------------------------------- 7. results
  $$("#results .stat").forEach(function (card, i) {
    gsap.fromTo(card, { y: 40 + i * 30 }, {
      y: 0, ease: "none",
      scrollTrigger: { trigger: card, start: "top bottom", end: "top 55%", scrub: true },
    });
  });

  // Charts, fonts and the lab change heights after load: measure again.
  window.addEventListener("load", function () { ST.refresh(); });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { ST.refresh(); });
  setTimeout(function () { ST.refresh(); }, 1500);
})();
