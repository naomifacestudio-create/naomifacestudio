(function () {
  "use strict";

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

    // Only Detalji / SEO / Objava edits require a full Django POST + reload.
    // Canvas edits are saved via the lean page/save AJAX endpoint (Cement-style).
    var metaDirty = false;
    var drawer = root.querySelector("[data-builder-drawer], [data-blog-drawer]");
    if (drawer) {
      drawer.addEventListener("input", function () {
        metaDirty = true;
      });
      drawer.addEventListener("change", function () {
        metaDirty = true;
      });
    }

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
        var result = await glue.flushBeforeSubmit(state);
        if (!result || !result.ok) {
          window.alert((result && result.message) || "Unable to save visual content.");
          setSubmitting(form, false);
          return;
        }

        if (!metaDirty) {
          // Same as Cement's lean content write — no SEO re-render round-trip.
          setSubmitting(form, false);
          return;
        }

        form.submit();
      } catch (_error) {
        setSubmitting(form, false);
        window.alert("Unexpected error while saving.");
      }
    });
  });
})();
