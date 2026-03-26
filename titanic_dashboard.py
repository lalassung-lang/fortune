import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns

# ─── 페이지 설정 ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="타이타닉 데이터 대시보드",
    page_icon="🚢",
    layout="wide",
)

# ─── 다크·소버 테마 CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp                          { background-color: #3A3D4A; }
    section[data-testid="stSidebar"]{ background-color: #2E3140; border-right: 1px solid #454859; }
    .stSidebar label, .stSidebar p  { color: #A8AEBF !important; }
    h4, h3, h2, h1                  { color: #D4D8E2 !important; }
    p, li                           { color: #A8AEBF; }
    hr                              { border-color: #454859 !important; }
    .stDownloadButton button        { background-color: #454859; color:#C0C5D0;
                                      border:1px solid #565A6E; border-radius:6px; }
    .stDownloadButton button:hover  { background-color: #565A6E; }
    div[data-testid="stExpander"]   { background-color: #2E3140;
                                      border: 1px solid #454859; border-radius:8px; }
</style>
""", unsafe_allow_html=True)

# ─── 공통 차트 레이아웃 ────────────────────────────────────────────────────────
CHART_BASE = dict(
    paper_bgcolor="#3A3D4A",
    plot_bgcolor="#2E3140",
    font=dict(color="#A8AEBF", size=12),
    xaxis=dict(gridcolor="#454859", linecolor="#454859", tickfont=dict(color="#A8AEBF")),
    yaxis=dict(gridcolor="#454859", linecolor="#454859", tickfont=dict(color="#A8AEBF")),
    legend=dict(bgcolor="#3A3D4A", bordercolor="#454859", borderwidth=1,
                font=dict(color="#C0C5D0")),
    margin=dict(t=16, b=16, l=8, r=8),
)

def apply_theme(fig, height=320):
    fig.update_layout(**CHART_BASE, height=height)
    return fig

# ─── 색상 팔레트 (톤다운) ──────────────────────────────────────────────────────
COLOR_SURVIVED = {"생존": "#3D7A6E", "사망": "#7A2A35"}
COLOR_CLASS    = {"1등석": "#3E5F8A", "2등석": "#5C4A82", "3등석": "#8A6030"}
COLOR_SEX      = {"남성": "#3E5F8A", "여성": "#6A3A60"}

KPI_COLORS = {
    "총 탑승객": "#4A5568",
    "생존자":    "#3D7A6E",
    "사망자":    "#7A2A35",
    "생존율":    "#3E5F8A",
    "평균 운임": "#5C4A82",
}

# ─── 데이터 로드 ───────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = sns.load_dataset("titanic")
    df["age"]         = df["age"].fillna(df["age"].median())
    df["embarked"]    = df["embarked"].fillna(df["embarked"].mode()[0])
    df["embark_town"] = df["embark_town"].fillna(df["embark_town"].mode()[0])
    df["survived_label"] = df["survived"].map({0: "사망", 1: "생존"})
    df["pclass_label"]   = df["pclass"].map({1: "1등석", 2: "2등석", 3: "3등석"})
    df["sex_label"]      = df["sex"].map({"male": "남성", "female": "여성"})
    df["embarked_label"] = df["embark_town"].map({
        "Southampton": "사우샘프턴",
        "Cherbourg":   "셰르부르",
        "Queenstown":  "퀸스타운",
    })
    return df

df = load_data()

# ─── 헤더 ──────────────────────────────────────────────────────────────────────
st.markdown("""
<h1 style='text-align:center; color:#8B9BB4; letter-spacing:2px;'>🚢 타이타닉 데이터 대시보드</h1>
<p style='text-align:center; color:#4A5568; font-size:15px; margin-top:-6px;'>
    1912년 4월 15일 · 탑승객 891명 데이터 분석
</p>
""", unsafe_allow_html=True)

st.markdown("<hr style='border-color:#1E2235; margin: 8px 0 16px 0;'>", unsafe_allow_html=True)

# ─── 사이드바 필터 ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<h3 style='color:#8B9BB4;'>⚙️ 필터</h3>", unsafe_allow_html=True)

    class_filter = st.multiselect(
        "객실 등급",
        options=["1등석", "2등석", "3등석"],
        default=["1등석", "2등석", "3등석"],
    )
    sex_filter = st.multiselect(
        "성별",
        options=["남성", "여성"],
        default=["남성", "여성"],
    )
    age_range = st.slider(
        "나이 범위",
        min_value=int(df["age"].min()),
        max_value=int(df["age"].max()),
        value=(int(df["age"].min()), int(df["age"].max())),
    )
    survived_filter = st.multiselect(
        "생존 여부",
        options=["생존", "사망"],
        default=["생존", "사망"],
    )
    st.markdown("<hr style='border-color:#1E2235;'>", unsafe_allow_html=True)
    st.caption("데이터 출처: Seaborn Titanic Dataset")

# ─── 필터 적용 ─────────────────────────────────────────────────────────────────
filtered = df[
    df["pclass_label"].isin(class_filter) &
    df["sex_label"].isin(sex_filter) &
    df["age"].between(age_range[0], age_range[1]) &
    df["survived_label"].isin(survived_filter)
]

if filtered.empty:
    st.warning("선택한 필터 조건에 맞는 데이터가 없습니다. 필터를 조정해 주세요.")
    st.stop()

# ─── KPI 카드 ──────────────────────────────────────────────────────────────────
total     = len(filtered)
survived  = filtered["survived"].sum()
dead      = total - survived
surv_rate = survived / total * 100 if total else 0
avg_fare  = filtered["fare"].mean()

def kpi_card(col, title, value, color):
    col.markdown(f"""
    <div style='background:#2E3140; border-left:3px solid {color};
                border-radius:6px; padding:14px 18px; text-align:center;'>
        <p style='color:#8A90A0; margin:0; font-size:12px; letter-spacing:1px;
                  text-transform:uppercase;'>{title}</p>
        <p style='color:{color}; margin:4px 0 0 0; font-size:24px; font-weight:700;'>{value}</p>
    </div>
    """, unsafe_allow_html=True)

k1, k2, k3, k4, k5 = st.columns(5)
kpi_card(k1, "총 탑승객",  f"{total:,}명",         KPI_COLORS["총 탑승객"])
kpi_card(k2, "생존자",     f"{survived:,}명",        KPI_COLORS["생존자"])
kpi_card(k3, "사망자",     f"{dead:,}명",            KPI_COLORS["사망자"])
kpi_card(k4, "생존율",     f"{surv_rate:.1f}%",      KPI_COLORS["생존율"])
kpi_card(k5, "평균 운임",  f"£{avg_fare:.1f}",       KPI_COLORS["평균 운임"])

st.markdown("<br>", unsafe_allow_html=True)

# ─── 행 1: 파이 / 성별 생존 / 등급별 생존 ────────────────────────────────────
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("#### 생존 여부 비율")
    fig = px.pie(
        filtered, names="survived_label",
        color="survived_label", color_discrete_map=COLOR_SURVIVED,
        hole=0.5,
    )
    fig.update_traces(textposition="outside", textinfo="percent+label",
                      textfont=dict(color="#8B9BB4"))
    fig.update_layout(**CHART_BASE, showlegend=False, height=300)
    st.plotly_chart(fig, width="stretch")

with c2:
    st.markdown("#### 성별 생존자 수")
    grp = filtered.groupby(["sex_label", "survived_label"]).size().reset_index(name="count")
    fig = px.bar(grp, x="sex_label", y="count",
                 color="survived_label", barmode="group",
                 color_discrete_map=COLOR_SURVIVED,
                 labels={"sex_label": "성별", "count": "인원수", "survived_label": ""})
    apply_theme(fig, 300)
    fig.update_layout(legend_title_text="")
    st.plotly_chart(fig, width="stretch")

with c3:
    st.markdown("#### 객실 등급별 생존자 수")
    grp = filtered.groupby(["pclass_label", "survived_label"]).size().reset_index(name="count")
    fig = px.bar(grp, x="pclass_label", y="count",
                 color="survived_label", barmode="stack",
                 color_discrete_map=COLOR_SURVIVED,
                 labels={"pclass_label": "등급", "count": "인원수", "survived_label": ""})
    apply_theme(fig, 300)
    fig.update_layout(legend_title_text="")
    st.plotly_chart(fig, width="stretch")

# ─── 행 2: 나이 분포 / 운임 박스 ──────────────────────────────────────────────
c4, c5 = st.columns(2)

with c4:
    st.markdown("#### 나이 분포 (생존 여부)")
    fig = px.histogram(
        filtered, x="age", color="survived_label", nbins=30,
        color_discrete_map=COLOR_SURVIVED, barmode="overlay", opacity=0.65,
        labels={"age": "나이", "count": "인원수", "survived_label": ""},
    )
    apply_theme(fig, 320)
    fig.update_layout(legend_title_text="")
    st.plotly_chart(fig, width="stretch")

with c5:
    st.markdown("#### 운임 분포 (객실 등급)")
    fig = px.box(
        filtered, x="pclass_label", y="fare",
        color="pclass_label", color_discrete_map=COLOR_CLASS,
        labels={"pclass_label": "객실 등급", "fare": "운임 (£)"},
        points="outliers",
    )
    apply_theme(fig, 320)
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, width="stretch")

# ─── 행 3: 승선 항구 / 생존 상관관계 Top 5 히트맵 ────────────────────────────
c6, c7 = st.columns(2)

with c6:
    st.markdown("#### 승선 항구별 탑승객 수")
    grp = filtered.groupby(["embarked_label", "survived_label"]).size().reset_index(name="count")
    fig = px.bar(grp, x="embarked_label", y="count",
                 color="survived_label", barmode="stack",
                 color_discrete_map=COLOR_SURVIVED,
                 labels={"embarked_label": "승선 항구", "count": "인원수", "survived_label": ""})
    apply_theme(fig, 320)
    fig.update_layout(legend_title_text="")
    st.plotly_chart(fig, width="stretch")

with c7:
    st.markdown("#### 생존 상관관계 Top 5 — 수치 히트맵")

    # 수치 인코딩
    corr_src = filtered[["survived", "pclass", "age", "sibsp", "parch", "fare"]].copy()
    corr_src["성별(여=1)"]  = (filtered["sex"] == "female").astype(int)
    corr_src["승선항구"]    = filtered["embarked"].map({"S": 0, "C": 1, "Q": 2})
    corr_src = corr_src.rename(columns={
        "survived": "생존 여부", "pclass": "객실 등급",
        "age": "나이", "sibsp": "형제/배우자",
        "parch": "부모/자녀", "fare": "운임",
    })

    corr_matrix = corr_src.corr()

    # 생존 여부와 상관계수 절댓값 기준 Top 5 인자
    top5 = (
        corr_matrix["생존 여부"]
        .drop("생존 여부")
        .abs()
        .nlargest(5)
        .index.tolist()
    )
    sub_cols = ["생존 여부"] + top5
    sub_corr  = corr_matrix.loc[sub_cols, sub_cols]

    # 상관 순위 주석 (생존 여부 기준)
    rank_note = "  |  ".join(
        [f"#{i+1} {c}" for i, c in enumerate(top5)]
    )
    st.caption(f"생존 상관 순위 → {rank_note}")

    z_vals  = sub_corr.values
    labels  = sub_corr.columns.tolist()
    texts   = [[f"{v:.2f}" for v in row] for row in z_vals]

    fig = go.Figure(go.Heatmap(
        z=z_vals,
        x=labels,
        y=labels,
        colorscale=[
            [0.0,  "#6B1A24"],
            [0.25, "#3A2840"],
            [0.5,  "#0E1019"],
            [0.75, "#1E3A36"],
            [1.0,  "#2D6B5E"],
        ],
        zmin=-1, zmax=1,
        text=texts,
        texttemplate="%{text}",
        textfont={"size": 13, "color": "#C8D0E0"},
        colorbar=dict(
            title=dict(text="상관계수", font=dict(color="#A8AEBF")),
            tickfont=dict(color="#A8AEBF"),
            tickvals=[-1, -0.5, 0, 0.5, 1],
            ticktext=["-1.0", "-0.5", "0", "+0.5", "+1.0"],
        ),
    ))
    apply_theme(fig, 360)
    fig.update_xaxes(tickfont=dict(color="#C0C5D0"), gridcolor="#454859",
                     linecolor="#454859", side="bottom")
    fig.update_yaxes(tickfont=dict(color="#C0C5D0"), gridcolor="#454859",
                     linecolor="#454859", autorange="reversed")
    st.plotly_chart(fig, width="stretch")

# ─── 원시 데이터 테이블 ────────────────────────────────────────────────────────
st.markdown("<hr style='border-color:#1E2235; margin:8px 0;'>", unsafe_allow_html=True)
with st.expander("📋 원시 데이터 보기", expanded=False):
    display_cols = {
        "survived_label": "생존 여부",
        "pclass_label":   "객실 등급",
        "sex_label":      "성별",
        "age":            "나이",
        "sibsp":          "형제/배우자 수",
        "parch":          "부모/자녀 수",
        "fare":           "운임(£)",
        "embarked_label": "승선 항구",
    }
    show = filtered[list(display_cols.keys())].rename(columns=display_cols).reset_index(drop=True)
    st.dataframe(show, width="stretch", height=350)
    csv = show.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ CSV 다운로드", data=csv,
                       file_name="titanic_filtered.csv", mime="text/csv")
