import streamlit as st
import pandas as pd
import datetime

# ----------------------------------------------------------------------------
# 페이지 설정
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="서울 역대 최고 더위 연도 찾기",
    page_icon="🌡️",
    layout="centered",
)

# 깔끔한 스타일을 위한 커스텀 CSS (별도 시각화 라이브러리 아님, 순수 CSS)
st.markdown(
    """
    <style>
    .main {background-color: #fafafa;}
    div[data-testid="stMetric"] {
        background-color: #fff5f0;
        border: 1px solid #ffd9c7;
        border-radius: 12px;
        padding: 16px 12px;
    }
    div[data-testid="stMetricLabel"] {font-weight: 600;}
    h1, h2, h3 {color: #d94f2b;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🌡️ 서울, 그해 여름은 얼마나 더웠을까?")
st.caption("원하는 기간(월-일)을 고르면, 그 기간을 기준으로 역대 가장 더웠던 연도를 찾아드립니다.")


# ----------------------------------------------------------------------------
# 데이터 로드 & 전처리
# ----------------------------------------------------------------------------
@st.cache_data
def load_data():
    # 같은 저장소(GitHub repo)에 seoul.csv가 함께 올라가 있다는 전제로
    # 상대 경로로 읽습니다. (Streamlit Cloud에 배포 시 자동으로 인식됨)
    df = pd.read_csv("seoul.csv", encoding="utf-8-sig")

    # 날짜 컬럼에 섞여있는 탭 문자, 공백, 따옴표 제거 후 datetime 변환
    df["날짜"] = df["날짜"].astype(str).str.replace("\t", "", regex=False).str.strip()
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")

    # 기온 컬럼 숫자형 변환 + 결측 제거
    df["평균기온"] = pd.to_numeric(df["평균기온"], errors="coerce")
    df = df.dropna(subset=["날짜", "평균기온"]).copy()

    df["연도"] = df["날짜"].dt.year
    df["월"] = df["날짜"].dt.month
    df["일"] = df["날짜"].dt.day
    df["월일"] = df["날짜"].dt.strftime("%m-%d")

    return df


df = load_data()

min_year = int(df["연도"].min())
max_year = int(df["연도"].max())

st.write(f"📅 데이터 기간: **{min_year}년 ~ {max_year}년** (총 {len(df):,}일)")


# ----------------------------------------------------------------------------
# 기간(월-일) 선택 UI
# ----------------------------------------------------------------------------
st.subheader("① 비교할 기간을 선택하세요")

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input(
        "시작일 (연도는 무시, 월-일만 사용)",
        value=datetime.date(2024, 6, 1),
        format="YYYY-MM-DD",
    )
with col2:
    end_date = st.date_input(
        "종료일 (연도는 무시, 월-일만 사용)",
        value=datetime.date(2024, 8, 31),
        format="YYYY-MM-DD",
    )

start_md = (start_date.month, start_date.day)
end_md = (end_date.month, end_date.day)


def in_period(month, day, start_md, end_md):
    """월-일이 지정 구간에 속하는지 확인 (연말-연초 걸치는 구간도 처리)"""
    md = (month, day)
    if start_md <= end_md:
        return start_md <= md <= end_md
    else:  # 예: 12-01 ~ 02-28 처럼 해를 넘기는 구간
        return md >= start_md or md <= end_md


mask = df.apply(lambda r: in_period(r["월"], r["일"], start_md, end_md), axis=1)
period_df = df[mask]

# 기간 하루 일수(대략) 계산 → 데이터가 너무 부족한 연도는 제외하기 위함
if start_md <= end_md:
    expected_days = (
        datetime.date(2024, end_md[0], end_md[1]) - datetime.date(2024, start_md[0], start_md[1])
    ).days + 1
else:
    expected_days = (
        365
        - (datetime.date(2024, start_md[0], start_md[1]) - datetime.date(2024, 1, 1)).days
        + (datetime.date(2024, end_md[0], end_md[1]) - datetime.date(2024, 1, 1)).days
        + 1
    )

# ----------------------------------------------------------------------------
# 연도별 평균기온 집계
# ----------------------------------------------------------------------------
yearly = (
    period_df.groupby("연도")
    .agg(평균기온=("평균기온", "mean"), 관측일수=("평균기온", "count"))
    .reset_index()
)

# 기간의 80% 이상 데이터가 있는 연도만 신뢰 (결측이 많은 해 제외)
yearly = yearly[yearly["관측일수"] >= expected_days * 0.8]

st.subheader("② 결과")

if yearly.empty:
    st.warning("선택한 기간에 해당하는 데이터가 충분하지 않습니다. 기간을 다시 선택해주세요.")
else:
    hottest = yearly.loc[yearly["평균기온"].idxmax()]
    coldest = yearly.loc[yearly["평균기온"].idxmin()]

    c1, c2, c3 = st.columns(3)
    c1.metric("🔥 가장 더웠던 연도", f"{int(hottest['연도'])}년", f"{hottest['평균기온']:.1f}°C")
    c2.metric("🧊 가장 시원했던 연도", f"{int(coldest['연도'])}년", f"{coldest['평균기온']:.1f}°C")
    c3.metric("📊 전체 기간 평균", f"{yearly['평균기온'].mean():.1f}°C")

    st.markdown(
        f"**{start_date.strftime('%m월 %d일')} ~ {end_date.strftime('%m월 %d일')}** 기간을 기준으로 "
        f"**{int(hottest['연도'])}년**이 평균기온 **{hottest['평균기온']:.1f}°C**로 가장 더웠습니다."
    )

    # 연도별 평균기온 막대 그래프 (Streamlit 내장 차트만 사용, 별도 라이브러리 없음)
    chart_data = yearly.set_index("연도")[["평균기온"]].sort_index()
    st.bar_chart(chart_data, height=380, color="#ff6b3d")

    # 연도별 순위 표 (더운 순 정렬, 가장 더운 해 강조)
    with st.expander("연도별 상세 순위 보기 (더운 순)"):
        ranked = yearly.sort_values("평균기온", ascending=False).reset_index(drop=True)
        ranked.index = ranked.index + 1
        ranked = ranked.rename(columns={"연도": "연도", "평균기온": "평균기온(°C)", "관측일수": "관측일수"})
        styled = ranked.style.format({"평균기온(°C)": "{:.1f}"}).highlight_max(
            subset=["평균기온(°C)"], color="#ffd9c7"
        )
        st.dataframe(styled, use_container_width=True)

    with st.expander("선택 기간 원본 데이터 보기"):
        st.dataframe(
            period_df[["날짜", "평균기온", "최저기온", "최고기온"]].sort_values("날짜"),
            use_container_width=True,
        )
