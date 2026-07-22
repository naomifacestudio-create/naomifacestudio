(function () {
  "use strict";

  const LOCALIZED_FIELDS = {
    hr: ["title_hr", "slug_hr", "short_description_hr"],
    en: ["title_en", "slug_en", "short_description_en"],
  };
  const LOCALE_LABELS = {
    hr: "Hrvatski",
    en: "Engleski",
  };
  // Readonly Django locale widgets may show English verbose names ("Croatian").
  const LOCALE_ALIASES = {
    hr: ["hr", "hrvatski", "croatian", "hr-hr", "sr", "srpski", "serbian"],
    en: ["en", "engleski", "english", "en-us", "en-gb"],
  };
  const DRAWER_TITLES = {
    details: "Detalji",
    seo: "SEO",
    publish: "Objava",
  };

  function setDetailsLocale(root, locale) {
    const activeFields = new Set(LOCALIZED_FIELDS[locale] || LOCALIZED_FIELDS.hr);
    const allFields = Object.values(LOCALIZED_FIELDS).flat();
    const detailsPanel =
      root.querySelector('[data-builder-drawer-panel="details"]') ||
      root.querySelector('[data-blog-drawer-panel="details"]') ||
      root;
    allFields.forEach((fieldName) => {
      detailsPanel.querySelectorAll(`.field-${fieldName}`).forEach((row) => {
        row.classList.toggle("builder-locale-hidden", !activeFields.has(fieldName));
      });
    });
    detailsPanel.querySelectorAll("fieldset").forEach((fieldset) => {
      const rows = Array.from(fieldset.querySelectorAll(".form-row"));
      if (!rows.length) return;
      const localizedRows = rows.filter((row) =>
        allFields.some((fieldName) => row.classList.contains(`field-${fieldName}`))
      );
      if (!localizedRows.length) return;
      const hasVisible = localizedRows.some(
        (row) => !row.classList.contains("builder-locale-hidden")
      );
      fieldset.classList.toggle("builder-locale-hidden", !hasVisible);
    });
    // Publishing lives in the Publish rail panel — hide duplicate fieldsets in Details.
    detailsPanel.querySelectorAll(".field-is_active, .field-publish_date, .field-created_at, .field-updated_at, .field-thumbnail").forEach((row) => {
      const fieldset = row.closest("fieldset");
      if (fieldset) fieldset.classList.add("builder-locale-hidden");
    });
    const label = root.querySelector("[data-builder-active-locale]");
    if (label) {
      label.textContent = LOCALE_LABELS[locale] || LOCALE_LABELS.hr;
    }
    setSeoLocale(root, locale);
  }

  function resolveLocaleCode(raw) {
    const value = String(raw || "").trim().toLowerCase().replace(/_/g, "-");
    if (!value) return "";
    if (LOCALIZED_FIELDS[value]) return value;
    const base = value.split("-")[0];
    if (LOCALIZED_FIELDS[base]) return base;
    for (const [code, aliases] of Object.entries(LOCALE_ALIASES)) {
      if (aliases.some((alias) => value === alias || value.includes(alias))) {
        return code;
      }
    }
    const byLabel = Object.entries(LOCALE_LABELS).find(
      ([code, label]) =>
        value === label.toLowerCase() ||
        value.includes(label.toLowerCase()) ||
        label.toLowerCase().startsWith(value)
    );
    return byLabel ? byLabel[0] : value;
  }

  function setSeoLocale(root, locale) {
    const seoPanel =
      root.querySelector('[data-builder-drawer-panel="seo"]') ||
      root.querySelector('[data-blog-drawer-panel="seo"]');
    if (!seoPanel) return;
    const related = Array.from(seoPanel.querySelectorAll(".inline-related")).filter(
      (block) => !block.classList.contains("empty-form")
    );
    related.forEach((block) => {
      let raw = block.dataset.seoLocale || "";
      if (!raw) {
        const localeField =
          block.querySelector('select[name$="-locale"]') ||
          block.querySelector('input[name$="-locale"]') ||
          block.querySelector(".field-locale .readonly") ||
          block.querySelector(".field-locale");
        if (localeField) {
          raw = localeField.value || localeField.textContent || "";
        }
      }
      if (!raw) {
        const heading = block.querySelector("h3, h2, .inline_label");
        raw = heading?.textContent || "";
      }
      const code = resolveLocaleCode(raw);
      const show = !code || code === locale;
      block.hidden = !show;
      block.classList.toggle("builder-locale-hidden", !show);
    });
  }

  function mount(root) {
    if (root.dataset.contentBuilderMounted === "1") {
      return;
    }
    root.dataset.contentBuilderMounted = "1";

    const drawer =
      root.querySelector("[data-builder-drawer]") ||
      root.querySelector("[data-blog-drawer]");
    const backdrop = root.querySelector("[data-builder-drawer-backdrop]");
    const panels = root.querySelectorAll(
      "[data-builder-drawer-panel], [data-blog-drawer-panel]"
    );
    const triggers = root.querySelectorAll(
      "[data-builder-drawer-trigger], [data-blog-drawer-trigger]"
    );
    const title =
      root.querySelector("[data-builder-drawer-title]") ||
      root.querySelector("[data-blog-drawer-title]");
    let activePanel = null;

    function closeDrawer() {
      if (!drawer) return;
      drawer.hidden = true;
      drawer.setAttribute("aria-hidden", "true");
      drawer.classList.remove("blog-post-editor__drawer--wide");
      root.classList.remove("is-drawer-open");
      if (backdrop) backdrop.hidden = true;
      triggers.forEach((trigger) => trigger.classList.remove("is-active"));
      activePanel = null;
    }

    function openDrawer(name) {
      if (!drawer) return;
      const panel =
        root.querySelector(`[data-builder-drawer-panel="${name}"]`) ||
        root.querySelector(`[data-blog-drawer-panel="${name}"]`);
      if (!panel) return;
      panels.forEach((item) => {
        item.hidden = item !== panel;
      });
      triggers.forEach((trigger) => {
        const triggerName =
          trigger.dataset.builderDrawerTrigger || trigger.dataset.blogDrawerTrigger;
        trigger.classList.toggle("is-active", triggerName === name);
      });
      if (title) title.textContent = DRAWER_TITLES[name] || name;
      drawer.classList.toggle("blog-post-editor__drawer--wide", name === "seo");
      drawer.hidden = false;
      drawer.setAttribute("aria-hidden", "false");
      root.classList.add("is-drawer-open");
      if (backdrop) backdrop.hidden = false;
      activePanel = name;
      if (name === "seo") {
        window.requestAnimationFrame(() => {
          if (window.SeoOgPreview) {
            window.SeoOgPreview.boot(panel || document);
          }
          document.dispatchEvent(new CustomEvent("seo-drawer-open"));
        });
      }
    }

    triggers.forEach((trigger) => {
      trigger.addEventListener("click", () => {
        const name =
          trigger.dataset.builderDrawerTrigger || trigger.dataset.blogDrawerTrigger;
        if (activePanel === name) closeDrawer();
        else openDrawer(name);
      });
    });
    root
      .querySelector("[data-builder-drawer-close], [data-blog-drawer-close]")
      ?.addEventListener("click", closeDrawer);
    backdrop?.addEventListener("click", closeDrawer);
    root.querySelector("[data-page-blocker-close]")?.addEventListener("click", () => {
      const blocker = root.querySelector("[data-page-blocker]");
      if (blocker) blocker.hidden = true;
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && drawer && !drawer.hidden) closeDrawer();
    });

    // Click anywhere outside the drawer (and rail triggers) to close it.
    document.addEventListener(
      "pointerdown",
      (event) => {
        if (!drawer || drawer.hidden) return;
        const target = event.target;
        if (!(target instanceof Element)) return;
        if (drawer.contains(target)) return;
        if (target.closest("[data-builder-drawer-trigger], [data-blog-drawer-trigger]")) {
          return;
        }
        closeDrawer();
      },
      true
    );

    const localeInput = root.querySelector('[name="_builder_locale"]');
    setDetailsLocale(root, localeInput?.value || "hr");

    const currentUrl = new URL(window.location.href);
    if (currentUrl.searchParams.get("new") === "1") {
      const publishedInput = root.querySelector("#id_is_active");
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

    // Pin the builder frame under the admin header / beside the sidebar so the
    // canvas scrollbar track runs all the way to the bottom of the window.
    let frameSyncRaf = 0;
    const syncBuilderFrame = () => {
      if (frameSyncRaf) return;
      frameSyncRaf = window.requestAnimationFrame(() => {
        frameSyncRaf = 0;
        const header = document.getElementById("header");
        const sidebar = document.getElementById("nav-sidebar");
        const top = header ? Math.round(header.getBoundingClientRect().bottom) : 0;
        let left = 0;
        if (sidebar) {
          const style = window.getComputedStyle(sidebar);
          const visible =
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            sidebar.getBoundingClientRect().width > 8;
          if (visible) {
            left = Math.round(sidebar.getBoundingClientRect().right);
          }
        }
        const rootStyle = document.documentElement.style;
        if (rootStyle.getPropertyValue("--vb-frame-top") !== `${top}px`) {
          rootStyle.setProperty("--vb-frame-top", `${top}px`);
        }
        if (rootStyle.getPropertyValue("--vb-frame-left") !== `${left}px`) {
          rootStyle.setProperty("--vb-frame-left", `${left}px`);
        }
      });
    };
    syncBuilderFrame();
    window.addEventListener("resize", syncBuilderFrame, { passive: true });
    document.addEventListener("click", (event) => {
      if (
        event.target instanceof Element &&
        event.target.closest("#toggle-nav-sidebar, .toggle-nav-sidebar")
      ) {
        window.setTimeout(syncBuilderFrame, 0);
        window.setTimeout(syncBuilderFrame, 200);
      }
    });
    if (window.ResizeObserver) {
      const ro = new ResizeObserver(syncBuilderFrame);
      const header = document.getElementById("header");
      const sidebar = document.getElementById("nav-sidebar");
      if (header) ro.observe(header);
      if (sidebar) ro.observe(sidebar);
    }
  }

  function boot() {
    document
      .querySelectorAll("[data-page-editor], [data-blog-post-editor]")
      .forEach(mount);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
