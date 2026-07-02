(function () {
  "use strict";

  var MODULE_COUNT = 11;
  var PASS_THRESHOLD = 0.8;
  var STORAGE_KEY = "mcatTutorProgress.v4";
  var params = new URLSearchParams(window.location.search);
  var moduleId = params.get("module") || "";
  var modules = [];
  var module = null;
  var tab = "learn";
  var tutorOpen = false;
  var practice = null;
  var root = document.getElementById("lessonRoot");

  function moduleFiles() {
    return Array.from({ length: MODULE_COUNT }, function (_, index) {
      return "/course-data/module-" + (index + 1) + ".json";
    });
  }

  function loadProgress() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{\"lessons\":{}}");
    } catch (_error) {
      return { lessons: {} };
    }
  }

  function saveProgress(progress) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
  }

  function setLessonState(data) {
    var progress = loadProgress();
    progress.lessons[module.id] = Object.assign({}, progress.lessons[module.id] || {}, data);
    saveProgress(progress);
  }

  function lessonState() {
    return loadProgress().lessons[module.id] || {};
  }

  function render() {
    if (!module) return;
    document.title = module.title + " - MCAT Tutor";
    root.innerHTML = "";
    root.className = "lesson-shell";
    var grid = node("div", "lesson-grid" + (tutorOpen ? " tutor-open" : ""));
    grid.appendChild(renderSectionNav());
    var main = node("article", "lesson-main");
    main.appendChild(renderHeader());
    var body = node("div", "lesson-body");
    if (tab === "practice") renderPractice(body);
    else if (tab === "review") renderReview(body);
    else renderLearn(body);
    main.appendChild(body);
    main.appendChild(renderBottomNav());
    grid.appendChild(main);
    grid.appendChild(renderTutor());
    root.appendChild(grid);
  }

  function renderSectionNav() {
    var nav = node("nav", "section-nav");
    nav.setAttribute("aria-label", "Lesson sections");
    [["learn", "Learn"], ["practice", "Practice"], ["review", "Review"]].forEach(function (item) {
      var button = node("button", tab === item[0] ? "active" : "", item[1]);
      button.type = "button";
      button.addEventListener("click", function () {
        tab = item[0];
        practice = null;
        render();
      });
      nav.appendChild(button);
    });
    (module.sections || []).forEach(function (section, index) {
      var button = node("button", "", section.title);
      button.type = "button";
      button.addEventListener("click", function () {
        tab = "learn";
        render();
        setTimeout(function () {
          var target = document.getElementById("section-" + index);
          if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 0);
      });
      nav.appendChild(button);
    });
    return nav;
  }

  function renderHeader() {
    var header = node("header", "lesson-header");
    var copy = node("div");
    copy.appendChild(node("p", "breadcrumb", "Biochemistry"));
    copy.appendChild(node("h1", "", module.title));
    var tabs = node("div", "tabs");
    [["learn", "Learn"], ["practice", "Practice"], ["review", "Review"]].forEach(function (item) {
      var button = node("button", "tab" + (tab === item[0] ? " active" : ""), item[1]);
      button.type = "button";
      button.addEventListener("click", function () {
        tab = item[0];
        practice = null;
        render();
      });
      tabs.appendChild(button);
    });
    copy.appendChild(tabs);
    header.appendChild(copy);
    var tutor = node("button", "button", tutorOpen ? "Close tutor" : "Open tutor");
    tutor.type = "button";
    tutor.addEventListener("click", function () {
      tutorOpen = !tutorOpen;
      render();
    });
    header.appendChild(tutor);
    return header;
  }

  function renderLearn(container) {
    var objectives = node("section");
    objectives.appendChild(node("h2", "", "Learning objectives"));
    var list = node("ul", "objectives");
    (module.objectives || []).forEach(function (objective) {
      list.appendChild(node("li", "", objective));
    });
    objectives.appendChild(list);
    container.appendChild(objectives);

    var concepts = node("section", "section");
    (module.sections || []).forEach(function (section, index) {
      var article = node("section", "concept");
      article.id = "section-" + index;
      article.appendChild(node("h3", "", section.title));
      article.appendChild(node("p", "", section.content));
      concepts.appendChild(article);
    });
    container.appendChild(concepts);

    if (module.equations && module.equations.length) {
      var equations = node("section", "section");
      equations.appendChild(node("h2", "", "Equations"));
      var rows = node("div", "equation-list");
      module.equations.forEach(function (equation) {
        var row = node("div", "equation-row");
        row.appendChild(node("div", "equation-expression", equation.expression));
        row.appendChild(node("div", "equation-meaning", equation.meaning));
        rows.appendChild(row);
      });
      equations.appendChild(rows);
      container.appendChild(equations);
    }

    if (module.workedExamples && module.workedExamples.length) {
      var example = module.workedExamples[0];
      var wrap = node("section", "worked-example");
      wrap.appendChild(node("h2", "", "Worked example"));
      wrap.appendChild(node("p", "question-text", example.question));
      var steps = node("ol");
      (example.steps || []).forEach(function (step) {
        steps.appendChild(node("li", "", step));
      });
      wrap.appendChild(steps);
      var answer = node("p");
      answer.innerHTML = "<strong>Answer:</strong> " + escapeHtml(example.answer);
      wrap.appendChild(answer);
      container.appendChild(wrap);
    }
  }

  function renderPractice(container) {
    if (!practice || practice.moduleId !== module.id) {
      practice = {
        moduleId: module.id,
        questions: (module.checks || []).map(function (question) { return Object.assign({}, question); }),
        index: 0,
        answers: [],
        correct: [],
        finished: false
      };
    }

    var shell = node("section", "practice-shell");
    if (!practice.questions.length) {
      shell.appendChild(node("p", "muted", "No practice checks are available for this lesson."));
      container.appendChild(shell);
      return;
    }
    if (practice.finished) {
      renderPracticeSummary(shell);
      container.appendChild(shell);
      return;
    }

    var question = practice.questions[practice.index];
    shell.appendChild(node("p", "question-count", "Question " + (practice.index + 1) + " of " + practice.questions.length));
    shell.appendChild(node("p", "question-text", question.question));
    if (question.choices && question.choices.length) {
      var choices = node("div", "choice-list");
      question.choices.forEach(function (choice) {
        var button = node("button", "choice", choice);
        button.type = "button";
        button.addEventListener("click", function () { answerQuestion(choice, shell); });
        choices.appendChild(button);
      });
      shell.appendChild(choices);
    } else {
      var form = node("div", "answer-form");
      var input = document.createElement("input");
      input.className = "answer-input";
      input.placeholder = "Type an answer";
      var check = node("button", "button primary", "Check");
      check.type = "button";
      check.addEventListener("click", function () { answerQuestion(input.value, shell); });
      input.addEventListener("keydown", function (event) {
        if (event.key === "Enter") answerQuestion(input.value, shell);
      });
      form.appendChild(input);
      form.appendChild(check);
      shell.appendChild(form);
    }
    shell.appendChild(node("div", "feedback", ""));
    var actions = node("div", "practice-actions");
    var previous = node("button", "button", "Previous");
    previous.type = "button";
    previous.disabled = practice.index === 0;
    previous.addEventListener("click", function () {
      if (practice.index > 0) {
        practice.index -= 1;
        render();
      }
    });
    var next = node("button", "button primary", practice.index === practice.questions.length - 1 ? "Finish" : "Next");
    next.type = "button";
    next.disabled = practice.answers[practice.index] === undefined;
    next.id = "nextQuestion";
    next.addEventListener("click", function () {
      if (practice.answers[practice.index] === undefined) return;
      if (practice.index === practice.questions.length - 1) finishPractice();
      else {
        practice.index += 1;
        render();
      }
    });
    actions.appendChild(previous);
    actions.appendChild(next);
    shell.appendChild(actions);
    container.appendChild(shell);
  }

  function answerQuestion(value, shell) {
    var question = practice.questions[practice.index];
    var correct = isCorrect(question, value);
    practice.answers[practice.index] = value;
    practice.correct[practice.index] = correct;
    Array.prototype.forEach.call(shell.querySelectorAll(".choice"), function (choice) {
      choice.disabled = true;
      if (normalize(choice.textContent) === normalize(question.answer)) choice.classList.add("correct");
      else if (normalize(choice.textContent) === normalize(value)) choice.classList.add("incorrect");
    });
    Array.prototype.forEach.call(shell.querySelectorAll("input, .answer-form .button"), function (control) {
      control.disabled = true;
    });
    var feedback = shell.querySelector(".feedback");
    feedback.className = "feedback open " + (correct ? "good" : "bad");
    feedback.innerHTML = "";
    feedback.appendChild(node("strong", "", correct ? "Correct" : "Not quite"));
    feedback.appendChild(node("p", "", correct ? question.explanation : "Answer: " + question.answer + ". " + question.explanation));
    document.getElementById("nextQuestion").disabled = false;
  }

  function finishPractice() {
    practice.finished = true;
    var correct = practice.correct.filter(Boolean).length;
    var total = practice.questions.length;
    var mastered = total > 0 && correct / total >= PASS_THRESHOLD;
    var mistakes = [];
    practice.questions.forEach(function (question, index) {
      if (!practice.correct[index]) mistakes.push(question.reviewTarget || question.question);
    });
    setLessonState({
      completed: mastered,
      needsReview: !mastered,
      score: correct,
      total: total,
      recentMistakes: mistakes.slice(0, 4)
    });
    render();
  }

  function renderPracticeSummary(container) {
    var correct = practice.correct.filter(Boolean).length;
    var total = practice.questions.length;
    var mastered = total > 0 && correct / total >= PASS_THRESHOLD;
    container.appendChild(node("h2", "", mastered ? "Lesson mastered" : "Review needed"));
    container.appendChild(node("p", "score-line " + (mastered ? "mastered" : "review"), "Score: " + correct + " of " + total));
    var actions = node("div", "practice-actions");
    var retry = node("button", "button", "Retry");
    retry.type = "button";
    retry.addEventListener("click", function () {
      practice = null;
      render();
    });
    var review = node("button", "button primary", mastered ? "Continue" : "Review targets");
    review.type = "button";
    review.addEventListener("click", function () {
      if (mastered) {
        var next = adjacent(1);
        if (next) window.location.href = "/learn?module=" + encodeURIComponent(next.id);
        else window.location.href = "/?screen=course";
      } else {
        tab = "review";
        render();
      }
    });
    actions.appendChild(retry);
    actions.appendChild(review);
    container.appendChild(actions);
  }

  function renderReview(container) {
    var state = lessonState();
    var targets = state.recentMistakes && state.recentMistakes.length
      ? state.recentMistakes
      : (module.checks || []).map(function (question) { return question.reviewTarget || question.question; }).slice(0, 4);
    container.appendChild(node("h2", "", "Review targets"));
    if (!targets.length) {
      container.appendChild(node("p", "muted", "Complete practice to generate review targets."));
    } else {
      var list = node("ul", "review-list");
      targets.forEach(function (target) {
        list.appendChild(node("li", "", target));
      });
      container.appendChild(list);
    }
    var actions = node("div", "practice-actions");
    var button = node("button", "button primary", "Go to practice");
    button.type = "button";
    button.addEventListener("click", function () {
      tab = "practice";
      practice = null;
      render();
    });
    actions.appendChild(node("span"));
    actions.appendChild(button);
    container.appendChild(actions);
  }

  function renderTutor() {
    var panel = node("aside", "tutor-panel");
    panel.appendChild(node("h2", "", "Tutor"));
    panel.appendChild(node("p", "", "Closed by default. Open it when you want a contextual prompt for this lesson."));
    var list = node("ul");
    (module.objectives || []).slice(0, 3).forEach(function (objective) {
      list.appendChild(node("li", "", objective));
    });
    panel.appendChild(list);
    var textarea = document.createElement("textarea");
    textarea.rows = 4;
    textarea.placeholder = "Ask about this lesson";
    panel.appendChild(textarea);
    var ask = node("button", "button primary", "Ask tutor");
    ask.type = "button";
    var response = node("div", "tutor-response", "The local citation-gated tutor is available when the backend maps this lesson to a verified section.");
    ask.addEventListener("click", function () {
      response.textContent = "Tutor question noted for this lesson context. Backend answer routing is unchanged by this visual rebuild.";
    });
    panel.appendChild(ask);
    panel.appendChild(response);
    return panel;
  }

  function renderBottomNav() {
    var nav = node("nav", "bottom-nav");
    nav.setAttribute("aria-label", "Lesson navigation");
    var previous = adjacent(-1);
    var next = adjacent(1);
    var prevButton = node("button", "button", "Previous");
    prevButton.type = "button";
    prevButton.disabled = !previous;
    prevButton.addEventListener("click", function () {
      if (previous) window.location.href = "/learn?module=" + encodeURIComponent(previous.id);
    });
    var nextButton = node("button", "button primary", next ? "Next" : "Course");
    nextButton.type = "button";
    nextButton.addEventListener("click", function () {
      window.location.href = next ? "/learn?module=" + encodeURIComponent(next.id) : "/?screen=course";
    });
    nav.appendChild(prevButton);
    nav.appendChild(nextButton);
    return nav;
  }

  function adjacent(offset) {
    var index = modules.findIndex(function (item) { return item.id === module.id; });
    return index < 0 ? null : modules[index + offset] || null;
  }

  function lessonState() {
    return loadProgress().lessons[module.id] || {};
  }

  function normalize(value) {
    return String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim().replace(/\s+/g, " ");
  }

  function isCorrect(question, value) {
    var answer = normalize(value);
    if (!answer) return false;
    var accepted = [question.answer].concat(question.acceptableAnswers || []).map(normalize);
    return accepted.indexOf(answer) !== -1;
  }

  function node(tag, className, text) {
    var element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function escapeHtml(value) {
    var div = document.createElement("div");
    div.textContent = value || "";
    return div.innerHTML;
  }

  Promise.all(moduleFiles().map(function (file) {
    return fetch(file).then(function (response) {
      if (!response.ok) throw new Error(file + " returned " + response.status);
      return response.json();
    });
  }))
    .then(function (loaded) {
      modules = loaded;
      module = modules.find(function (item) { return item.id === moduleId; }) || modules[0];
      render();
    })
    .catch(function (error) {
      root.innerHTML = "";
      root.appendChild(node("p", "muted", "Lesson could not load: " + error.message));
    });
}());
