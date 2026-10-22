# 고객 360° WM 인사이트 대시보드

한국어 UI로 구성한 Dash 기반 고객관리 목업입니다. 고객 목록, 자산·상품, 거래, 상담, 디지털 로그, 시장·하우스뷰를 합성 CSV로 연결해 PB 업무 큐와 고객 상세, 규칙 기반 NBA 및 목표 시뮬레이션을 제공합니다.

## 실행

```powershell
python -m pip install -r requirements.txt
python scripts/make_mock_data.py
python app.py
```

브라우저에서 `http://127.0.0.1:8050`을 엽니다. 데이터 파일은 `data/` 아래 13개 CSV이며, 앱 시작 시 필수 파일과 컬럼을 검증합니다.

## 구성

- `app.py`: Dash 진입점
- `pages/scr002_customer360.py`: 고객 360°, 액션 큐, NBA 및 시뮬레이션 화면/콜백
- `harness/schema.py`, `harness/data_loader.py`: CSV 계약과 데이터 로딩
- `harness/nba_engine.py`: 적합성 하드 게이트가 포함된 설명 가능한 목업 추천
- `scripts/make_mock_data.py`: 재현 가능한 합성 CSV 데이터 생성
- `assets/theme.css`: 반응형 대시보드 스타일

## 범위와 주의사항

모든 고객·거래·뉴스 데이터는 가상 데이터입니다. NBA는 규칙 기반 예시이며 운영 모델, 법률·컴플라이언스 판정 또는 실제 투자 권유가 아닙니다. 제안서·상담 버튼은 화면 피드백만 제공하며 실제 발송/일정 등록을 하지 않습니다. 몬테카를로 화면은 교육용 가정(연 기대수익률 4.5%, 고객별 목업 변동성, 1,500회)을 이용하며 미래 성과를 예측하거나 보장하지 않습니다.
