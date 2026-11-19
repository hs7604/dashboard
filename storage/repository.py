"""파일 저장/불러오기. 다른 클래스는 파일 형식을 몰라도 되도록 여기서만 다룬다."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from backend.config import Settings
from backend.district import District
from processor.geo import Area
from backend.road import Link


@dataclass
class TrafficSnapshot:
    """특정 시각에 수집한 전체 도로 속도."""

    collected_at: datetime
    speeds: dict[str, tuple[float, int]] = field(default_factory=dict)  # link_id → (속도, 통행시간)

    def apply_to(self, links: list[Link]) -> None:
        """수집한 속도를 도로 객체들에 반영한다."""
        for link in links:
            link.update_traffic(*self.speeds.get(link.link_id, (None, None)))

    def save(self, path: Path) -> None:
        data = {"collected_at": self.collected_at.isoformat(), "speeds": self.speeds}
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "TrafficSnapshot":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            collected_at=datetime.fromisoformat(data["collected_at"]),
            speeds={k: tuple(v) for k, v in data["speeds"].items()},
        )


class LinkRepository:
    """도로망(links.geojson)과 구 경계(seoul_gu.geojson) 파일을 다룬다."""

    def __init__(self, settings: Settings):
        self._settings = settings

    def save_links(self, links: list[Link]) -> None:
        data = {"type": "FeatureCollection", "features": [l.to_feature() for l in links]}
        self._settings.links_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def load_links(self) -> list[Link]:
        data = json.loads(self._settings.links_file.read_text(encoding="utf-8"))
        return [Link.from_feature(f) for f in data["features"]]

    def load_districts(self) -> list[District]:
        data = json.loads(self._settings.gu_file.read_text(encoding="utf-8"))
        districts = []
        for f in data["features"]:
            p = f["properties"]
            districts.append(District(p.get("name") or p.get("SIG_KOR_NM"), Area(f["geometry"])))
        return districts

    def load_network(self) -> tuple[list[District], list[Link]]:
        """구와 도로를 불러와 서로 연결한 뒤 함께 반환한다."""
        districts = self.load_districts()
        links = self.load_links()
        by_name = {d.name: d for d in districts}
        for link in links:
            if link.gu in by_name:
                by_name[link.gu].add_link(link)
        return districts, links
