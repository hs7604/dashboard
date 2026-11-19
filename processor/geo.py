"""좌표 변환과 도형 계산. 외부 DLL 패키지 없이 순수 파이썬으로 구현한다."""

import math


class TmConverter:
    """
    횡메르카토르(TM) 좌표 → 위경도(WGS84) 변환기.
    기본값은 EPSG:5181 (GRS80 타원체, 중부원점, 가산값 X 200,000 / Y 500,000).
    원점이나 가산값을 바꿔 다른 TM 좌표계에도 쓸 수 있다.
    """

    def __init__(self, lat0: float = 38.0, lon0: float = 127.0,
                 false_easting: float = 200000.0, false_northing: float = 500000.0,
                 a: float = 6378137.0, f: float = 1 / 298.257222101, k0: float = 1.0):
        self._a = a
        self._k0 = k0
        self._fe, self._fn = false_easting, false_northing
        self._lon0 = math.radians(lon0)
        self._e2 = f * (2 - f)
        self._ep2 = self._e2 / (1 - self._e2)
        self._e1 = (1 - math.sqrt(1 - self._e2)) / (1 + math.sqrt(1 - self._e2))
        self._m0 = self._meridian_arc(math.radians(lat0))

    def _meridian_arc(self, phi: float) -> float:
        e2, a = self._e2, self._a
        return a * (
            (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256) * phi
            - (3 * e2 / 8 + 3 * e2**2 / 32 + 45 * e2**3 / 1024) * math.sin(2 * phi)
            + (15 * e2**2 / 256 + 45 * e2**3 / 1024) * math.sin(4 * phi)
            - (35 * e2**3 / 3072) * math.sin(6 * phi)
        )

    def to_wgs84(self, x: float, y: float) -> tuple[float, float]:
        """TM (x, y) → (경도, 위도). Snyder(1987)의 TM 역변환 공식."""
        e2, ep2, e1, a = self._e2, self._ep2, self._e1, self._a
        m = self._m0 + (y - self._fn) / self._k0
        mu = m / (a * (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256))
        phi1 = (
            mu
            + (3 * e1 / 2 - 27 * e1**3 / 32) * math.sin(2 * mu)
            + (21 * e1**2 / 16 - 55 * e1**4 / 32) * math.sin(4 * mu)
            + (151 * e1**3 / 96) * math.sin(6 * mu)
            + (1097 * e1**4 / 512) * math.sin(8 * mu)
        )
        s, c, t = math.sin(phi1), math.cos(phi1), math.tan(phi1)
        c1, t1 = ep2 * c**2, t**2
        n1 = a / math.sqrt(1 - e2 * s**2)
        r1 = a * (1 - e2) / (1 - e2 * s**2) ** 1.5
        d = (x - self._fe) / (n1 * self._k0)

        lat = phi1 - (n1 * t / r1) * (
            d**2 / 2
            - (5 + 3 * t1 + 10 * c1 - 4 * c1**2 - 9 * ep2) * d**4 / 24
            + (61 + 90 * t1 + 298 * c1 + 45 * t1**2 - 252 * ep2 - 3 * c1**2) * d**6 / 720
        )
        lon = self._lon0 + (
            d
            - (1 + 2 * t1 + c1) * d**3 / 6
            + (5 - 2 * c1 + 28 * t1 - 3 * c1**2 + 8 * ep2 + 24 * t1**2) * d**5 / 120
        ) / c
        return math.degrees(lon), math.degrees(lat)


class Polyline:
    """점들을 이은 선. 길이와 선 위의 중간 지점을 계산한다."""

    def __init__(self, points: list[tuple[float, float]]):
        if len(points) < 2:
            raise ValueError("선은 점이 2개 이상 필요합니다.")
        self.points = points

    @property
    def length(self) -> float:
        return sum(math.dist(p, q) for p, q in zip(self.points, self.points[1:]))

    def midpoint(self) -> tuple[float, float]:
        """선을 따라 절반 거리에 있는 점."""
        half, walked = self.length / 2, 0.0
        for (x1, y1), (x2, y2) in zip(self.points, self.points[1:]):
            seg = math.dist((x1, y1), (x2, y2))
            if seg > 0 and walked + seg >= half:
                r = (half - walked) / seg
                return x1 + (x2 - x1) * r, y1 + (y2 - y1) * r
            walked += seg
        return self.points[-1]


class Area:
    """GeoJSON Polygon / MultiPolygon 영역."""

    def __init__(self, geometry: dict):
        if geometry["type"] == "Polygon":
            self._polygons = [geometry["coordinates"]]
        elif geometry["type"] == "MultiPolygon":
            self._polygons = geometry["coordinates"]
        else:
            raise ValueError(f"지원하지 않는 도형: {geometry['type']}")
        self.geometry = geometry

    @staticmethod
    def _in_ring(lon: float, lat: float, ring: list) -> bool:
        """광선 투사법(ray casting)."""
        inside, j = False, len(ring) - 1
        for i in range(len(ring)):
            xi, yi = ring[i][0], ring[i][1]
            xj, yj = ring[j][0], ring[j][1]
            if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
                inside = not inside
            j = i
        return inside

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        """(최소 경도, 최소 위도, 최대 경도, 최대 위도)"""
        if not hasattr(self, "_bbox"):
            xs = [p[0] for rings in self._polygons for ring in rings for p in ring]
            ys = [p[1] for rings in self._polygons for ring in rings for p in ring]
            self._bbox = (min(xs), min(ys), max(xs), max(ys))
        return self._bbox

    def _edges(self) -> list[tuple]:
        """경계선 조각 목록. 교차 계산을 빠르게 하려고 각 조각의 bbox도 함께 저장."""
        if not hasattr(self, "_edge_list"):
            edges = []
            for rings in self._polygons:
                for ring in rings:
                    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
                        edges.append((x1, y1, x2, y2, min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2)))
            self._edge_list = edges
        return self._edge_list

    def contains(self, lon: float, lat: float) -> bool:
        x0, y0, x1, y1 = self.bbox
        if not (x0 <= lon <= x1 and y0 <= lat <= y1):
            return False
        for rings in self._polygons:
            outer, holes = rings[0], rings[1:]
            if self._in_ring(lon, lat, outer) and not any(self._in_ring(lon, lat, h) for h in holes):
                return True
        return False

    def overlaps_bbox(self, points: list) -> bool:
        x0, y0, x1, y1 = self.bbox
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return not (max(xs) < x0 or min(xs) > x1 or max(ys) < y0 or min(ys) > y1)

    def clip_line(self, points: list) -> list[list[list[float]]]:
        """
        선을 이 영역 경계에서 잘라 영역 안에 있는 부분만 반환한다.
        결과는 선 여러 개일 수 있다 (영역을 들어갔다 나갔다 하는 경우).
        """
        pieces: list[list[list[float]]] = []
        edges = self._edges()

        for (px, py), (qx, qy) in zip(points, points[1:]):
            dx, dy = qx - px, qy - py
            sx0, sx1, sy0, sy1 = min(px, qx), max(px, qx), min(py, qy), max(py, qy)

            # 이 선분이 경계선과 만나는 지점들을 0~1 비율(t)로 구한다
            ts = [0.0, 1.0]
            for ex1, ey1, ex2, ey2, ex0, ex9, ey0, ey9 in edges:
                if ex9 < sx0 or ex0 > sx1 or ey9 < sy0 or ey0 > sy1:
                    continue
                fx, fy = ex2 - ex1, ey2 - ey1
                denom = dx * fy - dy * fx
                if denom == 0:
                    continue
                t = ((ex1 - px) * fy - (ey1 - py) * fx) / denom
                u = ((ex1 - px) * dy - (ey1 - py) * dx) / denom
                if 0 < t < 1 and 0 <= u <= 1:
                    ts.append(t)
            ts.sort()

            # 잘린 조각마다 가운데 점이 영역 안이면 남긴다
            for t0, t1 in zip(ts, ts[1:]):
                if t1 - t0 < 1e-9:
                    continue
                tm = (t0 + t1) / 2
                if not self.contains(px + dx * tm, py + dy * tm):
                    continue
                a = [px + dx * t0, py + dy * t0]
                b = [px + dx * t1, py + dy * t1]
                last = pieces[-1][-1] if pieces else None
                if last and abs(last[0] - a[0]) < 1e-12 and abs(last[1] - a[1]) < 1e-12:
                    pieces[-1].append(b)          # 앞 조각과 이어지면 연결
                else:
                    pieces.append([a, b])
        return pieces

    def label_point(self) -> tuple[float, float]:
        """구 이름을 표시할 위치 (가장 큰 조각의 무게중심, 밖이면 안쪽 지점으로 보정)."""
        def ring_area_centroid(ring):
            a = cx = cy = 0.0
            for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
                cross = x1 * y2 - x2 * y1
                a += cross
                cx += (x1 + x2) * cross
                cy += (y1 + y2) * cross
            a /= 2
            return abs(a), (cx / (6 * a), cy / (6 * a)) if a else ring[0]

        area, (lon, lat) = max(ring_area_centroid(rings[0]) for rings in self._polygons)
        if self.contains(lon, lat):
            return lon, lat

        # 무게중심이 영역 밖이면, 그 위도의 가로선에서 영역 안 가장 긴 구간의 가운데
        xs = []
        for ex1, ey1, ex2, ey2, *_ in self._edges():
            if (ey1 > lat) != (ey2 > lat):
                xs.append(ex1 + (lat - ey1) * (ex2 - ex1) / (ey2 - ey1))
        xs.sort()
        spans = [(b - a, (a + b) / 2) for a, b in zip(xs[::2], xs[1::2])]
        return (max(spans)[1], lat) if spans else (lon, lat)

    def distance_to(self, lon: float, lat: float) -> float:
        """경계 꼭짓점까지의 최소 거리 (위도 보정한 도 단위, 비교용)."""
        kx = math.cos(math.radians(lat))
        return min(
            math.hypot((p[0] - lon) * kx, p[1] - lat)
            for rings in self._polygons for ring in rings for p in ring
        )
