/**
 * Visual page builder — structure-first admin canvas (Phase D).
 */
(function () {
  "use strict";

  const PAGE_SAVE_TIMEOUT_MS = 30000;
  const VIDEO_UPLOAD_TIMEOUT_MS = 10 * 60 * 1000;

  const ROW_PRESETS = {
    one: [12],
    two_equal: [6, 6],
    two_66_33: [8, 4],
    two_33_66: [4, 8],
    three_equal: [4, 4, 4],
  };

  const ELEMENT_LABELS = {
    heading: "Naslov",
    text: "Tekst",
    image: "Slika",
    video: "Video",
    faq: "FAQ",
    button: "Dugme",
    divider: "Linija",
  };

  const TEXT_BLOCK_PLACEHOLDER = "Unesite tekst…";

  const ELEMENT_ICONS = {
    heading: "H",
    text: "¶",
    image: "🖼",
    video: "▶",
    faq: "?",
    button: "⬤",
    divider: "—",
  };

  const ELEMENT_ACTIONS = [
    "add-heading",
    "add-text",
    "add-button",
    "add-image",
    "add-video",
    "add-faq",
    "add-divider",
  ];

  const DEFAULT_SECTION_SETTINGS = {
    background: "default",
    container_width: "contained",
  };

  const DEFAULT_ROW_SETTINGS = {
    vertical_align: "top",
  };

  const DEFAULT_COLUMN_SETTINGS = {
    width_mobile: 12,
    width_tablet: 12,
    width_desktop: 12,
    horizontal_align: "center",
  };

  const DEFAULT_BLOCK_SETTINGS = {
    align: "center",
  };

  const MEDIA_WIDTH_MIN = 10;
  const MEDIA_WIDTH_MAX = 100;

  const FONT_SIZE_MIN_PX = 8;
  const FONT_SIZE_MAX_PX = 96;
  const FONT_SIZE_DEFAULT_PX = 16;

  const SAVE_LABELS = {
    saved: "Sačuvano",
    saving: "Čuva se…",
    dirty: "Nesačuvano",
    error: "Greška",
    conflict: "Konflikt",
  };

  const OPTION_LABELS = {
    none: "Bez",
    sm: "Malo",
    md: "Srednje",
    lg: "Veliko",
    default: "Podrazumevano",
    light: "Svetla",
    dark: "Tamna",
    accent: "Naglašena",
    contained: "Ograničena",
    full: "Puna širina",
    top: "Gore",
    center: "Sredina",
    bottom: "Dole",
    left: "Levo",
    right: "Desno",
    primary: "Primarno",
    secondary: "Sekundarno",
    outline: "Kontura",
    "16:9": "Široko (16:9)",
    "4:3": "Standardno (4:3)",
    "1:1": "Kvadratno (1:1)",
  };

  function uid(prefix) {
    return `${prefix}_${Math.random().toString(16).slice(2, 14)}`;
  }

  function readJsonScript(id, fallback) {
    const node = document.getElementById(id);
    if (!node || !node.textContent) {
      return fallback;
    }
    try {
      return JSON.parse(node.textContent);
    } catch (_error) {
      return fallback;
    }
  }

  function getCsrfToken() {
    const input = document.querySelector("[name=csrfmiddlewaretoken]");
    if (input && input.value) {
      return input.value;
    }
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function trackSessionUpload(state, storage, path) {
    const normalized = String(path || "").trim();
    if (!normalized || !state.sessionUploads) {
      return;
    }
    const key = `${storage}:${normalized}`;
    state.sessionUploads.set(key, { storage, path: normalized });
  }

  function clearSessionUploads(state) {
    if (state.sessionUploads) {
      state.sessionUploads.clear();
    }
    state.abandonCleanupSent = false;
  }

  function getSessionUploadList(state) {
    if (!state.sessionUploads) {
      return [];
    }
    return Array.from(state.sessionUploads.values());
  }

  function shouldAbandonPendingUploads(state) {
    return Boolean(
      state
        && state.cleanupPendingUrl
        && state.sessionUploads
        && state.sessionUploads.size > 0
        && !state.abandonCleanupSent,
    );
  }

  function abandonPendingUploads(state, options) {
    const opts = options || {};
    if (!shouldAbandonPendingUploads(state)) {
      return Promise.resolve({ ok: true, skipped: true });
    }

    state.abandonCleanupSent = true;
    const paths = getSessionUploadList(state);
    state.sessionUploads.clear();

    const request = fetch(state.cleanupPendingUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({ paths }),
      keepalive: Boolean(opts.keepalive),
    });

    return request
      .then((response) => response.json().catch(() => ({})).then((data) => ({ response, data })))
      .then(({ response, data }) => {
        if (!response.ok || !data.ok) {
          paths.forEach((item) => {
            trackSessionUpload(state, item.storage || "default", item.path);
          });
          state.abandonCleanupSent = false;
          return { ok: false };
        }
        return { ok: true };
      })
      .catch(() => {
        paths.forEach((item) => {
          trackSessionUpload(state, item.storage || "default", item.path);
        });
        state.abandonCleanupSent = false;
        return { ok: false };
      });
  }

  async function cleanupPendingUploadsAfterSave(state) {
    if (!state || !state.cleanupPendingUrl || !state.sessionUploads || state.sessionUploads.size === 0) {
      return { ok: true, skipped: true };
    }

    // The server checks saved Topic/News JSON after the save. Referenced uploads are kept;
    // only paths that remained unused are deleted. One batched request keeps R2 operations low.
    const result = await abandonPendingUploads(state);
    if (result && result.ok) {
      clearSessionUploads(state);
    }
    return result;
  }

  function initAbandonUploadCleanup(state, postRoot) {
    const onLeave = () => {
      abandonPendingUploads(state, { keepalive: true });
    };

    window.addEventListener("pagehide", onLeave);

    const backLink = postRoot.querySelector(".blog-post-editor__back");
    if (backLink) {
      backLink.addEventListener("click", (event) => {
        if (!shouldAbandonPendingUploads(state)) {
          return;
        }
        event.preventDefault();
        const destination = backLink.href;
        abandonPendingUploads(state).finally(() => {
          window.location.href = destination;
        });
      });
    }
  }

  function emptyPage() {
    return { format: "iv_page_v1", type: "page", sections: [] };
  }

  function createSection() {
    return {
      id: uid("sec"),
      settings: { ...DEFAULT_SECTION_SETTINGS },
      rows: [createRow("one")],
    };
  }

  function createRow(preset) {
    const widths = ROW_PRESETS[preset] || ROW_PRESETS.one;
    return {
      id: uid("row"),
      settings: { ...DEFAULT_ROW_SETTINGS },
      columns: widths.map((width) => createColumn(width)),
    };
  }

  function createColumn(widthDesktop) {
    return {
      id: uid("col"),
      settings: {
        ...DEFAULT_COLUMN_SETTINGS,
        width_desktop: widthDesktop,
        width_tablet: widthDesktop >= 6 ? widthDesktop : 12,
      },
      blocks: [],
    };
  }

  function createBlock(type) {
    if (type === "heading") {
      return {
        id: uid("blk"),
        type: "heading",
        settings: { ...DEFAULT_BLOCK_SETTINGS },
        attrs: { level: 2, text: "Naslov" },
      };
    }
    if (type === "text") {
      return {
        id: uid("blk"),
        type: "text",
        settings: { ...DEFAULT_BLOCK_SETTINGS },
        attrs: { text: "" },
      };
    }
    if (type === "image") {
      return {
        id: uid("blk"),
        type: "image",
        settings: { ...DEFAULT_BLOCK_SETTINGS, width_percent: "100" },
        attrs: { src: "", path: "", alt: "", caption: "", media_asset_id: "" },
      };
    }
    if (type === "video") {
      return {
        id: uid("blk"),
        type: "video",
        settings: { ...DEFAULT_BLOCK_SETTINGS, aspect: "16:9", width_percent: "100" },
        attrs: {
          url: "",
          path: "",
          src: "",
          poster: "",
          poster_path: "",
          caption: "",
        },
      };
    }
    if (type === "faq") {
      return {
        id: uid("blk"),
        type: "faq",
        settings: { ...DEFAULT_BLOCK_SETTINGS },
        attrs: {
          style: "accordion",
          items: [
            { question: "Prvo pitanje?", answer: "Odgovor na prvo pitanje." },
            { question: "Drugo pitanje?", answer: "Odgovor na drugo pitanje." },
          ],
        },
      };
    }
    if (type === "button") {
      return {
        id: uid("blk"),
        type: "button",
        settings: { ...DEFAULT_BLOCK_SETTINGS },
        attrs: { label: "Saznajte više", href: "", style: "primary" },
      };
    }
    return {
      id: uid("blk"),
      type: "divider",
      settings: { ...DEFAULT_BLOCK_SETTINGS },
      attrs: {},
    };
  }

  function detectRowPreset(row) {
    const widths = row.columns.map((column) => column.settings.width_desktop);
    for (const [preset, presetWidths] of Object.entries(ROW_PRESETS)) {
      if (
        presetWidths.length === widths.length &&
        presetWidths.every((width, index) => width === widths[index])
      ) {
        return preset;
      }
    }
    return "one";
  }

  function findBlock(state, blockId) {
    for (const section of state.page.sections) {
      for (const row of section.rows) {
        for (const column of row.columns) {
          const block = column.blocks.find((item) => item.id === blockId);
          if (block) {
            return { section, row, column, block };
          }
        }
      }
    }
    return null;
  }

  function findColumn(state, columnId) {
    for (const section of state.page.sections) {
      for (const row of section.rows) {
        for (const column of row.columns) {
          if (column.id === columnId) {
            return { section, row, column };
          }
        }
      }
    }
    return null;
  }

  function sectionCssClasses(settings) {
    const s = settings || {};
    const custom = normalizeHexColor(s.background_color);
    return [
      "iv-page-section",
      `iv-page-section--width-${s.container_width || "contained"}`,
      custom ? "iv-page-section--bg-custom" : `iv-page-section--bg-${s.background || "default"}`,
    ].join(" ");
  }

  function sectionInlineStyle(settings) {
    const color = normalizeHexColor((settings || {}).background_color);
    return color ? `background-color: ${color};` : "";
  }

  function normalizeHexColor(value) {
    let raw = String(value || "").trim();
    if (!raw) {
      return "";
    }
    if (!raw.startsWith("#")) {
      raw = `#${raw}`;
    }
    if (!/^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(raw)) {
      return "";
    }
    return raw.toLowerCase();
  }

  function isSafeHref(href) {
    const value = String(href || "").trim();
    if (!value || value.startsWith("#") || value.startsWith("/")) {
      return true;
    }
    if (value.startsWith("mailto:") || value.startsWith("tel:")) {
      return true;
    }
    try {
      const parsed = new URL(value, window.location.origin);
      const scheme = (parsed.protocol || "").replace(":", "").toLowerCase();
      if (["javascript", "data", "vbscript"].includes(scheme)) {
        return false;
      }
      return ["http", "https"].includes(scheme) || !scheme;
    } catch (_error) {
      return false;
    }
  }

  function rowCssClasses(settings) {
    const s = settings || {};
    return `iv-page-row iv-page-row--align-${s.vertical_align || "top"}`;
  }

  function columnCssClasses(settings) {
    const s = settings || {};
    const mobile = s.width_mobile ?? 12;
    const tablet = s.width_tablet ?? 12;
    const desktop = s.width_desktop ?? 12;
    const align = s.horizontal_align || "left";
    return (
      `iv-page-col col-mobile-${mobile} col-tablet-${tablet} col-desktop-${desktop} ` +
      `iv-page-col--align-${align}`
    );
  }

  function blockAlignClass(block, prefix) {
    const align = (block.settings || {}).align || "left";
    return `${prefix}--align-${align}`;
  }

  function clampFontSizePx(value) {
    const num = Math.round(Number(value));
    if (!Number.isFinite(num)) {
      return null;
    }
    return Math.max(FONT_SIZE_MIN_PX, Math.min(FONT_SIZE_MAX_PX, num));
  }

  function normalizeSpanFontSize(style) {
    const match = String(style || "").match(/font-size:\s*([0-9]+(?:\.[0-9]+)?)px/i);
    if (!match) {
      return null;
    }
    const px = clampFontSizePx(match[1]);
    return px == null ? null : `${px}px`;
  }

  function normalizeEditorTextEntities(value) {
    const textarea = document.createElement("textarea");
    let normalized = String(value || "");
    for (let index = 0; index < 8; index += 1) {
      textarea.innerHTML = normalized;
      const decoded = textarea.value;
      if (decoded === normalized) {
        break;
      }
      normalized = decoded;
    }
    return normalized.replace(/\u00a0/g, " ");
  }

  function sanitizeEditableHtml(html) {
    const wrapper = document.createElement("div");
    wrapper.innerHTML = html || "";
    const allowed = new Set(["B", "STRONG", "I", "EM", "U", "BR", "SPAN", "A"]);

    function clean(node) {
      const children = [...node.childNodes];
      children.forEach((child) => {
        if (child.nodeType === Node.TEXT_NODE) {
          child.nodeValue = normalizeEditorTextEntities(child.nodeValue);
          return;
        }
        if (child.nodeType !== Node.ELEMENT_NODE) {
          child.remove();
          return;
        }
        const tag = child.tagName;
        if (tag === "BR") {
          return;
        }
        if (tag === "A") {
          const href = String(child.getAttribute("href") || "").trim();
          [...child.attributes].forEach((attr) => {
            child.removeAttribute(attr.name);
          });
          if (href && isSafeHref(href)) {
            child.setAttribute("href", href);
            child.setAttribute("target", "_blank");
            child.setAttribute("rel", "noopener noreferrer");
            clean(child);
            return;
          }
          while (child.firstChild) {
            node.insertBefore(child.firstChild, child);
          }
          child.remove();
          clean(node);
          return;
        }
        if (tag === "SPAN") {
          const fontSize = normalizeSpanFontSize(child.getAttribute("style"));
          if (fontSize) {
            [...child.attributes].forEach((attr) => {
              child.removeAttribute(attr.name);
            });
            child.style.fontSize = fontSize;
            clean(child);
            return;
          }
          while (child.firstChild) {
            node.insertBefore(child.firstChild, child);
          }
          child.remove();
          clean(node);
          return;
        }
        if (!allowed.has(tag)) {
          while (child.firstChild) {
            node.insertBefore(child.firstChild, child);
          }
          child.remove();
          clean(node);
          return;
        }
        [...child.attributes].forEach((attr) => {
          child.removeAttribute(attr.name);
        });
        clean(child);
      });
    }

    clean(wrapper);
    return wrapper.innerHTML.trim();
  }

  function htmlToPlainText(html) {
    const wrapper = document.createElement("div");
    wrapper.innerHTML = html || "";
    return normalizeEditorTextEntities(wrapper.textContent || "").trim();
  }

  function getEditableHtml(element) {
    const plain = htmlToPlainText(element.innerHTML);
    if (!plain) {
      return "";
    }
    return sanitizeEditableHtml(element.innerHTML);
  }

  function setEditableHtml(element, html) {
    const value = html || "";
    if (!value) {
      element.innerHTML = "";
      element.classList.add("is-empty");
      return;
    }
    if (value.includes("<")) {
      element.innerHTML = sanitizeEditableHtml(value);
    } else {
      element.textContent = value;
    }
    annotateEditorLinks(element);
    element.classList.remove("is-empty");
  }

  function annotateEditorLinks(root) {
    if (!root) {
      return;
    }
    root.querySelectorAll("a[href]").forEach((link) => {
      const href = String(link.getAttribute("href") || "").trim();
      if (!href) {
        return;
      }
      link.setAttribute("title", href);
      link.setAttribute("data-link-url", href);
    });
  }

  function getNodePath(root, node) {
    const path = [];
    let current = node;
    while (current && current !== root) {
      const parent = current.parentNode;
      if (!parent) {
        break;
      }
      path.unshift(Array.prototype.indexOf.call(parent.childNodes, current));
      current = parent;
    }
    if (current !== root) {
      throw new Error("node is outside root");
    }
    return path;
  }

  function resolveNodePath(root, path) {
    let node = root;
    path.forEach((index) => {
      node = node.childNodes[index];
      if (!node) {
        throw new Error("invalid node path");
      }
    });
    return node;
  }

  const FONT_SIZE_BOOKMARK_HIGHLIGHT = "vb-font-size-bookmark";

  function supportsBookmarkHighlight() {
    return typeof CSS !== "undefined" && CSS.highlights && typeof Highlight !== "undefined";
  }

  function clearBookmarkHighlight() {
    if (supportsBookmarkHighlight()) {
      CSS.highlights.delete(FONT_SIZE_BOOKMARK_HIGHLIGHT);
    }
  }

  function showBookmarkHighlight(block, bookmark, editable) {
    clearBookmarkHighlight();
    if (!supportsBookmarkHighlight() || !bookmark?.range || bookmark.blockId !== block.id || !editable) {
      return false;
    }
    try {
      const range = bookmark.range.cloneRange();
      if (range.collapsed || !editable.contains(range.commonAncestorContainer)) {
        return false;
      }
      CSS.highlights.set(FONT_SIZE_BOOKMARK_HIGHLIGHT, new Highlight(range));
      return true;
    } catch (_error) {
      return false;
    }
  }

  function refreshBookmarkHighlight(state, block) {
    const input = state.inspectorBody?.querySelector(".page-builder__inspector-number");
    if (!input || document.activeElement !== input) {
      return;
    }
    const editable = getActiveTextEditable(state, block);
    showBookmarkHighlight(block, state.textSelectionBookmark, editable);
  }

  function clearTextSelectionState(state) {
    state.textSelectionBookmark = null;
    clearBookmarkHighlight();
  }

  function saveTextSelectionState(state, block, editable) {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0 || selection.isCollapsed) {
      return false;
    }
    const range = selection.getRangeAt(0);
    if (!editable.contains(range.commonAncestorContainer)) {
      return false;
    }
    try {
      state.textSelectionBookmark = {
        blockId: block.id,
        range: range.cloneRange(),
      };
      return true;
    } catch (_error) {
      return false;
    }
  }

  function readFontSizePxAtPosition(node, editable) {
    const span = findFontSizeSpan(node, editable);
    if (span) {
      const normalized = normalizeSpanFontSize(span.getAttribute("style"));
      if (normalized) {
        return parseInt(normalized, 10);
      }
    }
    let element = node.nodeType === Node.TEXT_NODE ? node.parentElement : node;
    if (!element || !editable.contains(element)) {
      element = editable;
    }
    const computed = window.getComputedStyle(element).fontSize;
    const px = Math.round(parseFloat(computed));
    return clampFontSizePx(px) ?? FONT_SIZE_DEFAULT_PX;
  }

  function rangeIntersectsTextNode(range, textNode) {
    if (!textNode.textContent) {
      return false;
    }
    if (range.collapsed) {
      return (
        range.startContainer === textNode ||
        textNode === range.startContainer.parentNode ||
        textNode.contains(range.startContainer)
      );
    }
    try {
      const nodeRange = document.createRange();
      nodeRange.selectNodeContents(textNode);
      return (
        range.compareBoundaryPoints(Range.END_TO_START, nodeRange) < 0 &&
        range.compareBoundaryPoints(Range.START_TO_END, nodeRange) > 0
      );
    } catch (_error) {
      return false;
    }
  }

  function collectFontSizePxInRange(range, editable) {
    const sizes = new Set();
    if (!range || !editable) {
      return sizes;
    }

    if (range.collapsed) {
      sizes.add(readFontSizePxAtPosition(range.startContainer, editable));
      return sizes;
    }

    const walker = document.createTreeWalker(editable, NodeFilter.SHOW_TEXT);
    let textNode = walker.nextNode();
    while (textNode) {
      if (rangeIntersectsTextNode(range, textNode)) {
        sizes.add(readFontSizePxAtPosition(textNode, editable));
      }
      textNode = walker.nextNode();
    }

    if (!sizes.size) {
      sizes.add(readFontSizePxAtPosition(range.startContainer, editable));
    }
    return sizes;
  }

  function resolveFontSizeInputValue(range, editable) {
    const sizes = collectFontSizePxInRange(range, editable);
    if (!sizes.size) {
      return "";
    }
    if (sizes.size === 1) {
      return String([...sizes][0]);
    }
    return "";
  }

  function syncFontSizeInputFromRange(editable, range, input) {
    if (!editable || !range || !input) {
      return;
    }
    input.value = resolveFontSizeInputValue(range, editable);
  }

  function syncFontSizeInputFromSelection(editable, input) {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) {
      return;
    }
    const range = selection.getRangeAt(0);
    if (!editable.contains(range.commonAncestorContainer)) {
      return;
    }
    syncFontSizeInputFromRange(editable, range, input);
  }

  function getBookmarkedTextRange(state, block, editable) {
    const bookmark = state.textSelectionBookmark;
    if (!bookmark || bookmark.blockId !== block.id || !bookmark.range) {
      return null;
    }
    try {
      const range = bookmark.range.cloneRange();
      if (range.collapsed || !editable.contains(range.commonAncestorContainer)) {
        return null;
      }
      return range;
    } catch (_error) {
      state.textSelectionBookmark = null;
      return null;
    }
  }

  function captureLiveTextSelection(state, block, editable) {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0 || selection.isCollapsed) {
      return false;
    }
    const range = selection.getRangeAt(0);
    if (!editable.contains(range.commonAncestorContainer)) {
      return false;
    }
    return saveTextSelectionState(state, block, editable);
  }

  function selectRangeContents(range) {
    const selection = window.getSelection();
    if (!selection) {
      return;
    }
    selection.removeAllRanges();
    selection.addRange(range);
  }

  function selectNodeContents(node) {
    const range = document.createRange();
    range.selectNodeContents(node);
    selectRangeContents(range);
    return range;
  }

  function getTextSelectionRange(state, block, editable) {
    const bookmarked = getBookmarkedTextRange(state, block, editable);
    if (bookmarked) {
      return bookmarked;
    }
    if (captureLiveTextSelection(state, block, editable)) {
      return getBookmarkedTextRange(state, block, editable);
    }
    return null;
  }

  function findFontSizeSpan(node, editable) {
    let current = node.nodeType === Node.TEXT_NODE ? node.parentElement : node;
    while (current && current !== editable) {
      if (current.tagName === "SPAN" && normalizeSpanFontSize(current.getAttribute("style"))) {
        return current;
      }
      current = current.parentElement;
    }
    return null;
  }

  function unwrapFontSizeSpansInNode(node) {
    if (!node || !node.querySelectorAll) {
      return;
    }
    [...node.querySelectorAll("span")].forEach((span) => {
      if (!normalizeSpanFontSize(span.getAttribute("style"))) {
        return;
      }
      const parent = span.parentNode;
      if (!parent) {
        return;
      }
      while (span.firstChild) {
        parent.insertBefore(span.firstChild, span);
      }
      parent.removeChild(span);
    });
  }

  function normalizeFontSpans(container) {
    if (!container) {
      return;
    }

    [...container.querySelectorAll("span")].forEach((inner) => {
      const innerSize = normalizeSpanFontSize(inner.getAttribute("style"));
      if (!innerSize) {
        return;
      }
      const parent = inner.parentElement;
      if (
        parent &&
        parent.tagName === "SPAN" &&
        normalizeSpanFontSize(parent.getAttribute("style")) === innerSize
      ) {
        while (inner.firstChild) {
          parent.insertBefore(inner.firstChild, inner);
        }
        inner.remove();
      }
    });

    let node = container.firstChild;
    while (node) {
      const next = node.nextSibling;
      if (
        node.nodeType === Node.ELEMENT_NODE &&
        node.tagName === "SPAN" &&
        next &&
        next.nodeType === Node.ELEMENT_NODE &&
        next.tagName === "SPAN"
      ) {
        const sizeA = normalizeSpanFontSize(node.getAttribute("style"));
        const sizeB = normalizeSpanFontSize(next.getAttribute("style"));
        if (sizeA && sizeA === sizeB) {
          while (next.firstChild) {
            node.appendChild(next.firstChild);
          }
          next.remove();
          continue;
        }
      }
      node = next;
    }
  }

  function applyFontSizeToRange(range, fontSize) {
    const fragment = range.extractContents();
    unwrapFontSizeSpansInNode(fragment);
    const span = document.createElement("span");
    span.style.fontSize = fontSize;
    span.appendChild(fragment);
    range.insertNode(span);
    selectNodeContents(span);
    return span;
  }

  function commitEditableText(state, block, editable) {
    block.attrs.text = getEditableHtml(editable);
    syncEditablePlaceholderRich(editable);
    saveTextSelectionState(state, block, editable);
    markDirty(state);
  }

  function bindTextSelectionBookmark(state, block, editable) {
    const capture = () => {
      const selection = window.getSelection();
      if (!selection || selection.rangeCount === 0) {
        return;
      }
      const range = selection.getRangeAt(0);
      if (!editable.contains(range.commonAncestorContainer)) {
        return;
      }

      const input = state.inspectorBody?.querySelector(".page-builder__inspector-number");
      if (input && document.activeElement !== input) {
        syncFontSizeInputFromSelection(editable, input);
      }

      if (!range.collapsed) {
        saveTextSelectionState(state, block, editable);
      }
    };
    editable.addEventListener("mouseup", capture);
    editable.addEventListener("keyup", capture);
    editable.addEventListener("click", capture);
  }

  function getActiveTextEditable(state, block) {
    const className = block.type === "heading" ? "iv-page-heading" : "iv-page-text";
    return state.canvas.querySelector(
      `.page-builder__block[data-block-id="${block.id}"] .${className}[contenteditable="true"]`,
    );
  }

  function applyTextFormat(state, block, command) {
    const editable = getActiveTextEditable(state, block);
    if (!editable) {
      return;
    }
    const range = getTextSelectionRange(state, block, editable);
    if (!range) {
      showToast(state.root, "Prvo označite tekst u bloku.", true);
      return;
    }
    selectRangeContents(range);
    if (command === "createLink") {
      const current = document.queryCommandValue("createLink") || "";
      const href = window.prompt("Unesite URL linka", current || "https://");
      if (href == null) {
        return;
      }
      const trimmed = String(href).trim();
      if (!trimmed) {
        document.execCommand("unlink", false, null);
      } else if (!isSafeHref(trimmed)) {
        showToast(state.root, "Link nije dozvoljen (koristite http/https, / ili #).", true);
        return;
      } else {
        document.execCommand("createLink", false, trimmed);
      }
    } else if (command === "unlink") {
      document.execCommand("unlink", false, null);
    } else {
      document.execCommand(command, false, null);
    }
    commitEditableText(state, block, editable);
    annotateEditorLinks(editable);
  }

  function applyInlineFontSize(state, block, sizeValue) {
    const px = clampFontSizePx(sizeValue);
    if (px == null) {
      return false;
    }
    const editable = getActiveTextEditable(state, block);
    if (!editable) {
      return false;
    }

    const range = getTextSelectionRange(state, block, editable);
    if (!range) {
      return false;
    }

    const fontSize = `${px}px`;
    const startSpan = findFontSizeSpan(range.startContainer, editable);
    const endSpan = findFontSizeSpan(range.endContainer, editable);
    if (startSpan && startSpan === endSpan && range.toString() === (startSpan.textContent || "")) {
      startSpan.style.fontSize = fontSize;
      normalizeFontSpans(editable);
      selectNodeContents(startSpan);
      commitEditableText(state, block, editable);
    } else {
      applyFontSizeToRange(range, fontSize);
      normalizeFontSpans(editable);
      commitEditableText(state, block, editable);
    }

    refreshBookmarkHighlight(state, block);
    return true;
  }

  function syncRangeFill(range) {
    const min = Number(range.min);
    const max = Number(range.max);
    const value = Number(range.value);
    const percent = max > min ? ((value - min) / (max - min)) * 100 : 100;
    range.style.setProperty("--range-fill", `${percent}%`);
  }

  function normalizeMediaWidthPercent(block) {
    const raw = Number((block.settings || {}).width_percent ?? MEDIA_WIDTH_MAX);
    if (!Number.isFinite(raw)) {
      return String(MEDIA_WIDTH_MAX);
    }
    const clamped = Math.max(MEDIA_WIDTH_MIN, Math.min(MEDIA_WIDTH_MAX, Math.round(raw)));
    return String(clamped);
  }

  function mediaAlignClass(block) {
    const align = (block.settings || {}).align || "left";
    return `iv-page-media iv-page-media--align-${align}`;
  }

  function applyMediaWidthStyles(element, block) {
    element.className = mediaAlignClass(block);
    element.style.width = `${normalizeMediaWidthPercent(block)}%`;
    element.style.maxWidth = "100%";
  }

  function updateMediaWidthPreview(state, block) {
    const scale = state.canvas.querySelector(
      `.page-builder__block[data-block-id="${block.id}"] .iv-page-media`,
    );
    if (scale) {
      applyMediaWidthStyles(scale, block);
    }
  }

  function appendMediaWidthField(bodyEl, block, state) {
    if (!block.settings) {
      block.settings = { ...DEFAULT_BLOCK_SETTINGS };
    }

    const row = document.createElement("div");
    row.className = "page-builder__inspector-field";

    const labelRow = document.createElement("div");
    labelRow.className = "page-builder__inspector-range-label";

    const labelEl = document.createElement("span");
    labelEl.textContent = "Širina (%)";

    const valueEl = document.createElement("span");
    valueEl.className = "page-builder__inspector-range-value";
    const current = normalizeMediaWidthPercent(block);
    valueEl.textContent = `${current}%`;

    labelRow.appendChild(labelEl);
    labelRow.appendChild(valueEl);

    const range = document.createElement("input");
    range.type = "range";
    range.min = String(MEDIA_WIDTH_MIN);
    range.max = String(MEDIA_WIDTH_MAX);
    range.step = "1";
    range.value = current;
    range.className = "page-builder__inspector-range";
    const syncRange = () => {
      const value = normalizeMediaWidthPercent({ settings: { width_percent: range.value } });
      block.settings.width_percent = value;
      range.value = value;
      valueEl.textContent = `${value}%`;
      syncRangeFill(range);
      updateMediaWidthPreview(state, block);
      markDirty(state);
    };
    range.addEventListener("input", syncRange);
    syncRangeFill(range);

    const rangeWrap = document.createElement("div");
    rangeWrap.className = "page-builder__inspector-range-wrap";
    rangeWrap.appendChild(range);

    row.appendChild(labelRow);
    row.appendChild(rangeWrap);
    bodyEl.appendChild(row);
  }

  function extractYouTubeId(url) {
    const value = String(url || "").trim();
    if (!value) {
      return "";
    }
    const patterns = [
      /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([\w-]{11})/,
      /^([\w-]{11})$/,
    ];
    for (const pattern of patterns) {
      const match = value.match(pattern);
      if (match) {
        return match[1];
      }
    }
    return "";
  }

  function markDirty(state) {
    state.dirty = true;
    if (state.documents && state.documents[state.locale]) {
      state.documents[state.locale].page = state.page;
      state.documents[state.locale].dirty = true;
    }
    setSaveStatus(state.postRoot, "dirty");
    syncPlaintextField(extractPlaintext(state.page));
    state.postRoot.dispatchEvent(new CustomEvent("page-builder:change", { bubbles: true }));
  }

  function extractPlaintext(page) {
    const parts = [];
    for (const section of page.sections || []) {
      for (const row of section.rows || []) {
        for (const column of row.columns || []) {
          for (const block of column.blocks || []) {
            const attrs = block.attrs || {};
            if (block.type === "heading" || block.type === "text") {
              let text = htmlToPlainText(String(attrs.text || "")).trim();
              if (block.type === "text") {
                text = htmlToPlainText(normalizePlaceholderText(attrs.text, TEXT_BLOCK_PLACEHOLDER)).trim();
              }
              if (text) {
                parts.push(text);
              }
            } else if (block.type === "image") {
              const alt = String(attrs.alt || "").trim();
              const caption = String(attrs.caption || "").trim();
              const combined = [alt, caption].filter(Boolean).join(" ");
              if (combined) {
                parts.push(combined);
              }
            } else if (block.type === "faq") {
              for (const item of attrs.items || []) {
                const question = String(item.question || "").trim();
                const answer = String(item.answer || "").trim();
                if (question) {
                  parts.push(question);
                }
                if (answer) {
                  parts.push(answer);
                }
              }
            } else if (block.type === "button") {
              const label = String(attrs.label || "").trim();
              if (label) {
                parts.push(label);
              }
            }
          }
        }
      }
    }
    return parts.join("\n\n");
  }

  function syncPlaintextField(plaintext) {
    const field = document.getElementById("id_body_plaintext");
    if (field) {
      field.value = plaintext || "";
      field.dispatchEvent(new Event("input", { bubbles: true }));
    }
  }

  function setSaveStatus(postRoot, stateKey, tooltip) {
    const statusEl = postRoot.querySelector("[data-page-save-status]");
    if (!statusEl) {
      return;
    }
    statusEl.dataset.state = stateKey;
    const labelEl = statusEl.querySelector("[data-page-save-label]");
    if (labelEl) {
      labelEl.textContent = SAVE_LABELS[stateKey] || SAVE_LABELS.saved;
    }
    if (tooltip) {
      statusEl.title = tooltip;
    }
  }

  function showBlocker(postRoot, message) {
    const blocker = postRoot.querySelector("[data-page-blocker]");
    const messageEl = postRoot.querySelector("[data-page-blocker-message]");
    if (!blocker || !messageEl) {
      window.alert(message);
      return;
    }
    messageEl.textContent = message;
    blocker.hidden = false;
  }

  function showToast(root, message, isError) {
    const toast = root.querySelector("[data-builder-toast]");
    if (!toast) {
      return;
    }
    toast.textContent = message;
    toast.hidden = false;
    toast.classList.toggle("is-error", Boolean(isError));
    if (toast._timer) {
      window.clearTimeout(toast._timer);
    }
    toast._timer = window.setTimeout(() => {
      toast.hidden = true;
    }, 5000);
  }

  function setPanelTab(state, tab) {
    state.panelTab = tab;
    state.panelBrowse.querySelectorAll("[data-panel-tab]").forEach((btn) => {
      btn.classList.toggle("is-active", btn.dataset.panelTab === tab);
    });
    state.panelWidgets.hidden = tab !== "widgets";
    state.panelNavigator.hidden = tab !== "navigator";
    if (tab === "navigator") {
      renderNavigator(state);
    }
  }

  function showBrowsePanel(state) {
    state.panelBrowse.hidden = false;
    state.panelEdit.hidden = true;
    setPanelTab(state, state.panelTab || "widgets");
    renderWidgetGrid(state);
  }

  function showEditPanel(state) {
    state.panelBrowse.hidden = true;
    state.panelEdit.hidden = false;
    if (state.panelEditTitle && state.selection) {
      state.panelEditTitle.textContent = state.selection.label;
    }
    renderEditPanel(state);
  }

  function renderPanel(state) {
    if (state.selection) {
      showEditPanel(state);
    } else {
      showBrowsePanel(state);
    }
  }

  function renderWidgetGrid(state) {
    if (!state.panelWidgets) {
      return;
    }
    state.panelWidgets.innerHTML = "";

    const hint = document.createElement("p");
    hint.className = "page-builder__panel-hint";
    if (state.targetColumnId) {
      hint.classList.add("is-active");
      hint.textContent = "Izaberite widget u listi ispod da ga dodate u označenu kolonu.";
    } else {
      hint.textContent = "Prvo kliknite kolonu na stranici, zatim izaberite widget.";
    }
    state.panelWidgets.appendChild(hint);

    const grid = document.createElement("div");
    grid.className = "page-builder__widget-grid";

    const elements = state.catalog.elements || ELEMENT_ACTIONS.map((action) => {
      const type = action.replace("add-", "");
      return { id: type, label: ELEMENT_LABELS[type] || type };
    });

    elements.forEach((element) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "page-builder__widget-card";
      card.innerHTML =
        `<span class="page-builder__widget-card-icon">${ELEMENT_ICONS[element.id] || "+"}</span>` +
        `<span>${element.label}</span>`;
      card.addEventListener("click", () => {
        if (!state.targetColumnId) {
          showToast(state.root, "Prvo kliknite kolonu na stranici.", true);
          setPanelTab(state, "widgets");
          return;
        }
        const found = findColumn(state, state.targetColumnId);
        if (!found) {
          return;
        }
        const block = createBlock(element.id);
        found.column.blocks.push(block);
        markDirty(state);
        selectItem(state, {
          kind: "block",
          id: block.id,
          label: ELEMENT_LABELS[element.id] || element.label,
          settings: block.settings,
          fields: state.catalog.block_settings,
          block,
          type: element.id,
        });
      });
      grid.appendChild(card);
    });

    state.panelWidgets.appendChild(grid);
  }

  function renderNavigator(state) {
    if (!state.panelNavigator) {
      return;
    }
    state.panelNavigator.innerHTML = "";
    const tree = document.createElement("ul");
    tree.className = "page-builder__nav-tree";

    state.page.sections.forEach((section, sectionIndex) => {
      tree.appendChild(
        navItem(state, `Sekcija ${sectionIndex + 1}`, "section", section.id, "section", {
          kind: "section",
          id: section.id,
          label: "Sekcija",
          settings: section.settings,
          fields: state.catalog.section_settings,
        }, "page-builder__nav-btn--section"),
      );

      section.rows.forEach((row, rowIndex) => {
        tree.appendChild(
          navItem(state, `Red ${rowIndex + 1}`, "row", row.id, "row", {
            kind: "row",
            id: row.id,
            label: "Red",
            settings: row.settings,
            fields: state.catalog.row_settings,
          }, "page-builder__nav-btn--row"),
        );

        row.columns.forEach((column, columnIndex) => {
          tree.appendChild(
            navItem(state, `Kolona ${columnIndex + 1}`, "column", column.id, "column", {
              kind: "column",
              id: column.id,
              label: "Kolona",
              settings: column.settings,
              fields: state.catalog.column_settings,
            }, "page-builder__nav-btn--column"),
          );

          column.blocks.forEach((block) => {
            tree.appendChild(
              navItem(state, ELEMENT_LABELS[block.type] || block.type, "block", block.id, "block", {
                kind: "block",
                id: block.id,
                label: ELEMENT_LABELS[block.type] || block.type,
                settings: block.settings,
                fields: state.catalog.block_settings,
                block,
                type: block.type,
              }, "page-builder__nav-btn--block"),
            );
          });
        });
      });
    });

    state.panelNavigator.appendChild(tree);
  }

  function navItem(state, label, icon, id, kind, payload, extraClass) {
    const li = document.createElement("li");
    li.className = "page-builder__nav-item";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `page-builder__nav-btn ${extraClass || ""}`.trim();
    if (state.selection && state.selection.id === id && state.selection.kind === kind) {
      btn.classList.add("is-selected");
    }
    btn.innerHTML = `<span class="page-builder__nav-icon">${icon === "section" ? "▦" : icon === "row" ? "☰" : icon === "column" ? "▯" : "•"}</span><span>${label}</span>`;
    btn.addEventListener("click", () => {
      if (kind === "column") {
        state.targetColumnId = id;
      }
      selectItem(state, payload);
    });
    li.appendChild(btn);
    return li;
  }

  function addWidgetToColumn(state, column, type) {
    const block = createBlock(type);
    column.blocks.push(block);
    markDirty(state);
    selectItem(state, {
      kind: "block",
      id: block.id,
      label: ELEMENT_LABELS[type] || type,
      settings: block.settings,
      fields: state.catalog.block_settings,
      block,
      type,
    });
  }

  function appendSelectField(bodyEl, label, value, options, onChange, formatOption) {
    const row = document.createElement("label");
    row.className = "page-builder__inspector-field";
    const labelEl = document.createElement("span");
    labelEl.textContent = label;
    const select = document.createElement("select");
    options.forEach((optionValue) => {
      const option = document.createElement("option");
      option.value = optionValue;
      option.textContent = formatOption
        ? formatOption(optionValue)
        : (OPTION_LABELS[optionValue] || optionValue);
      option.selected = value === optionValue;
      select.appendChild(option);
    });
    select.addEventListener("change", () => onChange(select.value));
    row.appendChild(labelEl);
    row.appendChild(select);
    bodyEl.appendChild(row);
  }

  function appendTextField(bodyEl, label, value, onChange, multiline) {
    const row = document.createElement("label");
    row.className = "page-builder__inspector-field";
    const labelEl = document.createElement("span");
    labelEl.textContent = label;
    const input = document.createElement(multiline ? "textarea" : "input");
    if (!multiline) {
      input.type = "text";
    }
    input.value = value || "";
    input.addEventListener("input", () => onChange(input.value));
    row.appendChild(labelEl);
    row.appendChild(input);
    bodyEl.appendChild(row);
  }

  function appendTextFormatToolbar(bodyEl, block, state) {
    const row = document.createElement("div");
    row.className = "page-builder__inspector-field";

    const labelEl = document.createElement("span");
    labelEl.textContent = "Formatiranje";
    row.appendChild(labelEl);

    const toolbar = document.createElement("div");
    toolbar.className = "page-builder__text-format";
    [
      ["bold", "B", "Podebljano"],
      ["italic", "I", "Kurziv"],
      ["underline", "U", "Podvučeno"],
      ["createLink", "🔗", "Dodaj link"],
      ["unlink", "⌀", "Ukloni link"],
    ].forEach(([command, label, title]) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "page-builder__text-format-btn";
      btn.textContent = label;
      btn.title = title;
      btn.addEventListener("mousedown", (event) => {
        event.preventDefault();
      });
      btn.addEventListener("click", () => {
        applyTextFormat(state, block, command);
      });
      toolbar.appendChild(btn);
    });

    row.appendChild(toolbar);
    bodyEl.appendChild(row);
  }

  function appendTextFontSizeField(bodyEl, block, state) {
    const row = document.createElement("div");
    row.className = "page-builder__inspector-field";

    const labelEl = document.createElement("span");
    labelEl.textContent = "Veličina fonta (px)";
    row.appendChild(labelEl);

    const controls = document.createElement("div");
    controls.className = "page-builder__inspector-inline-controls";

    const sizeControl = document.createElement("div");
    sizeControl.className = "page-builder__font-size-control";

    const input = document.createElement("input");
    input.type = "text";
    input.inputMode = "numeric";
    input.autocomplete = "off";
    input.value = String(FONT_SIZE_DEFAULT_PX);
    input.className = "page-builder__inspector-number";
    input.setAttribute("aria-label", "Veličina fonta u pikselima");

    const arrows = document.createElement("div");
    arrows.className = "page-builder__font-size-arrows";

    const stepUp = document.createElement("button");
    stepUp.type = "button";
    stepUp.className = "page-builder__font-size-step";
    stepUp.textContent = "▲";
    stepUp.title = "Povećaj";
    stepUp.setAttribute("aria-label", "Povećaj veličinu fonta");

    const stepDown = document.createElement("button");
    stepDown.type = "button";
    stepDown.className = "page-builder__font-size-step";
    stepDown.textContent = "▼";
    stepDown.title = "Smanji";
    stepDown.setAttribute("aria-label", "Smanji veličinu fonta");

    const nudgeFontSize = (delta) => {
      const current = clampFontSizePx(input.value) ?? FONT_SIZE_DEFAULT_PX;
      input.value = String(
        Math.max(FONT_SIZE_MIN_PX, Math.min(FONT_SIZE_MAX_PX, current + delta)),
      );
      input.focus();
      refreshBookmarkHighlight(state, block);
    };

    const applyBtn = document.createElement("button");
    applyBtn.type = "button";
    applyBtn.className = "page-builder__inspector-btn page-builder__inspector-btn--inline";
    applyBtn.textContent = "Primeni";

    const apply = () => {
      const applied = applyInlineFontSize(state, block, input.value);
      if (!applied) {
        showToast(state.root, "Prvo označite tekst u bloku.", true);
      }
    };

    const pinBookmarkHighlight = () => {
      const editable = getActiveTextEditable(state, block);
      const selection = window.getSelection();
      if (selection) {
        selection.removeAllRanges();
      }
      showBookmarkHighlight(block, state.textSelectionBookmark, editable);
    };

    controls.addEventListener(
      "pointerdown",
      () => {
        const editable = getActiveTextEditable(state, block);
        if (editable) {
          captureLiveTextSelection(state, block, editable);
        }
      },
      true,
    );
    applyBtn.addEventListener("mousedown", (event) => {
      event.preventDefault();
    });
    applyBtn.addEventListener("click", apply);
    input.addEventListener("focus", pinBookmarkHighlight);
    input.addEventListener("blur", () => {
      clearBookmarkHighlight();
    });
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        apply();
        return;
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        nudgeFontSize(1);
        return;
      }
      if (event.key === "ArrowDown") {
        event.preventDefault();
        nudgeFontSize(-1);
      }
    });
    input.addEventListener("input", () => {
      input.value = input.value.replace(/[^\d]/g, "");
      refreshBookmarkHighlight(state, block);
    });
    stepUp.addEventListener("mousedown", (event) => {
      event.preventDefault();
      nudgeFontSize(1);
    });
    stepDown.addEventListener("mousedown", (event) => {
      event.preventDefault();
      nudgeFontSize(-1);
    });

    const hint = document.createElement("p");
    hint.className = "page-builder__inspector-hint";
    hint.textContent = "Označite tekst, unesite veličinu u pikselima i kliknite Primeni.";

    arrows.appendChild(stepUp);
    arrows.appendChild(stepDown);
    sizeControl.appendChild(input);
    sizeControl.appendChild(arrows);
    controls.appendChild(sizeControl);
    controls.appendChild(applyBtn);
    row.appendChild(controls);
    row.appendChild(hint);
    bodyEl.appendChild(row);
  }

  function syncInspectorFontSizeInput(bodyEl, block, state) {
    const editable = getActiveTextEditable(state, block);
    const fontSizeInput = bodyEl.querySelector(".page-builder__inspector-number");
    if (!editable || !fontSizeInput) {
      return;
    }
    const selection = window.getSelection();
    if (selection && selection.rangeCount > 0 && editable.contains(selection.anchorNode)) {
      syncFontSizeInputFromSelection(editable, fontSizeInput);
      return;
    }
    const bookmark = state.textSelectionBookmark;
    if (bookmark?.range && bookmark.blockId === block.id) {
      syncFontSizeInputFromRange(editable, bookmark.range, fontSizeInput);
    }
  }

  function appendVideoUploadProgress(bodyEl, upload) {
    const wrap = document.createElement("div");
    wrap.className = "page-builder__upload-progress";
    wrap.dataset.videoUploadProgress = "1";
    wrap.setAttribute("role", "status");
    wrap.setAttribute("aria-live", "polite");

    const label = document.createElement("div");
    label.className = "page-builder__upload-progress-label";
    label.dataset.videoUploadProgressLabel = "1";
    const percent = Number.isFinite(upload.percent) ? upload.percent : 0;
    label.textContent = percent > 0 ? `Otpremanje: ${percent}%` : "Priprema otpremanja…";

    const progress = document.createElement("progress");
    progress.className = "page-builder__upload-progress-bar";
    progress.max = 100;
    progress.value = percent;
    progress.dataset.videoUploadProgressBar = "1";
    progress.setAttribute("aria-label", "Napredak otpremanja video fajla");

    wrap.appendChild(label);
    wrap.appendChild(progress);
    bodyEl.appendChild(wrap);
  }

  function updateVideoUploadProgress(state, block, percent) {
    const normalized = Math.max(0, Math.min(100, Math.round(percent || 0)));
    state.videoUploadProgress = { blockId: block.id, percent: normalized };

    if (state.selection?.block?.id !== block.id) {
      return;
    }
    const label = state.inspectorBody?.querySelector("[data-video-upload-progress-label]");
    const progress = state.inspectorBody?.querySelector("[data-video-upload-progress-bar]");
    if (label) {
      label.textContent = normalized > 0 ? `Otpremanje: ${normalized}%` : "Priprema otpremanja…";
    }
    if (progress) {
      progress.value = normalized;
    }
  }

  async function copyImagePath(path, input) {
    const value = String(path || "").trim();
    if (!value) {
      return false;
    }
    try {
      await navigator.clipboard.writeText(value);
      return true;
    } catch (_error) {
      input.focus();
      input.select();
      return document.execCommand("copy");
    }
  }

  function appendImagePathField(bodyEl, block, state) {
    const path = String(block?.attrs?.path || "").trim();
    if (!path) {
      return;
    }

    const field = document.createElement("label");
    field.className = "page-builder__inspector-field";
    const label = document.createElement("span");
    label.textContent = "Putanja slike (za ponovnu upotrebu)";
    const controls = document.createElement("div");
    controls.className = "page-builder__image-path-controls";
    const input = document.createElement("input");
    input.type = "text";
    input.value = path;
    input.readOnly = true;
    input.setAttribute("aria-label", "Putanja slike");
    const copyBtn = document.createElement("button");
    copyBtn.type = "button";
    copyBtn.textContent = "Kopiraj";
    copyBtn.className = "page-builder__inspector-btn page-builder__inspector-btn--inline";
    copyBtn.addEventListener("click", async () => {
      const copied = await copyImagePath(path, input);
      showToast(
        state.root,
        copied ? "Putanja slike je kopirana." : "Kopiranje nije uspelo. Označite i kopirajte putanju ručno.",
        !copied,
      );
    });
    controls.appendChild(input);
    controls.appendChild(copyBtn);
    field.appendChild(label);
    field.appendChild(controls);
    bodyEl.appendChild(field);
  }

  function renderEditPanel(state) {
    const bodyEl = state.inspectorBody;
    if (!bodyEl || !state.selection) {
      return;
    }
    bodyEl.innerHTML = "";

    for (const field of state.selection.fields || []) {
      if (field.type === "text") {
        appendTextField(
          bodyEl,
          field.label,
          state.selection.settings[field.id] || "",
          (value) => {
            if (field.id === "background_color") {
              const normalized = normalizeHexColor(value);
              state.selection.settings[field.id] = value.trim() ? (normalized || value.trim()) : "";
            } else {
              state.selection.settings[field.id] = value;
            }
            markDirty(state);
            renderCanvas(state);
          },
        );
        if (field.placeholder) {
          const input = bodyEl.querySelector(".page-builder__inspector-field:last-child input");
          if (input) {
            input.placeholder = field.placeholder;
          }
        }
        continue;
      }
      appendSelectField(
        bodyEl,
        field.label,
        state.selection.settings[field.id],
        field.options,
        (value) => {
          state.selection.settings[field.id] = value;
          markDirty(state);
          renderCanvas(state);
        },
      );
    }

    if (state.selection.type === "heading") {
      const headingBlock = state.selection.block;
      appendSelectField(
        bodyEl,
        "Nivo naslova (H1–H4)",
        String(headingBlock.attrs.level || 2),
        ["1", "2", "3", "4"],
        (value) => {
          headingBlock.attrs.level = Number(value);
          markDirty(state);
          renderCanvas(state);
        },
      );
      appendTextFormatToolbar(bodyEl, headingBlock, state);
      appendTextFontSizeField(bodyEl, headingBlock, state);
      syncInspectorFontSizeInput(bodyEl, headingBlock, state);
    }

    if (state.selection.type === "text") {
      const textBlock = state.selection.block;
      appendTextFormatToolbar(bodyEl, textBlock, state);
      appendTextFontSizeField(bodyEl, textBlock, state);
      syncInspectorFontSizeInput(bodyEl, textBlock, state);
    }

    if (state.selection.type === "image") {
      const uploadBtn = document.createElement("button");
      uploadBtn.type = "button";
      uploadBtn.textContent = "Otpremi sliku";
      uploadBtn.className = "page-builder__inspector-btn";
      uploadBtn.addEventListener("click", () => {
        state.pendingImageBlock = state.selection.block;
        state.fileInput.click();
      });
      bodyEl.appendChild(uploadBtn);
      appendImagePathField(bodyEl, state.selection.block, state);

      const reuseField = document.createElement("label");
      reuseField.className = "page-builder__inspector-field";
      const reuseLabel = document.createElement("span");
      reuseLabel.textContent = "Postojeća slika (storage path)";
      const reuseInput = document.createElement("input");
      reuseInput.type = "text";
      reuseInput.placeholder = "page/images/...";
      reuseInput.value = "";
      reuseField.appendChild(reuseLabel);
      reuseField.appendChild(reuseInput);
      bodyEl.appendChild(reuseField);

      const reuseBtn = document.createElement("button");
      reuseBtn.type = "button";
      reuseBtn.textContent = "Koristi postojeću sliku";
      reuseBtn.className = "page-builder__inspector-btn";
      reuseBtn.addEventListener("click", async () => {
        reuseBtn.disabled = true;
        const result = await resolveExistingImage(
          state,
          state.selection.block,
          reuseInput.value,
        );
        reuseBtn.disabled = false;
        if (!result.ok) {
          showToast(state.root, result.message || "Putanja nije validna.", true);
          return;
        }
        reuseInput.value = "";
        showToast(state.root, "Postojeća slika je primenjena.");
      });
      bodyEl.appendChild(reuseBtn);

      appendTextField(bodyEl, "Alt tekst", state.selection.block.attrs.alt, (value) => {
        state.selection.block.attrs.alt = value;
        markDirty(state);
        renderCanvas(state);
      });
      appendTextField(bodyEl, "Opis (caption)", state.selection.block.attrs.caption, (value) => {
        state.selection.block.attrs.caption = value;
        markDirty(state);
        renderCanvas(state);
      }, true);
      appendMediaWidthField(bodyEl, state.selection.block, state);
    }

    if (state.selection.type === "video") {
      const videoBlock = state.selection.block;
      const activeUpload = state.videoUploadProgress;
      const isUploading = Boolean(activeUpload && activeUpload.blockId === videoBlock.id);

      appendTextField(bodyEl, "YouTube URL", videoBlock.attrs.url, (value) => {
        videoBlock.attrs.url = value;
        if (value.trim()) {
          videoBlock.attrs.path = "";
          videoBlock.attrs.src = "";
          videoBlock.attrs.poster = "";
          videoBlock.attrs.poster_path = "";
        }
        markDirty(state);
        renderCanvas(state);
      });
      const uploadBtn = document.createElement("button");
      uploadBtn.type = "button";
      uploadBtn.textContent = isUploading ? "Otpremanje videa…" : "Otpremi video fajl";
      uploadBtn.className = "page-builder__inspector-btn";
      uploadBtn.disabled = isUploading;
      uploadBtn.addEventListener("click", () => {
        state.pendingVideoBlock = videoBlock;
        state.videoFileInput.click();
      });
      bodyEl.appendChild(uploadBtn);
      const videoHint = document.createElement("p");
      videoHint.className = "page-builder__inspector-hint";
      videoHint.textContent =
        "Podržano: MP4 (H.264) i WebM. Učitani fajl koristi svoj prirodni odnos strana.";
      bodyEl.appendChild(videoHint);

      if (isUploading) {
        appendVideoUploadProgress(bodyEl, activeUpload);
      }

      if (videoBlock.attrs.path || videoBlock.attrs.src) {
        const clearBtn = document.createElement("button");
        clearBtn.type = "button";
        clearBtn.textContent = "Ukloni video fajl";
        clearBtn.className = "page-builder__inspector-btn";
        clearBtn.addEventListener("click", () => {
          videoBlock.attrs.path = "";
          videoBlock.attrs.src = "";
          videoBlock.attrs.poster = "";
          videoBlock.attrs.poster_path = "";
          videoBlock.attrs.video_width = "";
          videoBlock.attrs.video_height = "";
          markDirty(state);
          renderCanvas(state);
          renderEditPanel(state);
        });
        bodyEl.appendChild(clearBtn);
      }
      appendTextField(bodyEl, "Opis", videoBlock.attrs.caption, (value) => {
        videoBlock.attrs.caption = value;
        markDirty(state);
        renderCanvas(state);
      }, true);
      if (!videoBlock.attrs.path && !videoBlock.attrs.src) {
        appendSelectField(
          bodyEl,
          "YouTube odnos strana",
          videoBlock.settings.aspect || "16:9",
          ["16:9", "4:3"],
          (value) => {
            videoBlock.settings.aspect = value;
            markDirty(state);
            renderCanvas(state);
          },
        );
      }
      appendMediaWidthField(bodyEl, videoBlock, state);
    }

    if (state.selection.type === "faq") {
      appendSelectField(
        bodyEl,
        "Prikaz",
        state.selection.block.attrs.style || "accordion",
        ["accordion", "list"],
        (value) => {
          state.selection.block.attrs.style = value;
          markDirty(state);
          renderCanvas(state);
        },
      );

      const itemsWrap = document.createElement("div");
      itemsWrap.className = "page-builder__faq-items";
      (state.selection.block.attrs.items || []).forEach((item, index) => {
        const itemEl = document.createElement("div");
        itemEl.className = "page-builder__faq-item";

        appendTextField(itemEl, `Pitanje ${index + 1}`, item.question, (value) => {
          item.question = value;
          markDirty(state);
          renderCanvas(state);
        });
        appendTextField(itemEl, `Odgovor ${index + 1}`, item.answer, (value) => {
          item.answer = value;
          markDirty(state);
          renderCanvas(state);
        }, true);

        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.textContent = "Ukloni pitanje";
        removeBtn.addEventListener("click", () => {
          state.selection.block.attrs.items.splice(index, 1);
          markDirty(state);
          renderEditPanel(state);
          renderCanvas(state);
        });
        itemEl.appendChild(removeBtn);
        itemsWrap.appendChild(itemEl);
      });
      bodyEl.appendChild(itemsWrap);

      const addBtn = document.createElement("button");
      addBtn.type = "button";
      addBtn.textContent = "+ Dodaj pitanje";
      addBtn.className = "page-builder__inspector-btn";
      addBtn.addEventListener("click", () => {
        state.selection.block.attrs.items.push({
          question: "Novo pitanje?",
          answer: "Odgovor.",
        });
        markDirty(state);
        renderEditPanel(state);
        renderCanvas(state);
      });
      bodyEl.appendChild(addBtn);
    }

    if (state.selection.type === "button") {
      appendTextField(bodyEl, "Tekst dugmeta", state.selection.block.attrs.label, (value) => {
        state.selection.block.attrs.label = value;
        markDirty(state);
        renderCanvas(state);
      });
      appendTextField(bodyEl, "Link (URL)", state.selection.block.attrs.href, (value) => {
        state.selection.block.attrs.href = value;
        markDirty(state);
        renderCanvas(state);
      });
      appendSelectField(
        bodyEl,
        "Stil",
        state.selection.block.attrs.style || "primary",
        ["primary", "secondary"],
        (value) => {
          state.selection.block.attrs.style = value;
          markDirty(state);
          renderCanvas(state);
        },
      );
    }
  }

  function shouldShowColumnTarget(state, columnId) {
    return (
      state.targetColumnId === columnId &&
      (!state.selection || state.selection.kind === "column")
    );
  }

  function targetColumn(state, column) {
    state.targetColumnId = column.id;
    state.selection = null;
    state.panelBrowse.hidden = false;
    state.panelEdit.hidden = true;
    setPanelTab(state, "widgets");
    renderWidgetGrid(state);
    renderCanvas(state);
  }

  function selectBlock(state, block) {
    selectItem(state, {
      kind: "block",
      id: block.id,
      label: ELEMENT_LABELS[block.type] || block.type,
      settings: block.settings,
      fields: state.catalog.block_settings,
      block,
      type: block.type,
    });
  }

  function isEditableBlock(block) {
    return block.type === "text" || block.type === "heading";
  }

  function placeCaretAtPoint(element, x, y) {
    element.focus();
    let range = null;
    if (document.caretRangeFromPoint) {
      range = document.caretRangeFromPoint(x, y);
    } else if (document.caretPositionFromPoint) {
      const position = document.caretPositionFromPoint(x, y);
      if (position) {
        range = document.createRange();
        range.setStart(position.offsetNode, position.offset);
        range.collapse(true);
      }
    }
    if (!range) {
      return;
    }
    const selection = window.getSelection();
    if (!selection) {
      return;
    }
    selection.removeAllRanges();
    selection.addRange(range);
  }

  function focusEditableBlock(state, blockId, clientX, clientY) {
    requestAnimationFrame(() => {
      const editable = state.canvas.querySelector(
        `.page-builder__block[data-block-id="${blockId}"] [contenteditable="true"]`,
      );
      if (!editable) {
        return;
      }
      if (clientX != null && clientY != null) {
        placeCaretAtPoint(editable, clientX, clientY);
      } else {
        editable.focus();
      }
    });
  }

  function selectItem(state, payload) {
    const previous = state.selection;
    const sameSelection =
      previous &&
      payload &&
      previous.kind === payload.kind &&
      previous.id === payload.id;

    state.selection = payload;
    if (payload && payload.kind === "column") {
      state.targetColumnId = payload.id;
    } else if (payload && payload.kind === "block") {
      const found = findBlock(state, payload.id);
      if (found) {
        state.targetColumnId = found.column.id;
      }
    }

    if (sameSelection) {
      renderPanel(state);
      return;
    }

    renderCanvas(state);
    renderPanel(state);
  }

  function clearSelection(state) {
    state.selection = null;
    renderCanvas(state);
    renderPanel(state);
  }

  function chromeBtn(label, action, className, title) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `vb-chrome-btn ${className || ""}`.trim();
    btn.dataset.action = action;
    btn.textContent = label;
    if (title) {
      btn.title = title;
    }
    return btn;
  }

  async function uploadImage(state, file, block) {
    if (!state.uploadUrl || !file) {
      return { ok: false, message: "Otpremanje nije dostupno." };
    }

    const formData = new FormData();
    formData.append("image", file);

    try {
      const response = await fetch(state.uploadUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-CSRFToken": getCsrfToken() },
        body: formData,
        signal: AbortSignal.timeout(PAGE_SAVE_TIMEOUT_MS),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        return { ok: false, message: "Otpremanje slike nije uspelo." };
      }

      block.attrs.src = data.url;
      block.attrs.path = data.path;
      if (!String(block.attrs.alt || "").trim()) {
        const fromServer = String(data.alt || "").trim();
        const fromFile = String(file.name || "")
          .replace(/\.[^.]+$/, "")
          .replace(/[_-]+/g, " ")
          .trim();
        block.attrs.alt = fromServer || fromFile || "Slika";
      }
      trackSessionUpload(state, "default", data.path);
      markDirty(state);
      renderCanvas(state);
      renderEditPanel(state);
      return { ok: true };
    } catch (_error) {
      return { ok: false, message: "Mrežna greška pri otpremanju slike." };
    }
  }

  async function resolveExistingImage(state, block, draftPath) {
    if (!state.resolveMediaUrl || !block) {
      return { ok: false, message: "Ponovno korišćenje slike nije dostupno." };
    }
    const path = String(draftPath || "").trim();
    if (!path) {
      return { ok: false, message: "Unesite storage path (npr. page/images/...)." };
    }
    try {
      const response = await fetch(state.resolveMediaUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({ path }),
        signal: AbortSignal.timeout(PAGE_SAVE_TIMEOUT_MS),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        return {
          ok: false,
          message: "Putanja nije validna ili fajl nije ispravna slika.",
        };
      }
      block.attrs.path = data.path;
      block.attrs.src = data.url;
      block.attrs.media_asset_id = "";
      markDirty(state);
      renderCanvas(state);
      renderEditPanel(state);
      return { ok: true };
    } catch (_error) {
      return { ok: false, message: "Mrežna greška pri učitavanju postojeće slike." };
    }
  }

  function createVideoPoster(file) {
    return new Promise((resolve) => {
      const objectUrl = URL.createObjectURL(file);
      const video = document.createElement("video");
      let settled = false;

      function finish(result) {
        if (settled) {
          return;
        }
        settled = true;
        window.clearTimeout(timeout);
        URL.revokeObjectURL(objectUrl);
        resolve(result);
      }

      const timeout = window.setTimeout(() => finish(null), 15000);
      video.muted = true;
      video.playsInline = true;
      video.preload = "metadata";
      video.addEventListener("error", () => finish(null), { once: true });
      function captureFrame() {
        if (!video.videoWidth || !video.videoHeight) {
          finish(null);
          return;
        }
        const maxWidth = 1280;
        const scale = Math.min(1, maxWidth / video.videoWidth);
        const width = Math.max(1, Math.round(video.videoWidth * scale));
        const height = Math.max(1, Math.round(video.videoHeight * scale));
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const context = canvas.getContext("2d");
        if (!context) {
          finish(null);
          return;
        }
        context.drawImage(video, 0, 0, width, height);
        canvas.toBlob(
          (blob) => finish(blob ? {
            blob,
            width: video.videoWidth,
            height: video.videoHeight,
          } : null),
          "image/jpeg",
          0.82,
        );
      }
      video.addEventListener("loadedmetadata", () => {
        if (!video.videoWidth || !video.videoHeight) {
          finish(null);
          return;
        }
        const captureAt = Number.isFinite(video.duration) && video.duration > 0
          ? Math.min(1, Math.max(0, video.duration * 0.1))
          : 0;
        if (captureAt > 0.05) {
          video.addEventListener("seeked", captureFrame, { once: true });
          video.currentTime = captureAt;
        } else {
          video.addEventListener("loadeddata", captureFrame, { once: true });
        }
      }, { once: true });
      video.src = objectUrl;
    });
  }

  async function uploadVideoPoster(state, poster, block) {
    if (!poster?.blob || !state.uploadUrl) {
      return;
    }
    const formData = new FormData();
    const filename = `video-poster-${Date.now()}.jpg`;
    formData.append("image", poster.blob, filename);
    try {
      const response = await fetch(state.uploadUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-CSRFToken": getCsrfToken() },
        body: formData,
        signal: AbortSignal.timeout(PAGE_SAVE_TIMEOUT_MS),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        return;
      }
      block.attrs.poster = data.url;
      block.attrs.poster_path = data.path;
      block.attrs.video_width = poster.width;
      block.attrs.video_height = poster.height;
      trackSessionUpload(state, "default", data.path);
      markDirty(state);
      renderCanvas(state);
    } catch (_error) {
      // Poster je poboljšanje; video ostaje validan i ako izdvajanje slike ne uspe.
    }
  }

  function uploadVideo(state, file, block, onProgress) {
    if (!state.videoUploadUrl || !file) {
      return Promise.resolve({ ok: false, message: "Otpremanje videa nije dostupno." });
    }

    const formData = new FormData();
    formData.append("video", file);

    return new Promise((resolve) => {
      const request = new XMLHttpRequest();
      request.open("POST", state.videoUploadUrl);
      request.withCredentials = true;
      request.timeout = VIDEO_UPLOAD_TIMEOUT_MS;
      request.responseType = "json";
      request.setRequestHeader("X-CSRFToken", getCsrfToken());

      request.upload.addEventListener("progress", (event) => {
        if (event.lengthComputable && typeof onProgress === "function") {
          onProgress((event.loaded / event.total) * 100);
        }
      });

      request.addEventListener("load", () => {
        const data = request.response || {};
        if (request.status < 200 || request.status >= 300 || !data.ok) {
          resolve({ ok: false, message: data.error || "Otpremanje videa nije uspelo." });
          return;
        }

        if (typeof onProgress === "function") {
          onProgress(100);
        }
        block.attrs.src = data.url;
        block.attrs.path = data.path;
        block.attrs.url = "";
        trackSessionUpload(state, "default", data.path);
        markDirty(state);
        renderCanvas(state);
        renderEditPanel(state);
        resolve({ ok: true });
      });

      request.addEventListener("error", () => {
        resolve({ ok: false, message: "Mrežna greška pri otpremanju videa." });
      });
      request.addEventListener("timeout", () => {
        resolve({ ok: false, message: "Otpremanje videa je trajalo predugo. Pokušajte ponovo." });
      });
      request.addEventListener("abort", () => {
        resolve({ ok: false, message: "Otpremanje videa je prekinuto." });
      });

      request.send(formData);
    });
  }

  function normalizePlaceholderText(text, placeholder) {
    const value = String(text || "");
    return value.trim() === placeholder ? "" : value;
  }

  function syncEditablePlaceholderRich(element) {
    const isEmpty = !htmlToPlainText(element.innerHTML);
    element.classList.toggle("is-empty", isEmpty);
    if (isEmpty) {
      element.innerHTML = "";
    }
  }

  function bindEditablePlaceholderRich(element, placeholder, onChange) {
    element.dataset.placeholder = placeholder;
    const handleChange = () => {
      syncEditablePlaceholderRich(element);
      onChange(getEditableHtml(element));
    };
    element.addEventListener("input", handleChange);
    element.addEventListener("blur", handleChange);
    syncEditablePlaceholderRich(element);
  }

  function renderBlockPreview(state, block, preview) {
    const align = (block.settings || {}).align || "left";

    if (block.type === "heading") {
      const level = block.attrs.level || 2;
      const heading = document.createElement(`h${level}`);
      heading.className = `iv-page-heading ${blockAlignClass(block, "iv-page-heading")}`;
      heading.contentEditable = "true";
      heading.spellcheck = true;
      setEditableHtml(heading, block.attrs.text || "");
      bindEditablePlaceholderRich(heading, "Unesite naslov…", (value) => {
        block.attrs.text = value;
        markDirty(state);
      });
      bindTextSelectionBookmark(state, block, heading);
      preview.appendChild(heading);
      return;
    }

    if (block.type === "text") {
      const paragraph = document.createElement("p");
      paragraph.className = `iv-page-text ${blockAlignClass(block, "iv-page-text")}`;
      paragraph.contentEditable = "true";
      paragraph.spellcheck = true;
      let text = block.attrs.text || "";
      if (htmlToPlainText(text) === TEXT_BLOCK_PLACEHOLDER) {
        text = "";
      }
      block.attrs.text = text;
      setEditableHtml(paragraph, text);
      bindEditablePlaceholderRich(paragraph, TEXT_BLOCK_PLACEHOLDER, (value) => {
        block.attrs.text = value;
        markDirty(state);
      });
      bindTextSelectionBookmark(state, block, paragraph);
      preview.appendChild(paragraph);
      return;
    }

    if (block.type === "divider") {
      const hr = document.createElement("hr");
      hr.className = "iv-page-divider";
      preview.appendChild(hr);
      return;
    }

    if (block.type === "button") {
      const wrap = document.createElement("div");
      const align = block.settings?.align || "center";
      wrap.className = `iv-page-button-wrap iv-page-button-wrap--align-${align}`;
      const link = document.createElement("span");
      const style = block.attrs.style === "secondary" ? "secondary" : "primary";
      link.className = `btn btn--${style} iv-page-button`;
      link.textContent = block.attrs.label || "Dugme";
      wrap.appendChild(link);
      preview.appendChild(wrap);
      return;
    }

    if (block.type === "image") {
      const scale = document.createElement("div");
      applyMediaWidthStyles(scale, block);
      const wrap = document.createElement("div");
      wrap.className = "page-builder__image-preview";
      if (block.attrs.src) {
        const img = document.createElement("img");
        img.src = block.attrs.src;
        img.alt = block.attrs.alt || "";
        wrap.appendChild(img);
      } else {
        const placeholder = document.createElement("div");
        placeholder.className = "page-builder__widget-placeholder";
        placeholder.innerHTML =
          '<span class="page-builder__widget-placeholder-icon">🖼</span>' +
          "<span>Slika nije dodata</span>";
        wrap.appendChild(placeholder);
      }
      scale.appendChild(wrap);
      preview.appendChild(scale);
      return;
    }

    if (block.type === "video") {
      const fileSrc = block.attrs.src || "";
      const url = block.attrs.url || "";
      const videoId = extractYouTubeId(url);
      const scale = document.createElement("div");
      applyMediaWidthStyles(scale, block);
      if (fileSrc) {
        const wrap = document.createElement("div");
        wrap.className = "page-builder__video-preview page-builder__video-preview--file";
        const video = document.createElement("video");
        video.src = fileSrc;
        video.controls = true;
        video.preload = "metadata";
        video.playsInline = true;
        if (block.attrs.poster) {
          video.poster = block.attrs.poster;
        }
        wrap.appendChild(video);
        scale.appendChild(wrap);
      } else if (videoId) {
        const wrap = document.createElement("div");
        wrap.className = "page-builder__video-preview";
        const iframe = document.createElement("iframe");
        iframe.src = `https://www.youtube.com/embed/${videoId}`;
        iframe.title = block.attrs.caption || "Video";
        iframe.loading = "lazy";
        iframe.allow =
          "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture";
        iframe.allowFullscreen = true;
        wrap.appendChild(iframe);
        scale.appendChild(wrap);
      } else {
        const placeholder = document.createElement("div");
        placeholder.className = "page-builder__video-placeholder";
        placeholder.innerHTML =
          '<span class="page-builder__widget-placeholder-icon">▶</span>' +
          "<span>Video nije dodat</span>";
        scale.appendChild(placeholder);
      }
      preview.appendChild(scale);
      return;
    }

    if (block.type === "faq") {
      const list = document.createElement("div");
      list.className = "page-builder__faq-preview";
      (block.attrs.items || []).forEach((item) => {
        const itemEl = document.createElement("div");
        itemEl.className = "page-builder__faq-preview-item";
        itemEl.innerHTML = `<strong>${item.question || "Pitanje"}</strong><p>${item.answer || "Odgovor"}</p>`;
        list.appendChild(itemEl);
      });
      preview.appendChild(list);
    }
  }

  function bindSectionReorder(state, sectionHandle, sectionIndex) {
    sectionHandle.classList.add("page-builder__drag-handle");

    sectionHandle.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();

      const sections = state.page.sections;
      const draggedSection = sections[sectionIndex];
      if (!draggedSection) {
        return;
      }

      const indicator = document.createElement("div");
      indicator.className = "page-builder__section-drop-indicator";
      indicator.setAttribute("aria-hidden", "true");

      state.root.classList.add("is-dragging");
      sectionHandle.classList.add("is-dragging");

      function getWraps() {
        return Array.from(state.canvas.querySelectorAll(".page-builder__section-wrap"));
      }

      function getInsertIndex(clientY) {
        const wraps = getWraps();
        for (let index = 0; index < wraps.length; index += 1) {
          const rect = wraps[index].getBoundingClientRect();
          if (clientY < rect.top + rect.height / 2) {
            return index;
          }
        }
        return wraps.length;
      }

      function positionIndicator(insertIndex) {
        const wraps = getWraps();
        indicator.remove();
        if (!wraps.length) {
          return;
        }

        const canvasRect = state.canvas.getBoundingClientRect();
        if (insertIndex >= wraps.length) {
          const lastWrap = wraps[wraps.length - 1];
          const rect = lastWrap.getBoundingClientRect();
          indicator.style.top = `${rect.bottom - canvasRect.top + state.canvas.scrollTop}px`;
        } else {
          const targetWrap = wraps[insertIndex];
          const rect = targetWrap.getBoundingClientRect();
          indicator.style.top = `${rect.top - canvasRect.top + state.canvas.scrollTop}px`;
        }

        state.canvas.appendChild(indicator);
      }

      let insertIndex = sectionIndex;

      function onPointerMove(moveEvent) {
        insertIndex = getInsertIndex(moveEvent.clientY);
        positionIndicator(insertIndex);
      }

      function finishReorder() {
        if (insertIndex !== sectionIndex && insertIndex !== sectionIndex + 1) {
          sections.splice(sectionIndex, 1);
          let targetIndex = insertIndex;
          if (targetIndex > sectionIndex) {
            targetIndex -= 1;
          }
          sections.splice(targetIndex, 0, draggedSection);
          markDirty(state);
          renderCanvas(state);
        }
      }

      function cleanup() {
        state.root.classList.remove("is-dragging");
        sectionHandle.classList.remove("is-dragging");
        indicator.remove();
        window.removeEventListener("pointermove", onPointerMove);
        window.removeEventListener("pointerup", onPointerUp);
        window.removeEventListener("pointercancel", onPointerUp);
      }

      function onPointerUp() {
        finishReorder();
        cleanup();
      }

      window.addEventListener("pointermove", onPointerMove);
      window.addEventListener("pointerup", onPointerUp);
      window.addEventListener("pointercancel", onPointerUp);
      onPointerMove(event);
    });
  }

  function bindNestedReorder(state, handle, items, sourceIndex, container, selector, axis) {
    handle.classList.add("page-builder__drag-handle");
    handle.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();

      const draggedItem = items[sourceIndex];
      if (!draggedItem) {
        return;
      }

      let insertIndex = sourceIndex;
      handle.classList.add("is-dragging");
      state.root.classList.add("is-reordering");

      function elements() {
        return Array.from(container.querySelectorAll(`:scope > ${selector}`));
      }

      function clearMarkers() {
        elements().forEach((element) => {
          element.classList.remove("is-drop-before", "is-drop-after");
        });
      }

      function markInsertPosition(index) {
        const nodes = elements();
        clearMarkers();
        if (!nodes.length) {
          return;
        }
        if (index >= nodes.length) {
          nodes[nodes.length - 1].classList.add("is-drop-after");
        } else {
          nodes[index].classList.add("is-drop-before");
        }
      }

      function onPointerMove(moveEvent) {
        const coordinate = axis === "x" ? moveEvent.clientX : moveEvent.clientY;
        const nodes = elements();
        insertIndex = nodes.length;
        for (let index = 0; index < nodes.length; index += 1) {
          const rect = nodes[index].getBoundingClientRect();
          const midpoint = axis === "x"
            ? rect.left + rect.width / 2
            : rect.top + rect.height / 2;
          if (coordinate < midpoint) {
            insertIndex = index;
            break;
          }
        }
        markInsertPosition(insertIndex);
      }

      function cleanup() {
        clearMarkers();
        handle.classList.remove("is-dragging");
        state.root.classList.remove("is-reordering");
        window.removeEventListener("pointermove", onPointerMove);
        window.removeEventListener("pointerup", onPointerUp);
        window.removeEventListener("pointercancel", onPointerUp);
      }

      function onPointerUp() {
        if (insertIndex !== sourceIndex && insertIndex !== sourceIndex + 1) {
          items.splice(sourceIndex, 1);
          let targetIndex = insertIndex;
          if (targetIndex > sourceIndex) {
            targetIndex -= 1;
          }
          items.splice(targetIndex, 0, draggedItem);
          markDirty(state);
          cleanup();
          renderCanvas(state);
          return;
        }
        cleanup();
      }

      window.addEventListener("pointermove", onPointerMove);
      window.addEventListener("pointerup", onPointerUp);
      window.addEventListener("pointercancel", onPointerUp);
      onPointerMove(event);
    });
  }

  function renderCanvas(state) {
    clearTextSelectionState(state);
    state.canvas.innerHTML = "";

    if (!state.page.sections.length) {
      const empty = document.createElement("div");
      empty.className = "page-builder__empty";
      const message = document.createElement("p");
      message.textContent = "Stranica je prazna.";
      const addButton = document.createElement("button");
      addButton.type = "button";
      addButton.className = "page-builder__empty-add";
      addButton.innerHTML = '<span aria-hidden="true">+</span> Dodaj prvu sekciju';
      addButton.addEventListener("click", () => {
        const section = createSection();
        state.page.sections.push(section);
        state.targetColumnId = section.rows[0].columns[0].id;
        markDirty(state);
        renderCanvas(state);
        renderWidgetGrid(state);
      });
      empty.append(message, addButton);
      state.canvas.appendChild(empty);
      return;
    }

    const presetOptions = (state.catalog.row_presets || []).map(
      (preset) => `<option value="${preset.id}">${preset.label}</option>`,
    ).join("");

    state.page.sections.forEach((section, sectionIndex) => {
      const sectionEl = document.createElement("section");
      sectionEl.className = "page-builder__section";
      if (state.selection && state.selection.id === section.id && state.selection.kind === "section") {
        sectionEl.classList.add("is-selected");
      }

      const toolbar = document.createElement("div");
      toolbar.className = "page-builder__section-chrome";
      toolbar.appendChild(chromeBtn("⚙", "select-section", "vb-chrome-btn--icon vb-chrome-btn--accent", "Podešavanja sekcije"));
      toolbar.appendChild(chromeBtn("✕", "delete-section", "vb-chrome-btn--icon vb-chrome-btn--danger", "Obriši sekciju"));
      toolbar.querySelector('[data-action="select-section"]').addEventListener("click", () => {
        selectItem(state, {
          kind: "section",
          id: section.id,
          label: "Sekcija",
          settings: section.settings,
          fields: state.catalog.section_settings,
        });
      });
      toolbar.querySelector('[data-action="delete-section"]').addEventListener("click", () => {
        if (!window.confirm("Obrisati sekciju?")) {
          return;
        }
        state.page.sections = state.page.sections.filter((item) => item.id !== section.id);
        markDirty(state);
        clearSelection(state);
        renderCanvas(state);
      });
      sectionEl.appendChild(toolbar);

      const sectionHandle = document.createElement("div");
      sectionHandle.className = "page-builder__section-handle";
      sectionHandle.textContent = "Sekcija";
      sectionHandle.title = "Prevucite da promenite redosled sekcije";
      bindSectionReorder(state, sectionHandle, sectionIndex);
      sectionEl.appendChild(sectionHandle);

      const previewWrap = document.createElement("div");
      previewWrap.className = "page-builder__section-preview";

      const sectionPreview = document.createElement("div");
      sectionPreview.className = sectionCssClasses(section.settings);
      const sectionStyle = sectionInlineStyle(section.settings);
      if (sectionStyle) {
        sectionPreview.setAttribute("style", sectionStyle);
      } else {
        sectionPreview.removeAttribute("style");
      }

      const sectionInner = document.createElement("div");
      sectionInner.className = "iv-page-section__inner";

      section.rows.forEach((row, rowIndex) => {
        const rowEl = document.createElement("div");
        rowEl.className = "page-builder__row";
        if (state.selection && state.selection.id === row.id && state.selection.kind === "row") {
          rowEl.classList.add("is-selected");
        }

        const currentPreset = detectRowPreset(row);
        const rowToolbar = document.createElement("div");
        rowToolbar.className = "page-builder__row-chrome";
        const rowDragHandle = chromeBtn("↕", "drag-row", "vb-chrome-btn--icon", "Prevucite da promenite redosled reda");
        rowToolbar.appendChild(rowDragHandle);
        rowToolbar.appendChild(chromeBtn("⚙", "select-row", "vb-chrome-btn--icon vb-chrome-btn--accent"));
        const presetSelect = document.createElement("select");
        presetSelect.className = "vb-chrome-select";
        presetSelect.dataset.action = "row-preset";
        presetSelect.innerHTML = presetOptions;
        presetSelect.value = currentPreset;
        rowToolbar.appendChild(presetSelect);
        rowToolbar.appendChild(chromeBtn("✕", "delete-row", "vb-chrome-btn--icon vb-chrome-btn--danger"));
        rowToolbar.querySelector('[data-action="select-row"]').addEventListener("click", () => {
          selectItem(state, {
            kind: "row",
            id: row.id,
            label: "Red",
            settings: row.settings,
            fields: state.catalog.row_settings,
          });
        });
        rowToolbar.querySelector('[data-action="delete-row"]').addEventListener("click", (event) => {
          event.stopPropagation();
          section.rows = section.rows.filter((item) => item.id !== row.id);
          if (state.selection && state.selection.id === row.id) {
            clearSelection(state);
          }
          markDirty(state);
          renderCanvas(state);
        });
        presetSelect.addEventListener("change", (event) => {
          const preset = event.target.value;
          const widths = ROW_PRESETS[preset] || ROW_PRESETS.one;
          const existing = row.columns;
          row.columns = widths.map((width, index) => {
            const column = existing[index] || createColumn(width);
            column.settings.width_desktop = width;
            column.settings.width_tablet = width >= 6 ? width : 12;
            column.settings.width_mobile = 12;
            return column;
          });
          markDirty(state);
          renderCanvas(state);
        });
        rowEl.appendChild(rowToolbar);
        bindNestedReorder(
          state,
          rowDragHandle,
          section.rows,
          rowIndex,
          sectionInner,
          ".page-builder__row",
          "y",
        );

        const columnsEl = document.createElement("div");
        columnsEl.className = `page-builder__columns ${rowCssClasses(row.settings)}`;

        row.columns.forEach((column, columnIndex) => {
          const columnEl = document.createElement("div");
          columnEl.className = `page-builder__column ${columnCssClasses(column.settings)}`;
          if (state.selection && state.selection.id === column.id && state.selection.kind === "column") {
            columnEl.classList.add("is-selected");
          }
          if (shouldShowColumnTarget(state, column.id)) {
            columnEl.classList.add("is-target");
          }

          const columnDragHandle = document.createElement("button");
          columnDragHandle.type = "button";
          columnDragHandle.className = "page-builder__column-drag";
          columnDragHandle.textContent = "↔";
          columnDragHandle.title = "Prevucite da promenite redosled kolone";
          columnDragHandle.setAttribute("aria-label", "Promeni redosled kolone");
          columnEl.appendChild(columnDragHandle);
          bindNestedReorder(
            state,
            columnDragHandle,
            row.columns,
            columnIndex,
            columnsEl,
            ".page-builder__column",
            "x",
          );

          const columnInner = document.createElement("div");
          columnInner.className = "page-builder__column-inner";
          columnInner.addEventListener("click", (event) => {
            if (event.target.closest(".page-builder__block")) {
              return;
            }
            event.stopPropagation();
            targetColumn(state, column);
          });

          if (!column.blocks.length) {
            const emptyCol = document.createElement("div");
            emptyCol.className = "page-builder__column-empty";
            emptyCol.innerHTML =
              '<span class="page-builder__column-empty-icon">⊕</span>' +
              "<span>Kliknite kolonu, zatim izaberite widget u panelu <strong>Elementi</strong></span>";
            columnInner.appendChild(emptyCol);
          }

          column.blocks.forEach((block, blockIndex) => {
            const blockEl = document.createElement("div");
            blockEl.className = "page-builder__block iv-page-block";
            blockEl.dataset.blockId = block.id;
            if (state.selection && state.selection.id === block.id && state.selection.kind === "block") {
              blockEl.classList.add("is-selected");
            }

            const blockToolbar = document.createElement("div");
            blockToolbar.className = "page-builder__block-chrome";
            blockToolbar.appendChild(
              chromeBtn(ELEMENT_LABELS[block.type] || block.type, "select-block", "vb-chrome-btn--accent"),
            );
            blockToolbar.appendChild(chromeBtn("↑", "move-block-up", "vb-chrome-btn--icon"));
            blockToolbar.appendChild(chromeBtn("↓", "move-block-down", "vb-chrome-btn--icon"));
            blockToolbar.appendChild(chromeBtn("✕", "delete-block", "vb-chrome-btn--icon vb-chrome-btn--danger"));
            blockToolbar.querySelector('[data-action="select-block"]').addEventListener("click", () => {
              selectBlock(state, block);
            });
            blockToolbar.querySelector('[data-action="move-block-up"]').addEventListener("click", () => {
              if (blockIndex > 0) {
                const blocks = column.blocks;
                [blocks[blockIndex - 1], blocks[blockIndex]] = [blocks[blockIndex], blocks[blockIndex - 1]];
                markDirty(state);
                renderCanvas(state);
              }
            });
            blockToolbar.querySelector('[data-action="move-block-down"]').addEventListener("click", () => {
              if (blockIndex < column.blocks.length - 1) {
                const blocks = column.blocks;
                [blocks[blockIndex], blocks[blockIndex + 1]] = [blocks[blockIndex + 1], blocks[blockIndex]];
                markDirty(state);
                renderCanvas(state);
              }
            });
            blockToolbar.querySelector('[data-action="delete-block"]').addEventListener("click", () => {
              column.blocks = column.blocks.filter((item) => item.id !== block.id);
              markDirty(state);
              renderCanvas(state);
            });
            blockEl.appendChild(blockToolbar);

            const preview = document.createElement("div");
            preview.className = "page-builder__block-preview";
            renderBlockPreview(state, block, preview);
            blockEl.appendChild(preview);
            blockEl.addEventListener("click", (event) => {
              if (event.target.closest(".page-builder__block-chrome")) {
                return;
              }
              const editableClick = event.target.closest('[contenteditable="true"]');
              const wasSelected =
                state.selection &&
                state.selection.kind === "block" &&
                state.selection.id === block.id;

              if (wasSelected && editableClick) {
                return;
              }

              selectBlock(state, block);

              if (editableClick && isEditableBlock(block)) {
                focusEditableBlock(state, block.id, event.clientX, event.clientY);
              }
            });
            columnInner.appendChild(blockEl);
          });

          columnEl.appendChild(columnInner);
          columnsEl.appendChild(columnEl);
        });

        rowEl.appendChild(columnsEl);
        sectionInner.appendChild(rowEl);
      });

      const addRow = document.createElement("button");
      addRow.type = "button";
      addRow.className = "page-builder__add-row";
      addRow.textContent = "+ Dodaj red";
      addRow.addEventListener("click", () => {
        section.rows.push(createRow("one"));
        markDirty(state);
        renderCanvas(state);
      });
      sectionInner.appendChild(addRow);

      sectionPreview.appendChild(sectionInner);
      previewWrap.appendChild(sectionPreview);
      sectionEl.appendChild(previewWrap);

      const sectionWrap = document.createElement("div");
      sectionWrap.className = "page-builder__section-wrap";

      const sectionInsert = document.createElement("div");
      sectionInsert.className = "page-builder__section-insert";
      const insertBtn = document.createElement("button");
      insertBtn.type = "button";
      insertBtn.className = "page-builder__section-insert-btn";
      insertBtn.title = "Ubaci sekciju iznad";
      insertBtn.textContent = "+";
      insertBtn.addEventListener("click", () => {
        const section = createSection();
        state.page.sections.splice(sectionIndex, 0, section);
        state.targetColumnId = section.rows[0].columns[0].id;
        markDirty(state);
        renderCanvas(state);
        renderWidgetGrid(state);
      });
      sectionInsert.appendChild(insertBtn);
      sectionWrap.appendChild(sectionInsert);
      sectionWrap.appendChild(sectionEl);
      state.canvas.appendChild(sectionWrap);
    });
  }

  async function savePageContent(state, options) {
    const force = options && options.force === true;
    if (state.activeMediaUploads > 0) {
      return {
        ok: false,
        message: "Sačekajte da se otpremanje medija završi, pa pokušajte ponovo.",
      };
    }
    if (!force && !state.dirty) {
      return { ok: true, code: "clean" };
    }

    state.saving = true;
    setSaveStatus(state.postRoot, "saving");

    try {
      const response = await fetch(state.pageSaveUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({
          body_page: state.page,
          expected_page_version: state.pageVersion,
        }),
        signal: AbortSignal.timeout(PAGE_SAVE_TIMEOUT_MS),
      });

      const data = await response.json();
      if (response.status === 409) {
        state.pageVersion = data.page_version;
        setSaveStatus(state.postRoot, "conflict");
        return {
          ok: false,
          code: "version_conflict",
          message: data.message || "Sadržaj je izmenjen u drugoj sesiji. Jezik nije promenjen; osvežite stranicu pre ponovnog pokušaja.",
        };
      }
      if (!response.ok || !data.ok) {
        setSaveStatus(state.postRoot, "error");
        return {
          ok: false,
          message: (data.messages || []).join("\n") || data.message || data.error || "Greška pri čuvanju.",
        };
      }

      state.pageVersion = data.page_version;
      state.dirty = false;
      if (state.documents && state.documents[state.locale]) {
        state.documents[state.locale].page = state.page;
        state.documents[state.locale].page_version = state.pageVersion;
        state.documents[state.locale].dirty = false;
      }
      await cleanupPendingUploadsAfterSave(state);
      setSaveStatus(state.postRoot, "saved");
      return { ok: true };
    } catch (_error) {
      setSaveStatus(state.postRoot, "error");
      return { ok: false, message: "Mrežna greška pri čuvanju." };
    } finally {
      state.saving = false;
    }
  }

  async function switchLocale(state, locale, options = {}) {
    if (!state.documents || !state.documents[locale]) {
      return { ok: false, message: "Izabrani jezik nije dostupan." };
    }
    if (locale === state.locale) {
      return { ok: true, code: "already_active" };
    }
    if (state.switching) {
      return { ok: false, message: "Promena jezika je već u toku." };
    }

    state.switching = true;
    const localeButtons = state.postRoot.querySelectorAll("[data-builder-locale]");
    localeButtons.forEach((button) => {
      button.disabled = true;
    });

    try {
      const currentDocument = state.documents[state.locale];
      currentDocument.page = state.page;
      currentDocument.page_version = state.pageVersion;
      currentDocument.dirty = state.dirty;

      const result = await savePageContent(state);
      if (!result.ok) {
        showBlocker(
          state.postRoot,
          result.message || "Trenutni sadržaj nije sačuvan. Promena jezika je zaustavljena.",
        );
        return result;
      }

      const documentState = state.documents[locale];
      const blocker = state.postRoot.querySelector("[data-page-blocker]");
      if (blocker) {
        blocker.hidden = true;
      }
      state.locale = locale;
      state.page = documentState.page || emptyPage();
      state.pageVersion = Number(documentState.page_version || 0);
      state.pageSaveUrl = documentState.save_url;
      state.dirty = Boolean(documentState.dirty);
      state.selection = null;
      state.targetColumnId = null;
      state.root.dataset.pageSaveUrl = state.pageSaveUrl;
      state.root.dataset.pageVersion = String(state.pageVersion);

      const localeInput = state.postRoot.querySelector('[name="_builder_locale"]');
      if (localeInput) localeInput.value = locale;
      const preview = state.postRoot.querySelector("[data-builder-preview]");
      if (preview) preview.href = documentState.preview_url;
      localeButtons.forEach((button) => {
        const active = button.dataset.builderLocale === locale;
        button.classList.toggle("active", active);
        button.setAttribute("aria-selected", active ? "true" : "false");
      });

      renderCanvas(state);
      renderPanel(state);
      syncPlaintextField(extractPlaintext(state.page));
      setSaveStatus(state.postRoot, state.dirty ? "dirty" : "saved");
      state.postRoot.dispatchEvent(new CustomEvent("page-builder:locale-changed", {
        bubbles: true,
        detail: { locale, document: documentState },
      }));
      if (options.updateUrl !== false && window.history?.pushState) {
        const url = new URL(window.location.href);
        url.searchParams.set("locale", locale);
        window.history.pushState({ builderLocale: locale }, "", url);
      }
      return { ok: true, locale };
    } finally {
      state.switching = false;
      localeButtons.forEach((button) => {
        button.disabled = false;
      });
    }
  }

  function mount(root) {
    if (root.pageBuilderState) {
      return;
    }
    const postRoot = root.closest("[data-page-editor]");
    if (!postRoot || !root.dataset.pageSaveUrl) {
      return;
    }

    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = "image/jpeg,image/png,image/webp,image/gif";
    fileInput.hidden = true;
    root.appendChild(fileInput);

    const videoFileInput = document.createElement("input");
    videoFileInput.type = "file";
    videoFileInput.accept = "video/mp4,video/webm,video/quicktime";
    videoFileInput.hidden = true;
    root.appendChild(videoFileInput);

    const documents = readJsonScript("page-builder-documents", null);
    const locale = postRoot.querySelector('[name="_builder_locale"]')?.value || "sr-latn";
    const initialDocument = documents && documents[locale];
    const state = {
      root,
      postRoot,
      canvas: root.querySelector("[data-builder-canvas]"),
      panelBrowse: root.querySelector("[data-builder-panel-browse]"),
      panelEdit: root.querySelector("[data-builder-panel-edit]"),
      panelWidgets: root.querySelector("[data-builder-panel-widgets]"),
      panelNavigator: root.querySelector("[data-builder-panel-navigator]"),
      panelEditTitle: root.querySelector("[data-builder-panel-edit-title]"),
      inspectorBody: root.querySelector("[data-builder-inspector-body]"),
      pageSaveUrl: initialDocument?.save_url || root.dataset.pageSaveUrl,
      uploadUrl: root.dataset.uploadUrl || "",
      videoUploadUrl: root.dataset.videoUploadUrl || "",
      cleanupPendingUrl: root.dataset.cleanupPendingUrl || "",
      resolveMediaUrl: root.dataset.resolveMediaUrl || "",
      pageVersion: Number(initialDocument?.page_version ?? root.dataset.pageVersion ?? 0),
      page: initialDocument?.page || readJsonScript("page-builder-initial-page", emptyPage()),
      documents,
      locale,
      catalog: readJsonScript("page-builder-catalog", {
        section_settings: [],
        row_settings: [],
        column_settings: [],
        block_settings: [],
        row_presets: [],
        elements: [],
      }),
      panelTab: "widgets",
      targetColumnId: null,
      dirty: false,
      saving: false,
      switching: false,
      activeMediaUploads: 0,
      sessionUploads: new Map(),
      abandonCleanupSent: false,
      selection: null,
      pendingImageBlock: null,
      pendingVideoBlock: null,
      videoUploadProgress: null,
      fileInput,
      videoFileInput,
    };

    const initialUrl = new URL(window.location.href);
    const urlLocale = initialUrl.searchParams.get("locale");
    const normalizedLocale = urlLocale && state.documents?.[urlLocale] ? urlLocale : "sr-latn";
    if (urlLocale !== normalizedLocale && window.history?.replaceState) {
      initialUrl.searchParams.set("locale", normalizedLocale);
      window.history.replaceState({ builderLocale: normalizedLocale }, "", initialUrl);
    }

    root.querySelectorAll("[data-panel-tab]").forEach((btn) => {
      btn.addEventListener("click", () => setPanelTab(state, btn.dataset.panelTab));
    });

    root.querySelector("[data-builder-panel-back]")?.addEventListener("click", () => {
      clearSelection(state);
    });

    postRoot.querySelectorAll("[data-builder-locale]").forEach((button) => {
      button.addEventListener("click", () => {
        switchLocale(state, button.dataset.builderLocale);
      });
    });

    state.popStateHandler = () => {
      const url = new URL(window.location.href);
      const urlLocale = url.searchParams.get("locale");
      const requestedLocale = urlLocale && state.documents?.[urlLocale] ? urlLocale : "sr-latn";
      if (urlLocale !== requestedLocale && window.history?.replaceState) {
        url.searchParams.set("locale", requestedLocale);
        window.history.replaceState({ builderLocale: requestedLocale }, "", url);
      }
      if (requestedLocale !== state.locale) {
        switchLocale(state, requestedLocale, { updateUrl: false }).then((result) => {
          if (!result.ok && window.history?.replaceState) {
            const restoredUrl = new URL(window.location.href);
            restoredUrl.searchParams.set("locale", state.locale);
            window.history.replaceState({ builderLocale: state.locale }, "", restoredUrl);
          }
        });
      }
    };
    window.addEventListener("popstate", state.popStateHandler);

    fileInput.addEventListener("change", async () => {
      const file = fileInput.files && fileInput.files[0];
      fileInput.value = "";
      if (!file || !state.pendingImageBlock) {
        return;
      }
      state.activeMediaUploads += 1;
      try {
        const result = await uploadImage(state, file, state.pendingImageBlock);
        if (!result.ok) {
          showToast(state.root, result.message, true);
        }
      } finally {
        state.activeMediaUploads = Math.max(0, state.activeMediaUploads - 1);
      }
    });

    videoFileInput.addEventListener("change", async () => {
      const file = videoFileInput.files && videoFileInput.files[0];
      videoFileInput.value = "";
      if (!file || !state.pendingVideoBlock) {
        return;
      }
      const block = state.pendingVideoBlock;
      state.pendingVideoBlock = null;
      state.activeMediaUploads += 1;
      try {
        updateVideoUploadProgress(state, block, 0);
        renderEditPanel(state);
        const poster = await createVideoPoster(file);
        if (!poster) {
          state.videoUploadProgress = null;
          if (state.selection?.block?.id === block.id) {
            renderEditPanel(state);
          }
          showToast(
            state.root,
            "Video format ili kodek nije podržan u pregledaču. Koristite MP4 (H.264) ili WebM.",
            true,
          );
          return;
        }
        const result = await uploadVideo(
          state,
          file,
          block,
          (percent) => updateVideoUploadProgress(state, block, percent),
        );
        state.videoUploadProgress = null;
        if (state.selection?.block?.id === block.id) {
          renderEditPanel(state);
        }
        if (!result.ok) {
          showToast(state.root, result.message, true);
        } else {
          await uploadVideoPoster(state, poster, block);
          if (state.selection?.block?.id === block.id) {
            renderEditPanel(state);
          }
          showToast(state.root, "Video fajl je uspešno otpremljen.");
        }
      } finally {
        state.activeMediaUploads = Math.max(0, state.activeMediaUploads - 1);
      }
    });

    root.querySelector("[data-builder-add-section]")?.addEventListener("click", () => {
      const section = createSection();
      state.page.sections.push(section);
      state.targetColumnId = section.rows[0].columns[0].id;
      markDirty(state);
      renderCanvas(state);
      renderWidgetGrid(state);
    });

    renderCanvas(state);
    renderPanel(state);

    syncPlaintextField(extractPlaintext(state.page));
    setSaveStatus(postRoot, "saved");
    initAbandonUploadCleanup(state, postRoot);

    if (root.dataset.focusTitle === "1") {
      document.getElementById("blog-post-title-input")?.focus();
    }

    state.beforeUnloadHandler = (event) => {
      if (state.dirty) {
        event.preventDefault();
        event.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", state.beforeUnloadHandler);

    postRoot.pageBuilderState = state;
    window.PageBuilderGlue = {
      flushBeforeSubmit(currentState) {
        return savePageContent(currentState || state, { force: true });
      },
      abandonPendingUploads(currentState) {
        return abandonPendingUploads(currentState || state);
      },
      switchLocale(currentState, localeCode, options) {
        return switchLocale(currentState || state, localeCode, options);
      },
      getDocuments(currentState) {
        return (currentState || state).documents;
      },
      showBlocker,
    };
  }

  function init() {
    document.querySelectorAll("[data-page-builder]").forEach(mount);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
