(function exposeCellLayout(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.HFPSSCellLayout = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createCellLayout() {
  "use strict";

  const clampValue = (value, minimum, maximum) => Math.max(minimum, Math.min(maximum, value));

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
    const edgeInset = clampValue(cell * 0.08, 0.45, 4);
    const usableSpan = Math.max(0.5, cell - 2 * edgeInset);
    const collisionGap = clampValue(cell * 0.05, 0.45, 2);
    const largestRequestedSize = Math.max(...ordered.map((record) => Math.max(0.5, Number(record.size) || 5.5)));
    const sizeLimitForSlots = (slots) => slots > 1
      ? (usableSpan - collisionGap * (slots - 1)) / (2 * slots)
      : usableSpan / 2;
    const maximumPackedSize = Math.max(0.45, Math.min(sizeLimitForSlots(columns), sizeLimitForSlots(rows)));
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
      const size = Math.max(0.45, (Number(record.size) || 5.5) * sizeScale);
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
    const packed = [];
    for (const key of [...cells.keys()].sort()) packed.push(...packCell(cells.get(key), cellSize, options));
    return packed;
  }

  return { packCell, packInstances, stableRecordKey };
});
