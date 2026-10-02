(function exposeSidebarLayout(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.HFPSSSidebarLayout = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createSidebarLayout() {
  "use strict";

  const STORAGE_KEY = "hfpss-sidebar-widths-v1";
  const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
  const numeric = (value, fallback) => Number.isFinite(value) ? value : fallback;

  // Reserve chart space even after restoring widths on a smaller screen.
  function fitWidths(width, preferred = {}, rightVisible = true) {
    const leftMin = 180, rightMin = rightVisible ? 220 : 0;
    const budget = Math.max(leftMin + rightMin, numeric(width, 0) - 320);
    let left = clamp(numeric(preferred.left, rightVisible ? 300 : 220), leftMin, 520);
    let right = rightVisible ? clamp(numeric(preferred.right, 380), rightMin, 560) : 0;
    const excess = Math.max(0, left + right - budget);
    const flexible = left - leftMin + right - rightMin;
    if (excess && flexible) {
      const factor = Math.max(0, (flexible - excess) / flexible);
      left = leftMin + (left - leftMin) * factor;
      right = rightMin + (right - rightMin) * factor;
    }
    return {left, right};
  }

  function resizeWidth(side, proposed, current, width, rightVisible) {
    const min = side === "left" ? 180 : 220;
    const other = side === "left" ? current.right : current.left;
    const max = Math.max(min, Math.min(side === "left" ? 520 : 560, width - 320 - other));
    return {...current, [side]: clamp(proposed, min, max), ...(!rightVisible ? {right: 0} : {})};
  }

  function mount(layout, onResize = () => {}) {
    if (!layout || layout.dataset.resizableSidebars) return;
    layout.dataset.resizableSidebars = "true";
    const win = layout.ownerDocument.defaultView;
    const doc = layout.ownerDocument;
    const handles = Array.from(layout.querySelectorAll("[data-sidebar-resizer]"));
    let preferred = {}, current, drag = null, frame = null;
    try {
      const saved = JSON.parse(win.localStorage.getItem(STORAGE_KEY) || "{}");
      if (saved && typeof saved === "object") {
        for (const side of ["left", "right"]) if (Number.isFinite(saved[side])) preferred[side] = saved[side];
      }
    } catch (_) { /* Private browsing or invalid saved preferences: use defaults. */ }
    const rightVisible = () => win.innerWidth > 1040;
    const width = () => layout.getBoundingClientRect().width;
    function paint() {
      const next = fitWidths(width(), preferred, rightVisible());
      const changed = !current || next.left !== current.left || next.right !== current.right;
      current = next;
      layout.style.setProperty("--left-sidebar-width", `${current.left}px`);
      layout.style.setProperty("--right-sidebar-width", `${current.right}px`);
      for (const handle of handles) {
        const side = handle.dataset.sidebarResizer;
        const min = side === "left" ? 180 : 220;
        const max = resizeWidth(side, Infinity, current, width(), rightVisible())[side];
        handle.setAttribute("aria-valuemin", String(min));
        handle.setAttribute("aria-valuemax", String(Math.round(max)));
        handle.setAttribute("aria-valuenow", String(Math.round(current[side])));
        handle.setAttribute("aria-valuetext", `${Math.round(current[side])} pixels`);
      }
      if (changed && frame === null) frame = win.requestAnimationFrame(() => { frame = null; onResize(); });
    }
    function save() {
      try { win.localStorage.setItem(STORAGE_KEY, JSON.stringify(preferred)); } catch (_) { /* Optional preference only. */ }
    }
    function finish(commit) {
      if (!drag) return;
      const previous = drag;
      drag = null;
      previous.handle.classList.remove("is-resizing");
      doc.body.classList.remove("resizing-sidebars");
      if (previous.handle.hasPointerCapture?.(previous.id)) previous.handle.releasePointerCapture(previous.id);
      if (!commit) { preferred = previous.preferred; paint(); }
      else save();
    }
    for (const handle of handles) {
      const side = handle.dataset.sidebarResizer;
      handle.addEventListener("pointerdown", event => {
        if (event.button !== 0 || win.innerWidth <= 780 || (side === "right" && !rightVisible())) return;
        event.preventDefault();
        handle.focus();
        drag = {id: event.pointerId, handle, x: event.clientX, widths: {...current}, preferred: {...preferred}};
        handle.setPointerCapture(event.pointerId);
        handle.classList.add("is-resizing");
        doc.body.classList.add("resizing-sidebars");
      });
      handle.addEventListener("pointermove", event => {
        if (!drag || event.pointerId !== drag.id) return;
        const delta = (event.clientX - drag.x) * (side === "left" ? 1 : -1);
        const next = resizeWidth(side, drag.widths[side] + delta, drag.widths, width(), rightVisible());
        preferred = {...preferred, [side]: next[side]};
        paint();
      });
      handle.addEventListener("pointerup", event => { if (drag?.id === event.pointerId) finish(true); });
      handle.addEventListener("pointercancel", () => finish(false));
      handle.addEventListener("lostpointercapture", () => finish(true));
      handle.addEventListener("dblclick", () => { delete preferred[side]; paint(); save(); });
      handle.addEventListener("keydown", event => {
        if (event.key === "Escape" && drag) { event.preventDefault(); event.stopPropagation(); finish(false); return; }
        if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
        event.preventDefault();
        event.stopPropagation();
        const direction = (event.key === "ArrowRight" ? 1 : -1) * (side === "left" ? 1 : -1);
        const proposed = event.key === "Home" ? -Infinity : event.key === "End" ? Infinity
          : current[side] + direction * (event.shiftKey ? 40 : 10);
        preferred = {...preferred, [side]: resizeWidth(side, proposed, current, width(), rightVisible())[side]};
        paint(); save();
      });
    }
    win.addEventListener("blur", () => finish(true));
    win.addEventListener("resize", () => { finish(true); paint(); });
    if (win.ResizeObserver) new win.ResizeObserver(paint).observe(layout);
    paint();
  }

  return {fitWidths, resizeWidth, mount};
});
