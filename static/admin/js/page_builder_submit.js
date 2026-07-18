(function () {
  "use strict";
  document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector("#content-main form");
    const root = document.querySelector("[data-page-editor]");
    if (!form || !root) return;
    form.addEventListener("submit", async function (event) {
      if (form.dataset.builderSubmitting === "1") {
        event.preventDefault();
        return;
      }
      const state = root.pageBuilderState;
      const glue = window.PageBuilderGlue;
      if (!state || !glue) return;
      event.preventDefault();
      const result = await glue.flushBeforeSubmit(state);
      if (!result || !result.ok) {
        window.alert((result && result.message) || "Vizualni sadržaj nije moguće spremiti.");
        return;
      }
      form.dataset.builderSubmitting = "1";
      form.submit();
    });
  });
})();
