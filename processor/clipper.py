import json
import math
from pathlib import Path

from backend.district import District
from backend.road import Link

DistrictRoads = dict[str, list[tuple[str, list]]]


class RoadClipper:


    MIN_LENGTH_DEG = 0.00005
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
