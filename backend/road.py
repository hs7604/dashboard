"""도로(링크)와 정체도 판정."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class CongestionLevel(Enum):
    """정체도 단계. 각 단계가 화면에 표시할 이름, 색, 점수, 글자색을 함께 가진다."""

    #        이름        선·채우기 색  점수   배지 글자색
    SMOOTH = ("원활",     "#2e9d4f",  0,    "#ffffff")
    SLOW = ("서행",       "#e8c76a",  1,    "#4a3a06")   # 부드러운 파스텔 톤 노랑
    JAM = ("정체",        "#d93a2b",  2,    "#ffffff")
    UNKNOWN = ("정보 없음", "#9e9e9e", None, "#ffffff")

    def __init__(self, label: str, color: str, score: int | None, text_color: str):
        self.label = label
        self.color = color
        self.score = score
        self.text_color = text_color

    @classmethod
    def from_score(cls, score: float | None) -> "CongestionLevel":
        """0~2 사이 평균 점수를 다시 단계로 바꾼다 (구 단위 판정에 사용)."""
        if score is None:
            return cls.UNKNOWN
        if score < 2 / 3:
            return cls.SMOOTH
        if score < 4 / 3:
            return cls.SLOW
        return cls.JAM


# ---------------------------------------------------------------------------
# 도로 종류: 추상 클래스 + 하위 클래스 (상속과 다형성)
# ---------------------------------------------------------------------------
class RoadType(ABC):
    """
    도로 종류의 공통 틀(추상 클래스).
    하위 클래스는 정체/서행 기준 속도만 정하면 되고,
    판정 로직(classify)은 부모 클래스의 것을 그대로 물려받는다.
    """

    name: str = ""

    @property
    @abstractmethod
    def jam_max(self) -> float:
        """이 속도 이하이면 '정체'."""

    @property
    @abstractmethod
    def slow_max(self) -> float:
        """jam_max 초과 ~ 이 속도 미만이면 '서행', 이상이면 '원활'."""

    def classify(self, speed: float | None) -> CongestionLevel:
        if speed is None:
            return CongestionLevel.UNKNOWN
        if speed <= self.jam_max:
            return CongestionLevel.JAM
        if speed < self.slow_max:
            return CongestionLevel.SLOW
        return CongestionLevel.SMOOTH

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


class UrbanExpressway(RoadType):
    """도시고속도로 (TOPIS 기준: 정체 30 이하, 서행 30~50, 원활 50 이상)."""

    name = "도시고속도로"
    jam_max = 30
    slow_max = 50


class GeneralRoad(RoadType):
    """일반도로·간선도로 (TOPIS 기준: 정체 15 이하, 서행 15~25, 원활 25 이상)."""

    name = "일반도로"
    jam_max = 15
    slow_max = 25


ROAD_TYPES: dict[str, RoadType] = {t.name: t for t in (UrbanExpressway(), GeneralRoad())}


# ---------------------------------------------------------------------------
@dataclass
class Link:
    """도로 한 구간(링크). 위치·도로 정보와 실시간 속도를 함께 가진다."""

    link_id: str
    coords: list[list[float]]                 # [[경도, 위도], ...]
    length_m: float
    gu: str | None = None
    road_name: str = ""
    st_node_nm: str = ""
    ed_node_nm: str = ""
    road_type: RoadType = field(default_factory=GeneralRoad)
    speed: float | None = None                # 실시간 속도 (km/h)
    travel_time: int | None = None            # 통행시간 (초)

    @property
    def congestion(self) -> CongestionLevel:
        # 도로 종류마다 기준이 다르지만, 여기서는 그 차이를 신경 쓸 필요가 없다 (다형성)
        return self.road_type.classify(self.speed)

    def update_traffic(self, speed: float | None, travel_time: int | None) -> None:
        self.speed = speed
        self.travel_time = travel_time

    @property
    def title(self) -> str:
        """화면에 보여줄 이름. 예: '분당수서로 (청담대교남단 → 탄천IC진출)'"""
        name = self.road_name or f"링크 {self.link_id}"
        if self.st_node_nm and self.ed_node_nm:
            return f"{name} ({self.st_node_nm} → {self.ed_node_nm})"
        return name

    # ---- GeoJSON 변환 ---------------------------------------------------
    def to_feature(self) -> dict:
        return {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": self.coords},
            "properties": {
                "link_id": self.link_id,
                "gu": self.gu,
                "length_m": self.length_m,
                "road_name": self.road_name,
                "st_node_nm": self.st_node_nm,
                "ed_node_nm": self.ed_node_nm,
                "road_type": self.road_type.name,
            },
        }

    @classmethod
    def from_feature(cls, feature: dict) -> "Link":
        p = feature["properties"]
        return cls(
            link_id=p["link_id"],
            coords=feature["geometry"]["coordinates"],
            length_m=p["length_m"],
            gu=p.get("gu"),
            road_name=p.get("road_name", ""),
            st_node_nm=p.get("st_node_nm", ""),
            ed_node_nm=p.get("ed_node_nm", ""),
            road_type=ROAD_TYPES.get(p.get("road_type"), GeneralRoad()),
        )
