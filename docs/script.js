(function () {
  "use strict";

  var modules = window.PUBLIC_COURSE_PREVIEW || [];
  var chapterGrid = document.getElementById("chapterGrid");
  var heroPreview = document.getElementById("heroPreview");
  var revealNodes = Array.prototype.slice.call(document.querySelectorAll("[data-reveal]"));
  var navLinks = Array.prototype.slice.call(document.querySelectorAll(".site-nav a"));
  var sections = navLinks
    .map(function (link) {
      var id = link.getAttribute("href");
      return id && id.startsWith("#") ? document.querySelector(id) : null;
    })
    .filter(Boolean);

  function escapeHtml(text) {
    return String(text == null ? "" : text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function renderHeroPreview() {
    if (!heroPreview || !modules.length) return;
    var mod = modules[0];
    heroPreview.innerHTML =
      '<div class="lesson-preview-header">' +
        "<div>" +
          '<p class="lesson-label">Chapter ' + escapeHtml(mod.order) + "</p>" +
          "<h2>" + escapeHtml(mod.title) + "</h2>" +
          '<p class="lesson-meta">Static lesson preview with grounded explanations and built-in checks</p>' +
        "</div>" +
        '<div class="lesson-statuses">' +
          "<span>Citation verified</span>" +
          "<span>Gate 1 clean</span>" +
          "<span>Student lesson</span>" +
        "</div>" +
      "</div>" +
      '<div class="lesson-panels">' +
        "<article>" +
          "<h3>Lesson section</h3>" +
          "<strong>" + escapeHtml(mod.firstSection.title) + "</strong>" +
          "<p>" + escapeHtml(mod.firstSection.content) + "</p>" +
          '<div class="citation-line">Source-grounded excerpt from the validated lesson build</div>' +
        "</article>" +
        "<article>" +
          "<h3>Worked example</h3>" +
          "<strong>" + escapeHtml(mod.workedExample.question) + "</strong>" +
          "<p>" + escapeHtml(mod.workedExample.answer) + "</p>" +
          '<div class="practice-block">' +
            "<h4>Practice question</h4>" +
            "<p>" + escapeHtml(mod.practice.question) + "</p>" +
          "</div>" +
        "</article>" +
      "</div>";
  }

  function renderChapterGrid() {
    if (!chapterGrid) return;
    chapterGrid.innerHTML = modules.map(function (mod) {
      return (
        '<article class="chapter-card" data-reveal>' +
          '<span class="chapter-order">' + escapeHtml(mod.order) + "</span>" +
          "<div>" +
            "<h3>" + escapeHtml(mod.title) + "</h3>" +
            "<p>" + escapeHtml(mod.summary) + "</p>" +
          "</div>" +
          '<div class="chapter-stats">' +
            '<div class="stat-box"><strong>' + escapeHtml(mod.sections) + '</strong><span>Sections</span></div>' +
            '<div class="stat-box"><strong>' + escapeHtml(mod.workedExamples) + '</strong><span>Worked</span></div>' +
            '<div class="stat-box"><strong>' + escapeHtml(mod.practiceQuestions) + '</strong><span>Practice</span></div>' +
            '<div class="stat-box"><strong>' + escapeHtml(mod.checks) + '</strong><span>Checks</span></div>' +
          "</div>" +
          '<div class="chapter-actions">' +
            '<a class="button button-primary" href="demo.html?module=' + encodeURIComponent(mod.id) + '">Open demo</a>' +
            '<a class="button button-secondary" href="#case-study">View case study</a>' +
          "</div>" +
        "</article>"
      );
    }).join("");
  }

  function activateRevealAndNav() {
    revealNodes = Array.prototype.slice.call(document.querySelectorAll("[data-reveal]"));
    if ("IntersectionObserver" in window) {
      var revealObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            revealObserver.unobserve(entry.target);
          }
        });
      }, { threshold: 0.16 });

      revealNodes.forEach(function (node) {
        revealObserver.observe(node);
      });

      var sectionObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          var id = "#" + entry.target.id;
          var link = navLinks.find(function (item) {
            return item.getAttribute("href") === id;
          });
          if (!link) return;
          if (entry.isIntersecting) {
            navLinks.forEach(function (item) { item.classList.remove("is-active"); });
            link.classList.add("is-active");
          }
        });
      }, { rootMargin: "-35% 0px -45% 0px", threshold: 0.01 });

      sections.forEach(function (section) {
        sectionObserver.observe(section);
      });
    } else {
      revealNodes.forEach(function (node) {
        node.classList.add("is-visible");
      });
    }
  }

  renderHeroPreview();
  renderChapterGrid();
  activateRevealAndNav();
})();
