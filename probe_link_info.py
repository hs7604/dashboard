"""RoadInfo가 어떤 정보를 주는지 응답 원문을 확인한다."""
import os

import requests
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("SEOUL_API_KEY")

SERVICES = [
    "RoadInfo/1/100/02",   # 도시고속도로(02)에 속한 도로 목록
    "RoadInfo/1/5/03",     # 주간선도로(03) 일부
]

for svc in SERVICES:
    url = f"http://openapi.seoul.go.kr:8088/{KEY}/xml/{svc}"
    print("=" * 60)
    print(svc)
    try:
        resp = requests.get(url, timeout=10)
        resp.encoding = "utf-8"
        print(resp.text[:3000])
    except requests.RequestException as e:
        print(f"요청 실패: {e}")