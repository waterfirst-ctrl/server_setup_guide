"""
Streamlit Sample Service
========================
waterfirst.pro 인프라 테스트용 샘플 Streamlit 앱
포트: 8501 (내부)
경로: /apps/streamlit-sample/app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta

# ─── 페이지 설정 ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Waterfirst · Sample App",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── 커스텀 CSS ─────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* 전체 배경 */
    .stApp { background: #0d1117; }

    /* 헤더 */
    .hero-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #58a6ff 0%, #79c0ff 50%, #a5d6ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .hero-sub {
        color: #8b949e;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }

    /* 메트릭 카드 */
    div[data-testid="metric-container"] {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 1rem 1.2rem;
    }
    div[data-testid="metric-container"] label {
        color: #8b949e !important;
        font-size: 0.85rem !important;
    }
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #e6edf3 !important;
    }

    /* 섹션 구분선 */
    hr { border-color: #21262d; }

    /* 사이드바 */
    [data-testid="stSidebar"] { background: #161b22; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─── 사이드바 ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 💧 Waterfirst")
    st.markdown("---")
    st.markdown("### 메뉴")
    page = st.radio(
        "",
        ["📊 대시보드", "📈 차트 데모", "🔧 시스템 정보"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption("포트: **8501** (내부)")
    st.caption("호스트: **waterfirst.pro**")

# ─── 메인 콘텐츠 ─────────────────────────────────────────────────────────────

if page == "📊 대시보드":
    st.markdown('<p class="hero-title">💧 Waterfirst Sample</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-sub">Streamlit 기반 샘플 서비스 · 내부 포트 8501</p>',
        unsafe_allow_html=True,
    )

    # 메트릭 행
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("서비스 상태", "🟢 Running", "+정상")
    col2.metric("내부 포트", "8501", "Streamlit")
    col3.metric("업타임", "99.9%", "+0.1%")
    col4.metric("요청 수", "1,024", "+128")

    st.markdown("---")

    # 랜덤 시계열 차트
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📉 실시간 트래픽 시뮬레이션")
        n = 60
        idx = pd.date_range(end=datetime.now(), periods=n, freq="min")
        df_traffic = pd.DataFrame(
            {
                "요청 수": np.random.poisson(lam=80, size=n),
                "에러 수": np.random.poisson(lam=3, size=n),
            },
            index=idx,
        )
        st.line_chart(df_traffic)

    with col_b:
        st.subheader("📊 상태 코드 분포")
        codes = pd.DataFrame(
            {
                "상태코드": ["200 OK", "301 Redirect", "404 Not Found", "500 Error"],
                "비율": [87, 7, 4, 2],
            }
        )
        st.bar_chart(codes.set_index("상태코드"))

elif page == "📈 차트 데모":
    st.title("📈 차트 데모")
    st.markdown("다양한 Streamlit 차트 컴포넌트 예시입니다.")

    st.subheader("랜덤 산점도")
    n_pts = st.slider("데이터 포인트 수", 50, 500, 200)
    df_scatter = pd.DataFrame(
        {
            "x": np.random.randn(n_pts),
            "y": np.random.randn(n_pts),
            "size": np.random.randint(10, 100, n_pts),
        }
    )
    st.scatter_chart(df_scatter, x="x", y="y", size="size")

    st.subheader("면적 차트")
    df_area = pd.DataFrame(
        np.random.randn(30, 3).cumsum(axis=0),
        columns=["Series A", "Series B", "Series C"],
    )
    st.area_chart(df_area)

elif page == "🔧 시스템 정보":
    st.title("🔧 시스템 정보")
    st.markdown("배포 구성 요약입니다.")

    st.markdown(
        """
        | 항목 | 값 |
        |------|-----|
        | 앱 경로 | `/home/waterfirst/apps/streamlit-sample/` |
        | 내부 포트 | `8501` |
        | 프로세스 관리 | `systemd` (`streamlit-sample.service`) |
        | 리버스 프록시 | `nginx` → `/app/` |
        | 로그 경로 | `/home/waterfirst/logs/streamlit-sample/` |
        | 도메인 | `waterfirst.pro/app/` |
        | Python 환경 | `venv` (`/home/waterfirst/apps/streamlit-sample/venv`) |
        """
    )

    st.info(
        "💡 실제 배포 시 `deploy/nginx/streamlit-sample.conf` 와 "
        "`deploy/systemd/streamlit-sample.service` 를 시스템에 링크하세요."
    )
