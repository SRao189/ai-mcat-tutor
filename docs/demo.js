(function () {
  "use strict";

  var modules = window.PUBLIC_COURSE_PREVIEW || [];
  var nav = document.getElementById("demoNav");
  var title = document.getElementById("demoTitle");
  var summary = document.getElementById("demoSummary");
  var stats = document.getElementById("demoStats");
  var sectionTitle = document.getElementById("demoSectionTitle");
  var sectionContent = document.getElementById("demoSectionContent");
  var workedQuestion = document.getElementById("demoWorkedQuestion");
  var workedAnswer = document.getElementById("demoWorkedAnswer");
  var practiceQuestion = document.getElementById("demoPracticeQuestion");
  var practiceChoices = document.getElementById("demoPracticeChoices");
  var practiceAnswer = document.getElementById("demoPracticeAnswer");

  function byId(id) {
    return document.getElementById(id);
  }

  function moduleFromQuery() {
    var params = new URLSearchParams(window.location.search);
    var wanted = params.get("module");
    return modules.find(function (mod) { return mod.id === wanted; }) || modules[0];
  }

  function escapeHtml(text) {
    return String(text == null ? "" : text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function setActiveModule(moduleId) {
    nav.querySelectorAll(".demo-link").forEach(function (button) {
      button.classList.toggle("is-active", button.dataset.moduleId === moduleId);
    });
  }

  function renderStats(mod) {
    stats.innerHTML =
      '<div class="tag-row">' +
        "<span>" + escapeHtml(mod.sections) + " sections</span>" +
        "<span>" + escapeHtml(mod.workedExamples) + " worked examples</span>" +
        "<span>" + escapeHtml(mod.practiceQuestions) + " practice questions</span>" +
        "<span>" + escapeHtml(mod.checks) + " lesson checks</span>" +
      "</div>";
  }

  function renderModule(mod, updateUrl) {
    if (!mod) return;
    title.textContent = mod.title;
    summary.textContent = mod.summary;
    sectionTitle.textContent = mod.firstSection.title;
    sectionContent.textContent = mod.firstSection.content;
    workedQuestion.textContent = mod.workedExample.question;
    workedAnswer.textContent = mod.workedExample.answer;
    practiceQuestion.textContent = mod.practice.question;
    practiceChoices.innerHTML = mod.practice.choices.map(function (choice) {
      return "<li>" + escapeHtml(choice) + "</li>";
    }).join("");
    practiceAnswer.textContent = "Correct answer: " + mod.practice.choices[mod.practice.answerIndex];
    renderStats(mod);
    setActiveModule(mod.id);

    if (updateUrl) {
      var url = new URL(window.location.href);
      url.searchParams.set("module", mod.id);
      window.history.replaceState({}, "", url.toString());
    }
  }

  function buildNav() {
    nav.innerHTML = modules.map(function (mod) {
      return (
        '<button class="demo-link" type="button" data-module-id="' + escapeHtml(mod.id) + '">' +
          "<strong>" + escapeHtml(mod.order + "  " + mod.title) + "</strong>" +
          "<span>" + escapeHtml(mod.sections) + " sections, " + escapeHtml(mod.practiceQuestions) + " practice questions</span>" +
        "</button>"
      );
    }).join("");

    nav.addEventListener("click", function (event) {
      var target = event.target.closest(".demo-link");
      if (!target) return;
      var mod = modules.find(function (item) { return item.id === target.dataset.moduleId; });
      renderModule(mod, true);
    });
  }

  buildNav();
  renderModule(moduleFromQuery(), false);
  byId("year").textContent = String(new Date().getFullYear());
})();
