"""Filesystem-independent boundary for the visible lunar terrain limb."""

from typing import Protocol

from terralab3d.domain.eclipses.models import (
    ApparentEventBody,
    LunarLimbProfile,
)


class LunarLimbProfileProvider(Protocol):
    def profile(
        self,
        moon: ApparentEventBody,
        *,
        sample_count: int = 720,
    ) -> LunarLimbProfile | None: ...

