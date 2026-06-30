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

  function setStatus(status) {
    statusBadge.className = "status-badge " + (status || "idle");
    statusBadge.textContent = status || "idle";
  }

  function addMessage(kind, text, response) {
    var node = document.createElement("div");
    node.className = "message " + kind;
    var p = document.createElement("p");
    p.textContent = text;
    node.appendChild(p);

    if (response) {
      if (response.citedSources && response.citedSources.length) {
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

      if (response.recommendedNextAction) {
        var action = document.createElement("p");
        action.textContent = "Next: " + response.recommendedNextAction;
        node.appendChild(action);
      }

      if (response.gateOutcomes && response.gateOutcomes.length) {
        var gates = document.createElement("ul");
        gates.className = "gate-list";
        response.gateOutcomes.forEach(function (gate) {
          var gateItem = document.createElement("li");
          gateItem.textContent = gate.gate + ": " + (gate.ok ? "passed" : "failed") + " - " + gate.reason;
          gates.appendChild(gateItem);
        });
        node.appendChild(gates);
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

    messages.appendChild(node);
    messages.scrollTop = messages.scrollHeight;
  }

  function displayResponse(data) {
    setStatus(data.status);
    if (data.status === "verified") {
      addMessage("assistant", data.answer, data);
    } else if (data.status === "ambiguous") {
      addMessage("assistant warning", "The tutor found relevant material, but the answer could not be fully verified.", data);
    } else if (data.status === "insufficient_evidence") {
      addMessage("assistant warning", "The approved Section 7.1 evidence is insufficient for that question.", data);
    } else if (data.status === "model_error") {
      addMessage("assistant error", "A retryable technical error occurred. No unverified answer was shown.", data);
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
