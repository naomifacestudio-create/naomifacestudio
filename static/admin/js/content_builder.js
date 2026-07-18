(function () {
  "use strict";

  const LOCALIZED_FIELDS = {
    "sr-latn": ["title_sr", "slug_sr", "short_description_sr"],
    en: ["title_en", "slug_en", "short_description_en"],
  };
  const LOCALE_LABELS = {
    "sr-latn": "Srpski (latinica)",
    en: "Engleski",
  };

  function setDetailsLocale(root, locale) {
    const activeFields = new Set(LOCALIZED_FIELDS[locale] || LOCALIZED_FIELDS["sr-latn"]);
    const allFields = Object.values(LOCALIZED_FIELDS).flat();
    allFields.forEach((fieldName) => {
      root.querySelectorAll(`.field-${fieldName}`).forEach((row) => {
        row.classList.toggle("builder-locale-hidden", !activeFields.has(fieldName));
      });
    });
    const label = root.querySelector("[data-builder-active-locale]");
    if (label) {
      label.textContent = LOCALE_LABELS[locale] || LOCALE_LABELS["sr-latn"];
    }
  }

  function mountSeoProfileCollapsibles(root) {
    const profiles = root.querySelectorAll(
      '[data-builder-drawer-panel="seo"] .inline-related:not(.empty-form)',
    );
    profiles.forEach((profile, index) => {
      const heading = profile.querySelector(":scope > h3");
      if (!heading || heading.querySelector("[data-seo-profile-toggle]")) return;

      const label = index === 0 ? "Srpski SEO" : "Engleski SEO";
      heading.textContent = "";
      const title = document.createElement("span");
      title.textContent = label;
      heading.appendChild(title);

      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.dataset.seoProfileToggle = "";
      toggle.className = "seo-profile-toggle";
      toggle.setAttribute("aria-expanded", "false");
      toggle.textContent = "Otvori";
      heading.appendChild(toggle);

      profile.classList.add("seo-profile-collapsed");
      heading.addEventListener("click", () => {
        const collapsed = profile.classList.toggle("seo-profile-collapsed");
        toggle.setAttribute("aria-expanded", String(!collapsed));
        toggle.textContent = collapsed ? "Otvori" : "Zatvori";
      });
    });
  }

  function mount(root) {
    if (root.dataset.contentBuilderMounted === "1") {
      return;
    }
    root.dataset.contentBuilderMounted = "1";

    const drawer = root.querySelector("[data-builder-drawer]");
    const backdrop = root.querySelector("[data-builder-drawer-backdrop]");
    const panels = root.querySelectorAll("[data-builder-drawer-panel]");
    const triggers = root.querySelectorAll("[data-builder-drawer-trigger]");
    const title = root.querySelector("[data-builder-drawer-title]");
    let activePanel = null;

    function closeDrawer() {
      if (!drawer) return;
      drawer.hidden = true;
      drawer.setAttribute("aria-hidden", "true");
      if (backdrop) backdrop.hidden = true;
      triggers.forEach((trigger) => trigger.classList.remove("is-active"));
      activePanel = null;
    }

    function openDrawer(name) {
      if (!drawer) return;
      const panel = root.querySelector(`[data-builder-drawer-panel="${name}"]`);
      if (!panel) return;
      panels.forEach((item) => {
        item.hidden = item !== panel;
      });
      triggers.forEach((trigger) => {
        trigger.classList.toggle("is-active", trigger.dataset.builderDrawerTrigger === name);
      });
      if (title) title.textContent = name === "seo" ? "SEO" : "Detalji";
      drawer.hidden = false;
      drawer.setAttribute("aria-hidden", "false");
      if (backdrop) backdrop.hidden = false;
      activePanel = name;
    }

    triggers.forEach((trigger) => {
      trigger.addEventListener("click", () => {
        const name = trigger.dataset.builderDrawerTrigger;
        if (activePanel === name) closeDrawer();
        else openDrawer(name);
      });
    });
    root.querySelector("[data-builder-drawer-close]")?.addEventListener("click", closeDrawer);
    backdrop?.addEventListener("click", closeDrawer);
    root.querySelector("[data-page-blocker-close]")?.addEventListener("click", () => {
      const blocker = root.querySelector("[data-page-blocker]");
      if (blocker) blocker.hidden = true;
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && drawer && !drawer.hidden) closeDrawer();
    });

    const localeInput = root.querySelector('[name="_builder_locale"]');
    setDetailsLocale(root, localeInput?.value || "sr-latn");
    mountSeoProfileCollapsibles(root);

    const currentUrl = new URL(window.location.href);
    if (currentUrl.searchParams.get("new") === "1") {
      const publishedInput = root.querySelector("#id_is_published");
      if (publishedInput) {
        publishedInput.checked = true;
        publishedInput.dispatchEvent(new Event("change", { bubbles: true }));
      }
      currentUrl.searchParams.delete("new");
      window.history.replaceState(window.history.state, "", currentUrl);
    }

    root.addEventListener("page-builder:locale-changed", (event) => {
      setDetailsLocale(root, event.detail.locale);
    });
    root.contentBuilderDrawer = { open: openDrawer, close: closeDrawer };
  }

  function init() {
    document.querySelectorAll("[data-page-editor]").forEach(mount);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
