(function () {
  "use strict";

  var DEBOUNCE_MS = 450;

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

  function collectTwitterPayload(form, config) {
    return {
      content_type_id: config ? config.dataset.contentTypeId || null : null,
      object_id: config ? config.dataset.objectId || null : null,
      article_title: parentFieldValue(form, "title"),
      url_slug: parentFieldValue(form, "slug"),
      excerpt: parentFieldValue(form, "short_description") || parentFieldValue(form, "excerpt"),
      seo_title: fieldValue(form, "seo_title"),
      meta_description: fieldValue(form, "meta_description"),
      og_title: fieldValue(form, "og_title"),
      og_description: fieldValue(form, "og_description"),
      twitter_title: fieldValue(form, "twitter_title"),
      twitter_description: fieldValue(form, "twitter_description"),
      twitter_card: fieldValue(form, "twitter_card"),
    };
  }

  function initTwitterPreview(root) {
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
        body: JSON.stringify(collectTwitterPayload(form, config)),
        signal: inflight.signal,
      })
        .then(function (response) {
          if (!response.ok) throw new Error("Twitter preview failed");
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
            console.warn("SEO Twitter preview error:", error);
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

    [
      "twitter_title",
      "twitter_description",
      "twitter_card",
      "og_title",
      "og_description",
      "seo_title",
      "meta_description",
    ].forEach(function (suffix) {
      var input = form.querySelector('[name$="-' + suffix + '"]');
      if (input) {
        input.addEventListener("input", schedulePreview);
        input.addEventListener("change", schedulePreview);
      }
    });

    ["title", "slug", "excerpt"].forEach(function (name) {
      var input = form.querySelector("#id_" + name);
      if (input) {
        input.addEventListener("input", schedulePreview);
        input.addEventListener("change", schedulePreview);
      }
    });
  }

  function boot() {
    document.querySelectorAll("[data-seo-twitter-preview]").forEach(initTwitterPreview);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
