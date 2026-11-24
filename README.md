# 서울 실시간 도로 소통 지도

서울 열린데이터광장의 실시간 도로 소통 정보를 수집해 서울 25개 자치구와 도로 구간의 정체도를 지도에 표시하는 객체지향프로그래밍 수업의 팀 프로젝트다. 서울 전체의 교통 상황을 비교한 뒤, 자치구와 도로를 차례로 선택해 구간별 속도와 통행 시간을 확인할 수 있다. Python이 데이터를 수집해 정적 웹 파일을 만들고, Leaflet이 지도와 상세 정보를 표시한다.

[GitHub 저장소](https://github.com/hs7604/dashboard) · [대시보드 배포 주소](https://hs7604.github.io/dashboard/)

## GitHub Pages 배포

1. 저장소의 **Settings → Pages → Build and deployment → Source**에서 **GitHub Actions**를 선택한다.
2. **Settings → Secrets and variables → Actions**에서 서울 열린데이터광장 인증키를 저장소 시크릿 `SEOUL_API_KEY`로 등록한다.
3. **Actions → 사이트 자동 갱신 → Run workflow**에서 `main` 브랜치의 워크플로를 실행한다.
4. 배포가 성공하면 [대시보드](https://hs7604.github.io/dashboard/)에 접속한다. 상단에 표시된 수집 시각을 확인하고 지도에서 자치구와 도로를 선택해 상세 정보를 조회할 수 있다.

[사이트 자동 갱신 워크플로](.github/workflows/update-site.yml)는 `main` 푸시, 수동 실행, 5분 간격으로 설정된 스케줄에 따라 실행된다. 워크플로는 저장소에 포함된 `storage/data/links.geojson`을 사용해 `update_site.py`로 교통 정보를 수집하고, 생성된 `frontend/site/`를 GitHub Pages에 게시한다.

## 사용 데이터

최신 코드에서 사용하는 입력 출처는 총 **5개**다. 서울 열린데이터광장 Open API 3종과 파일 2종을 사용한다.

| 데이터 | API 서비스 또는 파일 | 활용 방법 |
| --- | --- | --- |
| [서울시 실시간 도로 소통 정보 (OA-13291)](https://data.seoul.go.kr/dataList/OA-13291/A/1/datasetView.do) | `TrafficInfo` | 링크 ID별 실시간 통행속도(km/h)와 통행시간(초)을 수집한다. |
| [서울시 소통 돌발 링크 정보 (OA-13310)](https://data.seoul.go.kr/dataList/OA-13310/A/1/datasetView.do) | `LinkInfo` | 도로망을 만들 때 링크 ID별 도로명과 시작·종료 지점 이름을 채운다. |
| [서울시 소통 돌발 도로 정보 (OA-13308)](https://data.seoul.go.kr/dataList/OA-13308/A/1/datasetView.do) | `RoadInfo` | 도로망을 만들 때 도로 구분 코드 `02`로 도시고속도로 이름 목록을 조회하고, 도로명과 대조해 도로 종류를 지정한다. |
| [서울시 교통소통 서비스링크 보간점 정보 (OA-15060)](https://data.seoul.go.kr/dataList/OA-15060/F/1/datasetView.do) | `서비스링크 보간점 정보(LINK_VERTEX)_2025.xlsx` | `LINK_ID`와 `VER_SEQ` 기준으로 점을 정렬해 도로 선을 만든다. GRS80 TM 좌표에서 구간 길이를 계산하고, 지도 표시용 좌표를 WGS84 경위도로 변환한다. |
| [서울 25개 자치구 경계 (통계청, southkorea/seoul-maps)](https://github.com/southkorea/seoul-maps/blob/master/kostat/2013/json/seoul_municipalities_geo_simple.json) | `seoul_gu.geojson` | 도로의 소속 구를 정하고, 구 상세 지도에 표시할 도로를 경계 안쪽으로 자른다. |

보간점·링크 정보·실시간 소통 정보는 **링크 ID**를 기준으로 연결한다. 정체 판정은 [서울시 교통정보센터(TOPIS)](https://topis.seoul.go.kr/)의 기준을 적용하며, 배경지도는 [© OpenStreetMap 기여자](https://www.openstreetmap.org/copyright)의 타일을 사용한다.

## 클래스 설계

| 파일 | 클래스 | 책임 및 주요 메서드·속성 |
| --- | --- | --- |
| `backend/config.py` | `Settings` | `load()`로 인증키를 읽고, `links_file`, `site_dir` 등 프로젝트 경로를 제공한다. |
| `backend/road.py` | `RoadType`, `UrbanExpressway`, `GeneralRoad` | 추상 클래스 `RoadType`이 공통 판정 메서드 `classify()`를 정의한다. 두 하위 클래스는 `jam_max`, `slow_max`에 각 도로 유형의 기준 속도를 지정한다. |
| `backend/road.py` | `Link`, `CongestionLevel` | `Link`는 도로 구간의 좌표·길이·교통 상태를 관리한다. `update_traffic()`으로 속도와 통행시간을 반영하고, `congestion` 속성은 도로 유형 객체에 판정을 맡긴다. `CongestionLevel` 열거형은 단계별 표시명·색·점수를 보관한다. |
| `backend/district.py` | `District` | 구 경계인 `Area`와 소속 `Link`들을 보유한다. `congestion_score`, `average_speed`, `level_counts()`로 구 단위 지표를 계산한다. |
| `collector/api.py`, `collector/traffic_collector.py` | `SeoulOpenApiClient`, `TrafficCollector` | API 클라이언트가 `get_speed()`, `get_link_info()`, `get_road_names()`를 제공한다. 수집기는 `collect()`에서 링크별 속도와 통행시간을 병렬 조회한다. |
| `processor/builder.py`, `processor/geo.py` | `NetworkBuilder`, `TmConverter`, `Polyline`, `Area` | `NetworkBuilder.run()`이 도로망 구축을 조율한다. `TmConverter.to_wgs84()`는 좌표를 변환하고, `Polyline`은 선의 길이·중간 지점을, `Area`는 경계 포함 여부와 선 자르기를 계산한다. |
| `processor/clipper.py` | `RoadClipper` | `load_or_build()`에서 자치구 경계 안의 도로 조각을 만들거나 `clipped_roads.json` 캐시를 읽는다. |
| `storage/repository.py` | `LinkRepository`, `TrafficSnapshot` | 저장소는 `save_links()`, `load_network()`로 GeoJSON 입출력을 담당한다. 스냅샷은 수집 시각과 링크별 측정값을 보관하고 `apply_to()`로 각 도로에 반영한다. |
| `frontend/renderer.py` | `SiteRenderer` | `build_payload()`로 Python 객체를 화면용 데이터로 변환하고, `render()`로 `frontend/site/index.html`과 `data.js`를 생성한다. |

- **상속과 다형성**은 `RoadType`에 적용한다. `Link.congestion`은 항상 `classify()`를 호출하고, 실제 도로 유형에 따라 적용되는 속도 기준이 달라진다.
- **캡슐화**는 API 요청 형식, XML 파싱, 재시도를 `SeoulOpenApiClient._request()`에 모아 구현했다. `District`도 내부 목록 `_links`를 관리하고, `links` 속성으로 목록의 복사본을 반환한다.

## 객체 간 상호작용

1. **도로망 구축** · `build_data.py`가 `Settings`와 `SeoulOpenApiClient`를 준비한다. `NetworkBuilder`는 보간점으로 `Link`를 만들고 `District`의 경계로 소속 구를 지정한 뒤, API에서 조회한 도로명·지점명·도로 종류를 채워 `LinkRepository.save_links()`로 저장한다.
2. **교통 정보 수집** · `update_site.py`가 `LinkRepository.load_network()`로 도로망을 불러와 `District.add_link()`로 도로와 소속 구를 연결한다. `TrafficCollector.collect()`가 API 클라이언트로 링크별 측정값을 조회해 `TrafficSnapshot`을 만들고, `TrafficSnapshot.apply_to()`가 `Link.update_traffic()`을 호출한다.
3. **정체도 집계와 지도 생성** · `Link`는 도로 유형에 따라 정체도를 판정한다. `District`는 소속 도로의 원활·서행·정체에 각각 0·1·2점을 부여하고 구간 길이로 가중평균한다. `RoadClipper`는 구 안에서 보이는 도로 조각을 구하고, `SiteRenderer`가 지표와 도로 조각을 화면용으로 변환한다. 브라우저는 `frontend/templates/index.html`에서 생성된 페이지와 `data.js`를 사용해 결과를 그린다.

## 대시보드 기능

| 화면 | 표시 정보와 조작 |
| --- | --- |
| 서울 전체 | 25개 자치구 경계를 원활·서행·정체·정보 없음에 따라 색으로 표시한다. 패널에는 서울 전체 도로 구간 상태와 정체 점수순 구 목록이 표시된다. 지도나 목록에서 구를 선택할 수 있다. |
| 자치구 상세 | 선택한 구로 확대해 경계 안의 도로를 상태별 색으로 표시한다. 패널에서 구의 정체도, 길이 가중 평균 속도, 상태별 구간 비율을 확인한다. `서울 전체` 버튼으로 돌아갈 수 있다. |
| 도로 상세 | 도로 선을 클릭하면 선택한 선이 강조되고, 패널에 도로명, 시작·종료 지점, 현재 속도, 통행시간, 링크 전체 길이, 도로 종류와 링크 ID가 표시된다. |

상태 비율 막대는 소속 구 기준으로 **속도 정보가 있는 도로 구간의 개수**를 집계한다. 경계를 지나는 도로는 상세 지도에서 구 안에 들어오는 부분만 표시되며, 같은 링크의 상세 정보가 연결된다.

## 프로젝트 파일

| 경로 | 역할 |
| --- | --- |
| `frontend/templates/index.html`, `frontend/assets/` | 지도 화면 템플릿과 정적 리소스 |
| `frontend/site/` | 워크플로가 생성하는 정적 사이트 |
| `storage/data/` | 보간점과 경계 파일, 도로망 GeoJSON, 수집과 지도 생성 과정에서 만들어지는 캐시 |
| `collector/test_api.py`, `collector/probe_link_info.py` | API 연결과 응답 확인 |
| `docs/` | 프로젝트 구상과 아키텍처 자료 |
