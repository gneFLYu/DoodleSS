/* Exact, display-only F4 bases and bounded polynomial labels.
 * Computational matrices and research records are never rewritten here.
 */
(function (root, factory) {
  "use strict";
  const api = factory(root.HFPSSGradedQuotient
    || (typeof require === "function" ? require("./graded-quotient.js") : null));
  root.HFPSSDisplayBasis = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis, function (L) {
  "use strict";
  if (!L) throw new Error("Exact F4 arithmetic is required.");
  const MAX_DIMENSION = 128, MAX_TERMS = 512, MAX_LENGTH = 2048, MAX_POWER = 256;
  const nonzero = row => row.some(Boolean);

  function create(dimension, preferredRows = []) {
    if (!Number.isInteger(dimension) || dimension < 0 || dimension > MAX_DIMENSION)
      throw new RangeError("Invalid display-basis dimension.");
    if (!Array.isArray(preferredRows) || preferredRows.length > MAX_TERMS)
      throw new RangeError("Invalid preferred display rows.");
    const rows = [];
    const add = values => {
      const row = L.vector(values, dimension);
      if (nonzero(row) && !L.reduce(row, rows).inSpan) rows.push(row);
    };
    preferredRows.forEach(add);
    for (let i = 0; i < dimension; i++)
      add(Array.from({length: dimension}, (_, j) => Number(i === j)));
    const saved = Object.freeze(rows.map(row => Object.freeze(row.slice())));
    return Object.freeze({
      dimension, rows: saved,
      project(values) {
        return L.reduce(L.vector(values, dimension), saved).inputCoordinates;
      },
      lift(coordinates) {
        const result = Array(dimension).fill(0);
        L.vector(coordinates, dimension).forEach((coefficient, i) => {
          for (let j = 0; j < dimension; j++)
            result[j] = L.add(result[j], L.mul(coefficient, saved[i][j]));
        });
        return result;
      },
    });
  }

  // Formatting never chooses a characteristic. F4 sum collection is explicitly
  // requested by combineLabels; ordinary names retain integral/Witt multiples.
  const integral = Object.freeze({
    add(a, b) { const n = a + b; if (!Number.isSafeInteger(n)) throw new RangeError("Coefficient is too large."); return n; },
    mul(a, b) { const n = a * b; if (!Number.isSafeInteger(n)) throw new RangeError("Coefficient is too large."); return n; },
    inverse(a) { if (a !== 1 && a !== -1) throw new RangeError("Only declared units can have negative powers."); return a; },
  });
  // Terms use canonical monomial keys independently of their presentation.
  const key = factors => JSON.stringify([...factors].filter(([, n]) => n).sort(([a], [b]) => a.localeCompare(b)));
  function collect(terms, arithmetic = L) {
    const output = new Map();
    for (const term of terms) {
      const factors = new Map([...term.factors].filter(([, n]) => n));
      if (factors.has("\\zeta")) {
        const n = ((factors.get("\\zeta") % 3) + 3) % 3;
        if (n) factors.set("\\zeta", n); else factors.delete("\\zeta");
      }
      const id = key(factors), previous = output.get(id);
      const coefficient = arithmetic.add(previous?.coefficient || 0, term.coefficient);
      if (coefficient) output.set(id, {coefficient, factors: previous?.factors || factors});
      else output.delete(id);
    }
    if (output.size > MAX_TERMS) throw new RangeError("Too many polynomial terms.");
    return [...output.values()];
  }
  const constant = coefficient => coefficient ? [{coefficient, factors: new Map()}] : [];
  function multiply(left, right, arithmetic = L) {
    if (left.length * right.length > MAX_TERMS) throw new RangeError("Polynomial expansion is too large.");
    return collect(left.flatMap(a => right.map(b => {
      const factors = new Map(a.factors);
      for (const [name, power] of b.factors) {
        const total = (factors.get(name) || 0) + power;
        if (Math.abs(total) > MAX_POWER) throw new RangeError("Power is too large.");
        factors.set(name, total);
      }
      return {coefficient: arithmetic.mul(a.coefficient, b.coefficient), factors};
    })), arithmetic);
  }
  function power(poly, exponent, arithmetic = L) {
    if (exponent < 0) {
      if (poly.length !== 1 || [...poly[0].factors.keys()].some(name => !["D", "\\zeta"].includes(name)))
        throw new RangeError("Negative powers require the declared D unit or an F4 unit.");
      const term = poly[0];
      poly = [{coefficient: arithmetic.inverse(term.coefficient),
        factors: new Map([...term.factors].map(([name, n]) => [name, -n]))}];
      exponent = -exponent;
    }
    let result = constant(1);
    while (exponent) {
      if (exponent % 2) result = multiply(result, poly, arithmetic);
      exponent = Math.floor(exponent / 2);
      if (exponent) poly = multiply(poly, poly, arithmetic);
    }
    return result;
  }
  function parse(label, arithmetic = L) {
    if (typeof label !== "string" || !label.trim() || label.length > MAX_LENGTH)
      throw new TypeError("A bounded nonempty label is required.");
    const text = label.replace(/\\zeta(?![A-Za-z])/g, "ζ")
      .replace(/\\\{/g, "(").replace(/\\\}/g, ")")
      .replace(/\\left(?![A-Za-z])|\\right(?![A-Za-z])|\\,/g, "")
      .replace(/\\cdot(?![A-Za-z])/g, "*").replace(/\s/g, "");
    let position = 0, depth = 0;
    const fail = () => { throw new SyntaxError("Unsupported algebra-label syntax."); };
    function expression() {
      if (++depth > 16) throw new RangeError("Label nesting is too deep.");
      let sign = 1;
      if (text[position] === "+" || text[position] === "-") {
        if (text[position++] === "-" && arithmetic === integral) sign = -1;
      }
      let result = product().map(term => ({...term, coefficient: arithmetic.mul(sign, term.coefficient)}));
      while (text[position] === "+" || text[position] === "-") {
        const negative = text[position++] === "-" && arithmetic === integral;
        const next = product().map(term => ({...term, coefficient: negative ? -term.coefficient : term.coefficient}));
        result = collect([...result, ...next], arithmetic);
      }
      depth--;
      return result;
    }
    function product() {
      let result = constant(1), count = 0, explicit = false;
      while (position < text.length && !"+-)}".includes(text[position])) {
        if (text[position] === "*") {
          if (!count || explicit) fail();
          explicit = true; position++; continue;
        }
        result = multiply(result, atom(), arithmetic); count++; explicit = false;
      }
      if (!count || explicit) fail();
      return result;
    }
    function atom() {
      let result;
      const token = text[position];
      if (token === "(" || token === "{") {
        position++; result = expression();
        if (text[position++] !== (token === "(" ? ")" : "}")) fail();
      } else if (/\d/.test(token || "")) {
        const number = /^\d+/.exec(text.slice(position))[0]; position += number.length;
        if (arithmetic === L && !["0", "1"].includes(number)) throw new SyntaxError("Integer/Witt coefficients are not F4 label scalars.");
        if (!Number.isSafeInteger(Number(number))) throw new RangeError("Coefficient is too large.");
        result = constant(Number(number));
      } else if (token === "ζ") {
        position++; result = arithmetic === L ? constant(2)
          : [{coefficient: 1, factors: new Map([["\\zeta", 1]])}];
      } else if (/[A-Za-z]/.test(token || "")) {
        let name = text[position++];
        if (text[position] === "_") {
          position++;
          if (text[position] === "{") {
            const start = ++position;
            let nesting = 1;
            while (position < text.length && nesting) {
              if (text[position] === "{") nesting++;
              if (text[position] === "}") nesting--;
              if (nesting) position++;
            }
            if (nesting) fail();
            const subscript = text.slice(start, position++);
            if (!subscript || !/^[A-Za-z0-9_\\{}+-]+$/.test(subscript)
                || /\\(?!sigma(?![A-Za-z]))/.test(subscript)) fail();
            name += /^[A-Za-z0-9]$/.test(subscript) ? "_" + subscript : "_{" + subscript + "}";
          } else {
            if (!/[A-Za-z0-9]/.test(text[position] || "")) fail();
            name += "_" + text[position++];
          }
        }
        result = [{coefficient: 1, factors: new Map([[name, 1]])}];
      } else fail();
      if (text[position] === "^") {
        position++;
        const braced = text[position] === "{";
        if (braced) position++;
        const match = /^[+-]?\d+/.exec(text.slice(position));
        if (!match) fail();
        position += match[0].length;
        if (braced && text[position++] !== "}") fail();
        const exponent = Number(match[0]);
        if (!Number.isSafeInteger(exponent) || Math.abs(exponent) > MAX_POWER) fail();
        result = power(result, exponent, arithmetic);
      }
      return result;
    }
    const result = expression();
    if (position !== text.length) fail();
    return result;
  }
  const factorLabel = (name, n) => n === 1 ? name : name + "^{" + n + "}";
  const unitLabel = c => c === 1 ? "" : c === 2 ? "\\zeta" : "\\zeta^{2}";
  const factorOrder = name => ({"\\zeta": -2, j: -1, x: 0, y: 1,
    h_1: 2, h_2: 3, v_1: 4, k: 5, D: 6})[name] ?? (name.startsWith("u_") ? 8 : 1.5);
  const orderedFactors = factors => [...factors].sort(([a], [b]) => factorOrder(a) - factorOrder(b) || a.localeCompare(b));
  const productLabel = factors => orderedFactors(factors).map(([name, n], index, all) =>
    factorLabel(name, n) + (name === "\\zeta" && n === 1 && index < all.length - 1 ? "\\," : "")).join("");
  function format(poly, arithmetic = L) {
    if (!poly.length) return "0";
    const suffix = new Map(), prefix = new Map();
    if (poly.length > 1) for (const [name, n] of poly[0].factors) {
      if (["h_1", "h_2", "v_1", "k", "D"].includes(name) || name.startsWith("u_")) {
        if (poly.every(term => term.factors.get(name) === n)) suffix.set(name, n);
      }
      if (name === "\\zeta" && poly.every(term => term.factors.get(name) === n)) prefix.set(name, n);
    }
    const gcd = (a, b) => { while (b) [a, b] = [b, a % b]; return a; };
    const commonCoefficient = arithmetic === integral && poly.length > 1
      ? poly.reduce((n, term) => gcd(n, Math.abs(term.coefficient)), 0) : 1;
    const body = poly.map((term, index) => {
      const factors = productLabel([...term.factors].filter(([name]) => !suffix.has(name) && !prefix.has(name)));
      if (arithmetic === integral) {
        const coefficient = Math.abs(term.coefficient) / commonCoefficient, sign = term.coefficient < 0 ? "-" : index ? "+" : "";
        return sign + (coefficient !== 1 || !factors ? coefficient : "") + factors;
      }
      return (index ? "+" : "") + unitLabel(term.coefficient) + (term.coefficient !== 1 && factors ? "\\," : "")
        + (factors || (term.coefficient === 1 ? "1" : ""));
    }).join("");
    return (commonCoefficient === 1 ? "" : commonCoefficient) + productLabel(prefix)
      + (poly.length > 1 ? "\\{" + body + "\\}" : body) + productLabel(suffix);
  }
  function normalizeLabel(label) {
    try { return {supported: true, label: format(parse(label, integral), integral)}; }
    catch (error) { return {supported: false, label: null, reason: error.message}; }
  }
  function shiftPeriodFactor(label, symbol, delta) {
    try {
      if (!["D", "k"].includes(symbol) || !Number.isSafeInteger(delta) || Math.abs(delta) > MAX_POWER)
        throw new RangeError("A bounded D or k shift is required.");
      const shifted = parse(label, integral).map(term => {
        const factors = new Map(term.factors), exponent = (factors.get(symbol) || 0) + delta;
        if (Math.abs(exponent) > MAX_POWER || (symbol === "k" && exponent < 0))
          throw new RangeError("Period shift requires an unsupported inverse or exponent.");
        factors.set(symbol, exponent);
        return {...term, factors};
      });
      return {supported: true, label: format(collect(shifted, integral), integral)};
    } catch (error) { return {supported: false, label: null, reason: error.message}; }
  }
  function combineLabels(terms, {coefficientContext} = {}) {
    const unsupported = reason => ({supported: false, label: null, reason});
    if (!["F4", "q8-residue-f4"].includes(coefficientContext))
      return unsupported("Label collection requires an explicit F4 residue-field context.");
    try {
      if (!Array.isArray(terms) || terms.length > MAX_TERMS) throw new RangeError("Invalid label terms.");
      const poly = collect(terms.flatMap(term => {
        const coefficient = L.scalar(term.coefficient);
        return parse(term.label).map(item => ({...item, coefficient: L.mul(coefficient, item.coefficient)}));
      }));
      return {supported: true, label: format(poly),
        terms: poly.map(term => ({coefficient: term.coefficient,
          factors: [...term.factors].map(([name, exponent]) => ({name, exponent}))}))};
    } catch (error) { return unsupported(error.message); }
  }
  return Object.freeze({create, combineLabels, normalizeLabel, shiftPeriodFactor});
});
