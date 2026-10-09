"""실시간 속도 수집."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from .api import SeoulOpenApiClient
from .road import Link
from .repository import TrafficSnapshot


class TrafficCollector:
    """전체 도로의 실시간 속도를 동시에 조회해 TrafficSnapshot으로 만든다."""

    def __init__(self, client: SeoulOpenApiClient, workers: int = 8):
        self._client = client
        self._workers = workers

    def _fetch(self, link_id: str) -> tuple[str, tuple[float, int] | None]:
        try:
            return link_id, self._client.get_speed(link_id)
        except Exception:
            return link_id, None

    def collect(self, links: list[Link]) -> TrafficSnapshot:
        started = datetime.now()
        with ThreadPoolExecutor(max_workers=self._workers) as pool:
            results = pool.map(self._fetch, [l.link_id for l in links])
            speeds = {lid: value for lid, value in results if value is not None}
        return TrafficSnapshot(collected_at=started, speeds=speeds)
