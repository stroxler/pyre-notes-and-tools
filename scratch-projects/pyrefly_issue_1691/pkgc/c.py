from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pkgb.b import PkgB


class PkgC:
    def __init__(self, b: PkgB) -> None:
        self.b: PkgB = b
