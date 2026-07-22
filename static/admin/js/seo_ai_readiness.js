(function () {
  "use strict";

  var DEBOUNCE_MS = 650;

  function scoreClass(score) {
    if (score >= 70) return "seo-analyzer__score--good";
    if (score >= 40) return "seo-analyzer__score--ok";
    return "seo-analyzer__score--bad";
  }

  function fieldValue(form, suffix) {
    var input = form.querySelector('[name$="-' + suffix + '"]');
    return input ? input.value.trim() : "";
  }

  function parentFieldValue(form, name) {
    var input = form.querySelector("#id_" + name);
    return input ? input.value.trim() : "";
  }

  function getCsrfToken(form) {
    var tokenInput = form.querySelector('[name="csrfmiddlewaretoken"]');
    return tokenInput ? tokenInput.value : "";
  }

  function getConfig(root) {
    if (root.nextElementSibling && root.nextElementSibling.classList.contains("seo-analyzer-config")) {
      return root.nextElementSibling;
    }
    return null;
  }

  function liveBodyPlaintext() {
    var field = document.getElementById("id_body_plaintext");
    return field ? field.value.trim() : null;
  }

  function liveBodyPage() {
    var editor = document.querySelector("[data-blog-post-editor]");
    if (editor && editor.blogPageBuilderState && editor.blogPageBuilderState.page) {
      return editor.blogPageBuilderState.page;
    }
    return null;
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

  function initAiReadinessAnalyzer(root) {
    var form = root.closest("form");
    if (!form) return;

    var config = getConfig(root);
    var apiUrl = config ? config.dataset.seoAnalyzerApi : null;
    if (!apiUrl || !config.dataset.objectId) return;

    var timer = null;
    var inflight = null;

    function collectPayload() {
      return {
        content_type_id: config.dataset.contentTypeId,
        object_id: config.dataset.objectId,
        article_title: parentFieldValue(form, "title"),
        excerpt: parentFieldValue(form, "short_description") || parentFieldValue(form, "excerpt"),
        focus_keyword: fieldValue(form, "focus_keyword"),
        seo_title: fieldValue(form, "seo_title"),
        meta_description: fieldValue(form, "meta_description"),
        body_plaintext: liveBodyPlaintext(),
        body_page: liveBodyPage(),
      };
    }

    function runAnalysis() {
      if (inflight) inflight.abort();
      inflight = new AbortController();
      root.classList.add("is-loading");

      fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(form),
        },
        body: JSON.stringify(collectPayload()),
        signal: inflight.signal,
      })
        .then(function (response) {
          if (!response.ok) throw new Error("AI readiness analysis failed");
          return response.json();
        })
        .then(function (data) {
          if (data.message && !data.checks) return;

          var scoreValue = root.querySelector("[data-seo-score-value]");
          var scoreRing = root.querySelector("[data-seo-score-ring]");
          var checksList = root.querySelector("[data-seo-checks-list]");
          var recommendationsList = root.querySelector("[data-seo-recommendations-list]");

          if (scoreValue) scoreValue.textContent = String(data.score);
          if (scoreRing) {
            scoreRing.classList.remove(
              "seo-analyzer__score--good",
              "seo-analyzer__score--ok",
              "seo-analyzer__score--bad",
              "seo-analyzer__score--neutral"
            );
            scoreRing.classList.add(scoreClass(data.score));
          }
          if (checksList && data.checks) renderChecks(checksList, data.checks);
          if (recommendationsList && data.recommendations) {
            recommendationsList.innerHTML = data.recommendations
              .map(function (item) {
                return '<li class="seo-analyzer__recommendation">' + item + "</li>";
              })
              .join("");
          }
        })
        .catch(function (error) {
          if (error.name !== "AbortError") {
            console.warn("SEO AI readiness error:", error);
          }
        })
        .finally(function () {
          root.classList.remove("is-loading");
        });
    }

    function scheduleAnalysis() {
      window.clearTimeout(timer);
      timer = window.setTimeout(runAnalysis, DEBOUNCE_MS);
    }

    ["title", "excerpt"].forEach(function (name) {
      var input = form.querySelector("#id_" + name);
      if (input) {
        input.addEventListener("input", scheduleAnalysis);
        input.addEventListener("change", scheduleAnalysis);
      }
    });

    var bodyPlaintextInput = form.querySelector("#id_body_plaintext");
    if (bodyPlaintextInput) {
      bodyPlaintextInput.addEventListener("input", scheduleAnalysis);
      bodyPlaintextInput.addEventListener("change", scheduleAnalysis);
    }

    document.addEventListener("blog-page-builder:change", scheduleAnalysis);

    runAnalysis();
  }

  function boot() {
    document.querySelectorAll("[data-seo-ai-readiness-analyzer]").forEach(initAiReadinessAnalyzer);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
