(function () {
  "use strict";

  var form = document.getElementById("chatForm");
  var input = document.getElementById("questionInput");
  var sendButton = document.getElementById("sendButton");
  var messages = document.getElementById("messages");
  var statusBadge = document.getElementById("statusBadge");
  var lessonTitle = document.getElementById("lesson-title");
  var chatTitle = document.getElementById("chat-title");
  var welcomeMessage = document.getElementById("welcomeMessage");
  var loading = document.getElementById("loadingIndicator");
  var errorState = document.getElementById("errorState");
  var debugToggle = document.getElementById("debugToggle");
  var sectionsRoot = document.getElementById("sectionsRoot");
  var objectivesList = document.getElementById("objectivesList");
  var workedExamplesRoot = document.getElementById("workedExamplesRoot");
  var finalQuizRoot = document.getElementById("finalQuizRoot");
  var progressCount = document.getElementById("progressCount");
  var progressBar = document.getElementById("progressBar");
  var quizScore = document.getElementById("quizScore");
  var inFlight = false;
  var lastQuestion = "";
  var chapter = null;
  var checkpointTotal = 0;
  var params = new URLSearchParams(window.location.search);
  var chapterId = params.get("chapter") || "7.1";
  var stateKey = "chapter-" + chapterId + "-state";
  var sessionId = window.crypto && window.crypto.randomUUID
    ? window.crypto.randomUUID()
    : String(Date.now()) + "-" + Math.random().toString(16).slice(2);

  var STATUS_LABELS = {
    verified: "Answer verified",
    ambiguous: "Couldn't fully verify",
    insufficient_evidence: "Needs another source",
    model_error: "Technical hiccup",
    conversational: "Tutor",
    checking: "Checking...",
    idle: "idle"
  };

  var NEXT_ACTION_LABELS = {
    ask_about_phosphorus_containing_compounds: "Ask a question about phosphorus-containing compounds.",
    review_phosphoric_acid_dissociation: "Review how phosphoric acid loses each proton.",
    review_cited_passages: "Review the cited passage.",
    review_chapter_7_1_passage: "Review the cited passage.",
    configure_missing_environment_variables: "The tutor isn't fully configured yet.",
    retry_or_use_mock_mode: "Try again in a moment."
  };

  function defaultState() {
    return {
      chapter: chapterId,
      currentSection: "",
      currentConcept: "",
      latestCheckpoint: "",
      completedCheckpoints: [],
      checkpointAttempts: {},
      detectedMisconception: "",
      chapterQuizScore: null
    };
  }

  function loadState() {
    try {
      return Object.assign(defaultState(), JSON.parse(localStorage.getItem(stateKey) || "{}"));
    } catch (_error) {
      return defaultState();
    }
  }

  var learnerState = loadState();

  function saveState() {
    learnerState.chapter = chapterId;
    localStorage.setItem(stateKey, JSON.stringify(learnerState));
    renderProgress();
  }

  function setBusy(value) {
    inFlight = value;
    input.disabled = value;
    sendButton.disabled = value;
    loading.hidden = !value;
  }

  function debugOn() {
    return !!(debugToggle && debugToggle.checked);
  }

  function setStatus(status) {
    statusBadge.className = "status-badge " + (status || "idle");
    statusBadge.textContent = STATUS_LABELS[status] || status || "idle";
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) {
      node.className = className;
    }
    if (text !== undefined) {
      node.textContent = text;
    }
    return node;
  }

  function humanizeAction(action) {
    if (!action) {
      return "";
    }
    if (NEXT_ACTION_LABELS[action]) {
      return NEXT_ACTION_LABELS[action];
    }
    var text = action.replace(/_/g, " ");
    return text.charAt(0).toUpperCase() + text.slice(1) + ".";
  }

  function currentSection() {
    if (!chapter) {
      return null;
    }
    return chapter.sections.find(function (section) {
      return section.id === learnerState.currentSection;
    }) || chapter.sections[0];
  }

  function sectionLabel() {
    return chapter ? "Section " + chapter.sectionId : "this chapter";
  }

  function currentConcept() {
    var section = currentSection();
    return section ? section.concept : "";
  }

  function renderProgress() {
    var completed = learnerState.completedCheckpoints || [];
    var total = checkpointTotal || 0;
    var pct = total ? Math.round((completed.length / total) * 100) : 0;
    progressCount.textContent = completed.length + "/" + total + " checkpoints";
    progressBar.style.width = pct + "%";
    if (learnerState.chapterQuizScore) {
      quizScore.textContent = "Quiz: " + learnerState.chapterQuizScore.correct + "/" + learnerState.chapterQuizScore.total;
    }
  }

  function addSuggestions(node, suggestions) {
    if (!suggestions || !suggestions.length) {
      return;
    }
    var wrap = el("div", "suggestions");
    suggestions.forEach(function (text) {
      var button = el("button", "suggestion-btn", text);
      button.type = "button";
      button.addEventListener("click", function () {
        submitQuestion(text);
      });
      wrap.appendChild(button);
    });
    node.appendChild(wrap);
  }

  function addDebugDetails(node, response) {
    if (!debugOn()) {
      return;
    }
    var box = el("details", "debug-block");
    box.open = true;
    box.appendChild(el("summary", "", "Developer details"));
    box.appendChild(el("p", "debug-line", "status=" + response.status + "  next=" + (response.recommendedNextAction || "-")));
    if (response.gateOutcomes && response.gateOutcomes.length) {
      var gates = el("ul", "gate-list");
      response.gateOutcomes.forEach(function (gate) {
        gates.appendChild(el("li", "", gate.gate + ": " + (gate.ok ? "passed" : "failed") + " - " + gate.reason));
      });
      box.appendChild(gates);
    }
    node.appendChild(box);
  }

  function addMessage(kind, text, response) {
    var node = el("div", "message " + kind);
    node.appendChild(el("p", "", text));
    if (response) {
      if (response.status === "conversational") {
        addSuggestions(node, response.metadata && response.metadata.suggestions);
      } else {
        if (response.citedSources && response.citedSources.length) {
          node.appendChild(el("p", "sources-heading", "Sources"));
          var citations = el("ul", "citations");
          response.citedSources.forEach(function (source) {
            var item = el("li");
            item.appendChild(el("strong", "", source.label));
            item.appendChild(el("span", "source-id", source.sourceId));
            citations.appendChild(item);
          });
          node.appendChild(citations);
        }
        var friendly = humanizeAction(response.recommendedNextAction);
        if (friendly) {
          node.appendChild(el("p", "next-step", "Suggested next step: " + friendly));
        }
        if (response.status === "model_error") {
          var retry = el("button", "retry-button", "Retry");
          retry.type = "button";
          retry.addEventListener("click", function () {
            submitQuestion(lastQuestion);
          });
          node.appendChild(retry);
        }
      }
      addDebugDetails(node, response);
    }
    messages.appendChild(node);
    messages.scrollTop = messages.scrollHeight;
  }

  function displayResponse(data) {
    setStatus(data.status);
    if (data.status === "conversational" || data.status === "verified") {
      addMessage("assistant", data.answer, data);
    } else if (data.status === "ambiguous") {
      addMessage("assistant warning", "I found relevant " + sectionLabel() + " material but couldn't fully verify an answer. Try asking it a different way.", data);
    } else if (data.status === "insufficient_evidence") {
      addMessage("assistant warning", "This " + sectionLabel() + " passage set doesn't cover that yet. Try asking about the concepts on the page.", data);
    } else if (data.status === "model_error") {
      addMessage("assistant error", "A technical error occurred, so no unverified answer was shown. Please try again.", data);
    } else {
      addMessage("assistant warning", "Unexpected tutor status.", data);
    }
  }

  function submitQuestion(question) {
    if (inFlight) {
      return;
    }
    errorState.textContent = "";
    question = (question || "").trim();
    if (!question) {
      errorState.textContent = "Enter a question first.";
      return;
    }
    if (question.length > 500) {
      errorState.textContent = "Question must be 500 characters or fewer.";
      return;
    }
    learnerState.currentConcept = currentConcept();
    saveState();
    lastQuestion = question;
    addMessage("user", question);
    setBusy(true);
    setStatus("checking");

    fetch("/api/tutor", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Session-ID": sessionId
      },
      body: JSON.stringify({ question: question, sectionId: chapterId, learnerState: learnerState })
    })
      .then(function (response) {
        return response.json().then(function (data) {
          if (!response.ok) {
            throw new Error(data.message || "Tutor request failed.");
          }
          return data;
        });
      })
      .then(displayResponse)
      .catch(function (error) {
        setStatus("model_error");
        errorState.textContent = error.message;
        addMessage("assistant error", "The tutor request failed before a verified answer could be shown.");
      })
      .finally(function () {
        setBusy(false);
      });
  }

  function renderCheckpoint(section, checkpoint) {
    var card = el("form", "checkpoint-card");
    card.dataset.checkpointId = checkpoint.id;
    card.appendChild(el("h3", "", "Checkpoint"));
    card.appendChild(el("p", "checkpoint-prompt", checkpoint.prompt));

    var answerControl;
    if (checkpoint.type === "multiple_choice") {
      answerControl = el("div", "choices");
      checkpoint.choices.forEach(function (choice) {
        var label = el("label", "choice");
        var radio = document.createElement("input");
        radio.type = "radio";
        radio.name = checkpoint.id;
        radio.value = choice.id;
        label.appendChild(radio);
        label.appendChild(el("span", "", choice.text));
        answerControl.appendChild(label);
      });
    } else {
      answerControl = document.createElement("input");
      answerControl.className = "checkpoint-input";
      answerControl.name = "answer";
      answerControl.placeholder = "Type your answer";
    }
    card.appendChild(answerControl);

    var actions = el("div", "checkpoint-actions");
    var submit = el("button", "", "Check");
    submit.type = "submit";
    var hint = el("button", "secondary-button", "Hint");
    hint.type = "button";
    var retry = el("button", "secondary-button", "Retry");
    retry.type = "button";
    retry.hidden = true;
    actions.appendChild(submit);
    actions.appendChild(hint);
    actions.appendChild(retry);
    card.appendChild(actions);

    var feedback = el("div", "checkpoint-feedback");
    feedback.setAttribute("aria-live", "polite");
    card.appendChild(feedback);

    hint.addEventListener("click", function () {
      feedback.className = "checkpoint-feedback hint";
      feedback.textContent = checkpoint.hint;
    });

    retry.addEventListener("click", function () {
      card.reset();
      feedback.textContent = "";
      feedback.className = "checkpoint-feedback";
      retry.hidden = true;
    });

    card.addEventListener("submit", function (event) {
      event.preventDefault();
      var answer = checkpoint.type === "multiple_choice"
        ? (card.querySelector("input[type=radio]:checked") || {}).value
        : card.querySelector(".checkpoint-input").value;
      learnerState.currentSection = section.id;
      learnerState.currentConcept = section.concept;
      fetch("/api/checkpoint", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sectionId: chapterId, checkpointId: checkpoint.id, answer: answer || "", learnerState: learnerState })
      })
        .then(function (response) {
          return response.json().then(function (data) {
            if (!response.ok) {
              throw new Error(data.message || "Checkpoint failed.");
            }
            return data;
          });
        })
        .then(function (data) {
          learnerState = data.learnerState;
          saveState();
          var result = data.evaluation.result;
          card.classList.toggle("completed", data.evaluation.completed);
          feedback.className = "checkpoint-feedback " + result;
          feedback.textContent = result.toUpperCase() + ": " + data.evaluation.explanation;
          retry.hidden = data.evaluation.completed;
        })
        .catch(function (error) {
          feedback.className = "checkpoint-feedback incorrect";
          feedback.textContent = error.message;
        });
    });
    return card;
  }

  function renderChapter(data) {
    chapter = data;
    chapterId = chapter.sectionId || chapterId;
    stateKey = "chapter-" + chapterId + "-state";
    learnerState = Object.assign(defaultState(), learnerState, { chapter: chapterId });
    if (!learnerState.currentSection || !chapter.sections.some(function (section) { return section.id === learnerState.currentSection; })) {
      learnerState.currentSection = chapter.sections[0] ? chapter.sections[0].id : "";
    }
    document.title = "Section " + chapter.sectionId + " Tutor - " + chapter.title;
    lessonTitle.textContent = "Section " + chapter.sectionId + ": " + chapter.title;
    chatTitle.textContent = "Ask Section " + chapter.sectionId;
    welcomeMessage.textContent = "Hi! Ask anything about Section " + chapter.sectionId + ". Factual answers cite the approved passage they came from.";
    checkpointTotal = chapter.sections.reduce(function (sum, section) {
      return sum + section.checkpoints.length;
    }, 0);
    objectivesList.innerHTML = "";
    chapter.learningObjectives.forEach(function (objective) {
      objectivesList.appendChild(el("li", "", objective));
    });
    sectionsRoot.innerHTML = "";
    chapter.sections.forEach(function (section) {
      var node = el("article", "lesson-section");
      node.id = section.id;
      node.appendChild(el("h2", "", section.title));
      section.explanationBlocks.forEach(function (block) {
        node.appendChild(el("p", "explanation-block", block));
      });
      var ideas = el("div", "key-ideas");
      section.keyIdeaCards.forEach(function (idea) {
        var card = el("div", "key-card");
        card.appendChild(el("h3", "", idea.title));
        card.appendChild(el("p", "", idea.text));
        ideas.appendChild(card);
      });
      node.appendChild(ideas);
      section.checkpoints.forEach(function (checkpoint) {
        node.appendChild(renderCheckpoint(section, checkpoint));
      });
      node.addEventListener("focusin", function () {
        learnerState.currentSection = section.id;
        learnerState.currentConcept = section.concept;
        saveState();
      });
      sectionsRoot.appendChild(node);
    });

    workedExamplesRoot.innerHTML = "";
    chapter.workedExamples.forEach(function (example) {
      var node = el("article", "worked-example");
      node.appendChild(el("h2", "", example.title));
      node.appendChild(el("p", "checkpoint-prompt", example.prompt));
      var list = el("ol", "worked-steps");
      example.steps.forEach(function (step) {
        list.appendChild(el("li", "", step));
      });
      node.appendChild(list);
      node.appendChild(el("p", "worked-answer", example.answer));
      workedExamplesRoot.appendChild(node);
    });

    renderFinalQuiz();
    renderProgress();
  }

  function renderFinalQuiz() {
    finalQuizRoot.innerHTML = "";
    finalQuizRoot.appendChild(el("h2", "", "Final Quiz"));
    var formNode = el("form", "quiz-form");
    chapter.finalQuiz.questions.forEach(function (question) {
      var field = el("fieldset", "quiz-question");
      field.appendChild(el("legend", "", question.prompt));
      question.choices.forEach(function (choice) {
        var label = el("label", "choice");
        var radio = document.createElement("input");
        radio.type = "radio";
        radio.name = question.id;
        radio.value = choice.id;
        label.appendChild(radio);
        label.appendChild(el("span", "", choice.text));
        field.appendChild(label);
      });
      formNode.appendChild(field);
    });
    var submit = el("button", "", "Submit quiz");
    submit.type = "submit";
    formNode.appendChild(submit);
    var resultBox = el("div", "quiz-results");
    formNode.appendChild(resultBox);
    formNode.addEventListener("submit", function (event) {
      event.preventDefault();
      var answers = {};
      chapter.finalQuiz.questions.forEach(function (question) {
        var checked = formNode.querySelector("input[name='" + question.id + "']:checked");
        answers[question.id] = checked ? checked.value : "";
      });
      fetch("/api/final-quiz", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sectionId: chapterId, answers: answers, learnerState: learnerState })
      })
        .then(function (response) {
          return response.json().then(function (data) {
            if (!response.ok) {
              throw new Error(data.message || "Quiz failed.");
            }
            return data;
          });
        })
        .then(function (data) {
          learnerState = data.learnerState;
          saveState();
          resultBox.innerHTML = "";
          resultBox.appendChild(el("p", "worked-answer", "Score: " + data.score.correct + "/" + data.score.total));
          data.results.forEach(function (result) {
            resultBox.appendChild(el("p", result.result, result.result.toUpperCase() + ": " + result.explanation));
          });
        })
        .catch(function (error) {
          resultBox.textContent = error.message;
        });
    });
    finalQuizRoot.appendChild(formNode);
  }

  document.querySelectorAll(".tutor-actions button").forEach(function (button) {
    button.addEventListener("click", function () {
      var action = button.dataset.action;
      var section = currentSection();
      var concept = section ? section.concept : "this section";
      var checkpoint = learnerState.latestCheckpoint || "my latest checkpoint";
      var misconception = learnerState.detectedMisconception || "no specific misconception detected";
      var prompt = action + " for " + sectionLabel() + ". Current section: " + (section ? section.title : "") + ". Concept: " + concept + ". Latest checkpoint: " + checkpoint + ". Detected misconception: " + misconception + ".";
      submitQuestion(prompt);
    });
  });

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    submitQuestion(input.value);
    input.value = "";
  });

  input.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  fetch("/api/chapter/" + encodeURIComponent(chapterId))
    .then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok) {
          throw new Error(data.message || "The interactive chapter could not load.");
        }
        return data;
      });
    })
    .then(renderChapter)
    .catch(function () {
      sectionsRoot.appendChild(el("p", "error", "The interactive chapter could not load."));
    });
}());
