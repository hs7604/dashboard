"""도로망과 실시간 속도로 웹사이트(site/index.html, site/data.js)를 만든다."""

import json
import shutil
from pathlib import Path

from .clipper import DistrictRoads
from .district import District
from .repository import TrafficSnapshot
from .road import CongestionLevel, Link, UrbanExpressway

TEMPLATE_DIR = Path(__file__).parent / "templates"


class SiteRenderer:
    """
    파이썬 객체(District, Link)를 웹 페이지가 읽을 데이터로 바꾸고 사이트 파일을 쓴다.
    정체도 판정은 전부 파이썬 클래스에서 끝내고, 웹 페이지는 결과를 그리기만 한다.
    """

    def __init__(self, out_dir: Path, assets_dir: Path | None = None):
        self._out_dir = out_dir
        self._assets_dir = assets_dir

    # ---- 객체 → 딕셔너리 ------------------------------------------------
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
            # 이 구 경계 안에서 잘라낸 도로 조각: [링크 번호, [선, ...]]
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

    # ---- 파일 쓰기 ------------------------------------------------------
    def render(self, districts: list[District], links: list[Link],
               district_roads: DistrictRoads, snapshot: TrafficSnapshot) -> Path:
        self._out_dir.mkdir(parents=True, exist_ok=True)
        payload = self.build_payload(districts, links, district_roads, snapshot)

        # data.js: <script>로 읽히므로 파일을 직접 열어도 동작한다
        data_js = "window.TRAFFIC_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n"
        (self._out_dir / "data.js").write_text(data_js, encoding="utf-8")

        # index.html: 브라우저가 옛 data.js를 캐시하지 않도록 버전 문자열을 붙인다
        version = snapshot.collected_at.strftime("%Y%m%d%H%M%S")
        html = (TEMPLATE_DIR / "index.html").read_text(encoding="utf-8").replace("{{VERSION}}", version)
        (self._out_dir / "index.html").write_text(html, encoding="utf-8")

        # assets 폴더의 파일(로고 등)을 사이트 폴더로 복사
        if self._assets_dir and self._assets_dir.is_dir():
            for f in self._assets_dir.iterdir():
                if f.is_file():
                    shutil.copy2(f, self._out_dir / f.name)
        return self._out_dir / "index.html"
