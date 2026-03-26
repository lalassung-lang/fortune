import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import zipfile
import io
import xml.etree.ElementTree as ET

# ─── 페이지 설정 ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="OpenDART 공시 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── API 키 ────────────────────────────────────────────────────────────────────
API_KEY = "02025785edca821566ac6f0efed128856538b453"
BASE_URL = "https://opendart.fss.or.kr/api"

# ─── 스타일 ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-title {
        font-size: 2rem;
        font-weight: 700;
        color: #1a3c6e;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1rem;
        color: #6c757d;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #1a3c6e 0%, #2563a8 100%);
        padding: 1.2rem 1.5rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 0.5rem;
        min-height: 100px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
    }
    .metric-label {
        font-size: 0.85rem;
        opacity: 0.85;
    }
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1a3c6e;
        border-left: 4px solid #2563a8;
        padding-left: 0.6rem;
        margin: 1rem 0 0.8rem 0;
    }
    .tag-badge {
        display: inline-block;
        background: #e8f0fe;
        color: #1a3c6e;
        border-radius: 6px;
        padding: 2px 10px;
        font-size: 0.78rem;
        margin: 2px;
    }
    .stDataFrame { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ─── API 함수 ──────────────────────────────────────────────────────────────────

@st.cache_data(ttl=86400, show_spinner=False)
def load_corp_code_map() -> pd.DataFrame:
    """DART 전체 기업코드 목록 다운로드 및 파싱 (하루 1회 캐싱)
    
    corpCode.xml → ZIP → DART_CORP_CODE.xml 파싱
    반환: corp_code, corp_name, stock_code, modify_date 컬럼의 DataFrame
    """
    url = f"{BASE_URL}/corpCode.xml"
    params = {"crtfc_key": API_KEY}
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            xml_filename = [n for n in z.namelist() if n.endswith(".xml")][0]
            with z.open(xml_filename) as f:
                tree = ET.parse(f)
        root = tree.getroot()
        rows = []
        for item in root.findall("list"):
            rows.append({
                "corp_code": (item.findtext("corp_code") or "").strip(),
                "corp_name": (item.findtext("corp_name") or "").strip(),
                "stock_code": (item.findtext("stock_code") or "").strip(),
                "modify_date": (item.findtext("modify_date") or "").strip(),
            })
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"기업코드 목록 로드 실패: {e}")
        return pd.DataFrame(columns=["corp_code", "corp_name", "stock_code", "modify_date"])


def search_company(keyword: str, corp_map: pd.DataFrame) -> list[dict]:
    """기업명 부분 일치 검색 (corp_map DataFrame 기반)"""
    if corp_map.empty or not keyword.strip():
        return []
    mask = corp_map["corp_name"].str.contains(keyword.strip(), case=False, na=False)
    matched = corp_map[mask].head(30)
    return matched.to_dict(orient="records")


@st.cache_data(ttl=300, show_spinner=False)
def get_company_info(corp_code: str) -> dict:
    """기업 기본 정보 조회"""
    url = f"{BASE_URL}/company.json"
    params = {"crtfc_key": API_KEY, "corp_code": corp_code}
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if data.get("status") == "000":
            return data
    except Exception:
        pass
    return {}

@st.cache_data(ttl=300, show_spinner=False)
def get_disclosure_list(
    corp_code: str = "",
    bgn_de: str = "",
    end_de: str = "",
    pblntf_ty: str = "",
    page_no: int = 1,
    page_count: int = 40,
) -> dict:
    """공시 목록 조회"""
    url = f"{BASE_URL}/list.json"
    params = {
        "crtfc_key": API_KEY,
        "corp_code": corp_code,
        "bgn_de": bgn_de,
        "end_de": end_de,
        "pblntf_ty": pblntf_ty,
        "page_no": page_no,
        "page_count": page_count,
        "sort": "date",
        "sort_mth": "desc",
    }
    params = {k: v for k, v in params.items() if v != ""}
    try:
        r = requests.get(url, params=params, timeout=10)
        return r.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

@st.cache_data(ttl=600, show_spinner=False)
def get_financial_single(corp_code: str, bsns_year: str, reprt_code: str, fs_div: str = "CFS") -> dict:
    """단일 재무제표 조회"""
    url = f"{BASE_URL}/fnlttSinglAcnt.json"
    params = {
        "crtfc_key": API_KEY,
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
        "fs_div": fs_div,
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        return r.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

@st.cache_data(ttl=300, show_spinner=False)
def get_major_shareholder(corp_code: str) -> dict:
    """최대주주 현황"""
    url = f"{BASE_URL}/hyslrSttus.json"
    params = {"crtfc_key": API_KEY, "corp_code": corp_code}
    try:
        r = requests.get(url, params=params, timeout=10)
        return r.json()
    except Exception:
        return {}

# ─── 공시 유형 코드 ────────────────────────────────────────────────────────────
PBLNTF_TYPE = {
    "전체": "",
    "정기공시": "A",
    "주요사항보고": "B",
    "발행공시": "C",
    "지분공시": "D",
    "기타공시": "E",
    "외부감사관련": "F",
    "펀드공시": "G",
    "자산유동화": "H",
    "거래소공시": "I",
    "공정위공시": "J",
}

REPRT_CODE = {
    "사업보고서(연간)": "11011",
    "반기보고서": "11012",
    "1분기보고서": "11013",
    "3분기보고서": "11014",
}

# ─── 사이드바 ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 OpenDART 공시 대시보드")
    st.markdown("---")

    menu = st.radio(
        "메뉴 선택",
        ["공시 검색", "기업 분석", "재무 정보"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("#### 날짜 범위 (공시 검색)")
    col_s, col_e = st.columns(2)
    with col_s:
        start_date = st.date_input(
            "시작일",
            value=datetime.today() - timedelta(days=30),
            label_visibility="visible",
        )
    with col_e:
        end_date = st.date_input(
            "종료일",
            value=datetime.today(),
            label_visibility="visible",
        )

    st.markdown("#### 공시 유형")
    pblntf_label = st.selectbox("공시 유형", list(PBLNTF_TYPE.keys()), label_visibility="collapsed")
    pblntf_code = PBLNTF_TYPE[pblntf_label]

    st.markdown("---")
    st.caption("데이터 출처: [금융감독원 DART](https://opendart.fss.or.kr)")

# ─── 기업코드 맵 로딩 (앱 시작 시 1회) ────────────────────────────────────────
with st.spinner("DART 기업코드 목록 로딩 중... (최초 1회, 이후 캐싱)"):
    corp_map = load_corp_code_map()

# ─── 메인 화면 ─────────────────────────────────────────────────────────────────
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
                label_visibility="visible",
            )
        with col2:
            page_count = st.selectbox("조회 건수", [20, 40, 100], index=1)
        with col3:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            search_btn = st.form_submit_button("🔍 공시 조회", type="primary", use_container_width=True)

    if search_btn or "dart_list" in st.session_state:
        corp_code_filter = ""

        if keyword.strip():
            companies = search_company(keyword.strip(), corp_map)
            if not companies:
                st.warning("검색된 기업이 없습니다.")
                st.stop()
            if len(companies) > 1:
                options = {
                    f"{c['corp_name']} ({c['stock_code'] if c['stock_code'].strip() else '비상장'})": c["corp_code"]
                    for c in companies
                }
                selected = st.selectbox("검색된 기업 선택", list(options.keys()))
                corp_code_filter = options[selected]
            else:
                corp_code_filter = companies[0]["corp_code"]
                stock = companies[0]["stock_code"].strip() or "비상장"
                st.info(f"기업: **{companies[0]['corp_name']}** (종목코드: {stock})")

        bgn = start_date.strftime("%Y%m%d")
        end = end_date.strftime("%Y%m%d")

        with st.spinner("공시 데이터 조회 중..."):
            result = get_disclosure_list(
                corp_code=corp_code_filter,
                bgn_de=bgn,
                end_de=end,
                pblntf_ty=pblntf_code,
                page_count=page_count,
            )

        if result.get("status") == "000":
            items = result.get("list", [])
            total = result.get("total_count", len(items))
            st.session_state["dart_list"] = items

            # 요약 지표
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.markdown(f'<div class="metric-card"><div class="metric-value">{total:,}</div><div class="metric-label">총 공시 건수</div></div>', unsafe_allow_html=True)
            with m2:
                unique_corps = len(set(i.get("corp_name", "") for i in items))
                st.markdown(f'<div class="metric-card"><div class="metric-value">{unique_corps}</div><div class="metric-label">공시 기업 수</div></div>', unsafe_allow_html=True)
            with m3:
                st.markdown(f'<div class="metric-card"><div class="metric-value">{len(items)}</div><div class="metric-label">현재 페이지 건수</div></div>', unsafe_allow_html=True)
            with m4:
                period = f"{start_date.strftime('%m/%d')} ~ {end_date.strftime('%m/%d')}"
                st.markdown(f'<div class="metric-card"><div class="metric-value">{period}</div><div class="metric-label">조회 기간</div></div>', unsafe_allow_html=True)

            if items:
                df = pd.DataFrame(items)

                # 날짜 형식 변환
                if "rcept_dt" in df.columns:
                    df["접수일"] = pd.to_datetime(df["rcept_dt"], format="%Y%m%d", errors="coerce").dt.strftime("%Y-%m-%d")

                # 보고서명 키워드로 공시 유형 분류
                def classify_report(name: str) -> str:
                    n = str(name)
                    if any(k in n for k in ["사업보고서", "분기보고서", "반기보고서"]):
                        return "정기공시"
                    if any(k in n for k in ["주요사항보고서", "주요사항"]):
                        return "주요사항보고"
                    if any(k in n for k in ["증권신고", "투자설명서", "발행"]):
                        return "발행공시"
                    if any(k in n for k in ["지분", "주식소유현황", "주식등의대량보유"]):
                        return "지분공시"
                    if any(k in n for k in ["자기주식"]):
                        return "자기주식"
                    if any(k in n for k in ["임원", "주요주주", "특수관계인"]):
                        return "임원·주요주주"
                    if any(k in n for k in ["감사보고서", "내부회계"]):
                        return "외부감사관련"
                    if any(k in n for k in ["합병", "분할", "영업양수도", "주식교환"]):
                        return "기업구조변경"
                    return "기타"

                # 공시 유형별 분포 차트
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    st.markdown('<div class="section-header">공시 유형별 분포</div>', unsafe_allow_html=True)
                    if "report_nm" in df.columns:
                        df["공시유형명"] = df["report_nm"].apply(classify_report)
                        type_cnt = df["공시유형명"].value_counts().reset_index()
                        type_cnt.columns = ["공시유형", "건수"]
                        fig = px.pie(
                            type_cnt, names="공시유형", values="건수",
                            color_discrete_sequence=px.colors.sequential.Blues_r,
                            hole=0.4,
                        )
                        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=260, showlegend=True)
                        st.plotly_chart(fig, use_container_width=True)

                with col_chart2:
                    st.markdown('<div class="section-header">일별 공시 건수 추이</div>', unsafe_allow_html=True)
                    if "접수일" in df.columns:
                        daily = df.groupby("접수일").size().reset_index(name="건수")
                        fig2 = px.bar(
                            daily, x="접수일", y="건수",
                            color_discrete_sequence=["#2563a8"],
                        )
                        fig2.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=260, xaxis_title="", yaxis_title="건수")
                        st.plotly_chart(fig2, use_container_width=True)

                # 공시 목록 테이블
                st.markdown('<div class="section-header">공시 목록</div>', unsafe_allow_html=True)

                # 실제 응답 컬럼 기준으로 구성
                tbl_col_map = {
                    "접수일": "접수일",
                    "corp_name": "기업명",
                    "공시유형명": "공시유형",
                    "report_nm": "보고서명",
                    "flr_nm": "공시제출인",
                    "rcept_no": "접수번호",
                }
                display_cols = [c for c in tbl_col_map if c in df.columns]
                show_df = df[display_cols].rename(columns=tbl_col_map).head(page_count)

                # DART 링크 추가
                if "rcept_no" in df.columns:
                    show_df["공시 링크"] = df["rcept_no"].apply(
                        lambda x: f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={x}"
                    )

                st.dataframe(show_df, use_container_width=True, height=420)

        elif result.get("status") == "013":
            st.info("조회 결과가 없습니다. 검색 조건을 변경해 주세요.")
        else:
            st.error(f"API 오류: {result.get('message', '알 수 없는 오류')}")


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

    if find_btn and corp_search.strip():
        companies = search_company(corp_search.strip(), corp_map)

        if not companies:
            st.warning("검색된 기업이 없습니다.")
        else:
            options = {
                f"{c['corp_name']} ({c['stock_code'].strip() if c['stock_code'].strip() else '비상장'})": c["corp_code"]
                for c in companies
            }
            selected_corp = st.selectbox("기업 선택", list(options.keys()))
            corp_code = options[selected_corp]

            with st.spinner("기업 정보 로딩 중..."):
                info = get_company_info(corp_code)

            if info.get("status") == "000":
                # 기업 개요 카드
                st.markdown('<div class="section-header">기업 개요</div>', unsafe_allow_html=True)
                c1, c2, c3 = st.columns(3)
                fields_left = [
                    ("법인명", "corp_name"),
                    ("영문명", "engl_nm"),
                    ("종목코드", "stock_code"),
                    ("법인구분", "corp_cls"),
                ]
                fields_mid = [
                    ("대표이사", "ceo_nm"),
                    ("설립일", "est_dt"),
                    ("결산월", "acc_mt"),
                    ("업종코드", "induty_code"),
                ]
                fields_right = [
                    ("주소", "adres"),
                    ("홈페이지", "hm_url"),
                    ("전화번호", "phn_no"),
                    ("IR 담당부서", "ir_url"),
                ]

                for col_obj, fields in zip([c1, c2, c3], [fields_left, fields_mid, fields_right]):
                    with col_obj:
                        for label, key in fields:
                            val = info.get(key, "-") or "-"
                            if key == "est_dt" and val != "-" and len(val) == 8:
                                val = f"{val[:4]}-{val[4:6]}-{val[6:]}"
                            if key == "corp_cls":
                                cls_map = {"Y": "유가증권시장", "K": "코스닥", "N": "코넥스", "E": "기타"}
                                val = cls_map.get(val, val)
                            if key == "hm_url" and val != "-":
                                val = f"[바로가기]({val})"
                            st.markdown(f"**{label}**: {val}")

                # 최근 공시 현황
                st.markdown('<div class="section-header">최근 30일 공시 현황</div>', unsafe_allow_html=True)
                bgn_30 = (datetime.today() - timedelta(days=30)).strftime("%Y%m%d")
                end_30 = datetime.today().strftime("%Y%m%d")
                with st.spinner("공시 목록 조회 중..."):
                    disc = get_disclosure_list(corp_code=corp_code, bgn_de=bgn_30, end_de=end_30, page_count=20)

                if disc.get("status") == "000" and disc.get("list"):
                    ddf = pd.DataFrame(disc["list"])
                    ddf["접수일"] = pd.to_datetime(ddf["rcept_dt"], format="%Y%m%d", errors="coerce").dt.strftime("%Y-%m-%d")
                    show = ddf[["접수일", "report_nm", "flr_nm"]].rename(
                        columns={"report_nm": "보고서명", "flr_nm": "공시제출인"}
                    )
                    st.dataframe(show, use_container_width=True, height=300)
                else:
                    st.info("최근 30일간 공시 내역이 없습니다.")

                # 최대주주 현황
                st.markdown('<div class="section-header">최대주주 현황</div>', unsafe_allow_html=True)
                with st.spinner("최대주주 조회 중..."):
                    shareholder_data = get_major_shareholder(corp_code)

                if shareholder_data.get("status") == "000" and shareholder_data.get("list"):
                    sdf = pd.DataFrame(shareholder_data["list"])
                    col_map = {
                        "nm": "주주명",
                        "relate": "관계",
                        "stock_knd": "주식종류",
                        "bsis_posesn_stock_co": "기초보유주식수",
                        "bsis_posesn_stock_qota_rt": "기초지분율(%)",
                        "trmend_posesn_stock_co": "기말보유주식수",
                        "trmend_posesn_stock_qota_rt": "기말지분율(%)",
                    }
                    available = {k: v for k, v in col_map.items() if k in sdf.columns}
                    st.dataframe(sdf[list(available.keys())].rename(columns=available), use_container_width=True)

                    # 지분율 파이차트
                    if "nm" in sdf.columns and "trmend_posesn_stock_qota_rt" in sdf.columns:
                        sdf["지분율"] = pd.to_numeric(sdf["trmend_posesn_stock_qota_rt"], errors="coerce")
                        sdf_valid = sdf[sdf["지분율"].notna() & (sdf["지분율"] > 0)]
                        if not sdf_valid.empty:
                            fig_s = px.pie(
                                sdf_valid, names="nm", values="지분율",
                                title="주요 주주 지분율",
                                color_discrete_sequence=px.colors.sequential.Blues_r,
                                hole=0.35,
                            )
                            fig_s.update_layout(height=350)
                            st.plotly_chart(fig_s, use_container_width=True)
                else:
                    st.info("최대주주 정보가 없습니다.")
            else:
                st.error("기업 정보를 불러오지 못했습니다.")


# ══════════════════════════════════════════════════════════════════════════════
# 탭 3: 재무 정보
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "재무 정보":
    st.markdown('<div class="section-header">재무제표 조회</div>', unsafe_allow_html=True)

    col_a, col_b, col_c, col_d = st.columns([3, 1, 2, 1])
    with col_a:
        fin_corp = st.text_input("기업명", placeholder="예: 삼성전자", label_visibility="visible")
    with col_b:
        fin_year = st.selectbox("사업연도", [str(y) for y in range(datetime.today().year - 1, 2014, -1)])
    with col_c:
        fin_reprt = st.selectbox("보고서 구분", list(REPRT_CODE.keys()))
    with col_d:
        fin_fs = st.selectbox("재무제표", ["연결(CFS)", "별도(OFS)"])
    fs_div = "CFS" if "CFS" in fin_fs else "OFS"

    fin_btn = st.button("📈 재무 데이터 조회", type="primary", use_container_width=True)

    if fin_btn and fin_corp.strip():
        comps = search_company(fin_corp.strip(), corp_map)

        if not comps:
            st.warning("기업을 찾을 수 없습니다.")
        else:
            opts = {
                f"{c['corp_name']} ({c['stock_code'].strip() if c['stock_code'].strip() else '비상장'})": c["corp_code"]
                for c in comps
            }
            sel = st.selectbox("기업 선택", list(opts.keys()))
            c_code = opts[sel]

            reprt_code = REPRT_CODE[fin_reprt]
            with st.spinner("재무 데이터 조회 중..."):
                fin_data = get_financial_single(c_code, fin_year, reprt_code, fs_div)

            if fin_data.get("status") == "000" and fin_data.get("list"):
                fdf = pd.DataFrame(fin_data["list"])

                # 계정 분류
                key_accounts = {
                    "자산총계": ["ifrs-full_Assets", "dart_Assets"],
                    "부채총계": ["ifrs-full_Liabilities", "dart_Liabilities"],
                    "자본총계": ["ifrs-full_Equity", "dart_Equity"],
                    "매출액": ["ifrs-full_Revenue", "dart_Revenue", "ifrs-full_GrossProfit"],
                    "영업이익": ["dart_OperatingIncomeLoss", "ifrs-full_ProfitLossFromOperatingActivities"],
                    "당기순이익": ["ifrs-full_ProfitLoss", "dart_ProfitLoss"],
                }

                summary_rows = []
                for kor_nm, tags in key_accounts.items():
                    row = fdf[fdf["account_id"].isin(tags)]
                    if not row.empty:
                        r = row.iloc[0]
                        thstrm = r.get("thstrm_amount", "0") or "0"
                        frmtrm = r.get("frmtrm_amount", "0") or "0"
                        try:
                            thstrm_val = int(str(thstrm).replace(",", ""))
                            frmtrm_val = int(str(frmtrm).replace(",", ""))
                            chg = ((thstrm_val - frmtrm_val) / abs(frmtrm_val) * 100) if frmtrm_val != 0 else 0
                            summary_rows.append({
                                "계정": kor_nm,
                                "당기(원)": thstrm_val,
                                "전기(원)": frmtrm_val,
                                "증감률(%)": round(chg, 2),
                            })
                        except Exception:
                            pass

                if summary_rows:
                    smdf = pd.DataFrame(summary_rows)

                    # 주요 재무 지표 카드
                    st.markdown('<div class="section-header">주요 재무 지표</div>', unsafe_allow_html=True)
                    cols_m = st.columns(len(summary_rows))
                    for i, row in enumerate(summary_rows):
                        with cols_m[i]:
                            val_b = row["당기(원)"] / 1e8
                            chg_color = "#4ade80" if row["증감률(%)"] >= 0 else "#f87171"
                            arrow = "▲" if row["증감률(%)"] >= 0 else "▼"
                            st.markdown(
                                f'<div class="metric-card">'
                                f'<div class="metric-label">{row["계정"]}</div>'
                                f'<div class="metric-value" style="font-size:1.3rem">{val_b:,.0f}억</div>'
                                f'<div style="color:{chg_color};font-size:0.85rem">{arrow} {abs(row["증감률(%)"]):.1f}%</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                    # 재무 비교 차트
                    st.markdown('<div class="section-header">당기 vs 전기 비교</div>', unsafe_allow_html=True)
                    smdf_m = smdf.copy()
                    smdf_m["당기(억원)"] = smdf_m["당기(원)"] / 1e8
                    smdf_m["전기(억원)"] = smdf_m["전기(원)"] / 1e8
                    fig_bar = go.Figure()
                    fig_bar.add_trace(go.Bar(name="전기", x=smdf_m["계정"], y=smdf_m["전기(억원)"], marker_color="#93c5fd"))
                    fig_bar.add_trace(go.Bar(name="당기", x=smdf_m["계정"], y=smdf_m["당기(억원)"], marker_color="#1d4ed8"))
                    fig_bar.update_layout(
                        barmode="group",
                        height=350,
                        margin=dict(t=20, b=20, l=20, r=20),
                        yaxis_title="억원",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)

                    # 전체 재무제표 테이블
                    st.markdown('<div class="section-header">전체 재무제표 상세</div>', unsafe_allow_html=True)
                    tbl_cols = {
                        "account_nm": "계정명",
                        "thstrm_amount": "당기금액",
                        "frmtrm_amount": "전기금액",
                        "bfefrmtrm_amount": "전전기금액",
                        "currency": "통화",
                    }
                    avail = {k: v for k, v in tbl_cols.items() if k in fdf.columns}
                    st.dataframe(
                        fdf[list(avail.keys())].rename(columns=avail),
                        use_container_width=True,
                        height=400,
                    )

            elif fin_data.get("status") == "013":
                st.warning("해당 기간의 재무 데이터가 없습니다. 연도나 보고서 유형을 변경해 보세요.")
            else:
                msg = fin_data.get("message", "알 수 없는 오류")
                st.error(f"조회 실패: {msg}")

# ─── 푸터 ──────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("본 대시보드는 금융감독원 DART OpenAPI를 활용하여 제작되었습니다. | 데이터는 참고용이며 투자 결정에 활용 시 주의가 필요합니다.")
