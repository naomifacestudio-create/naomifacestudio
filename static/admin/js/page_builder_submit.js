(function () {
  "use strict";

  var IGNORE_FIELDS = {
    csrfmiddlewaretoken: true,
    body_plaintext: true,
    _builder_locale: true,
  };

  function metaSignature(form) {
    var parts = [];
    form.querySelectorAll("input, textarea, select").forEach(function (el) {
      if (!el.name || IGNORE_FIELDS[el.name]) {
        return;
      }
      if (el.disabled) {
        return;
      }
      if (el.type === "file") {
        if (el.files && el.files.length) {
          var file = el.files[0];
          parts.push(el.name + "=file:" + file.name + ":" + file.size + ":" + file.lastModified);
        }
        return;
      }
      if (el.type === "checkbox" || el.type === "radio") {
        if (el.checked) {
          parts.push(el.name + "=" + el.value);
        }
        return;
      }
      parts.push(el.name + "=" + el.value);
    });
    return parts.sort().join("\n");
  }

  function setSubmitting(form, submitting) {
    form.dataset.builderSubmitting = submitting ? "1" : "0";
    form.querySelectorAll('button[type="submit"], input[type="submit"]').forEach(function (btn) {
      btn.disabled = !!submitting;
      if (btn.tagName === "BUTTON" && btn.name === "_save") {
        if (submitting) {
          if (!btn.dataset.labelDefault) {
            btn.dataset.labelDefault = btn.textContent;
          }
          btn.textContent = "Spremanje…";
        } else if (btn.dataset.labelDefault) {
          btn.textContent = btn.dataset.labelDefault;
        }
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var form = document.querySelector("#content-main form");
    var root = document.querySelector("[data-page-editor]");
    if (!form || !root) {
      return;
    }

    // Snapshot after Django/inlines finish painting so SEO defaults are included.
    var initialMeta = metaSignature(form);
    window.setTimeout(function () {
      initialMeta = metaSignature(form);
    }, 0);

    form.addEventListener("submit", async function (event) {
      if (form.dataset.builderSubmitting === "1") {
        event.preventDefault();
        return;
      }

      var state = root.pageBuilderState;
      var glue = window.PageBuilderGlue;
      if (!state || !glue) {
        return;
      }

      event.preventDefault();
      setSubmitting(form, true);

      try {
        // Canvas is saved via AJAX. Do not force a rewrite when nothing changed.
        var result = await glue.flushBeforeSubmit(state);
        if (!result || !result.ok) {
          window.alert((result && result.message) || "Unable to save visual content.");
          setSubmitting(form, false);
          return;
        }

        var metaChanged = metaSignature(form) !== initialMeta;
        if (!metaChanged) {
          // Titles / SEO / publish were untouched — page AJAX save is enough.
          setSubmitting(form, false);
          initialMeta = metaSignature(form);
          return;
        }

        // Details / SEO / publish changed — full Django save + reload.
        form.submit();
      } catch (_error) {
        setSubmitting(form, false);
        window.alert("Unexpected error while saving.");
      }
    });
  });
})();
