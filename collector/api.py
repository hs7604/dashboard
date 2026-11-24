"""서울 열린데이터광장 Open API 클라이언트."""

import time
import xml.etree.ElementTree as ET

import requests


class ApiError(Exception):
    """API가 오류 코드를 돌려줬을 때 발생하는 예외."""


class SeoulOpenApiClient:
    """
    서울 열린데이터광장 API 호출을 담당하는 클래스.

    API 주소 형식, 재시도, 오류 코드 처리 같은 세부사항은 이 클래스 안에 숨겨두고(캡슐화)
    바깥에는 get_speed(), get_link_info()처럼 의미 있는 메서드만 공개한다.
    """

    BASE_URL = "http://openapi.seoul.go.kr:8088"
    OK = "INFO-000"
    NO_DATA = "INFO-200"

    def __init__(self, api_key: str, timeout: float = 10, retries: int = 3):
        self._api_key = api_key
        self._timeout = timeout
        self._retries = retries

    def _request(self, service: str, start: int, end: int, *params: str) -> list[ET.Element]:
        """API를 호출해 <row> 요소 목록을 반환한다."""
        parts = [self.BASE_URL, self._api_key, "xml", service, str(start), str(end), *params]
        url = "/".join(parts)

        for attempt in range(self._retries):
            try:
                resp = requests.get(url, timeout=self._timeout)
                resp.raise_for_status()
                root = ET.fromstring(resp.content)
                break
            except (requests.RequestException, ET.ParseError):
                if attempt == self._retries - 1:
                    raise
                time.sleep(1 + attempt)

        code = root.findtext(".//CODE")
        if code == self.NO_DATA:
            return []
        if code != self.OK:
            raise ApiError(f"{service}: {code} {root.findtext('.//MESSAGE')}")
        return root.findall("row")

    def get_speed(self, link_id: str) -> tuple[float, int] | None:
        """링크의 (실시간 속도 km/h, 통행시간 초). 데이터가 없으면 None."""
        rows = self._request("TrafficInfo", 1, 1, link_id)
        if not rows:
            return None
        return float(rows[0].findtext("prcs_spd")), int(rows[0].findtext("prcs_trv_time"))

    def get_link_info(self, link_id: str) -> dict | None:
        """링크의 도로 이름, 시작/끝 지점 이름."""
        rows = self._request("LinkInfo", 1, 1, link_id)
        if not rows:
            return None
        row = rows[0]
        return {
            "road_name": row.findtext("road_name") or "",
            "st_node_nm": row.findtext("st_node_nm") or "",
            "ed_node_nm": row.findtext("ed_node_nm") or "",
        }

    def get_road_names(self, road_div_cd: str) -> list[str]:
        """도로 종류 코드(02=도시고속도로 등)에 속한 도로 이름 목록."""
        rows = self._request("RoadInfo", 1, 1000, road_div_cd)
        return [row.findtext("axis_name") for row in rows]
