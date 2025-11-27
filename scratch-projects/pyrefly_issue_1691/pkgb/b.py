from __future__ import annotations

from pkgc.c import PkgC

class PkgB:
    def __init__(self) -> None:
        self.c: PkgC = PkgC(self)
