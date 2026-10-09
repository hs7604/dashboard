"""
서울 실시간 도로소통정보 시각화 패키지

모듈 구성:
    config      - Settings      : API 키, 파일 경로 등 설정값
    api         - SeoulOpenApiClient : 서울 열린데이터광장 API 호출
    geo         - TmConverter, Polyline, Area : 좌표 변환과 도형 계산
    road        - CongestionLevel, RoadType(+하위 클래스), Link : 도로와 정체도
    district    - District      : 자치구와 구 단위 정체도
    repository  - LinkRepository, TrafficSnapshot : 파일 저장/불러오기
    builder     - NetworkBuilder : 원본 데이터로 도로망 만들기
    collector   - TrafficCollector : 실시간 속도 수집
"""
