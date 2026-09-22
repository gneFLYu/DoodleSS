/* Exact F4 subspaces and quotients. Basis vectors are ROW vectors in one
 * fixed ambient basis. Integer encoding: 0, 1, zeta=2, zeta^2=3.
 * Unspecified differential directions remain unknown, never silently zero.
 */
(function (root, factory) {
  "use strict";
  const api = factory();
  root.HFPSSGradedQuotient = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis, function () {
  "use strict";

  function scalar(value) {
    if (Number.isInteger(value) && value >= 0 && value <= 3) return value;
    if (typeof value !== "string") throw new TypeError("Expected an F4 scalar.");
    const name = value.trim().toLowerCase().replace(/\\zeta|ζ/g, "zeta")
      .replace(/\^\{2\}|\^2|²/g, "2").replace(/\s/g, "");
    const names = {"0": 0, "1": 1, "2": 2, "3": 3, z: 2, zeta: 2,
      z2: 3, zeta2: 3, "1+zeta": 3, "zeta+1": 3};
    if (!Object.prototype.hasOwnProperty.call(names, name)) throw new TypeError("Unknown F4 scalar: " + value);
    return names[name];
  }
  const multiply = (a, b) => {
    const x = a & 1, y = a >> 1, u = b & 1, v = b >> 1;
    return ((x & u) ^ (y & v)) | (((x & v) ^ (y & u) ^ (y & v)) << 1);
  };
  const add = (a, b) => scalar(a) ^ scalar(b);
  const mul = (a, b) => multiply(scalar(a), scalar(b));
  function inverse(value) {
    const a = scalar(value);
    if (!a) throw new RangeError("Zero is not invertible in F4.");
    return multiply(a, a);
  }
  function size(value, name) {
    if (!Number.isInteger(value) || value < 0) throw new RangeError(name + " must be a nonnegative integer.");
    return value;
  }
  function vector(values, dimension) {
    if (!Array.isArray(values) || values.length !== dimension) throw new RangeError("Expected " + dimension + " coordinates.");
    return values.map(scalar);
  }
  const copyRows = rows => rows.map(row => row.slice());
  const zero = n => Array(n).fill(0);
  const identity = n => Array.from({length: n}, (_, i) => Array.from({length: n}, (_, j) => Number(i === j)));
  const isZero = row => row.every(a => a === 0);

  function matrix(values, columns) {
    if (!Array.isArray(values)) throw new TypeError("Expected an array of matrix rows.");
    const n = columns === undefined ? (values.length ? values[0].length : 0) : size(columns, "columns");
    return {rows: values.map(row => vector(row, n)), columns: n};
  }

  // Pivot only in the domain when an augmented map is being reduced.
  function eliminate(values, columns, pivotLimit, withTransform) {
    const parsed = matrix(values, columns), rows = parsed.rows;
    const transforms = withTransform ? identity(rows.length) : null;
    const pivots = [];
    for (let column = 0; column < pivotLimit && pivots.length < rows.length; column++) {
      const pivotRow = pivots.length;
      let selected = pivotRow;
      while (selected < rows.length && rows[selected][column] === 0) selected++;
      if (selected === rows.length) continue;
      [rows[pivotRow], rows[selected]] = [rows[selected], rows[pivotRow]];
      if (transforms) [transforms[pivotRow], transforms[selected]] = [transforms[selected], transforms[pivotRow]];
      const scale = inverse(rows[pivotRow][column]);
      rows[pivotRow] = rows[pivotRow].map(a => multiply(a, scale));
      if (transforms) transforms[pivotRow] = transforms[pivotRow].map(a => multiply(a, scale));
      for (let row = 0; row < rows.length; row++) {
        const factor = row === pivotRow ? 0 : rows[row][column];
        if (!factor) continue;
        rows[row] = rows[row].map((a, j) => a ^ multiply(factor, rows[pivotRow][j]));
        if (transforms) transforms[row] = transforms[row].map((a, j) => a ^ multiply(factor, transforms[pivotRow][j]));
      }
      pivots.push(column);
    }
    return {rows, pivots, rank: pivots.length, columns: parsed.columns, transforms};
  }

  function rref(values, options = {}) {
    const n = matrix(values, options.columns).columns;
    const result = eliminate(values, n, n, false);
    delete result.transforms;
    return result;
  }
  function span(vectors, dimension) {
    const result = rref(vectors, {columns: dimension});
    return result.rows.slice(0, result.rank);
  }
  function combine(basis, coordinates, dimension) {
    const result = zero(dimension);
    coordinates.forEach((coefficient, i) => {
      for (let j = 0; j < dimension; j++) result[j] ^= multiply(coefficient, basis[i][j]);
    });
    return result;
  }
  function reduce(values, basis) {
    const input = vector(values, values.length);
    const echelon = eliminate(basis, input.length, input.length, true);
    const canonical = echelon.rows.slice(0, echelon.rank);
    const remainder = input.slice(), coordinates = zero(echelon.rank);
    for (let i = 0; i < echelon.rank; i++) {
      const coefficient = remainder[echelon.pivots[i]];
      coordinates[i] = coefficient;
      for (let j = 0; j < input.length; j++) remainder[j] ^= multiply(coefficient, canonical[i][j]);
    }
    return {inSpan: isZero(remainder), remainder, coordinates, basis: canonical,
      inputCoordinates: combine(echelon.transforms.slice(0, echelon.rank), coordinates, basis.length)};
  }
  function nullspace(values, options = {}) {
    const result = rref(values, options), basis = [];
    for (let free = 0; free < result.columns; free++) {
      if (result.pivots.includes(free)) continue;
      const row = zero(result.columns);
      row[free] = 1;
      result.pivots.forEach((pivot, i) => { row[pivot] = result.rows[i][free]; });
      basis.push(row);
    }
    return basis;
  }

  function quotient({ambientDimension, cycles, boundaries}) {
    const n = size(ambientDimension, "ambientDimension");
    const cycleBasis = span(cycles, n), boundaryBasis = span(boundaries, n);
    if (boundaryBasis.some(row => !reduce(row, cycleBasis).inSpan)) {
      throw new RangeError("Incoming boundaries are not contained in known cycles (d_r^2 != 0).");
    }
    const combined = copyRows(boundaryBasis), representatives = [];
    for (const row of cycleBasis) {
      if (!reduce(row, combined).inSpan) {
        representatives.push(row.slice());
        combined.push(row.slice());
      }
    }
    const dimension = representatives.length;
    // A fixed linear extension to the ambient space. Its quotient meaning
    // is restricted to cycleBasis; project() checks that domain explicitly.
    const images = identity(n).map(row => reduce(row, combined).inputCoordinates.slice(boundaryBasis.length));
    const projectionMatrix = Array.from({length: dimension}, (_, i) => images.map(row => row[i]));
    const lift = coordinates => combine(representatives, vector(coordinates, dimension), n);
    const tryProject = values => {
      const v = vector(values, n);
      if (!reduce(v, cycleBasis).inSpan) return {inCycles: false, coordinates: null, representative: null};
      const coordinates = reduce(v, combined).inputCoordinates.slice(boundaryBasis.length);
      return {inCycles: true, coordinates, representative: lift(coordinates)};
    };
    return {
      ambientDimension: n, dimension, cycleDimension: cycleBasis.length, boundaryDimension: boundaryBasis.length,
      cycleBasis: copyRows(cycleBasis), boundaryBasis: copyRows(boundaryBasis),
      representatives: copyRows(representatives), projectionMatrix: copyRows(projectionMatrix),
      project(values) {
        const result = tryProject(values);
        if (!result.inCycles) throw new RangeError("Cannot project a vector outside the known cycle subspace.");
        return result.coordinates;
      },
      tryProject,
      lift,
    };
  }

  function partialMap({sourceDimension, targetDimension, constraints}) {
    const n = size(sourceDimension, "sourceDimension"), m = size(targetDimension, "targetDimension");
    if (!Array.isArray(constraints)) throw new TypeError("Expected an array of linear constraints.");
    const normalized = constraints.map(item => ({id: item.id ?? null, source: vector(item.source, n), target: vector(item.target, m)}));
    const reduced = eliminate(normalized.map(item => item.source.concat(item.target)), n + m, n, true);
    const conflicts = [];
    for (let i = reduced.rank; i < reduced.rows.length; i++) {
      const residual = reduced.rows[i].slice(n);
      if (!isZero(residual)) conflicts.push({
        combination: reduced.transforms[i].slice(), constraintIds: normalized.map(item => item.id),
        targetResidual: residual,
      });
    }
    const domainBasis = reduced.rows.slice(0, reduced.rank).map(row => row.slice(0, n));
    const images = reduced.rows.slice(0, reduced.rank).map(row => row.slice(n));
    const consistent = conflicts.length === 0;
    const imageEquations = Array.from({length: m}, (_, j) => images.map(row => row[j]));
    const kernel = consistent
      ? span(nullspace(imageEquations, {columns: domainBasis.length}).map(row => combine(domainBasis, row, n)), n)
      : null;
    return {
      consistent, conflicts, sourceDimension: n, targetDimension: m,
      domainDimension: domainBasis.length, domainBasis: copyRows(domainBasis),
      images: consistent ? copyRows(images) : null,
      knownKernelBasis: kernel === null ? null : copyRows(kernel),
      knownImageBasis: consistent ? span(images, m) : null,
      isTotal: consistent && domainBasis.length === n,
      evaluate(values) {
        const v = vector(values, n);
        if (!consistent) return {defined: false, value: null, reason: "inconsistent-constraints"};
        const reducedVector = reduce(v, domainBasis);
        if (!reducedVector.inSpan) return {defined: false, value: null, reason: "outside-defined-subspace"};
        return {defined: true, value: combine(images, reducedVector.inputCoordinates, m)};
      },
    };
  }

  return Object.freeze({scalar, add, mul, inverse, vector, rref, span, reduce, nullspace, quotient, partialMap});
});
