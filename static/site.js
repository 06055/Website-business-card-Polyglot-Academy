/* Polyglot Academy - behaviour shared by every page: language, header, mobile menu.
 *
 * The server already renders the page in the right language (manual choice, IP country, then the
 * browser language), so nothing is re-translated on load and nothing flashes.
 * This script only switches languages by hand - instantly, from the same texts the server used -
 * and remembers that choice in a cookie the server reads on the next visit.
 */
(function () {
  "use strict";

  var root = document.documentElement;
  var dataEl = document.getElementById("i18n-data");
  var I18N = dataEl ? JSON.parse(dataEl.textContent) : {};
  var COOKIE = root.getAttribute("data-lang-cookie") || "polyglot_lang";
  var LANGS = ["en", "uk", "ru"];
  var META = {
    en: { label: "EN", flag: "fi-us" },
    uk: { label: "UA", flag: "fi-ua" },
    ru: { label: "RU", flag: "fi-ru" }
  };

  function readCookie(name) {
    var match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    try {
      return match ? decodeURIComponent(match[1]) : "";
    } catch (e) {
      return ""; // A malformed cookie must not disable the language switcher or mobile menu.
    }
  }

  function saveChoice(lang) {
    var secure = location.protocol === "https:" ? "; Secure" : "";
    document.cookie = COOKIE + "=" + lang + "; Max-Age=31536000; Path=/; SameSite=Lax" + secure;
  }

  function applyLang(lang) {
    var dict = I18N[lang];
    if (!dict) return;
    root.lang = lang;

    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      var key = el.getAttribute("data-i18n");
      if (dict[key] !== undefined) el.textContent = dict[key];
    });
    document.querySelectorAll("[data-i18n-html]").forEach(function (el) {
      var key = el.getAttribute("data-i18n-html");
      if (dict[key] !== undefined) el.innerHTML = dict[key];
    });
    document.querySelectorAll("[data-i18n-attr]").forEach(function (el) {
      el.getAttribute("data-i18n-attr").split(";").forEach(function (pair) {
        var parts = pair.split(":");
        var attr = (parts[0] || "").trim();
        var key = (parts[1] || "").trim();
        if (attr && key && dict[key] !== undefined) el.setAttribute(attr, dict[key]);
      });
    });

    var meta = META[lang] || META.en;
    var flag = document.getElementById("langFlag");
    var label = document.getElementById("langLabel");
    if (flag) flag.className = "fi " + meta.flag + " fis";
    if (label) label.textContent = meta.label;
    document.querySelectorAll("[data-lang]").forEach(function (el) {
      el.setAttribute("aria-pressed", String(el.getAttribute("data-lang") === lang));
    });
  }

  function chooseLang(lang) {
    if (LANGS.indexOf(lang) === -1) return;
    saveChoice(lang);
    applyLang(lang);
  }

  // One-time move of a choice made before this version: the old code kept it in localStorage and also
  // wrote "en" there on every visit, so only "uk" / "ru" can be told apart as a real choice.
  (function migrateOldChoice() {
    var old = "";
    try {
      old = localStorage.getItem("lang") || "";
      localStorage.removeItem("lang");
    } catch (e) { /* storage blocked: nothing to move */ }
    if (!readCookie(COOKIE) && (old === "uk" || old === "ru")) {
      saveChoice(old);
      if (old !== root.lang) applyLang(old);
    }
  })();

  // ---------------------------------------------------------------- language dropdown and buttons
  var dropdown = document.getElementById("langDropdown");
  var dropdownBtn = document.getElementById("langBtn");

  function closeDropdown() {
    if (!dropdown) return;
    dropdown.classList.remove("is-open");
    if (dropdownBtn) dropdownBtn.setAttribute("aria-expanded", "false");
  }

  if (dropdownBtn) {
    dropdownBtn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      var open = dropdown.classList.toggle("is-open");
      dropdownBtn.setAttribute("aria-expanded", String(open));
    });
  }

  document.addEventListener("click", function (e) {
    var item = e.target.closest("[data-lang]");
    if (item) {
      chooseLang(item.getAttribute("data-lang"));
      closeDropdown();
      return;
    }
    if (dropdown && !dropdown.contains(e.target)) closeDropdown();
  });

  // ---------------------------------------------------------------- header and mobile menu
  var header = document.getElementById("header");
  if (header) {
    var setHeader = function () { header.classList.toggle("is-solid", window.scrollY > 10); };
    window.addEventListener("scroll", setHeader, { passive: true });
    setHeader();
  }

  var burger = document.getElementById("burger");
  var mobile = document.getElementById("mobile");
  var closeMobile = document.getElementById("closeMobile");

  function setMenu(open) {
    if (!mobile) return;
    mobile.classList.toggle("is-open", open);
    if (burger) burger.setAttribute("aria-expanded", String(open));
    document.body.classList.toggle("menu-open", open);
  }

  if (burger) burger.addEventListener("click", function () { setMenu(true); });
  if (closeMobile) closeMobile.addEventListener("click", function () { setMenu(false); });
  if (mobile) {
    mobile.addEventListener("click", function (e) { if (e.target === mobile) setMenu(false); });
  }

  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    closeDropdown();
    setMenu(false);
  });

  document.querySelectorAll('a[href^="#"]').forEach(function (link) {
    link.addEventListener("click", function (e) {
      var id = link.getAttribute("href");
      if (!id || id === "#") return;
      var target = document.querySelector(id);
      if (!target) return;
      e.preventDefault();
      setMenu(false);
      var prefersLessMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      var behavior = prefersLessMotion ? "auto" : "smooth";
      var isMobile = window.matchMedia && window.matchMedia("(max-width: 980px)").matches;
      var sectionTitle = isMobile && target.querySelector && target.querySelector(".section-title");
      if (sectionTitle) {
        var header = document.querySelector(".header");
        var headerHeight = header ? header.getBoundingClientRect().height : 72;
        window.scrollTo({
          top: window.scrollY + sectionTitle.getBoundingClientRect().top - headerHeight - 26,
          behavior: behavior
        });
      } else {
        target.scrollIntoView({ behavior: behavior, block: "start" });
      }
    });
  });

  // Keep the vertical travelling light between the A1 and C1 marker centers as text wraps or changes language.
  var levelTrack = document.querySelector && document.querySelector(".levels__track");
  var c1Code = levelTrack && levelTrack.querySelector(".level--c1 .level__code");
  if (c1Code) {
    var setLevelShimmerEnd = function () {
      var trackBottom = levelTrack.getBoundingClientRect().bottom;
      var c1Rect = c1Code.getBoundingClientRect();
      levelTrack.style.setProperty("--level-shimmer-tail", (trackBottom - c1Rect.top - c1Rect.height / 2) + "px");
    };
    setLevelShimmerEnd();
    if ("ResizeObserver" in window) {
      var levelObserver = new window.ResizeObserver(setLevelShimmerEnd);
      levelObserver.observe(levelTrack);
    } else {
      window.addEventListener("resize", setLevelShimmerEnd);
    }
  }

  // Reveal lower-page content once. Without IntersectionObserver or with reduced motion, it stays visible.
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!reduceMotion && "IntersectionObserver" in window) {
    var revealItems = document.querySelectorAll(
      "#about .section-title, #about .card, #program .section-title, #program .levels, " +
      "#program .grid > .card, #reviews .section-title, #reviews .review-card, " +
      "#contacts .section-title, #contacts .card"
    );
    if (revealItems.length) {
      var revealObserver = new window.IntersectionObserver(function (entries, observer) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        });
      }, { threshold: 0.08, rootMargin: "0px 0px -32px 0px" });

      revealItems.forEach(function (item) {
        item.classList.add("reveal");
        // Keep anything already in view visible when loading or refreshing mid-page.
        if (item.getBoundingClientRect().top < window.innerHeight - 32) {
          item.classList.add("is-visible");
        } else {
          revealObserver.observe(item);
        }
      });
      root.classList.add("motion-ready");
    }
  }
})();
