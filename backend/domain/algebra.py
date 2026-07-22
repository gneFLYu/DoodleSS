"""Small exact algebra primitives used by the HFPSS domain model.

The residue field is deliberately implemented independently of the Witt and
2-adic coefficient contexts.  In particular, this module must never be used
to conclude that ``2 == 0`` in a Witt-valued calculation.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class F4Element:
    """An element ``a + b*zeta`` of F_4, with ``a,b`` in F_2."""

    a: int = 0
    b: int = 0

    def __post_init__(self) -> None:
        if self.a not in (0, 1) or self.b not in (0, 1):
            raise ValueError("F4 coefficients must be bits.")

    @classmethod
    def zero(cls) -> "F4Element":
        return cls(0, 0)

    @classmethod
    def one(cls) -> "F4Element":
        return cls(1, 0)

    @classmethod
    def zeta(cls) -> "F4Element":
        return cls(0, 1)

    @classmethod
    def zeta_squared(cls) -> "F4Element":
        return cls(1, 1)

    @classmethod
    def elements(cls) -> tuple["F4Element", ...]:
        return (cls.zero(), cls.one(), cls.zeta(), cls.zeta_squared())

    @classmethod
    def parse(cls, value: str | int | "F4Element") -> "F4Element":
        if isinstance(value, cls):
            return value
        normalized = str(value).strip().lower().replace("ζ", "zeta").replace("^2", "2")
        lookup = {
            "0": cls.zero(),
            "1": cls.one(),
            "zeta": cls.zeta(),
            "z": cls.zeta(),
            "zeta2": cls.zeta_squared(),
            "z2": cls.zeta_squared(),
            "1+zeta": cls.zeta_squared(),
            "zeta+1": cls.zeta_squared(),
        }
        try:
            return lookup[normalized]
        except KeyError as error:
            raise ValueError(f"Unknown F4 element: {value!r}") from error

    def __add__(self, other: object) -> "F4Element":
        if not isinstance(other, F4Element):
            return NotImplemented
        return F4Element(self.a ^ other.a, self.b ^ other.b)

    def __sub__(self, other: object) -> "F4Element":
        return self + other

    def __neg__(self) -> "F4Element":
        return self

    def __mul__(self, other: object) -> "F4Element":
        if not isinstance(other, F4Element):
            return NotImplemented
        # zeta^2 = zeta + 1 in characteristic two.
        return F4Element(
            (self.a * other.a) ^ (self.b * other.b),
            (self.a * other.b) ^ (self.b * other.a) ^ (self.b * other.b),
        )

    def __pow__(self, exponent: int) -> "F4Element":
        if exponent < 0:
            if self == self.zero():
                raise ZeroDivisionError("Zero is not invertible in F4.")
            return self ** ((exponent % 3) + 3)
        result = self.one()
        factor = self
        power = exponent
        while power:
            if power & 1:
                result = result * factor
            factor = factor * factor
            power >>= 1
        return result

    def inverse(self) -> "F4Element":
        if self == self.zero():
            raise ZeroDivisionError("Zero is not invertible in F4.")
        return self ** 2

    def to_dict(self) -> dict[str, int]:
        return {"a": self.a, "b": self.b}

    def __str__(self) -> str:
        return {
            (0, 0): "0",
            (1, 0): "1",
            (0, 1): "zeta",
            (1, 1): "zeta^2",
        }[(self.a, self.b)]
