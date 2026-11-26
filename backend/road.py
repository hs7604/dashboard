from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class CongestionLevel(Enum):

    SMOOTH = ("원활",     "#2e9d4f",  0,    "#ffffff")
    SLOW = ("서행",       "#e8c76a",  1,    "#4a3a06")
    JAM = ("정체",        "#d93a2b",  2,    "#ffffff")
    UNKNOWN = ("정보 없음", "#9e9e9e", None, "#ffffff")

    def __init__(self, label: str, color: str, score: int | None, text_color: str):
        self.label = label
        self.color = color
        self.score = score
        self.text_color = text_color

    @classmethod
    def from_score(cls, score: float | None) -> "CongestionLevel":
        if score is None:
            return cls.UNKNOWN
        if score < 2 / 3:
            return cls.SMOOTH
        if score < 4 / 3:
            return cls.SLOW
        return cls.JAM


class RoadType(ABC):

    name: str = ""

    @property
    @abstractmethod
    def jam_max(self) -> float:
        """이 속도 이하이면 '정체'."""

    @property
    @abstractmethod
    def slow_max(self) -> float:
        pass

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
    name = "도시고속도로"
    jam_max = 30
    slow_max = 50


class GeneralRoad(RoadType):
    name = "일반도로"
    jam_max = 15
    slow_max = 25


ROAD_TYPES: dict[str, RoadType] = {t.name: t for t in (UrbanExpressway(), GeneralRoad())}


@dataclass
class Link:
    link_id: str
    coords: list[list[float]]
    length_m: float
    gu: str | None = None
    road_name: str = ""
    st_node_nm: str = ""
    ed_node_nm: str = ""
    road_type: RoadType = field(default_factory=GeneralRoad)
    speed: float | None = None
    travel_time: int | None = None

    @property
    def congestion(self) -> CongestionLevel:
        return self.road_type.classify(self.speed)

    def update_traffic(self, speed: float | None, travel_time: int | None) -> None:
        self.speed = speed
        self.travel_time = travel_time

    @property
    def title(self) -> str:
        name = self.road_name or f"링크 {self.link_id}"
        if self.st_node_nm and self.ed_node_nm:
            return f"{name} ({self.st_node_nm} → {self.ed_node_nm})"
        return name

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
