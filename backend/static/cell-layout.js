(function exposeCellLayout(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.HFPSSCellLayout = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createCellLayout() {
  "use strict";

  const clampValue = (value, minimum, maximum) => Math.max(minimum, Math.min(maximum, value));
  const DEFAULT_DOT_SIZE_THRESHOLD = 1.5;
  const DEFAULT_DOT_FILL_RATIO = 0.42;
  const DEFAULT_DOT_SHRINK_EXPONENT = 0.65;

  function stableRecordKey(record) {
    const explicitOrder = Number.isFinite(Number(record.order)) ? Number(record.order) : 0;
    return [
      String(explicitOrder).padStart(12, "0"),
      record.periodic ? "1" : "0",
      record.shape === "square" ? "0" : "1",
      String(record.label || ""),
      String(record.key || ""),
    ].join("\u0000");
  }

  function packCell(records, cellSize, options = {}) {
    if (!Array.isArray(records) || !records.length) return [];
    const cell = Math.max(1, Number(cellSize) || 1);
    const baseYOffset = Number.isFinite(Number(options.baseYOffset)) ? Number(options.baseYOffset) : 0.16;
    const baseXOffset = Number.isFinite(Number(options.baseXOffset)) ? Number(options.baseXOffset) : 0.16;
    const ordered = [...records].sort((left, right) => stableRecordKey(left).localeCompare(stableRecordKey(right)));
    const count = ordered.length;
    const rows = Math.ceil(Math.sqrt(count));
    const columns = Math.ceil(count / rows);
    const minimum = options.uniformSize ? 0.01 : 0.45;
    const edgeInset = clampValue(cell * 0.08, minimum, 4);
    const usableSpan = Math.max(0.5, cell - 2 * edgeInset);
    const collisionGap = clampValue(cell * 0.05, minimum, 2);
    const largestRequestedSize = Math.max(...ordered.map((record) => Math.max(options.uniformSize ? minimum : 0.5, Number(record.size) || 5.5)));
    const sizeLimitForSlots = (slots) => slots > 1
      ? (usableSpan - collisionGap * (slots - 1)) / (2 * slots)
      : usableSpan / 2;
    const maximumPackedSize = Math.max(minimum, Math.min(sizeLimitForSlots(columns), sizeLimitForSlots(rows)));
    const sizeScale = Math.min(1, maximumPackedSize / largestRequestedSize);
    const largestPackedSize = largestRequestedSize * sizeScale;
    const minimumSeparation = 2 * largestPackedSize + collisionGap;
    const centerSpan = Math.max(0, usableSpan - 2 * largestPackedSize);
    const maximumStepX = columns > 1 ? centerSpan / (columns - 1) : Number.POSITIVE_INFINITY;
    const maximumStepY = rows > 1 ? centerSpan / (rows - 1) : Number.POSITIVE_INFINITY;
    const stepX = columns > 1
      ? Math.min(maximumStepX, Math.max(cell * baseXOffset, minimumSeparation))
      : 0;
    const stepY = rows > 1
      ? Math.min(maximumStepY, Math.max(cell * baseYOffset, minimumSeparation))
      : 0;
    const neighborDistance = Math.min(...[stepX, stepY].filter((value) => value > 0), Number.POSITIVE_INFINITY);

    return ordered.map((record, index) => {
      const row = Math.floor(index / columns);
      const itemsBeforeRow = row * columns;
      const itemsInRow = Math.min(columns, count - itemsBeforeRow);
      const column = index - itemsBeforeRow;
      const size = Math.max(minimum, (Number(record.size) || 5.5) * sizeScale);
      const dx = (column - (itemsInRow - 1) / 2) * stepX;
      const dy = (row - (rows - 1) / 2) * stepY;
      const maximumHitRadius = Number.isFinite(neighborDistance)
        ? Math.max(size, (neighborDistance - 0.4) / 2)
        : Math.max(size, Math.min(8, cell * 0.45));
      const hitRadius = Math.min(Math.max(size + 1.5, 5), maximumHitRadius);
      return {
        ...record,
        dx,
        dy,
        size,
        hitRadius,
        baseYOffset,
        packIndex: index,
        packCount: count,
      };
    });
  }

  function packInstances(records, cellSize, options = {}) {
    const cells = new Map();
    for (const record of records || []) {
      const key = String(record.cellKey || "");
      if (!cells.has(key)) cells.set(key, []);
      cells.get(key).push(record);
    }
    // One viewport-wide size: an anchor, periodic copy and quotient port
    // are not different kinds of generators merely because of their origin.
    if (options.uniformSize && cells.size) {
      const cell = Math.max(1, Number(cellSize) || 1);
      const envelope = Math.max(1, Number(options.glyphEnvelope) || 1);
      const inset = clampValue(cell * 0.08, 0.01, 4);
      const gap = clampValue(cell * 0.05, 0.01, 2);
      const span = Math.max(0.5, cell - 2 * inset);
      const threshold = Math.max(0.5, Number(options.dotSizeThreshold) || DEFAULT_DOT_SIZE_THRESHOLD);
      const fillRatio = clampValue(Number(options.dotFillRatio) || DEFAULT_DOT_FILL_RATIO, 0.2, 0.48);
      const exponent = Math.max(0.35, Number(options.dotShrinkExponent) || DEFAULT_DOT_SHRINK_EXPONENT);
      const nominalRadius = clampValue(cell * 0.105, 0.55, 7);
      const fillRadius = clampValue(cell * fillRatio / envelope, 0.01, 7);
      const lowZoomBlend = Math.pow(clampValue(nominalRadius / threshold, 0, 1), exponent);
      let radius = nominalRadius < threshold
        ? fillRadius + (nominalRadius - fillRadius) * lowZoomBlend
        : nominalRadius;
      for (const group of cells.values()) {
        const slots = Math.ceil(Math.sqrt(group.length));
        radius = Math.min(radius, Math.max(0.01, (span - gap * (slots - 1)) / (2 * slots * envelope)));
      }
      for (const [key, group] of cells) cells.set(key, group.map(record => ({...record, size: radius * envelope})));
      const packed = [];
      for (const key of [...cells.keys()].sort()) {
        packed.push(...packCell(cells.get(key), cellSize, options).map(record => ({...record, size: record.size / envelope})));
      }
      return packed;
    }
    const packed = [];
    for (const key of [...cells.keys()].sort()) packed.push(...packCell(cells.get(key), cellSize, options));
    return packed;
  }

  return { packCell, packInstances, stableRecordKey };
});
