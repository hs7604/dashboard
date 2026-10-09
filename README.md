# 서울 실시간 도로 소통 지도

서울 열린데이터광장의 실시간 도로소통정보를 수집해, 25개 자치구와 도로별 정체도를 지도로 보여주는 사이트입니다.
5분마다 GitHub Actions가 자동으로 데이터를 수집하고 GitHub Pages에 다시 배포합니다.

## 구조

| 파일 | 역할 |
|---|---|
| `traffic/config.py` | `Settings` — API 키, 파일 경로 |
| `traffic/api.py` | `SeoulOpenApiClient` — 서울 열린데이터광장 API 호출 |
| `traffic/geo.py` | `TmConverter`, `Polyline`, `Area` — 좌표 변환, 도형 계산, 경계 자르기 |
| `traffic/road.py` | `CongestionLevel`, `RoadType`(`UrbanExpressway`, `GeneralRoad`), `Link` — 도로와 정체도 판정 |
| `traffic/district.py` | `District` — 자치구 단위 정체도 |
| `traffic/repository.py` | `LinkRepository`, `TrafficSnapshot` — 파일 저장/불러오기 |
| `traffic/builder.py` | `NetworkBuilder` — 원본 데이터로 도로망 생성 |
| `traffic/clipper.py` | `RoadClipper` — 구 경계로 도로 자르기 |
| `traffic/collector.py` | `TrafficCollector` — 실시간 속도 동시 수집 |
| `traffic/renderer.py` | `SiteRenderer` — 웹사이트 파일 생성 |

## 실행

```bash
pip install -r requirements.txt
python build_data.py      # 도로망 데이터 생성 (처음 한 번)
python update_site.py     # 속도 수집 + 사이트 생성
python -m http.server 8000 --directory site   # http://localhost:8000
```

`.env` 파일에 `SEOUL_API_KEY=인증키`를 넣어야 합니다.

## 데이터 출처

- 실시간 도로 소통 정보, 링크 정보, 서비스링크 보간점: 서울 열린데이터광장
- 정체 판정 기준: 서울시 교통정보센터(TOPIS)
- 자치구 경계: 통계청 (southkorea/seoul-maps)
- 배경지도: © OpenStreetMap 기여자
