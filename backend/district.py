from processor.geo import Area
from .road import CongestionLevel, Link


class District:

    def __init__(self, name: str, area: Area):
        self.name = name
        self.area = area
        self._links: list[Link] = []

    def add_link(self, link: Link) -> None:
        self._links.append(link)

    @property
    def links(self) -> list[Link]:
        return list(self._links)

    def _measured(self) -> list[Link]:
        return [l for l in self._links if l.congestion is not CongestionLevel.UNKNOWN]

    @property
    def congestion_score(self) -> float | None:
        measured = self._measured()
        total = sum(l.length_m for l in measured)
        if total == 0:
            return None
        return sum(l.congestion.score * l.length_m for l in measured) / total

    @property
    def congestion(self) -> CongestionLevel:
        return CongestionLevel.from_score(self.congestion_score)

    @property
    def average_speed(self) -> float | None:
        measured = [l for l in self._links if l.speed is not None]
        total = sum(l.length_m for l in measured)
        if total == 0:
            return None
        return sum(l.speed * l.length_m for l in measured) / total

    def level_counts(self) -> dict[CongestionLevel, int]:
        counts = {level: 0 for level in CongestionLevel}
        for link in self._links:
            counts[link.congestion] += 1
        return counts

    def __repr__(self) -> str:
        return f"District({self.name}, 도로 {len(self._links)}개, {self.congestion.label})"
