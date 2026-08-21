import streamlit as st
import pandas as pd
import plotly.express as px

# -------------------------------------------------
# 기본 설정
# -------------------------------------------------
st.set_page_config(
    page_title="업무지원 요청 현황 대시보드",
    page_icon="📊",
    layout="wide"
)

st.title("📊 업무지원 요청 현황 대시보드")
st.caption("CSV 파일을 업로드하면 업무지원 요청 현황을 자동으로 시각화합니다.")


# -------------------------------------------------
# CSV 읽기 함수
# -------------------------------------------------
@st.cache_data
def load_csv(file):
    """
    UTF-8 계열을 우선 사용하고,
    필요하면 CP949도 시도합니다.
    """
    try:
        return pd.read_csv(file, encoding="utf-8-sig")
    except UnicodeDecodeError:
        file.seek(0)
        return pd.read_csv(file, encoding="cp949")


# -------------------------------------------------
# 파일 업로드
# -------------------------------------------------
uploaded_file = st.file_uploader(
    "업무지원 요청 CSV 파일을 업로드하세요.",
    type=["csv"]
)

if uploaded_file is None:
    st.info("위에서 CSV 파일을 업로드하면 대시보드가 표시됩니다.")
    st.stop()


# -------------------------------------------------
# 데이터 로드
# -------------------------------------------------
try:
    df = load_csv(uploaded_file)
except Exception as e:
    st.error(f"CSV 파일을 읽는 중 오류가 발생했습니다: {e}")
    st.stop()


# -------------------------------------------------
# 필수 컬럼 확인
# -------------------------------------------------
required_columns = [
    "request_id",
    "request_date",
    "category",
    "summary",
    "urgency",
    "status",
    "ai_handling"
]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    st.error(
        "CSV 파일에 필요한 컬럼이 없습니다.\n\n"
        f"누락된 컬럼: {', '.join(missing_columns)}"
    )
    st.stop()


# -------------------------------------------------
# 데이터 전처리
# -------------------------------------------------
df["request_date"] = pd.to_datetime(
    df["request_date"],
    errors="coerce"
)

# 문자열 컬럼 공백 제거
text_columns = [
    "request_id",
    "category",
    "summary",
    "urgency",
    "status",
    "ai_handling"
]

for col in text_columns:
    df[col] = df[col].fillna("").astype(str).str.strip()


# -------------------------------------------------
# 사이드바 필터
# -------------------------------------------------
st.sidebar.header("🔎 데이터 필터")

category_options = sorted(
    df["category"].dropna().unique().tolist()
)

status_options = sorted(
    df["status"].dropna().unique().tolist()
)

urgency_options = sorted(
    df["urgency"].dropna().unique().tolist()
)

ai_options = sorted(
    df["ai_handling"].dropna().unique().tolist()
)


selected_categories = st.sidebar.multiselect(
    "업무분류",
    category_options,
    default=category_options
)

selected_status = st.sidebar.multiselect(
    "처리상태",
    status_options,
    default=status_options
)

selected_urgency = st.sidebar.multiselect(
    "긴급도",
    urgency_options,
    default=urgency_options
)

selected_ai = st.sidebar.multiselect(
    "AI 처리 기준",
    ai_options,
    default=ai_options
)


# 날짜 필터
valid_dates = df["request_date"].dropna()

if not valid_dates.empty:
    min_date = valid_dates.min().date()
    max_date = valid_dates.max().date()

    selected_dates = st.sidebar.date_input(
        "요청기간",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
else:
    selected_dates = None


# -------------------------------------------------
# 필터 적용
# -------------------------------------------------
filtered_df = df[
    df["category"].isin(selected_categories)
    & df["status"].isin(selected_status)
    & df["urgency"].isin(selected_urgency)
    & df["ai_handling"].isin(selected_ai)
].copy()


if (
    selected_dates
    and isinstance(selected_dates, (tuple, list))
    and len(selected_dates) == 2
):
    start_date = pd.Timestamp(selected_dates[0])
    end_date = pd.Timestamp(selected_dates[1])

    filtered_df = filtered_df[
        (filtered_df["request_date"] >= start_date)
        & (filtered_df["request_date"] <= end_date)
    ]


# -------------------------------------------------
# KPI 계산
# -------------------------------------------------
total_count = len(filtered_df)

completed_count = (
    filtered_df["status"] == "완료"
).sum()

incomplete_count = (
    filtered_df["status"] != "완료"
).sum()

urgent_incomplete_count = (
    (filtered_df["urgency"] == "상")
    & (filtered_df["status"] != "완료")
).sum()


# -------------------------------------------------
# KPI 표시
# -------------------------------------------------
st.subheader("📌 주요 현황")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "전체 요청",
    f"{total_count:,}건"
)

col2.metric(
    "완료",
    f"{completed_count:,}건"
)

col3.metric(
    "처리중 / 대기",
    f"{incomplete_count:,}건"
)

col4.metric(
    "🚨 긴급 미완료",
    f"{urgent_incomplete_count:,}건"
)

st.divider()


# -------------------------------------------------
# 데이터가 없는 경우
# -------------------------------------------------
if filtered_df.empty:
    st.warning("현재 조건에 해당하는 데이터가 없습니다.")
    st.stop()


# -------------------------------------------------
# 상태 / 업무분류 차트
# -------------------------------------------------
left, right = st.columns(2)


with left:
    st.subheader("처리 상태")

    status_count = (
        filtered_df["status"]
        .value_counts()
        .reset_index()
    )

    status_count.columns = [
        "status",
        "count"
    ]

    fig_status = px.pie(
        status_count,
        names="status",
        values="count",
        hole=0.45
    )

    fig_status.update_traces(
        textposition="inside",
        textinfo="label+percent"
    )

    fig_status.update_layout(
        margin=dict(
            l=10,
            r=10,
            t=20,
            b=10
        )
    )

    st.plotly_chart(
        fig_status,
        use_container_width=True
    )


with right:
    st.subheader("업무분류별 요청")

    category_count = (
        filtered_df["category"]
        .value_counts()
        .reset_index()
    )

    category_count.columns = [
        "category",
        "count"
    ]

    fig_category = px.bar(
        category_count,
        x="category",
        y="count",
        text="count"
    )

    fig_category.update_layout(
        xaxis_title="업무분류",
        yaxis_title="요청 건수",
        showlegend=False,
        margin=dict(
            l=10,
            r=10,
            t=20,
            b=10
        )
    )

    fig_category.update_traces(
        textposition="outside"
    )

    st.plotly_chart(
        fig_category,
        use_container_width=True
    )


# -------------------------------------------------
# 긴급도 / AI 처리기준 차트
# -------------------------------------------------
left, right = st.columns(2)


with left:
    st.subheader("긴급도별 요청")

    urgency_order = ["상", "보통", "하"]

    urgency_count = (
        filtered_df["urgency"]
        .value_counts()
        .reindex(urgency_order)
        .fillna(0)
        .reset_index()
    )

    urgency_count.columns = [
        "urgency",
        "count"
    ]

    fig_urgency = px.bar(
        urgency_count,
        x="urgency",
        y="count",
        text="count"
    )

    fig_urgency.update_layout(
        xaxis_title="긴급도",
        yaxis_title="요청 건수",
        showlegend=False
    )

    fig_urgency.update_traces(
        textposition="outside"
    )

    st.plotly_chart(
        fig_urgency,
        use_container_width=True
    )


with right:
    st.subheader("AI 처리 기준")

    ai_count = (
        filtered_df["ai_handling"]
        .value_counts()
        .reset_index()
    )

    ai_count.columns = [
        "ai_handling",
        "count"
    ]

    fig_ai = px.pie(
        ai_count,
        names="ai_handling",
        values="count"
    )

    fig_ai.update_traces(
        textposition="inside",
        textinfo="label+percent"
    )

    st.plotly_chart(
        fig_ai,
        use_container_width=True
    )


# -------------------------------------------------
# 날짜별 추이
# -------------------------------------------------
st.subheader("📈 날짜별 요청 추이")

daily_count = (
    filtered_df
    .dropna(subset=["request_date"])
    .groupby(
        filtered_df["request_date"].dt.date
    )
    .size()
    .reset_index(name="count")
)

daily_count.columns = [
    "request_date",
    "count"
]

if not daily_count.empty:

    fig_daily = px.line(
        daily_count,
        x="request_date",
        y="count",
        markers=True
    )

    fig_daily.update_layout(
        xaxis_title="요청일",
        yaxis_title="요청 건수"
    )

    st.plotly_chart(
        fig_daily,
        use_container_width=True
    )


# -------------------------------------------------
# 긴급 미완료 요청
# -------------------------------------------------
st.subheader("🚨 긴급 미완료 요청")

urgent_df = filtered_df[
    (filtered_df["urgency"] == "상")
    & (filtered_df["status"] != "완료")
].copy()

if urgent_df.empty:
    st.success("현재 긴급 미완료 요청이 없습니다.")

else:
    st.warning(
        f"긴급도가 '상'이면서 완료되지 않은 요청이 "
        f"{len(urgent_df)}건 있습니다."
    )

    st.dataframe(
        urgent_df[
            [
                "request_id",
                "request_date",
                "category",
                "summary",
                "urgency",
                "status",
                "ai_handling"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )


# -------------------------------------------------
# 전체 상세 데이터
# -------------------------------------------------
st.subheader("📋 상세 요청 목록")

display_df = filtered_df.copy()

display_df["request_date"] = (
    display_df["request_date"]
    .dt.strftime("%Y-%m-%d")
)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "request_id": "요청번호",
        "request_date": "요청일",
        "category": "업무분류",
        "summary": "요청내용",
        "urgency": "긴급도",
        "status": "상태",
        "ai_handling": "AI 처리기준"
    }
)


# -------------------------------------------------
# 필터 결과 다운로드
# -------------------------------------------------
csv = filtered_df.to_csv(
    index=False,
    encoding="utf-8-sig"
)

st.download_button(
    label="⬇️ 필터 결과 CSV 다운로드",
    data=csv,
    file_name="업무지원요청_필터결과.csv",
    mime="text/csv"
)
