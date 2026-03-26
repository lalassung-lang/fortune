import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import zipfile
import io
import xml.etree.ElementTree as ET

# ─── 상수 ──────────────────────────────────────────────────────────────────────
API_KEY  = "02025785edca821566ac6f0efed128856538b453"
BASE_URL = "https://opendart.fss.or.kr/api"

PBLNTF_TYPE = {
    "전체": "", "정기공시": "A", "주요사항보고": "B", "발행공시": "C",
    "지분공시": "D", "기타공시": "E", "외부감사관련": "F",
    "펀드공시": "G", "자산유동화": "H", "거래소공시": "I", "공정위공시": "J",
}

REPRT_CODE = {
    "사업보고서(연간)": "11011", "반기보고서": "11012",
    "1분기보고서": "11013",     "3분기보고서": "11014",
}

CORP_CLS_MAP = {"Y": "유가증권시장", "K": "코스닥", "N": "코넥스", "E": "기타"}

KEY_ACCOUNTS = {
    "자산총계":   ["ifrs-full_Assets",       "dart_Assets"],
    "부채총계":   ["ifrs-full_Liabilities",   "dart_Liabilities"],
    "자본총계":   ["ifrs-full_Equity",        "dart_Equity"],
    "매출액":     ["ifrs-full_Revenue",       "dart_Revenue", "ifrs-full_GrossProfit"],
    "영업이익":   ["dart_OperatingIncomeLoss", "ifrs-full_ProfitLossFromOperatingActivities"],
    "당기순이익": ["ifrs-full_ProfitLoss",    "dart_ProfitLoss"],
}

# ─── 페이지 설정 ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="OpenDART 공시 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── 스타일 ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-title  { font-size:2rem; font-weight:700; color:#1a3c6e; margin-bottom:0.2rem; }
    .sub-title   { font-size:1rem; color:#6c757d; margin-bottom:1.5rem; }
    .metric-card {
        background: linear-gradient(135deg,#1a3c6e 0%,#2563a8 100%);
        padding:1.2rem 1.5rem; border-radius:12px; color:white;
        text-align:center; margin-bottom:0.5rem;
        min-height:100px; display:flex; flex-direction:column;
        justify-content:center; align-items:center;
    }
    .metric-value { font-size:2rem; font-weight:700; }
    .metric-label { font-size:0.85rem; opacity:0.85; }
    .section-header {
        font-size:1.1rem; font-weight:600; color:#1a3c6e;
        border-left:4px solid #2563a8; padding-left:0.6rem;
        margin:1rem 0 0.8rem 0;
    }
    .stDataFrame { border-radius:8px; }
</style>
""", unsafe_allow_html=True)

# ─── 유틸 함수 ─────────────────────────────────────────────────────────────────
def fmt_stock(code: str) -> str:
    """종목코드가 있으면 반환, 없으면 '비상장'"""
    return code.strip() if code.strip() else "비상장"

def metric_card(value: str, label: str) -> str:
    return (
        f'<div class="metric-card">'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-label">{label}</div>'
        f'</div>'
    )

def classify_report(name: str) -> str:
    """보고서명 키워드로 공시 유형 분류"""
    n = str(name)
    rules = [
        (["사업보고서", "분기보고서", "반기보고서"],          "정기공시"),
        (["주요사항보고서", "주요사항"],                       "주요사항보고"),
        (["증권신고", "투자설명서", "발행"],                   "발행공시"),
        (["지분", "주식소유현황", "주식등의대량보유"],         "지분공시"),
        (["자기주식"],                                         "자기주식"),
        (["임원", "주요주주", "특수관계인"],                   "임원·주요주주"),
        (["감사보고서", "내부회계"],                           "외부감사관련"),
        (["합병", "분할", "영업양수도", "주식교환"],           "기업구조변경"),
    ]
    for keywords, label in rules:
        if any(k in n for k in keywords):
            return label
    return "기타"

def fmt_date8(val: str) -> str:
    """'YYYYMMDD' → 'YYYY-MM-DD'"""
    if val and len(val) == 8:
        return f"{val[:4]}-{val[4:6]}-{val[6:]}"
    return val

# ─── API 함수 ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def load_corp_code_map() -> pd.DataFrame:
    """DART 전체 기업코드 ZIP 다운로드 후 DataFrame 반환 (24h 캐싱)"""
    try:
        r = requests.get(f"{BASE_URL}/corpCode.xml", params={"crtfc_key": API_KEY}, timeout=30)
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            xml_name = next(n for n in z.namelist() if n.endswith(".xml"))
            with z.open(xml_name) as f:
                root = ET.parse(f).getroot()
        rows = [
            {
                "corp_code":  (item.findtext("corp_code")  or "").strip(),
                "corp_name":  (item.findtext("corp_name")  or "").strip(),
                "stock_code": (item.findtext("stock_code") or "").strip(),
            }
            for item in root.findall("list")
        ]
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"기업코드 목록 로드 실패: {e}")
        return pd.DataFrame(columns=["corp_code", "corp_name", "stock_code"])


def search_company(keyword: str, corp_map: pd.DataFrame) -> list[dict]:
    """기업명 부분 일치 검색"""
    if corp_map.empty or not keyword.strip():
        return []
    mask = corp_map["corp_name"].str.contains(keyword.strip(), case=False, na=False)
    return corp_map[mask].head(30).to_dict(orient="records")


@st.cache_data(ttl=300, show_spinner=False)
def get_company_info(corp_code: str) -> dict:
    """기업 기본정보 조회"""
    try:
        r = requests.get(
            f"{BASE_URL}/company.json",
            params={"crtfc_key": API_KEY, "corp_code": corp_code},
            timeout=10,
        )
        data = r.json()
        return data if data.get("status") == "000" else {}
    except Exception:
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def get_disclosure_list(
    corp_code: str = "", bgn_de: str = "", end_de: str = "",
    pblntf_ty: str = "", page_no: int = 1, page_count: int = 40,
) -> dict:
    """공시 목록 조회"""
    params = {
        "crtfc_key": API_KEY, "corp_code": corp_code,
        "bgn_de": bgn_de, "end_de": end_de, "pblntf_ty": pblntf_ty,
        "page_no": page_no, "page_count": page_count,
        "sort": "date", "sort_mth": "desc",
    }
    params = {k: v for k, v in params.items() if v not in ("", 0)}
    try:
        return requests.get(f"{BASE_URL}/list.json", params=params, timeout=10).json()
    except Exception as e:
        return {"status": "error", "message": str(e)}


@st.cache_data(ttl=600, show_spinner=False)
def get_financial_single(
    corp_code: str, bsns_year: str, reprt_code: str, fs_div: str = "CFS"
) -> dict:
    """단일 재무제표 조회"""
    try:
        return requests.get(
            f"{BASE_URL}/fnlttSinglAcnt.json",
            params={
                "crtfc_key": API_KEY, "corp_code": corp_code,
                "bsns_year": bsns_year, "reprt_code": reprt_code, "fs_div": fs_div,
            },
            timeout=15,
        ).json()
    except Exception as e:
        return {"status": "error", "message": str(e)}


@st.cache_data(ttl=300, show_spinner=False)
def get_major_shareholder(corp_code: str) -> dict:
    """최대주주 현황 조회"""
    try:
        return requests.get(
            f"{BASE_URL}/hyslrSttus.json",
            params={"crtfc_key": API_KEY, "corp_code": corp_code},
            timeout=10,
        ).json()
    except Exception:
        return {}

# ─── 기업코드 맵 로딩 (앱 시작 시 1회, 이후 캐싱) ────────────────────────────
with st.spinner("DART 기업코드 목록 로딩 중... (최초 1회, 이후 캐싱)"):
    corp_map = load_corp_code_map()

# ─── 사이드바 ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 OpenDART 공시 대시보드")
    st.markdown("---")

    menu = st.radio("메뉴 선택", ["공시 검색", "기업 분석", "재무 정보"], label_visibility="collapsed")

    st.markdown("---")
    st.markdown("#### 날짜 범위 (공시 검색)")
    col_s, col_e = st.columns(2)
    with col_s:
        start_date = st.date_input("시작일", value=datetime.today() - timedelta(days=30))
    with col_e:
        end_date = st.date_input("종료일", value=datetime.today())

    st.markdown("#### 공시 유형")
    pblntf_label = st.selectbox("공시 유형", list(PBLNTF_TYPE.keys()), label_visibility="collapsed")
    pblntf_code  = PBLNTF_TYPE[pblntf_label]

    st.markdown("---")
    st.caption("데이터 출처: [금융감독원 DART](https://opendart.fss.or.kr)")

# ─── 메인 타이틀 ───────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">📊 OpenDART 공시 대시보드</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">금융감독원 전자공시시스템(DART) 기반 기업 공시 분석 플랫폼</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 탭 1: 공시 검색
# ══════════════════════════════════════════════════════════════════════════════
if menu == "공시 검색":
    st.markdown('<div class="section-header">공시 검색</div>', unsafe_allow_html=True)

    with st.form("search_form"):
        col1, col2, col3 = st.columns([2, 1, 0.5])
        with col1:
            keyword = st.text_input(
                "회사명 검색 (비워두면 전체 조회)",
                placeholder="예: 삼성전자, 카카오, LG에너지솔루션",
            )
        with col2:
            page_count = st.selectbox("조회 건수", [20, 40, 100], index=1)
        with col3:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            search_btn = st.form_submit_button("🔍 공시 조회", type="primary", use_container_width=True)

    # 검색 버튼 클릭 시 session_state에 검색 조건 저장
    if search_btn:
        st.session_state["s_keyword"]    = keyword
        st.session_state["s_page_count"] = page_count
        st.session_state["s_bgn"]        = start_date.strftime("%Y%m%d")
        st.session_state["s_end"]        = end_date.strftime("%Y%m%d")
        st.session_state["s_pblntf"]     = pblntf_code
        if keyword.strip():
            st.session_state["s_companies"] = search_company(keyword.strip(), corp_map)
        else:
            st.session_state["s_companies"] = []

    # 이전 검색 결과가 없으면 중단
    if "s_bgn" not in st.session_state:
        st.stop()

    # session_state에서 검색 조건 복원
    s_keyword    = st.session_state["s_keyword"]
    s_page_count = st.session_state["s_page_count"]
    s_bgn        = st.session_state["s_bgn"]
    s_end        = st.session_state["s_end"]
    s_pblntf     = st.session_state["s_pblntf"]
    s_companies  = st.session_state["s_companies"]

    # 기업 선택 (드롭다운 변경 시에도 유지)
    corp_code_filter = ""
    if s_keyword.strip():
        if not s_companies:
            st.warning("검색된 기업이 없습니다.")
            st.stop()
        if len(s_companies) == 1:
            corp_code_filter = s_companies[0]["corp_code"]
            st.info(f"기업: **{s_companies[0]['corp_name']}** (종목코드: {fmt_stock(s_companies[0]['stock_code'])})")
        else:
            options = {f"{c['corp_name']} ({fmt_stock(c['stock_code'])})": c["corp_code"] for c in s_companies}
            corp_code_filter = options[st.selectbox("검색된 기업 선택", list(options.keys()))]

    # 공시 조회
    with st.spinner("공시 데이터 조회 중..."):
        result = get_disclosure_list(
            corp_code=corp_code_filter,
            bgn_de=s_bgn,
            end_de=s_end,
            pblntf_ty=s_pblntf,
            page_count=s_page_count,
        )

    if result.get("status") == "013":
        st.info("조회 결과가 없습니다. 검색 조건을 변경해 주세요.")
        st.stop()
    if result.get("status") != "000":
        st.error(f"API 오류: {result.get('message', '알 수 없는 오류')}")
        st.stop()

    items = result.get("list", [])
    total = result.get("total_count", len(items))

    # 요약 지표
    m1, m2, m3, m4 = st.columns(4)
    unique_corps = len({i.get("corp_name", "") for i in items})
    period       = f"{start_date.strftime('%m/%d')} ~ {end_date.strftime('%m/%d')}"
    for col, val, label in zip(
        [m1, m2, m3, m4],
        [f"{total:,}", str(unique_corps), str(len(items)), period],
        ["총 공시 건수", "공시 기업 수", "현재 페이지 건수", "조회 기간"],
    ):
        col.markdown(metric_card(val, label), unsafe_allow_html=True)

    if not items:
        st.stop()

    df = pd.DataFrame(items)
    if "rcept_dt" in df.columns:
        df["접수일"] = pd.to_datetime(df["rcept_dt"], format="%Y%m%d", errors="coerce").dt.strftime("%Y-%m-%d")
    if "report_nm" in df.columns:
        df["공시유형명"] = df["report_nm"].apply(classify_report)

    # 차트
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.markdown('<div class="section-header">공시 유형별 분포</div>', unsafe_allow_html=True)
        if "공시유형명" in df.columns:
            type_cnt = df["공시유형명"].value_counts().reset_index()
            type_cnt.columns = ["공시유형", "건수"]
            fig = px.pie(
                type_cnt, names="공시유형", values="건수",
                color_discrete_sequence=px.colors.sequential.Blues_r, hole=0.4,
            )
            fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=260)
            st.plotly_chart(fig, use_container_width=True)

    with col_chart2:
        st.markdown('<div class="section-header">일별 공시 건수 추이</div>', unsafe_allow_html=True)
        if "접수일" in df.columns:
            daily = df.groupby("접수일").size().reset_index(name="건수")
            fig2 = px.bar(daily, x="접수일", y="건수", color_discrete_sequence=["#2563a8"])
            fig2.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=260, xaxis_title="", yaxis_title="건수")
            st.plotly_chart(fig2, use_container_width=True)

    # 공시 목록 테이블
    st.markdown('<div class="section-header">공시 목록</div>', unsafe_allow_html=True)
    tbl_col_map = {
        "접수일": "접수일", "corp_name": "기업명", "공시유형명": "공시유형",
        "report_nm": "보고서명", "flr_nm": "공시제출인", "rcept_no": "접수번호",
    }
    display_cols = [c for c in tbl_col_map if c in df.columns]
    show_df = df[display_cols].rename(columns=tbl_col_map).copy()
    if "rcept_no" in df.columns:
        show_df["공시 링크"] = df["rcept_no"].apply(
            lambda x: f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={x}"
        )
    st.dataframe(show_df, use_container_width=True, height=420)


# ══════════════════════════════════════════════════════════════════════════════
# 탭 2: 기업 분석
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "기업 분석":
    st.markdown('<div class="section-header">기업 기본 정보 조회</div>', unsafe_allow_html=True)

    col_inp, col_btn = st.columns([4, 1])
    with col_inp:
        corp_search = st.text_input("기업명 입력", placeholder="예: 삼성전자, 현대차, NAVER", label_visibility="collapsed")
    with col_btn:
        find_btn = st.button("검색", type="primary", use_container_width=True)

    if not (find_btn and corp_search.strip()):
        st.stop()

    companies = search_company(corp_search.strip(), corp_map)
    if not companies:
        st.warning("검색된 기업이 없습니다.")
        st.stop()

    options    = {f"{c['corp_name']} ({fmt_stock(c['stock_code'])})": c["corp_code"] for c in companies}
    corp_code  = options[st.selectbox("기업 선택", list(options.keys()))]

    with st.spinner("기업 정보 로딩 중..."):
        info = get_company_info(corp_code)

    if not info:
        st.error("기업 정보를 불러오지 못했습니다.")
        st.stop()

    # 기업 개요
    st.markdown('<div class="section-header">기업 개요</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    field_groups = [
        [("법인명", "corp_name"), ("영문명", "engl_nm"), ("종목코드", "stock_code"), ("법인구분", "corp_cls")],
        [("대표이사", "ceo_nm"),  ("설립일", "est_dt"),  ("결산월", "acc_mt"),       ("업종코드", "induty_code")],
        [("주소", "adres"),       ("홈페이지", "hm_url"), ("전화번호", "phn_no"),     ("IR 담당부서", "ir_url")],
    ]
    for col_obj, fields in zip([c1, c2, c3], field_groups):
        with col_obj:
            for label, key in fields:
                val = info.get(key, "-") or "-"
                if key == "est_dt":
                    val = fmt_date8(val)
                elif key == "corp_cls":
                    val = CORP_CLS_MAP.get(val, val)
                elif key == "hm_url" and val != "-":
                    val = f"[바로가기]({val})"
                st.markdown(f"**{label}**: {val}")

    # 최근 30일 공시
    st.markdown('<div class="section-header">최근 30일 공시 현황</div>', unsafe_allow_html=True)
    bgn_30 = (datetime.today() - timedelta(days=30)).strftime("%Y%m%d")
    end_30 = datetime.today().strftime("%Y%m%d")
    with st.spinner("공시 목록 조회 중..."):
        disc = get_disclosure_list(corp_code=corp_code, bgn_de=bgn_30, end_de=end_30, page_count=20)

    if disc.get("status") == "000" and disc.get("list"):
        ddf = pd.DataFrame(disc["list"])
        ddf["접수일"] = pd.to_datetime(ddf["rcept_dt"], format="%Y%m%d", errors="coerce").dt.strftime("%Y-%m-%d")
        st.dataframe(
            ddf[["접수일", "report_nm", "flr_nm"]].rename(columns={"report_nm": "보고서명", "flr_nm": "공시제출인"}),
            use_container_width=True, height=300,
        )
    else:
        st.info("최근 30일간 공시 내역이 없습니다.")

    # 최대주주 현황
    st.markdown('<div class="section-header">최대주주 현황</div>', unsafe_allow_html=True)
    with st.spinner("최대주주 조회 중..."):
        shareholder_data = get_major_shareholder(corp_code)

    if shareholder_data.get("status") == "000" and shareholder_data.get("list"):
        sdf = pd.DataFrame(shareholder_data["list"])
        col_map = {
            "nm": "주주명", "relate": "관계", "stock_knd": "주식종류",
            "bsis_posesn_stock_co":       "기초보유주식수",
            "bsis_posesn_stock_qota_rt":  "기초지분율(%)",
            "trmend_posesn_stock_co":     "기말보유주식수",
            "trmend_posesn_stock_qota_rt":"기말지분율(%)",
        }
        available = {k: v for k, v in col_map.items() if k in sdf.columns}
        st.dataframe(sdf[list(available.keys())].rename(columns=available), use_container_width=True)

        if "nm" in sdf.columns and "trmend_posesn_stock_qota_rt" in sdf.columns:
            sdf["지분율"] = pd.to_numeric(sdf["trmend_posesn_stock_qota_rt"], errors="coerce")
            sdf_valid = sdf[sdf["지분율"].notna() & (sdf["지분율"] > 0)]
            if not sdf_valid.empty:
                fig_s = px.pie(
                    sdf_valid, names="nm", values="지분율", title="주요 주주 지분율",
                    color_discrete_sequence=px.colors.sequential.Blues_r, hole=0.35,
                )
                fig_s.update_layout(height=350)
                st.plotly_chart(fig_s, use_container_width=True)
    else:
        st.info("최대주주 정보가 없습니다.")


# ══════════════════════════════════════════════════════════════════════════════
# 탭 3: 재무 정보
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "재무 정보":
    st.markdown('<div class="section-header">재무제표 조회</div>', unsafe_allow_html=True)

    col_a, col_b, col_c, col_d = st.columns([3, 1, 2, 1])
    with col_a:
        fin_corp  = st.text_input("기업명", placeholder="예: 삼성전자")
    with col_b:
        fin_year  = st.selectbox("사업연도", [str(y) for y in range(datetime.today().year - 1, 2014, -1)])
    with col_c:
        fin_reprt = st.selectbox("보고서 구분", list(REPRT_CODE.keys()))
    with col_d:
        fin_fs    = st.selectbox("재무제표", ["연결(CFS)", "별도(OFS)"])
    fs_div = "CFS" if "CFS" in fin_fs else "OFS"

    fin_btn = st.button("📈 재무 데이터 조회", type="primary", use_container_width=True)

    if not (fin_btn and fin_corp.strip()):
        st.stop()

    comps = search_company(fin_corp.strip(), corp_map)
    if not comps:
        st.warning("기업을 찾을 수 없습니다.")
        st.stop()

    opts   = {f"{c['corp_name']} ({fmt_stock(c['stock_code'])})": c["corp_code"] for c in comps}
    c_code = opts[st.selectbox("기업 선택", list(opts.keys()))]

    with st.spinner("재무 데이터 조회 중..."):
        fin_data = get_financial_single(c_code, fin_year, REPRT_CODE[fin_reprt], fs_div)

    if fin_data.get("status") == "013":
        st.warning("해당 기간의 재무 데이터가 없습니다. 연도나 보고서 유형을 변경해 보세요.")
        st.stop()
    if fin_data.get("status") != "000" or not fin_data.get("list"):
        st.error(f"조회 실패: {fin_data.get('message', '알 수 없는 오류')}")
        st.stop()

    fdf = pd.DataFrame(fin_data["list"])

    # 주요 계정 요약
    summary_rows = []
    for kor_nm, tags in KEY_ACCOUNTS.items():
        row = fdf[fdf["account_id"].isin(tags)]
        if row.empty:
            continue
        r = row.iloc[0]
        try:
            cur = int(str(r.get("thstrm_amount", "0") or "0").replace(",", ""))
            prv = int(str(r.get("frmtrm_amount", "0") or "0").replace(",", ""))
            chg = round((cur - prv) / abs(prv) * 100, 2) if prv else 0
            summary_rows.append({"계정": kor_nm, "당기(원)": cur, "전기(원)": prv, "증감률(%)": chg})
        except Exception:
            pass

    if summary_rows:
        smdf = pd.DataFrame(summary_rows)

        # 주요 재무 지표 카드
        st.markdown('<div class="section-header">주요 재무 지표</div>', unsafe_allow_html=True)
        for col_obj, row in zip(st.columns(len(summary_rows)), summary_rows):
            val_b      = row["당기(원)"] / 1e8
            chg_color  = "#4ade80" if row["증감률(%)"] >= 0 else "#f87171"
            arrow      = "▲" if row["증감률(%)"] >= 0 else "▼"
            col_obj.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-label">{row["계정"]}</div>'
                f'<div class="metric-value" style="font-size:1.3rem">{val_b:,.0f}억</div>'
                f'<div style="color:{chg_color};font-size:0.85rem">{arrow} {abs(row["증감률(%)"]):.1f}%</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # 당기 vs 전기 비교 차트
        st.markdown('<div class="section-header">당기 vs 전기 비교</div>', unsafe_allow_html=True)
        smdf["당기(억원)"] = smdf["당기(원)"] / 1e8
        smdf["전기(억원)"] = smdf["전기(원)"] / 1e8
        fig_bar = go.Figure([
            go.Bar(name="전기", x=smdf["계정"], y=smdf["전기(억원)"], marker_color="#93c5fd"),
            go.Bar(name="당기", x=smdf["계정"], y=smdf["당기(억원)"], marker_color="#1d4ed8"),
        ])
        fig_bar.update_layout(
            barmode="group", height=350,
            margin=dict(t=20, b=20, l=20, r=20), yaxis_title="억원",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # 전체 재무제표 테이블
        st.markdown('<div class="section-header">전체 재무제표 상세</div>', unsafe_allow_html=True)
        tbl_cols = {
            "account_nm": "계정명", "thstrm_amount": "당기금액",
            "frmtrm_amount": "전기금액", "bfefrmtrm_amount": "전전기금액", "currency": "통화",
        }
        avail = {k: v for k, v in tbl_cols.items() if k in fdf.columns}
        st.dataframe(fdf[list(avail.keys())].rename(columns=avail), use_container_width=True, height=400)

# ─── 푸터 ──────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("본 대시보드는 금융감독원 DART OpenAPI를 활용하여 제작되었습니다. | 데이터는 참고용이며 투자 결정에 활용 시 주의가 필요합니다.")
