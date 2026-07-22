(function () {
  "use strict";

  function fieldChecked(form, suffix) {
    var input = form.querySelector('[name$="-' + suffix + '"]');
    return input ? input.checked : true;
  }

  function fieldValue(form, suffix) {
    var input = form.querySelector('[name$="-' + suffix + '"]');
    return input ? input.value.trim() : "";
  }

  function syncIndexToFollow(form) {
    var indexInput = form.querySelector('[name$="-robots_index"]:checked');
    if (!indexInput) {
      return;
    }

    var allow = indexInput.value === "True" || indexInput.value === "true" || indexInput.value === "on";
    var followInput = form.querySelector('[name$="-robots_follow"]');
    if (followInput) {
      followInput.checked = allow;
    }
  }

  function indexChecked(form) {
    var checked = form.querySelector('[name$="-robots_index"]:checked');
    if (checked) {
      return (
        checked.value === "True" ||
        checked.value === "true" ||
        checked.value === "on"
      );
    }

    var input = form.querySelector('[name$="-robots_index"]');
    return input ? input.checked : true;
  }

  function buildRobotsContent(values) {
    var parts = [];
    parts.push(values.index ? "index" : "noindex");
    parts.push(values.follow ? "follow" : "nofollow");
    if (values.nosnippet) parts.push("nosnippet");
    if (values.noarchive) parts.push("noarchive");
    if (values.maxSnippet) {
      parts.push("max-snippet:" + values.maxSnippet);
    }
    if (values.maxImagePreview) {
      parts.push("max-image-preview:" + values.maxImagePreview);
    }
    return parts.join(", ");
  }

  function collectValues(form) {
    syncIndexToFollow(form);
    return {
      index: indexChecked(form),
      follow: fieldChecked(form, "robots_follow"),
      nosnippet: fieldChecked(form, "robots_nosnippet"),
      noarchive: fieldChecked(form, "robots_noarchive"),
      maxSnippet: fieldValue(form, "robots_max_snippet"),
      maxImagePreview: fieldValue(form, "robots_max_image_preview"),
    };
  }

  function renderDirectives(container, directives) {
    container.innerHTML = directives
      .map(function (directive) {
        return '<span class="seo-robots-preview__pill">' + directive + "</span>";
      })
      .join("");
  }

  function updatePreview(root, form) {
    var values = collectValues(form);
    var content = buildRobotsContent(values);
    var metaTag = root.querySelector("[data-robots-meta-tag]");
    var directives = root.querySelector("[data-robots-directives]");

    if (metaTag) {
      metaTag.textContent = '<meta name="robots" content="' + content + '">';
    }
    if (directives) {
      renderDirectives(
        directives,
        content.split(",").map(function (part) {
          return part.trim();
        })
      );
    }
  }

  function initRobotsPreview(root) {
    var form = root.closest("form");
    if (!form) return;

    var selectors = [
      '[name$="-robots_index"]',
      '[name$="-robots_follow"]',
      '[name$="-robots_nosnippet"]',
      '[name$="-robots_noarchive"]',
      '[name$="-robots_max_snippet"]',
      '[name$="-robots_max_image_preview"]',
    ];

    function refresh() {
      updatePreview(root, form);
    }

    selectors.forEach(function (selector) {
      form.querySelectorAll(selector).forEach(function (input) {
        input.addEventListener("change", refresh);
        input.addEventListener("input", refresh);
      });
    });

    refresh();
  }

  function boot() {
    document.querySelectorAll("[data-seo-robots-preview]").forEach(initRobotsPreview);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
