(function () {
  "use strict";

  var DEBOUNCE_MS = 600;

  function scoreClass(score) {
    if (score >= 70) return "seo-analyzer__score--good";
    if (score >= 40) return "seo-analyzer__score--ok";
    return "seo-analyzer__score--bad";
  }

  function parentFieldValue(form, name) {
    var input = form.querySelector("#id_" + name);
    return input ? input.value.trim() : "";
  }

  function getCsrfToken(form) {
    var tokenInput = form.querySelector('[name="csrfmiddlewaretoken"]');
    return tokenInput ? tokenInput.value : "";
  }

  function liveBodyPlaintext() {
    var field = document.getElementById("id_body_plaintext");
    return field ? field.value.trim() : null;
  }

  function getReadabilityConfig(root) {
    if (root.nextElementSibling && root.nextElementSibling.classList.contains("seo-analyzer-config")) {
      return root.nextElementSibling;
    }
    return null;
  }

  function updateScoreRing(ring, score) {
    ring.classList.remove(
      "seo-analyzer__score--good",
      "seo-analyzer__score--ok",
      "seo-analyzer__score--bad",
      "seo-analyzer__score--neutral"
    );
    ring.classList.add(scoreClass(score));
  }

  function renderChecks(container, checks) {
    container.innerHTML = checks
      .map(function (check) {
        return (
          '<li class="seo-analyzer__check seo-analyzer__check--' +
          check.status +
          '">' +
          '<span class="seo-analyzer__dot" aria-hidden="true"></span>' +
          '<span class="seo-analyzer__check-body">' +
          "<strong>" +
          check.label +
          "</strong>" +
          '<span class="seo-analyzer__message">' +
          check.message +
          "</span></span></li>"
        );
      })
      .join("");
  }

  function renderList(container, items, className, emptyMessage) {
    if (!items || !items.length) {
      container.innerHTML =
        '<li class="' + className + ' ' + className + '--none">' + emptyMessage + "</li>";
      return;
    }
    container.innerHTML = items
      .map(function (item) {
        return '<li class="' + className + '">' + item + "</li>";
      })
      .join("");
  }

  function initReadabilityAnalyzer(root) {
    var form = root.closest("form");
    if (!form) return;

    var config = getReadabilityConfig(root);
    var apiUrl = config ? config.dataset.seoAnalyzerApi : null;
    if (!apiUrl) return;

    var timer = null;
    var inflight = null;
    var requestId = 0;

    function runAnalysis() {
      if (inflight) inflight.abort();
      var thisRequestId = ++requestId;
      inflight = new AbortController();
      root.classList.add("is-loading");

      fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(form),
        },
        body: JSON.stringify({
          content_type_id: config.dataset.contentTypeId || null,
          object_id: config.dataset.objectId || null,
          excerpt: parentFieldValue(form, "short_description") || parentFieldValue(form, "excerpt"),
          // Live document overrides (Phase 2).
          body_plaintext: liveBodyPlaintext(),
        }),
        signal: inflight.signal,
      })
        .then(function (response) {
          if (!response.ok) throw new Error("Analysis failed");
          return response.json();
        })
        .then(function (data) {
          if (thisRequestId !== requestId) {
            return;
          }
          var scoreValue = root.querySelector("[data-seo-score-value]");
          var scoreRing = root.querySelector("[data-seo-score-ring]");
          var difficultyLabel = root.querySelector("[data-seo-difficulty-label]");
          var checksList = root.querySelector("[data-seo-checks-list]");
          var warningsList = root.querySelector("[data-seo-warnings-list]");
          var recommendationsList = root.querySelector("[data-seo-recommendations-list]");

          if (scoreValue) scoreValue.textContent = String(data.score);
          if (scoreRing) updateScoreRing(scoreRing, data.score);
          if (difficultyLabel) difficultyLabel.textContent = data.difficulty_label || "N/A";
          if (checksList && data.checks) renderChecks(checksList, data.checks);
          if (warningsList) {
            renderList(warningsList, data.warnings, "seo-analyzer__warning", "No warnings.");
          }
          if (recommendationsList && data.recommendations) {
            renderList(
              recommendationsList,
              data.recommendations,
              "seo-analyzer__recommendation",
              "No recommendations."
            );
          }
        })
        .catch(function (error) {
          if (error.name !== "AbortError") {
            console.warn("SEO readability analysis error:", error);
          }
        })
        .finally(function () {
          if (thisRequestId === requestId) {
            root.classList.remove("is-loading");
            inflight = null;
          }
        });
    }

    function scheduleAnalysis() {
      window.clearTimeout(timer);
      timer = window.setTimeout(runAnalysis, DEBOUNCE_MS);
    }

    var excerptInput = form.querySelector("#id_excerpt");
    if (excerptInput) {
      excerptInput.addEventListener("input", scheduleAnalysis);
      excerptInput.addEventListener("change", scheduleAnalysis);
    }

    var bodyPlaintextInput = form.querySelector("#id_body_plaintext");
    if (bodyPlaintextInput) {
      bodyPlaintextInput.addEventListener("input", scheduleAnalysis);
      bodyPlaintextInput.addEventListener("change", scheduleAnalysis);
    }
  }

  function boot() {
    document.querySelectorAll("[data-seo-readability-analyzer]").forEach(initReadabilityAnalyzer);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
