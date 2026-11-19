"""설정값을 한 곳에 모아 관리한다."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    """프로젝트 전체에서 쓰는 설정. frozen=True라서 만든 뒤에는 값을 바꿀 수 없다."""

    api_key: str
    base_dir: Path = PROJECT_DIR

    # 파일 경로들은 base_dir로부터 계산되는 속성(property)으로 제공한다
    @property
    def data_dir(self) -> Path:
        """원본 데이터 및 캐시 파일이 저장되는 폴더."""
        return self.base_dir / "storage" / "data"

    @property
    def links_file(self) -> Path:
        return self.data_dir / "links.geojson"

    @property
    def gu_file(self) -> Path:
        return self.data_dir / "seoul_gu.geojson"

    @property
    def traffic_file(self) -> Path:
        return self.data_dir / "traffic.json"

    @property
    def clipped_file(self) -> Path:
        """구 경계로 자른 도로 조각 (자동 생성되는 캐시 파일)."""
        return self.data_dir / "clipped_roads.json"

    @property
    def assets_dir(self) -> Path:
        """로고 등 사이트에 그대로 복사할 파일을 넣는 폴더."""
        return self.base_dir / "frontend" / "assets"

    @property
    def site_dir(self) -> Path:
        """웹사이트 파일(index.html, data.js)이 만들어지는 폴더."""
        return self.base_dir / "frontend" / "site"

    @property
    def vertex_file(self) -> Path:
        files = sorted(self.data_dir.glob("*보간점*.xlsx"))
        if not files:
            raise FileNotFoundError("보간점 xlsx 파일을 찾지 못했습니다.")
        return files[-1]

    @classmethod
    def load(cls, base_dir: Path = PROJECT_DIR) -> "Settings":
        """.env 파일에서 API 키를 읽어 Settings 객체를 만든다."""
        load_dotenv(base_dir / ".env")
        key = os.getenv("SEOUL_API_KEY")
        if not key:
            raise RuntimeError("SEOUL_API_KEY가 없습니다. .env 파일을 확인하세요.")
        return cls(api_key=key, base_dir=base_dir)
