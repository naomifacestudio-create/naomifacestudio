(function () {
  "use strict";

  var DEBOUNCE_MS = 650;

  function scoreClass(score) {
    if (score >= 70) return "seo-analyzer__score--good";
    if (score >= 40) return "seo-analyzer__score--ok";
    return "seo-analyzer__score--bad";
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

  function liveBodyPage() {
    var editor = document.querySelector("[data-blog-post-editor]");
    if (editor && editor.blogPageBuilderState && editor.blogPageBuilderState.page) {
      return editor.blogPageBuilderState.page;
    }
    return null;
  }

  function renderImages(container, images) {
    if (!images || !images.length) {
      container.innerHTML =
        '<tr><td colspan="6" class="seo-image-seo__empty">No images in content.</td></tr>';
      return;
    }

    container.innerHTML = images
      .map(function (row) {
        var dimensions =
          row.width && row.height ? row.width + "×" + row.height + " px" : "—";
        var size = row.file_size_kb != null ? row.file_size_kb + " KB" : "—";
        return (
          "<tr class=\"seo-image-seo__row\">" +
          "<td>" +
          row.label +
          "</td>" +
          "<td><code>" +
          row.filename +
          "</code></td>" +
          "<td>" +
          row.alt_text +
          "</td>" +
          "<td>" +
          dimensions +
          "</td>" +
          "<td>" +
          size +
          "</td>" +
          "<td>" +
          (row.loading || "—") +
          "</td></tr>"
        );
      })
      .join("");
  }

  function renderIssues(container, issues) {
    if (!issues || !issues.length) {
      container.innerHTML =
        '<li class="seo-image-seo__issue seo-image-seo__issue--good">No image issues.</li>';
      return;
    }

    container.innerHTML = issues
      .slice(0, 10)
      .map(function (issue) {
        return (
          '<li class="seo-image-seo__issue seo-image-seo__issue--' +
          issue.severity +
          '">' +
          "<strong>" +
          issue.label +
          "</strong> · " +
          issue.filename +
          " — " +
          issue.issue +
          "</li>"
        );
      })
      .join("");
  }

  function initImageSeoAnalyzer(root) {
    var form = root.closest("form");
    if (!form) return;

    var config = getConfig(root);
    var apiUrl = config ? config.dataset.seoAnalyzerApi : null;
    if (!apiUrl || !config.dataset.objectId) return;

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
          content_type_id: config.dataset.contentTypeId,
          object_id: config.dataset.objectId,
          body_plaintext: liveBodyPlaintext(),
          body_page: liveBodyPage(),
        }),
        signal: inflight.signal,
      })
        .then(function (response) {
          if (!response.ok) throw new Error("Image SEO analysis failed");
          return response.json();
        })
        .then(function (data) {
          if (thisRequestId !== requestId) {
            return;
          }
          if (data.message && !data.checks) return;

          var scoreValue = root.querySelector("[data-seo-score-value]");
          var scoreRing = root.querySelector("[data-seo-score-ring]");
          var imageCount = root.querySelector("[data-seo-image-count]");
          var checksList = root.querySelector("[data-seo-checks-list]");
          var imageList = root.querySelector("[data-seo-image-list]");
          var issuesList = root.querySelector("[data-seo-image-issues]");
          var recommendationsList = root.querySelector("[data-seo-recommendations-list]");

          if (scoreValue) scoreValue.textContent = String(data.score);
          if (scoreRing) {
            scoreRing.classList.remove(
              "seo-analyzer__score--good",
              "seo-analyzer__score--ok",
              "seo-analyzer__score--bad"
            );
            scoreRing.classList.add(scoreClass(data.score));
          }
          if (imageCount) imageCount.textContent = String(data.image_count || 0);
          if (checksList && data.checks) renderChecks(checksList, data.checks);
          if (imageList) renderImages(imageList, data.images);
          if (issuesList) renderIssues(issuesList, data.issues);
          if (recommendationsList && data.recommendations) {
            renderList(recommendationsList, data.recommendations, "seo-analyzer__recommendation");
          }
        })
        .catch(function (error) {
          if (error.name !== "AbortError") {
            console.warn("SEO image analysis error:", error);
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

    var bodyPlaintextInput = form.querySelector("#id_body_plaintext");
    if (bodyPlaintextInput) {
      bodyPlaintextInput.addEventListener("input", scheduleAnalysis);
      bodyPlaintextInput.addEventListener("change", scheduleAnalysis);
    }

    document.addEventListener("blog-page-builder:change", scheduleAnalysis);

    runAnalysis();
  }

  function boot() {
    document.querySelectorAll("[data-seo-image-seo-analyzer]").forEach(initImageSeoAnalyzer);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  document.addEventListener("seo-analyzer-hydrated", function (event) {
    var root = event.detail && event.detail.root;
    if (root && root.matches("[data-seo-image-seo-analyzer]")) {
      initImageSeoAnalyzer(root);
    }
  });
})();
