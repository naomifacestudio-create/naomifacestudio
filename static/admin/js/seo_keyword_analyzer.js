(function () {
  "use strict";

  var DEBOUNCE_MS = 450;

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

  function liveBodyPlaintext() {
    var field = document.getElementById("id_body_plaintext");
    return field ? field.value.trim() : null;
  }

  function getConfig(root) {
    if (root.nextElementSibling && root.nextElementSibling.classList.contains("seo-analyzer-config")) {
      return root.nextElementSibling;
    }
    return null;
  }

  function collectKeywordPayload(form, config) {
    return {
      content_type_id: config ? config.dataset.contentTypeId || null : null,
      object_id: config ? config.dataset.objectId || null : null,
      article_title: parentFieldValue(form, "title"),
      url_slug: parentFieldValue(form, "slug"),
      excerpt: parentFieldValue(form, "short_description") || parentFieldValue(form, "excerpt"),
      seo_title: fieldValue(form, "seo_title"),
      meta_description: fieldValue(form, "meta_description"),
      focus_keyword: fieldValue(form, "focus_keyword"),
      body_plaintext: liveBodyPlaintext(),
    };
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

  function renderList(container, items, className) {
    container.innerHTML = items
      .map(function (item) {
        return '<li class="' + className + '">' + item + "</li>";
      })
      .join("");
  }

  function initKeywordAnalyzer(root) {
    var form = root.closest("form");
    if (!form) return;

    var config = getConfig(root);
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
        body: JSON.stringify(collectKeywordPayload(form, config)),
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
          var focusKeyword = root.querySelector("[data-seo-focus-keyword]");
          var checksList = root.querySelector("[data-seo-checks-list]");
          var recommendationsList = root.querySelector("[data-seo-recommendations-list]");

          if (scoreValue) scoreValue.textContent = String(data.score);
          if (scoreRing) updateScoreRing(scoreRing, data.score);
          if (focusKeyword) focusKeyword.textContent = data.focus_keyword || "—";
          if (checksList && data.checks) renderChecks(checksList, data.checks);
          if (recommendationsList && data.recommendations) {
            renderList(recommendationsList, data.recommendations, "seo-analyzer__recommendation");
          }
        })
        .catch(function (error) {
          if (error.name !== "AbortError") {
            console.warn("SEO keyword analysis error:", error);
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

    ["focus_keyword", "seo_title", "meta_description"].forEach(function (suffix) {
      var input = form.querySelector('[name$="-' + suffix + '"]');
      if (input) {
        input.addEventListener("input", scheduleAnalysis);
        input.addEventListener("change", scheduleAnalysis);
      }
    });

    ["title", "slug", "excerpt"].forEach(function (name) {
      var input = form.querySelector("#id_" + name);
      if (input) {
        input.addEventListener("input", scheduleAnalysis);
        input.addEventListener("change", scheduleAnalysis);
      }
    });

    // Document JSON changes sync into `#id_body_plaintext`; trigger analysis on typing.
    var bodyPlaintextInput = form.querySelector("#id_body_plaintext");
    if (bodyPlaintextInput) {
      bodyPlaintextInput.addEventListener("input", scheduleAnalysis);
      bodyPlaintextInput.addEventListener("change", scheduleAnalysis);
    }
  }

  function boot() {
    document.querySelectorAll("[data-seo-keyword-analyzer]").forEach(initKeywordAnalyzer);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  document.addEventListener("seo-analyzer-hydrated", function (event) {
    var root = event.detail && event.detail.root;
    if (root && root.matches("[data-seo-keyword-analyzer]")) {
      initKeywordAnalyzer(root);
    }
  });
})();
