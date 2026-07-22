(function () {
  "use strict";

  var FIELD_LIMITS = {
    seo_title: { idealMin: 50, idealMax: 60, hardMax: 70, label: "Recommended: 50–60" },
    meta_description: { idealMin: 120, idealMax: 160, hardMax: 320, label: "Recommended: 120–160" },
    og_title: { idealMin: 50, idealMax: 60, hardMax: 70, label: "Recommended: 50–60" },
    og_description: { idealMin: 120, idealMax: 160, hardMax: 320, label: "Recommended: 120–160" },
  };

  function counterClass(length, limits) {
    if (length === 0) return "seo-char-counter--empty";
    if (length > limits.hardMax) return "seo-char-counter--over";
    if (length >= limits.idealMin && length <= limits.idealMax) return "seo-char-counter--good";
    if (length >= limits.idealMin - 10 && length <= limits.idealMax + 15) return "seo-char-counter--ok";
    return "seo-char-counter--bad";
  }

  function inputKey(input) {
    return input.id || input.getAttribute("name") || "";
  }

  function resolveFieldName(input) {
    var name = input.getAttribute("name") || "";
    if (!name || name.indexOf("__prefix__") !== -1) {
      return null;
    }
    var keys = Object.keys(FIELD_LIMITS);
    for (var index = 0; index < keys.length; index += 1) {
      var fieldName = keys[index];
      if (name === fieldName || name.slice(-(fieldName.length + 1)) === "-" + fieldName) {
        return fieldName;
      }
    }
    return null;
  }

  function isCountableField(input) {
    if (!input || input.disabled || input.readOnly) {
      return false;
    }
    if (input.closest(".empty-form")) {
      return false;
    }
    if (input.type === "hidden" || input.type === "checkbox" || input.type === "radio") {
      return false;
    }
    return input.tagName === "TEXTAREA" || input.tagName === "INPUT";
  }

  function findCounter(input) {
    var key = inputKey(input);
    if (!key) {
      return null;
    }
    var row = input.closest(".form-row") || input.closest(".blog-post-editor__field");
    if (row) {
      return row.querySelector('.seo-char-counter[data-seo-char-counter-input="' + key + '"]');
    }
    return document.querySelector('.seo-char-counter[data-seo-char-counter-input="' + key + '"]');
  }

  function updateCounter(input, counter, limits) {
    var length = (input.value || "").length;
    counter.textContent = length + " / " + limits.idealMax + " (" + limits.label + ")";
    counter.className = "seo-char-counter " + counterClass(length, limits);
    counter.hidden = false;
  }

  function placeCounter(input, counter) {
    var row = input.closest(".form-row") || input.closest(".blog-post-editor__field");
    var help = row ? row.querySelector(".help, p.help") : null;
    if (help) {
      help.insertAdjacentElement("afterend", counter);
      return;
    }
    input.insertAdjacentElement("afterend", counter);
  }

  function attachCounter(input, fieldName) {
    var limits = FIELD_LIMITS[fieldName];
    if (!limits || !isCountableField(input)) {
      return null;
    }

    var existing = findCounter(input);
    if (existing) {
      updateCounter(input, existing, limits);
      return existing;
    }

    var counter = document.createElement("div");
    counter.className = "seo-char-counter seo-char-counter--empty";
    counter.setAttribute("aria-live", "polite");
    counter.setAttribute("data-seo-char-counter-input", inputKey(input));

    placeCounter(input, counter);
    updateCounter(input, counter, limits);
    return counter;
  }

  function refreshCounter(input) {
    if (!isCountableField(input)) {
      return;
    }
    var fieldName = resolveFieldName(input);
    if (!fieldName) {
      return;
    }
    attachCounter(input, fieldName);
  }

  function initCounters(scope) {
    var root = scope || document;
    root.querySelectorAll("input, textarea").forEach(function (input) {
      var fieldName = resolveFieldName(input);
      if (fieldName) {
        attachCounter(input, fieldName);
      }
    });
  }

  function scheduleInit(scope) {
    window.requestAnimationFrame(function () {
      initCounters(scope);
    });
  }

  function watchSeoDrawer() {
    var panel = document.querySelector('[data-blog-drawer-panel="seo"]');
    if (!panel) {
      return;
    }

    function sync() {
      scheduleInit(panel);
    }

    sync();

    if (panel.dataset.seoCharCounterWatch === "1") {
      return;
    }
    panel.dataset.seoCharCounterWatch = "1";

    new MutationObserver(sync).observe(panel, {
      attributes: true,
      attributeFilter: ["hidden"],
      childList: true,
      subtree: true,
    });
  }

  function boot() {
    scheduleInit(document);
    watchSeoDrawer();

    document.addEventListener("input", function (event) {
      refreshCounter(event.target);
    }, true);
    document.addEventListener("change", function (event) {
      refreshCounter(event.target);
    }, true);

    document.addEventListener("click", function (event) {
      var trigger = event.target.closest("[data-blog-drawer-trigger]");
      if (!trigger || trigger.getAttribute("data-blog-drawer-trigger") !== "seo") {
        return;
      }
      var panel = document.querySelector('[data-blog-drawer-panel="seo"]');
      scheduleInit(panel || document);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
