(function () {
  "use strict";

  var DEBOUNCE_MS = 450;

  var PLATFORMS = {
    facebook: {
      label: "Facebook pregled",
      titleMax: 60,
      descMax: 160,
      cardClass: "seo-og-preview__card--facebook",
    },
    linkedin: {
      label: "LinkedIn pregled",
      titleMax: 70,
      descMax: 160,
      cardClass: "seo-og-preview__card--linkedin",
    },
    whatsapp: {
      label: "WhatsApp pregled",
      titleMax: 65,
      descMax: 90,
      cardClass: "seo-og-preview__card--whatsapp",
    },
  };

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
    var sibling = root.nextElementSibling;
    if (sibling && sibling.classList.contains("seo-analyzer-config")) {
      return sibling;
    }

    sibling = root.previousElementSibling;
    if (sibling && sibling.classList.contains("seo-analyzer-config")) {
      return sibling;
    }

    var parent = root.parentElement;
    if (parent) {
      var nested = parent.querySelector(":scope > .seo-analyzer-config");
      if (nested) {
        return nested;
      }
    }

    var readonly = root.closest(".readonly, .form-row");
    if (readonly) {
      return readonly.querySelector(".seo-analyzer-config");
    }

    return null;
  }

  function resolveAnalyzerIds(form, config) {
    var contentTypeId = config ? config.dataset.contentTypeId || "" : "";
    var objectId = config ? config.dataset.objectId || "" : "";

    if (!contentTypeId || !objectId) {
      var ctInput = form.querySelector('[name$="-content_type"]');
      var oidInput = form.querySelector('[name$="-object_id"]');
      if (ctInput && ctInput.value) {
        contentTypeId = ctInput.value;
      }
      if (oidInput && oidInput.value) {
        objectId = oidInput.value;
      }
    }

    return {
      content_type_id: contentTypeId || null,
      object_id: objectId || null,
    };
  }

  function truncatePreviewText(text, maxLength) {
    var value = (text || "").trim();
    if (!value) {
      return "";
    }
    if (value.length <= maxLength) {
      return value;
    }
    return value.slice(0, maxLength - 1).trim() + "…";
  }

  function resolvePreviewTitle(form) {
    return (
      fieldValue(form, "og_title") ||
      fieldValue(form, "seo_title") ||
      parentFieldValue(form, "title") ||
      "Share title"
    );
  }

  function resolvePreviewDescription(form) {
    return (
      fieldValue(form, "og_description") ||
      fieldValue(form, "meta_description") ||
      parentFieldValue(form, "short_description") || parentFieldValue(form, "excerpt") ||
      "Social media description"
    );
  }

  function resolvePreviewDomain(form) {
    var ogUrl = fieldValue(form, "og_url");
    if (ogUrl) {
      return ogUrl.replace(/^https?:\/\//, "").split("/")[0];
    }
    return PLATFORMS.facebook.label;
  }

  function collectOgPayload(form, config, root) {
    var ids = resolveAnalyzerIds(form, config);
    return {
      content_type_id: ids.content_type_id,
      object_id: ids.object_id,
      article_title: parentFieldValue(form, "title"),
      url_slug: parentFieldValue(form, "slug"),
      excerpt: parentFieldValue(form, "short_description") || parentFieldValue(form, "excerpt"),
      seo_title: fieldValue(form, "seo_title"),
      meta_description: fieldValue(form, "meta_description"),
      og_title: fieldValue(form, "og_title"),
      og_description: fieldValue(form, "og_description"),
      og_type: fieldValue(form, "og_type"),
      og_url: fieldValue(form, "og_url"),
      platform: root.getAttribute("data-og-platform") || "facebook",
    };
  }

  function applyPlatformPreview(root, form, platformKey) {
    var profile = PLATFORMS[platformKey] || PLATFORMS.facebook;
    root.setAttribute("data-og-platform", platformKey);

    root.querySelectorAll(".seo-og-preview__tab").forEach(function (tab) {
      var tabPlatform = tab.getAttribute("data-og-platform");
      if (!tabPlatform) {
        return;
      }
      var active = tabPlatform === platformKey;
      tab.classList.toggle("seo-og-preview__tab--active", active);
      tab.setAttribute("aria-pressed", active ? "true" : "false");
    });

    var card = root.querySelector(".seo-og-preview__card");
    if (card) {
      card.classList.remove(
        "seo-og-preview__card--facebook",
        "seo-og-preview__card--linkedin",
        "seo-og-preview__card--whatsapp"
      );
      card.classList.add(profile.cardClass);
    }

    var domain = root.querySelector("[data-og-preview-domain]");
    var title = root.querySelector("[data-og-preview-title]");
    var description = root.querySelector("[data-og-preview-description]");

    if (domain) {
      domain.textContent = fieldValue(form, "og_url")
        ? resolvePreviewDomain(form)
        : profile.label;
    }
    if (title) {
      title.textContent = truncatePreviewText(resolvePreviewTitle(form), profile.titleMax);
    }
    if (description) {
      description.textContent = truncatePreviewText(
        resolvePreviewDescription(form),
        profile.descMax
      );
    }
  }

  function handleTabClick(event) {
    var button = event.target.closest(".seo-og-preview__tab");
    if (!button) {
      return;
    }

    var root = button.closest("[data-seo-og-preview]");
    if (!root) {
      return;
    }

    var form = root.closest("form");
    if (!form) {
      return;
    }

    var platform = button.getAttribute("data-og-platform");
    if (!platform || !PLATFORMS[platform]) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    applyPlatformPreview(root, form, platform);
  }

  function updateServerContent(root, newPreview, form) {
    var platform = root.getAttribute("data-og-platform") || "facebook";

    var oldImage = root.querySelector(".seo-og-preview__image");
    var newImage = newPreview.querySelector(".seo-og-preview__image");
    if (oldImage && newImage) {
      oldImage.replaceWith(newImage.cloneNode(true));
    }

    var oldValidation = root.querySelector(".seo-og-preview__validation");
    var newValidation = newPreview.querySelector(".seo-og-preview__validation");
    if (newValidation) {
      var validationClone = newValidation.cloneNode(true);
      if (oldValidation) {
        oldValidation.replaceWith(validationClone);
      } else {
        var card = root.querySelector(".seo-og-preview__card");
        if (card) {
          card.insertAdjacentElement("afterend", validationClone);
        }
      }
    } else if (oldValidation) {
      oldValidation.remove();
    }

    var oldMetaBody = root.querySelector(".seo-og-preview__meta tbody");
    var newMetaBody = newPreview.querySelector(".seo-og-preview__meta tbody");
    if (oldMetaBody && newMetaBody) {
      oldMetaBody.innerHTML = newMetaBody.innerHTML;
    }

    applyPlatformPreview(root, form, platform);
  }

  function initOgPreview(root) {
    var form = root.closest("form");
    if (!form) return;

    var config = getConfig(root);
    var apiUrl = config ? config.dataset.seoAnalyzerApi : null;
    if (!apiUrl) return;

    if (root.dataset.seoOgPreviewReady === "1") {
      return;
    }
    root.dataset.seoOgPreviewReady = "1";

    var timer = null;
    var inflight = null;
    var requestId = 0;

    function runPreview() {
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
        body: JSON.stringify(collectOgPayload(form, config, root)),
        signal: inflight.signal,
      })
        .then(function (response) {
          if (!response.ok) throw new Error("OG preview failed");
          return response.json();
        })
        .then(function (data) {
          if (thisRequestId !== requestId || !data.html) {
            return;
          }

          var wrapper = document.createElement("div");
          wrapper.innerHTML = data.html;
          var newPreview = wrapper.firstElementChild;
          if (!newPreview) {
            return;
          }

          updateServerContent(root, newPreview, form);
        })
        .catch(function (error) {
          if (error.name !== "AbortError") {
            console.warn("SEO Open Graph preview error:", error);
          }
        })
        .finally(function () {
          if (thisRequestId === requestId) {
            root.classList.remove("is-loading");
            inflight = null;
          }
        });
    }

    function schedulePreview() {
      var platform = root.getAttribute("data-og-platform") || "facebook";
      applyPlatformPreview(root, form, platform);
      window.clearTimeout(timer);
      timer = window.setTimeout(runPreview, DEBOUNCE_MS);
    }

    var initialPlatform = root.getAttribute("data-og-platform") || "facebook";
    applyPlatformPreview(root, form, initialPlatform);

    [
      "og_title",
      "og_description",
      "og_type",
      "og_url",
      "seo_title",
      "meta_description",
    ].forEach(function (suffix) {
      var input = form.querySelector('[name$="-' + suffix + '"]');
      if (input && input.dataset.seoOgPreviewBound !== "1") {
        input.dataset.seoOgPreviewBound = "1";
        input.addEventListener("input", schedulePreview);
        input.addEventListener("change", schedulePreview);
      }
    });

    ["title", "slug", "excerpt"].forEach(function (name) {
      var input = form.querySelector("#id_" + name);
      if (input && input.dataset.seoOgPreviewBound !== "1") {
        input.dataset.seoOgPreviewBound = "1";
        input.addEventListener("input", schedulePreview);
        input.addEventListener("change", schedulePreview);
      }
    });

    runPreview();
  }

  function boot(scope) {
    var container = scope || document;
    container.querySelectorAll("[data-seo-og-preview]").forEach(initOgPreview);
  }

  function watchSeoDrawer() {
    var panel = document.querySelector('[data-blog-drawer-panel="seo"]');
    if (!panel) {
      return;
    }

    function sync() {
      window.requestAnimationFrame(function () {
        boot(panel);
      });
    }

    sync();

    if (panel.dataset.seoOgPreviewWatch === "1") {
      return;
    }
    panel.dataset.seoOgPreviewWatch = "1";

    new MutationObserver(sync).observe(panel, {
      attributes: true,
      attributeFilter: ["hidden"],
      childList: true,
      subtree: true,
    });
  }

  function onBoot() {
    if (!document.documentElement.dataset.seoOgPreviewTabsBound) {
      document.documentElement.dataset.seoOgPreviewTabsBound = "1";
      document.addEventListener("click", handleTabClick, true);
    }

    boot(document);
    watchSeoDrawer();

    document.addEventListener("seo-drawer-open", function () {
      var panel = document.querySelector('[data-blog-drawer-panel="seo"]');
      boot(panel || document);
    });

    document.addEventListener("click", function (event) {
      var trigger = event.target.closest("[data-blog-drawer-trigger]");
      if (!trigger || trigger.getAttribute("data-blog-drawer-trigger") !== "seo") {
        return;
      }
      window.requestAnimationFrame(function () {
        var panel = document.querySelector('[data-blog-drawer-panel="seo"]');
        boot(panel || document);
      });
    });
  }

  window.SeoOgPreview = {
    boot: boot,
    applyPlatformPreview: applyPlatformPreview,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", onBoot);
  } else {
    onBoot();
  }
})();
