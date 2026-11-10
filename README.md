# 고객 360° WM 인사이트 대시보드

한국어 UI로 구성한 Dash 기반 고객관리 목업입니다. 고객 선택 필터, 자산·거래·앱 행동·예측 인사이트, 고객별 Next Best Action을 합성 CSV로 연결합니다.

## 실행

```powershell
python -m pip install -r requirements.txt
python scripts/make_mock_data.py
python app.py
```

브라우저에서 `http://127.0.0.1:8050`을 엽니다. 데이터 파일은 `data/` 아래 14개 CSV이며, 앱 시작 시 필수 파일·컬럼과 고객번호 참조를 검증합니다.

## 인터넷 차단 환경용 단일 HTML

인터넷에 연결하지 않고 브라우저에서 열 수 있는 대시보드 파일을 생성합니다. 증권사 내부 PC의 Python 3.12.11 아나콘다 환경에서 프로젝트의 기존 `pandas`, `dash`, `plotly`가 사용 가능해야 하며, 이 기능을 위해 추가 패키지를 설치하지 않습니다.

```powershell
python export_html.py
```

프로젝트 폴더에 `customer360_offline.html`이 생성됩니다. 다른 경로를 지정하려면 `python export_html.py --output "D:\전달\customer360.html"`을 사용합니다. HTML에는 스타일, 로고, Plotly 실행 코드가 포함되어 있어 네트워크나 Dash 서버 없이 브라우저에서 열 수 있습니다. 고객 선택, 5개 탭, 거래 자산군 선택도 HTML 내부에서 동작합니다. 생성기에서 다시 만들 경우 `data/`, `assets/`, `pages/`, `harness/` 폴더와 `export_html.py`를 함께 반입하세요. 기존 `app.py`는 변경하지 않았습니다.

## 구성

- `app.py`: Dash 진입점
- `export_html.py`: 자체 포함형 오프라인 HTML 생성기
- `pages/scr002_customer360.py`: 고객·자산·거래·행동·예측 탭 및 고객별 NBA
- `harness/schema.py`, `harness/data_loader.py`: CSV 계약과 데이터 로딩
- `scripts/make_mock_data.py`: 재현 가능한 합성 CSV 데이터 생성
- `assets/theme.css`: 반응형 대시보드 스타일

## 목업 데이터 및 디자인

`python scripts/make_mock_data.py`를 실행하면 고객 10명의 한국어 CSV 14개를 생성합니다. 예측 탭은 고객당 16개 주제를 표시하고, NBA.csv는 고객별로 순서가 있는 제안 3건을 제공합니다. 각 제안은 점수 없이 주제·내용·상세로 구성됩니다. `고객.csv`에는 상단 요약의 만기 표시를 위한 `만기일` 컬럼이 추가되어 있습니다.

상단 로고는 `assets/mirae_asset_logo.png`이며, 색상은 미래에셋증권 Mirae Asset Orange(`#F58220`)를 주색상으로, Mirae Asset Blue(`#043B72`)와 가이드의 보조색을 차트 및 디지털 배경에 적용했습니다.

## 범위와 주의사항

모든 고객·거래·예측 데이터는 가상 데이터입니다. Next Best Action은 화면 시연용 목업이며 운영 모델, 법률·컴플라이언스 판정 또는 실제 투자 권유가 아닙니다.
