(function () {
  "use strict";

  var DEBOUNCE_MS = 350;

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

  function collectPayload(form, config) {
    return {
      content_type_id: config ? config.dataset.contentTypeId || null : null,
      object_id: config ? config.dataset.objectId || null : null,
      article_title: parentFieldValue(form, "title"),
      url_slug: parentFieldValue(form, "slug"),
      excerpt: parentFieldValue(form, "short_description") || parentFieldValue(form, "excerpt"),
      seo_title: fieldValue(form, "seo_title"),
      meta_description: fieldValue(form, "meta_description"),
      canonical_url: fieldValue(form, "canonical_url"),
    };
  }

  function updateWarnings(container, warnings) {
    if (!warnings || !warnings.length) {
      container.innerHTML = "";
      return;
    }

    container.innerHTML = warnings
      .map(function (warning) {
        return (
          '<li class="seo-serp-preview__warning seo-serp-preview__warning--' +
          warning.status +
          '">' +
          "<strong>" +
          warning.label +
          "</strong> " +
          '<span data-serp-warning-field="' +
          warning.field +
          '">' +
          warning.length +
          " characters</span> — " +
          warning.message +
          "</li>"
        );
      })
      .join("");
  }

  function updateVariant(root, variant, data) {
    var block = root.querySelector('[data-serp-variant="' + variant + '"]');
    if (!block) return;

    var title = block.querySelector("[data-serp-title]");
    var url = block.querySelector("[data-serp-url]");
    var description = block.querySelector("[data-serp-description]");

    if (variant === "desktop") {
      if (title) title.textContent = data.title_desktop || data.title || "Page title";
      if (description) {
        description.textContent =
          data.description_desktop || data.description || "Page meta description.";
      }
    } else {
      if (title) title.textContent = data.title_mobile || data.title || "Page title";
      if (description) {
        description.textContent =
          data.description_mobile || data.description || "Page meta description.";
      }
    }

    if (url) url.textContent = data.display_url || "example.com";
  }

  function initSerpPreview(root) {
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
        body: JSON.stringify(collectPayload(form, config)),
        signal: inflight.signal,
      })
        .then(function (response) {
          if (!response.ok) throw new Error("SERP preview failed");
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
              if (next && next.classList.contains("seo-analyzer-config")) {
                newPreview.after(next);
              }
              initSerpPreview(newPreview);
            }
            return;
          }

          updateVariant(root, "desktop", data);
          updateVariant(root, "mobile", data);

          var fullUrl = root.querySelector("[data-serp-full-url]");
          if (fullUrl) fullUrl.textContent = data.url || "—";

          var warnings = root.querySelector("[data-serp-warnings]");
          if (warnings) updateWarnings(warnings, data.warnings);
        })
        .catch(function (error) {
          if (error.name !== "AbortError") {
            console.warn("SEO SERP preview error:", error);
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

    ["seo_title", "meta_description", "canonical_url"].forEach(function (suffix) {
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
    document.querySelectorAll("[data-seo-serp-preview]").forEach(initSerpPreview);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  document.addEventListener("seo-analyzer-hydrated", function (event) {
    var root = event.detail && event.detail.root;
    if (root && root.matches("[data-seo-serp-preview]")) {
      initSerpPreview(root);
    }
  });
})();
