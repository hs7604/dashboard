"""
API 연결 확인용 스크립트.

    python test_api.py                        # 샘플 링크 1개
    python test_api.py 1220003800 1220003900  # 여러 링크
"""

import sys

from traffic.api import SeoulOpenApiClient
from traffic.config import Settings
from traffic.road import GeneralRoad, Link, UrbanExpressway

SAMPLE_LINK_ID = "1220003800"


def main() -> None:
    settings = Settings.load()
    client = SeoulOpenApiClient(settings.api_key)
    expressways = set(client.get_road_names("02"))

    for link_id in sys.argv[1:] or [SAMPLE_LINK_ID]:
        info = client.get_link_info(link_id) or {}
        traffic = client.get_speed(link_id)

        road_type = UrbanExpressway() if info.get("road_name") in expressways else GeneralRoad()
        link = Link(link_id=link_id, coords=[], length_m=0, road_type=road_type, **info)
        if traffic:
            link.update_traffic(*traffic)

        print(f"{link.title}")
        print(f"  종류: {link.road_type.name} / 속도: {link.speed} km/h / "
              f"통행시간: {link.travel_time}초 / 상태: {link.congestion.label}")


if __name__ == "__main__":
    main()
