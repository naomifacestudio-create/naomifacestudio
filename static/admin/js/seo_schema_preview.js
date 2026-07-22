(function () {
  "use strict";

  var DEBOUNCE_MS = 450;

  function fieldValue(form, suffix) {
    var input = form.querySelector('[name$="-' + suffix + '"]');
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

  function scoreClass(score) {
    if (score >= 70) return "seo-analyzer__score--good";
    if (score >= 40) return "seo-analyzer__score--ok";
    return "seo-analyzer__score--bad";
  }

  function collectSchemaPayload(form, config) {
    return {
      content_type_id: config ? config.dataset.contentTypeId || null : null,
      object_id: config ? config.dataset.objectId || null : null,
      schema_type: fieldValue(form, "schema_type"),
      seo_title: fieldValue(form, "seo_title"),
      meta_description: fieldValue(form, "meta_description"),
    };
  }

  function initSchemaPreview(root) {
    var form = root.closest("form");
    if (!form) return;

    var config = getConfig(root);
    var apiUrl = config ? config.dataset.seoAnalyzerApi : null;
    if (!apiUrl) return;

    var timer = null;
    var inflight = null;

    function runPreview() {
      if (inflight) inflight.abort();
      inflight = new AbortController();
      root.classList.add("is-loading");

      fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(form),
        },
        body: JSON.stringify(collectSchemaPayload(form, config)),
        signal: inflight.signal,
      })
        .then(function (response) {
          if (!response.ok) throw new Error("Schema preview failed");
          return response.json();
        })
        .then(function (data) {
          if (data.html) {
            var wrapper = document.createElement("div");
            wrapper.innerHTML = data.html;
            var next = root.nextElementSibling;
            var newPreview = wrapper.firstElementChild;
            if (newPreview) {
              root.replaceWith(newPreview);
              root = newPreview;
              if (next && next.classList.contains("seo-analyzer-config")) {
                newPreview.insertAdjacentElement("afterend", next);
              }
            }
          }
        })
        .catch(function (error) {
          if (error.name !== "AbortError") {
            console.warn("SEO schema preview error:", error);
          }
        })
        .finally(function () {
          root.classList.remove("is-loading");
        });
    }

    function schedulePreview() {
      window.clearTimeout(timer);
      timer = window.setTimeout(runPreview, DEBOUNCE_MS);
    }

    ["schema_type", "seo_title", "meta_description", "breadcrumb_title"].forEach(function (suffix) {
      var input = form.querySelector('[name$="-' + suffix + '"]');
      if (input) {
        input.addEventListener("input", schedulePreview);
        input.addEventListener("change", schedulePreview);
      }
    });
  }

  function boot() {
    document.querySelectorAll("[data-seo-schema-preview]").forEach(initSchemaPreview);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
