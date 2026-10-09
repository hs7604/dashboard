"""원본 데이터(보간점 xlsx, 구 경계, 링크 정보 API)로 도로망을 만든다."""

from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests

from .api import SeoulOpenApiClient
from .config import Settings
from .district import District
from .geo import Polyline, TmConverter
from .repository import LinkRepository
from .road import ROAD_TYPES, GeneralRoad, Link, UrbanExpressway

GU_URL = (
    "https://raw.githubusercontent.com/southkorea/seoul-maps/master/"
    "kostat/2013/json/seoul_municipalities_geo_simple.json"
)
EXPRESSWAY_CODE = "02"


class NetworkBuilder:
    """
    도로망 생성 과정을 단계별 메서드로 나눈 클래스.
    필요한 객체(설정, API 클라이언트, 좌표 변환기, 저장소)는 생성자에서 받아 쓴다.
    """

    def __init__(self, settings: Settings, client: SeoulOpenApiClient,
                 converter: TmConverter | None = None, workers: int = 8):
        self._settings = settings
        self._client = client
        self._converter = converter or TmConverter()
        self._repo = LinkRepository(settings)
        self._workers = workers

    # 1단계 --------------------------------------------------------------
    def ensure_gu_file(self) -> None:
        if not self._settings.gu_file.exists():
            print("구 경계 파일 내려받는 중...")
            resp = requests.get(GU_URL, timeout=30)
            resp.raise_for_status()
            self._settings.gu_file.write_bytes(resp.content)

    # 2단계 --------------------------------------------------------------
    def build_links(self) -> list[Link]:
        """보간점 좌표로 도로 선을 만든다."""
        path = self._settings.vertex_file
        print(f"보간점 파일 읽는 중: {path.name}")
        df = pd.read_excel(path).sort_values(["LINK_ID", "VER_SEQ"])

        links = []
        for link_id, grp in df.groupby("LINK_ID"):
            tm_points = list(zip(grp["GRS80TM_X"], grp["GRS80TM_Y"]))
            if len(tm_points) < 2:
                continue
            coords = [[round(v, 6) for v in self._converter.to_wgs84(x, y)] for x, y in tm_points]
            links.append(Link(
                link_id=str(link_id),
                coords=coords,
                length_m=round(Polyline(tm_points).length, 1),   # TM 좌표는 미터 단위
            ))
        print(f"도로 {len(links):,}개 생성")
        return links

    # 3단계 --------------------------------------------------------------
    def assign_districts(self, links: list[Link], districts: list[District]) -> None:
        """도로 중간 지점이 속한 구를 지정한다. 어디에도 없으면 가장 가까운 구."""
        nearest_count = 0
        for link in links:
            lon, lat = Polyline([tuple(c) for c in link.coords]).midpoint()
            owner = next((d for d in districts if d.area.contains(lon, lat)), None)
            if owner is None:
                owner = min(districts, key=lambda d: d.area.distance_to(lon, lat))
                nearest_count += 1
            link.gu = owner.name
        print(f"구 지정 완료 (가장 가까운 구로 지정: {nearest_count}개)")

    # 4단계 --------------------------------------------------------------
    def enrich_link_info(self, links: list[Link]) -> list[str]:
        """도로 이름·시작/끝 지점·도로 종류를 채운다. 실패한 링크 ID 목록을 반환."""
        expressways = set(self._client.get_road_names(EXPRESSWAY_CODE))
        print(f"도시고속도로 {len(expressways)}개: {', '.join(sorted(expressways))}")
        print(f"링크 {len(links):,}개 정보 조회 중... (몇 분 걸릴 수 있어요)")

        def fetch(link: Link) -> bool:
            try:
                info = self._client.get_link_info(link.link_id)
            except Exception:
                return False
            if info is None:
                return False
            link.road_name = info["road_name"]
            link.st_node_nm = info["st_node_nm"]
            link.ed_node_nm = info["ed_node_nm"]
            link.road_type = (
                ROAD_TYPES[UrbanExpressway.name] if link.road_name in expressways
                else ROAD_TYPES[GeneralRoad.name]
            )
            return True

        with ThreadPoolExecutor(max_workers=self._workers) as pool:
            results = list(pool.map(fetch, links))
        return [l.link_id for l, ok in zip(links, results) if not ok]

    # 전체 실행 ----------------------------------------------------------
    def run(self) -> list[Link]:
        self.ensure_gu_file()
        districts = self._repo.load_districts()
        links = self.build_links()
        self.assign_districts(links, districts)
        failed = self.enrich_link_info(links)
        self._repo.save_links(links)

        n_exp = sum(isinstance(l.road_type, UrbanExpressway) for l in links)
        print(f"\n저장 완료: {self._settings.links_file.name}")
        print(f"  도시고속도로 {n_exp:,}개 / 일반도로 {len(links) - n_exp:,}개")
        print(f"  정보 조회 실패 {len(failed)}개 {failed[:10] if failed else ''}")
        return links
