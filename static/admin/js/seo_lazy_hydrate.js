/**
 * Hydrate deferred SEO analyzer shells (seo-analyzer--empty) via live admin APIs.
 * Panels are no longer computed during change_form render — that made Spremi
 * redirects slow (2 locales × many analyzers). Load on SEO drawer open instead.
 */
(function () {
  "use strict";

  var SELECTOR =
    "[data-seo-keyword-analyzer], [data-seo-readability-analyzer], " +
    "[data-seo-og-preview], [data-seo-twitter-preview], [data-seo-schema-preview], " +
    "[data-seo-internal-linking-analyzer], [data-seo-cornerstone-analyzer], " +
    "[data-seo-unified-score-analyzer], [data-seo-serp-preview], " +
    "[data-seo-image-seo-analyzer], [data-seo-slug-analyzer], [data-seo-ai-readiness-analyzer]";

  function fieldValue(scope, suffix) {
    var input = scope.querySelector('[name$="-' + suffix + '"]');
    return input ? String(input.value || "").trim() : "";
  }

  function parentFieldValue(form, name) {
    var input = form.querySelector("#id_" + name);
    if (input) {
      return String(input.value || "").trim();
    }
    // Localized builder hosts use title_hr / title_en etc.
    var localized = form.querySelector("#id_" + name + "_hr") || form.querySelector("#id_" + name + "_en");
    return localized ? String(localized.value || "").trim() : "";
  }

  function getCsrfToken(form) {
    var tokenInput = form.querySelector('[name="csrfmiddlewaretoken"]');
    return tokenInput ? tokenInput.value : "";
  }

  function liveBodyPlaintext() {
    var field = document.getElementById("id_body_plaintext");
    return field ? field.value.trim() : null;
  }

  function activeLocaleTitle(form) {
    var localeInput = form.querySelector('[name="_builder_locale"]');
    var locale = localeInput && localeInput.value === "en" ? "en" : "hr";
    return (
      parentFieldValue(form, "title_" + locale) ||
      parentFieldValue(form, "title") ||
      ""
    );
  }

  function activeLocaleSlug(form) {
    var localeInput = form.querySelector('[name="_builder_locale"]');
    var locale = localeInput && localeInput.value === "en" ? "en" : "hr";
    return (
      parentFieldValue(form, "slug_" + locale) ||
      parentFieldValue(form, "slug") ||
      ""
    );
  }

  function activeLocaleExcerpt(form) {
    var localeInput = form.querySelector('[name="_builder_locale"]');
    var locale = localeInput && localeInput.value === "en" ? "en" : "hr";
    return (
      parentFieldValue(form, "short_description_" + locale) ||
      parentFieldValue(form, "excerpt") ||
      parentFieldValue(form, "short_description") ||
      ""
    );
  }

  function collectPayload(root, config) {
    var form = root.closest("form");
    var inline = root.closest(".inline-related") || form;
    if (!form) {
      return null;
    }
    return {
      content_type_id: config ? config.dataset.contentTypeId || null : null,
      object_id: config ? config.dataset.objectId || null : null,
      article_title: activeLocaleTitle(form),
      url_slug: activeLocaleSlug(form),
      excerpt: activeLocaleExcerpt(form),
      seo_title: fieldValue(inline, "seo_title"),
      meta_description: fieldValue(inline, "meta_description"),
      focus_keyword: fieldValue(inline, "focus_keyword"),
      secondary_keywords: fieldValue(inline, "secondary_keywords"),
      body_plaintext: liveBodyPlaintext(),
      og_title: fieldValue(inline, "og_title"),
      og_description: fieldValue(inline, "og_description"),
      og_type: fieldValue(inline, "og_type"),
      twitter_title: fieldValue(inline, "twitter_title"),
      twitter_description: fieldValue(inline, "twitter_description"),
      schema_type: fieldValue(inline, "schema_type"),
    };
  }

  function replaceWithHtml(root, html) {
    var wrapper = document.createElement("div");
    wrapper.innerHTML = html;
    var neu = wrapper.firstElementChild;
    if (!neu) {
      return null;
    }
    var next = root.nextElementSibling;
    root.replaceWith(neu);
    if (next && next.classList.contains("seo-analyzer-config")) {
      neu.after(next);
    }
    return neu;
  }

  function hydrateRoot(root) {
    if (!root || !root.classList.contains("seo-analyzer--empty")) {
      return;
    }
    if (root.dataset.seoHydrating === "1" || root.dataset.seoHydrated === "1") {
      return;
    }
    // Skip hidden locale profiles — only hydrate the visible SEO inline.
    var inline = root.closest(".inline-related");
    if (inline && (inline.hidden || inline.classList.contains("builder-locale-hidden"))) {
      return;
    }

    var config = root.nextElementSibling;
    if (!config || !config.classList.contains("seo-analyzer-config")) {
      return;
    }
    var apiUrl = config.dataset.seoAnalyzerApi;
    if (!apiUrl || !config.dataset.objectId) {
      return;
    }

    var form = root.closest("form");
    var payload = collectPayload(root, config);
    if (!form || !payload) {
      return;
    }

    root.dataset.seoHydrating = "1";
    root.classList.add("is-loading");

    fetch(apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(form),
      },
      body: JSON.stringify(payload),
    })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("hydrate failed");
        }
        return response.json();
      })
      .then(function (data) {
        if (!data.html) {
          return;
        }
        var neu = replaceWithHtml(root, data.html);
        if (neu) {
          neu.dataset.seoHydrated = "1";
          // Re-bind live analyzers on the new markup.
          document.dispatchEvent(
            new CustomEvent("seo-analyzer-hydrated", { detail: { root: neu } })
          );
        }
      })
      .catch(function (error) {
        console.warn("SEO lazy hydrate error:", error);
        delete root.dataset.seoHydrating;
        root.classList.remove("is-loading");
      });
  }

  function hydrateVisibleSeoPanels() {
    var panel =
      document.querySelector('[data-builder-drawer-panel="seo"]:not([hidden])') ||
      document.querySelector('[data-blog-drawer-panel="seo"]:not([hidden])');
    var scope = panel || document;
    scope.querySelectorAll(SELECTOR).forEach(hydrateRoot);
  }

  document.addEventListener("seo-drawer-open", function () {
    window.requestAnimationFrame(hydrateVisibleSeoPanels);
  });

  // If SEO drawer is already open on load, hydrate shortly after paint.
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      window.setTimeout(hydrateVisibleSeoPanels, 50);
    });
  } else {
    window.setTimeout(hydrateVisibleSeoPanels, 50);
  }
})();
