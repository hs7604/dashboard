"""
도로망 데이터(links.geojson)를 만든다. 처음 한 번, 또는 보간점 파일이 바뀔 때만 실행.
(예전의 build_links.py + add_link_info.py를 대체)

    python build_data.py
"""

from traffic.api import SeoulOpenApiClient
from traffic.builder import NetworkBuilder
from traffic.config import Settings


def main() -> None:
    settings = Settings.load()
    client = SeoulOpenApiClient(settings.api_key)
    NetworkBuilder(settings, client).run()


if __name__ == "__main__":
    main()
