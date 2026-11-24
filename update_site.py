"""
실시간 속도를 수집하고 웹사이트(site/index.html)를 새로 만든다.

    python update_site.py               # 전체 도로 1회 수집 (API 약 5,100회 사용)
    python update_site.py --limit 300   # 도로 300개만 골고루 뽑아 빠르게 테스트
    python update_site.py --offline     # API 호출 없이 저장된 traffic.json으로 화면만 다시 만들기
    python update_site.py --loop        # 5분마다 계속 반복 (Ctrl+C로 종료)
"""

import argparse
import time
from datetime import datetime

from collector.api import SeoulOpenApiClient
from collector.traffic_collector import TrafficCollector
from processor.clipper import RoadClipper
from backend.config import Settings
from frontend.renderer import SiteRenderer
from storage.repository import LinkRepository, TrafficSnapshot


def run_once(settings: Settings, limit: int | None, offline: bool) -> None:
    districts, links = LinkRepository(settings).load_network()

    if offline:
        snapshot = TrafficSnapshot.load(settings.traffic_file)
        print(f"저장된 속도 데이터 사용 ({snapshot.collected_at:%H:%M} 수집분)")
    else:
        targets = links
        if limit:
            step = max(1, len(links) // limit)
            targets = links[::step][:limit]
        print(f"[{datetime.now():%H:%M:%S}] 도로 {len(targets):,}개 속도 수집 중...")
        started = time.time()
        client = SeoulOpenApiClient(settings.api_key)
        snapshot = TrafficCollector(client).collect(targets)
        snapshot.save(settings.traffic_file)
        print(f"  수집 완료: {len(snapshot.speeds):,}개 ({time.time() - started:.0f}초)")

    snapshot.apply_to(links)
    clipper = RoadClipper(settings.clipped_file, [settings.links_file, settings.gu_file])
    district_roads = clipper.load_or_build(districts, links)
    page = SiteRenderer(settings.site_dir).render(districts, links, district_roads, snapshot)
    print(f"  사이트 생성: {page}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="테스트용으로 이 개수만큼만 수집")
    parser.add_argument("--offline", action="store_true", help="API 호출 없이 저장된 데이터로 화면만 생성")
    parser.add_argument("--loop", action="store_true", help="주기적으로 계속 반복")
    parser.add_argument("--interval", type=int, default=5, help="반복 주기(분), 기본 5")
    args = parser.parse_args()

    settings = Settings.load()
    if not args.loop:
        run_once(settings, args.limit, args.offline)
        return

    while True:
        started = time.time()
        try:
            run_once(settings, args.limit, args.offline)
        except Exception as e:
            print(f"  오류: {e}")
        wait = args.interval * 60 - (time.time() - started)
        if wait > 0:
            print(f"  다음 갱신까지 {wait / 60:.1f}분 대기\n")
            time.sleep(wait)


if __name__ == "__main__":
    main()
