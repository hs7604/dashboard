import json
import shutil
from pathlib import Path

from processor.clipper import DistrictRoads
from backend.district import District
from storage.repository import TrafficSnapshot
from backend.road import CongestionLevel, Link, UrbanExpressway

TEMPLATE_DIR = Path(__file__).parent / "templates"


class SiteRenderer:

    def __init__(self, out_dir: Path, assets_dir: Path | None = None):
        self._out_dir = out_dir
        self._assets_dir = assets_dir

    @staticmethod
    def _district_dict(d: District, roads: list, index_of: dict[str, int]) -> dict:
        score, speed = d.congestion_score, d.average_speed
        lon, lat = d.area.label_point()
        return {
            "name": d.name,
            "level": d.congestion.name,
            "score": None if score is None else round(score, 2),
            "avg_speed": None if speed is None else round(speed, 1),
            "counts": {lv.name: n for lv, n in d.level_counts().items()},
            "label": [round(lat, 5), round(lon, 5)],
            "geometry": d.area.geometry,
            "roads": [[index_of[link_id], pieces] for link_id, pieces in roads if link_id in index_of],
        }

    @staticmethod
    def _link_dict(l: Link) -> dict:
        return {
            "id": l.link_id,
            "road_name": l.road_name,
            "from": l.st_node_nm,
            "to": l.ed_node_nm,
            "type": l.road_type.name,
            "expressway": isinstance(l.road_type, UrbanExpressway),
            "jam_max": l.road_type.jam_max,
            "slow_max": l.road_type.slow_max,
            "speed": l.speed,
            "travel_time": l.travel_time,
            "length_m": l.length_m,
            "level": l.congestion.name,
        }

    def build_payload(self, districts: list[District], links: list[Link],
                      district_roads: DistrictRoads, snapshot: TrafficSnapshot) -> dict:
        index_of = {l.link_id: i for i, l in enumerate(links)}
        return {
            "updated_at": snapshot.collected_at.strftime("%Y-%m-%d %H:%M"),
            "levels": {lv.name: {"label": lv.label, "color": lv.color, "text": lv.text_color} for lv in CongestionLevel},
            "links": [self._link_dict(l) for l in links],
            "districts": [self._district_dict(d, district_roads.get(d.name, []), index_of) for d in districts],
        }

    def render(self, districts: list[District], links: list[Link],
               district_roads: DistrictRoads, snapshot: TrafficSnapshot) -> Path:
        self._out_dir.mkdir(parents=True, exist_ok=True)
        payload = self.build_payload(districts, links, district_roads, snapshot)

        data_js = "window.TRAFFIC_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n"
        (self._out_dir / "data.js").write_text(data_js, encoding="utf-8")

        version = snapshot.collected_at.strftime("%Y%m%d%H%M%S")
        html = (TEMPLATE_DIR / "index.html").read_text(encoding="utf-8").replace("{{VERSION}}", version)
        (self._out_dir / "index.html").write_text(html, encoding="utf-8")

        if self._assets_dir and self._assets_dir.is_dir():
            for f in self._assets_dir.iterdir():
                if f.is_file():
                    shutil.copy2(f, self._out_dir / f.name)
        return self._out_dir / "index.html"
