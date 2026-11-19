"""고객 360° 대시보드(Dash 웹 애플리케이션) 실행 엔트리포인트 스크립트."""

from pages.scr002_customer360 import app, server


if __name__ == "__main__":
    # 대시보드 로컬 웹 서버 실행 (기본 포트: 8050)
    app.run(debug=False)
