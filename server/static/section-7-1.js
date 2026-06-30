(function () {
  "use strict";

  var form = document.getElementById("chatForm");
  var input = document.getElementById("questionInput");
  var sendButton = document.getElementById("sendButton");
  var messages = document.getElementById("messages");
  var statusBadge = document.getElementById("statusBadge");
  var loading = document.getElementById("loadingIndicator");
  var errorState = document.getElementById("errorState");
  var inFlight = false;
  var lastQuestion = "";
  var sessionId = window.crypto && window.crypto.randomUUID
    ? window.crypto.randomUUID()
    : String(Date.now()) + "-" + Math.random().toString(16).slice(2);

  function setBusy(value) {
    inFlight = value;
    input.disabled = value;
    sendButton.disabled = value;
    loading.hidden = !value;
  }

  var debugToggle = document.getElementById("debugToggle");

  var STATUS_LABELS = {
    verified: "Answer verified",
    ambiguous: "Couldn't fully verify",
    insufficient_evidence: "Needs another source",
    model_error: "Technical hiccup",
    conversational: "Tutor",
    checking: "Checking…",
    idle: "idle"
  };

  // Learner-friendly rewrites of internal snake_case next actions.
  var NEXT_ACTION_LABELS = {
    ask_about_phosphorus_containing_compounds: "Ask a question about phosphorus-containing compounds.",
    review_phosphoric_acid_dissociation: "Review how phosphoric acid loses each proton.",
    review_cited_passages: "Review the cited passage.",
    configure_missing_environment_variables: "The tutor isn't fully configured yet.",
    retry_or_use_mock_mode: "Try again in a moment."
  };

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

  function debugOn() {
    return !!(debugToggle && debugToggle.checked);
  }

  function setStatus(status) {
    statusBadge.className = "status-badge " + (status || "idle");
    statusBadge.textContent = STATUS_LABELS[status] || status || "idle";
  }

  function addSuggestions(node, suggestions) {
    if (!suggestions || !suggestions.length) {
      return;
    }
    var wrap = document.createElement("div");
    wrap.className = "suggestions";
    suggestions.forEach(function (text) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "suggestion-btn";
      button.textContent = text;
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
    var box = document.createElement("details");
    box.className = "debug-block";
    box.open = true;
    var summary = document.createElement("summary");
    summary.textContent = "Developer details";
    box.appendChild(summary);

    var meta = document.createElement("p");
    meta.className = "debug-line";
    meta.textContent = "status=" + response.status + "  next=" + (response.recommendedNextAction || "-");
    box.appendChild(meta);

    if (response.gateOutcomes && response.gateOutcomes.length) {
      var gates = document.createElement("ul");
      gates.className = "gate-list";
      response.gateOutcomes.forEach(function (gate) {
        var gateItem = document.createElement("li");
        gateItem.textContent = gate.gate + ": " + (gate.ok ? "passed" : "failed") + " - " + gate.reason;
        gates.appendChild(gateItem);
      });
      box.appendChild(gates);
    }
    node.appendChild(box);
  }

  function addMessage(kind, text, response) {
    var node = document.createElement("div");
    node.className = "message " + kind;
    var p = document.createElement("p");
    p.textContent = text;
    node.appendChild(p);

    if (response) {
      if (response.status === "conversational") {
        addSuggestions(node, response.metadata && response.metadata.suggestions);
      } else {
        if (response.citedSources && response.citedSources.length) {
          var sourcesHeading = document.createElement("p");
          sourcesHeading.className = "sources-heading";
          sourcesHeading.textContent = "Sources";
          node.appendChild(sourcesHeading);

          var citations = document.createElement("ul");
          citations.className = "citations";
          response.citedSources.forEach(function (source) {
            var item = document.createElement("li");
            var label = document.createElement("strong");
            label.textContent = source.label;
            var id = document.createElement("span");
            id.className = "source-id";
            id.textContent = source.sourceId;
            item.appendChild(label);
            item.appendChild(id);
            citations.appendChild(item);
          });
          node.appendChild(citations);
        }

        var friendly = humanizeAction(response.recommendedNextAction);
        if (friendly) {
          var action = document.createElement("p");
          action.className = "next-step";
          action.textContent = "Suggested next step: " + friendly;
          node.appendChild(action);
        }

        if (response.status === "model_error") {
          var retry = document.createElement("button");
          retry.type = "button";
          retry.className = "retry-button";
          retry.textContent = "Retry";
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
    if (data.status === "conversational") {
      addMessage("assistant", data.answer, data);
    } else if (data.status === "verified") {
      addMessage("assistant", data.answer, data);
    } else if (data.status === "ambiguous") {
      addMessage("assistant warning", "I found relevant Section 7.1 material but couldn't fully verify an answer. Try asking it a different way.", data);
    } else if (data.status === "insufficient_evidence") {
      addMessage("assistant warning", "This Section 7.1 passage set doesn't cover that yet. I can help with phosphoric acid, pyrophosphate, or ATP — or this can search other sections later.", data);
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
      body: JSON.stringify({ question: question, sectionId: "7.1" })
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
}());
