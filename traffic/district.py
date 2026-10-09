"""자치구와 구 단위 정체도."""

from .geo import Area
from .road import CongestionLevel, Link


class District:
    """
    서울의 자치구 하나.
    구에 속한 도로(Link)들을 가지고 있고(구성, composition),
    그 도로들의 정체도를 모아 구 전체의 정체도를 계산한다.
    """

    def __init__(self, name: str, area: Area):
        self.name = name
        self.area = area
        self._links: list[Link] = []

    def add_link(self, link: Link) -> None:
        self._links.append(link)

    @property
    def links(self) -> list[Link]:
        return list(self._links)       # 복사본을 돌려줘서 바깥에서 목록을 망가뜨리지 못하게 함

    def _measured(self) -> list[Link]:
        return [l for l in self._links if l.congestion is not CongestionLevel.UNKNOWN]

    @property
    def congestion_score(self) -> float | None:
        """
        구 정체 점수 (0=원활 ~ 2=정체).
        도로마다 원활 0 / 서행 1 / 정체 2점을 주고 도로 길이로 가중평균한다.
        도시고속도로와 일반도로의 기준 속도가 달라서 속도 평균 대신 이 방식을 쓴다.
        """
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
        """길이 가중 평균 속도 (참고 정보로 표시)."""
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
