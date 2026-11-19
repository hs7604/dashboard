"""구 경계로 도로를 잘라 구 상세 지도용 도로 조각을 만든다."""

import json
import math
from pathlib import Path

from backend.district import District
from backend.road import Link

# 구 이름 → [(링크 ID, [선, 선, ...]), ...]
DistrictRoads = dict[str, list[tuple[str, list]]]


class RoadClipper:
    """
    구 상세 지도에서는 그 구 안에 있는 도로 부분만 보여준다.
    구 경계를 넘어가는 도로는 경계에서 잘라내고,
    옆 구에 속한 도로라도 이 구 안을 지나는 부분은 함께 보여준다.

    자르기 계산은 몇 초 걸리므로 결과를 파일에 저장해두고,
    도로망 파일이 바뀌었을 때만 다시 계산한다.
    """

    MIN_LENGTH_DEG = 0.00005    # 약 5m보다 짧은 자투리 조각은 버림
    DIGITS = 5

    def __init__(self, cache_file: Path, source_files: list[Path]):
        self._cache_file = cache_file
        self._source_files = source_files

    def _cache_is_fresh(self) -> bool:
        if not self._cache_file.exists():
            return False
        cache_time = self._cache_file.stat().st_mtime
        return all(cache_time > f.stat().st_mtime for f in self._source_files)

    @classmethod
    def _piece_length(cls, piece: list) -> float:
        return sum(math.dist(a, b) for a, b in zip(piece, piece[1:]))

    def build(self, districts: list[District], links: list[Link]) -> DistrictRoads:
        result: DistrictRoads = {}
        for d in districts:
            roads = []
            for link in links:
                if not d.area.overlaps_bbox(link.coords):
                    continue
                pieces = [
                    [[round(x, self.DIGITS), round(y, self.DIGITS)] for x, y in p]
                    for p in d.area.clip_line(link.coords)
                    if self._piece_length(p) >= self.MIN_LENGTH_DEG
                ]
                if pieces:
                    roads.append((link.link_id, pieces))
            result[d.name] = roads
        return result

    def load_or_build(self, districts: list[District], links: list[Link]) -> DistrictRoads:
        if self._cache_is_fresh():
            data = json.loads(self._cache_file.read_text(encoding="utf-8"))
            return {gu: [tuple(r) for r in roads] for gu, roads in data.items()}

        print("  구 경계로 도로 자르는 중... (처음 한 번만, 잠시 걸려요)")
        result = self.build(districts, links)
        self._cache_file.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        return result
