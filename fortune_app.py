"""
🔮 오늘의 운세 대시보드
사주 · 별자리 · 띠 · 타로카드 → 종합 리포트 + 추천 로또번호
"""

import base64
import re
from datetime import date

import streamlit as st
import streamlit.components.v1 as st_components
from streamlit_clickable_images import clickable_images

from utils.saju import get_saju_info, OHENG_EMOJI
from utils.zodiac import get_star_sign, get_animal_sign
from utils.tarot import draw_cards, card_label
from utils import openai_client as ai

# ── 페이지 설정 ────────────────────────────────────────────────────────────────

st.set_page_config(page_title="수리수리 오늘의 운세", page_icon="🔮", layout="wide")


# ── SVG 타로 카드: 뒷면 / 앞면 ────────────────────────────────────────────────

def make_card_back_svg(card_num: int = 0, dimmed: bool = False) -> str:
    """카드 뒷면 — 미스틱 퍼플 패턴. dimmed=True 면 반투명."""
    opacity = "0.28" if dimmed else "1"
    n = card_num
    svg = f"""<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 200"
     style="opacity:{opacity};display:block;border-radius:12px;">
<defs>
  <linearGradient id="bg{n}" x1="0" y1="0" x2=".3" y2="1">
    <stop offset="0%"   stop-color="#2b1762"/>
    <stop offset="58%"  stop-color="#170942"/>
    <stop offset="100%" stop-color="#0b0422"/>
  </linearGradient>
  <radialGradient id="cg{n}" cx="50%" cy="50%" r="50%">
    <stop offset="0%"   stop-color="#7b40ff" stop-opacity=".5"/>
    <stop offset="100%" stop-color="#7b40ff" stop-opacity="0"/>
  </radialGradient>
</defs>
<rect width="120" height="200" rx="10" fill="url(#bg{n})"/>
<rect x="1.5" y="1.5" width="117" height="197" rx="9"
      fill="none" stroke="#7a4dcc" stroke-width="1.8" stroke-opacity=".95"/>
<rect x="9" y="9" width="102" height="182" rx="6"
      fill="none" stroke="rgba(150,90,255,.3)" stroke-width="1"/>
<circle cx="60" cy="100" r="50" fill="url(#cg{n})"/>
<circle cx="60" cy="100" r="31" fill="none" stroke="rgba(140,80,255,.44)" stroke-width="1.2"/>
<path d="M60,71 L63.5,87 L74,75 L67,91 L85,88 L73,99 L87,109
         L70,107 L77,125 L63,113 L60,131 L57,113 L43,125 L50,107
         L33,109 L47,99 L35,88 L53,91 L46,75 L56.5,87 Z"
      fill="rgba(120,58,255,.2)" stroke="rgba(152,92,255,.46)" stroke-width=".8"/>
<circle cx="60" cy="100" r="15" fill="rgba(76,28,180,.58)"
        stroke="rgba(162,102,255,.74)" stroke-width="1.2"/>
<line x1="60" y1="85"  x2="60" y2="115" stroke="rgba(162,102,255,.34)" stroke-width=".9"/>
<line x1="45" y1="100" x2="75" y2="100" stroke="rgba(162,102,255,.34)" stroke-width=".9"/>
<circle cx="60" cy="100" r="4.5" fill="rgba(192,132,255,.95)"/>
<circle cx="60" cy="100" r="2"   fill="rgba(255,235,255,1)"/>
<polygon points="60,27 62,34 60,41 58,34"     fill="rgba(152,92,255,.55)" stroke="rgba(162,102,255,.6)"  stroke-width=".7"/>
<polygon points="47,31 49,38 47,45 45,38"     fill="rgba(132,70,222,.4)"  stroke="rgba(142,82,242,.5)"  stroke-width=".6"/>
<polygon points="73,31 75,38 73,45 71,38"     fill="rgba(132,70,222,.4)"  stroke="rgba(142,82,242,.5)"  stroke-width=".6"/>
<polygon points="60,159 62,166 60,173 58,166" fill="rgba(152,92,255,.55)" stroke="rgba(162,102,255,.6)" stroke-width=".7"/>
<polygon points="47,155 49,162 47,169 45,162" fill="rgba(132,70,222,.4)"  stroke="rgba(142,82,242,.5)" stroke-width=".6"/>
<polygon points="73,155 75,162 73,169 71,162" fill="rgba(132,70,222,.4)"  stroke="rgba(142,82,242,.5)" stroke-width=".6"/>
<circle cx="20"  cy="22"  r="2.8" fill="rgba(152,92,255,.55)"/>
<circle cx="100" cy="22"  r="2.8" fill="rgba(152,92,255,.55)"/>
<circle cx="20"  cy="178" r="2.8" fill="rgba(152,92,255,.55)"/>
<circle cx="100" cy="178" r="2.8" fill="rgba(152,92,255,.55)"/>
<circle cx="17"  cy="82"  r="1.6" fill="rgba(132,70,222,.4)"/>
<circle cx="17"  cy="100" r="1.6" fill="rgba(132,70,222,.4)"/>
<circle cx="17"  cy="118" r="1.6" fill="rgba(132,70,222,.4)"/>
<circle cx="103" cy="82"  r="1.6" fill="rgba(132,70,222,.4)"/>
<circle cx="103" cy="100" r="1.6" fill="rgba(132,70,222,.4)"/>
<circle cx="103" cy="118" r="1.6" fill="rgba(132,70,222,.4)"/>
</svg>"""
    return f"data:image/svg+xml;base64,{base64.b64encode(svg.encode('utf-8')).decode()}"


def make_card_front_svg(card: dict) -> str:
    """카드 앞면 — 골드 테두리 + 이모지 + 카드명 + 방향. SMIL 페이드인 애니메이션 포함."""
    emoji    = card.get("emoji", "✨")
    korean   = card.get("korean", "")
    direction = card.get("direction", "")
    # 방향에 따라 배경 색조 변경
    top_col = "#4a2090" if direction == "정방향" else "#1e0e5a"
    svg = f"""<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 200"
     style="display:block;border-radius:12px;">
<defs>
  <linearGradient id="ffg" x1="0" y1="0" x2=".25" y2="1">
    <stop offset="0%"   stop-color="{top_col}"/>
    <stop offset="55%"  stop-color="#1a0840"/>
    <stop offset="100%" stop-color="#0d0628"/>
  </linearGradient>
  <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
    <feGaussianBlur stdDeviation="3.5" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <radialGradient id="cshine" cx="50%" cy="45%" r="45%">
    <stop offset="0%"   stop-color="rgba(200,150,255,.18)"/>
    <stop offset="100%" stop-color="rgba(180,100,255,0)"/>
  </radialGradient>
</defs>
<!-- 페이드인 애니메이션 래퍼 -->
<g>
  <animate attributeName="opacity" from="0" to="1" dur="0.35s" begin="0s" fill="freeze"/>
  <!-- 배경 -->
  <rect width="120" height="200" rx="10" fill="url(#ffg)"/>
  <!-- 골드 광택 오버레이 -->
  <ellipse cx="60" cy="88" rx="52" ry="70" fill="url(#cshine)"/>
  <!-- 외부 골드 테두리 (glow) -->
  <rect x="1.5" y="1.5" width="117" height="197" rx="9"
        fill="none" stroke="#ffd700" stroke-width="2.8" stroke-opacity=".95"
        filter="url(#glow)"/>
  <!-- 내부 얇은 골드 테두리 -->
  <rect x="6" y="6" width="108" height="188" rx="7"
        fill="none" stroke="rgba(255,215,0,.3)" stroke-width=".8"/>
  <!-- 상단 장식 라인 -->
  <rect x="14" y="15" width="92" height="1.2" rx=".6" fill="rgba(255,215,0,.4)"/>
  <!-- 하단 장식 라인 -->
  <rect x="14" y="183" width="92" height="1.2" rx=".6" fill="rgba(255,215,0,.4)"/>
  <!-- 이모지 (SVG text, 브라우저 이모지 폰트 사용) -->
  <text x="60" y="95" text-anchor="middle" dominant-baseline="central"
        font-size="40"
        font-family="'Segoe UI Emoji','Apple Color Emoji','Noto Color Emoji',sans-serif">{emoji}</text>
  <!-- 카드명 (한글) -->
  <text x="60" y="130" text-anchor="middle"
        font-size="10" font-weight="700" fill="#ffd700"
        font-family="'Malgun Gothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif">{korean}</text>
  <!-- 방향 -->
  <text x="60" y="148" text-anchor="middle"
        font-size="8.5" fill="rgba(210,170,255,.95)"
        font-family="'Malgun Gothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif">{direction}</text>
  <!-- 코너 골드 장식 -->
  <circle cx="17" cy="27"  r="2.4" fill="rgba(255,215,0,.6)"/>
  <circle cx="103" cy="27" r="2.4" fill="rgba(255,215,0,.6)"/>
  <circle cx="17" cy="173" r="2.4" fill="rgba(255,215,0,.6)"/>
  <circle cx="103" cy="173" r="2.4" fill="rgba(255,215,0,.6)"/>
  <!-- 사이드 별 장식 -->
  <text x="13"  y="105" text-anchor="middle" font-size="7"
        fill="rgba(255,215,0,.45)" font-family="sans-serif">★</text>
  <text x="107" y="105" text-anchor="middle" font-size="7"
        fill="rgba(255,215,0,.45)" font-family="sans-serif">★</text>
  <!-- 하단 작은 장식 다이아 -->
  <polygon points="60,163 63,168 60,173 57,168"
           fill="rgba(255,215,0,.35)" stroke="rgba(255,215,0,.5)" stroke-width=".7"/>
</g>
</svg>"""
    return f"data:image/svg+xml;base64,{base64.b64encode(svg.encode('utf-8')).decode()}"


# ── 글로벌 CSS ─────────────────────────────────────────────────────────────────

st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); }

/* ── 입력 폼 ────────────────────────────────────────────── */
[data-testid="stForm"] {
    max-width: 660px !important; margin: 0 auto !important;
    background: transparent !important; border: none !important;
    padding: 0 !important; box-shadow: none !important;
}
[data-testid="stForm"] > div:first-child {
    border: none !important; background: transparent !important;
    box-shadow: none !important; padding: 0 !important;
}
[data-testid="stForm"] [data-testid="stDateInput"] input {
    height: 44px !important; font-size: 1.05rem !important;
    padding: 0 14px !important; border-radius: 12px !important;
    background: #1e0f4a !important;
    border: 1px solid rgba(200,160,255,.45) !important;
    color: #f0e6ff !important; caret-color: #d4a8ff !important;
}
[data-testid="stForm"] [data-testid="stDateInput"] > div,
[data-testid="stForm"] [data-testid="stDateInput"] [data-baseweb="input"],
[data-testid="stForm"] [data-testid="stDateInput"] [data-baseweb="base-input"] {
    background: #1e0f4a !important; border-radius: 12px !important;
}
[data-testid="stForm"] [data-testid="stRadio"] {
    display: flex !important; align-items: center !important;
    height: 44px !important; padding-top: 6px !important;
}
[data-testid="stForm"] [data-testid="stRadio"] div[role="radiogroup"] { gap: 1.4rem !important; }
[data-testid="stForm"] [data-testid="stRadio"] label p,
[data-testid="stForm"] [data-testid="stRadio"] label span {
    color: #f0e6ff !important; font-size: 1.05rem !important; font-weight: 600 !important;
}
[data-testid="stFormSubmitButton"] button {
    height: 44px !important; border-radius: 12px !important;
    font-size: 1rem !important; font-weight: 700 !important; margin-top: 6px !important;
}

/* ══════════════════════════════════════════════════════════
   운세 카드 공통 스타일 (고정 높이 시스템)
   ══════════════════════════════════════════════════════════ */
.fortune-card {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 16px; padding: 1.4rem 1.6rem;
    backdrop-filter: blur(8px); color: #f0e6ff;
    box-shadow: 0 4px 28px rgba(0,0,0,.35), 0 0 0 0.5px rgba(200,160,255,.08);
    box-sizing: border-box;
    min-height: 440px;
    display: flex; flex-direction: column;
}
.fortune-card h3 {
    color: #d4a8ff; font-size: 1.15rem;
    flex-shrink: 0; margin-bottom: .7rem;
}
.fortune-card .card-body {
    flex: 1; overflow-y: auto;
    max-height: 360px; padding-right: 3px; line-height: 1.75; font-size: .92rem;
}
.fortune-card .card-body::-webkit-scrollbar { width: 3px; }
.fortune-card .card-body::-webkit-scrollbar-thumb {
    background: rgba(200,160,255,.4); border-radius: 2px;
}

/* ── Row 1 동일 높이 (사주 ↔ 별자리) ────────────────────── */
.element-container:has(.row1-eq-marker) + [data-testid="stHorizontalBlock"],
.element-container:has(.row1-eq-marker) ~ [data-testid="stHorizontalBlock"]:first-of-type {
    align-items: stretch !important;
}
.element-container:has(.row1-eq-marker) + [data-testid="stHorizontalBlock"] > [data-testid="column"],
.element-container:has(.row1-eq-marker) ~ [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"] {
    display: flex !important; flex-direction: column !important;
}
.element-container:has(.row1-eq-marker) + [data-testid="stHorizontalBlock"] > [data-testid="column"] > *,
.element-container:has(.row1-eq-marker) + [data-testid="stHorizontalBlock"] > [data-testid="column"] > * > *,
.element-container:has(.row1-eq-marker) + [data-testid="stHorizontalBlock"] > [data-testid="column"] > * > * > *,
.element-container:has(.row1-eq-marker) ~ [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"] > *,
.element-container:has(.row1-eq-marker) ~ [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"] > * > *,
.element-container:has(.row1-eq-marker) ~ [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"] > * > * > * {
    flex: 1 !important; display: flex !important; flex-direction: column !important;
}
.element-container:has(.row1-eq-marker) + [data-testid="stHorizontalBlock"] .fortune-card,
.element-container:has(.row1-eq-marker) ~ [data-testid="stHorizontalBlock"]:first-of-type .fortune-card {
    flex: 1 !important; margin-bottom: 0 !important;
}

/* ── Row 2 동일 높이 (띠 ↔ 타로카드) ────────────────────── */
.element-container:has(.row2-eq-marker) + [data-testid="stHorizontalBlock"],
.element-container:has(.row2-eq-marker) ~ [data-testid="stHorizontalBlock"]:first-of-type {
    align-items: stretch !important;
}
.element-container:has(.row2-eq-marker) + [data-testid="stHorizontalBlock"] > [data-testid="column"],
.element-container:has(.row2-eq-marker) ~ [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"] {
    display: flex !important; flex-direction: column !important;
}
.element-container:has(.row2-eq-marker) + [data-testid="stHorizontalBlock"] .fortune-card,
.element-container:has(.row2-eq-marker) ~ [data-testid="stHorizontalBlock"]:first-of-type .fortune-card {
    flex: 1 !important; margin-bottom: 0 !important;
}

/* col_t 스타일은 JS로 직접 주입 (CSS :has() 미지원 환경 대응) */
/* clickable_images iframe: 깔끔하게 처리 */
.tarot-styled iframe {
    color-scheme: dark !important;
    border: none !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}

/* 타로 해석 컴팩트 패널 */
.tarot-interp-compact {
    color: #f0e6ff; padding: .7rem 1rem;
    line-height: 1.65; font-size: .85rem;
    max-height: 160px; overflow-y: auto;
}
.tarot-interp-compact::-webkit-scrollbar { width: 3px; }
.tarot-interp-compact::-webkit-scrollbar-thumb {
    background: rgba(200,160,255,.4); border-radius: 2px;
}
.tarot-interp-compact h4 {
    color: #ffd700; font-size: .92rem; margin: 0 0 .35rem;
}

/* Row 간격 */
.row2-spacer { height: 24px; }

/* ── 종합 리포트 ──────────────────────────────────────────── */
.report-banner {
    background: linear-gradient(135deg, rgba(100,60,180,.35), rgba(30,20,80,.6));
    border: 1px solid rgba(180,140,255,.4);
    border-radius: 20px; padding: 1.8rem 2rem; margin: 1.5rem 0; color: #f0e6ff;
}
.report-item {
    background: rgba(255,255,255,0.06);
    border-radius: 12px; padding: .9rem 1.2rem; margin-bottom: .7rem;
}
.lotto-wrap { display:flex; gap:10px; flex-wrap:wrap; margin: .8rem 0; }
.lotto-ball-sm {
    width: 40px; height: 40px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: .75rem; color: #fff;
    box-shadow: 0 0 8px rgba(255,255,255,.25);
}
.section-title {
    font-size: 1.5rem; font-weight: 700; color: #d4a8ff;
    border-bottom: 1px solid rgba(200,160,255,.3);
    padding-bottom: .4rem; margin: 1.8rem 0 1rem;
}
</style>
""", unsafe_allow_html=True)


# ── 유틸 함수 ──────────────────────────────────────────────────────────────────

def lotto_color(n: int) -> str:
    if n <= 10: return "#f6a623"
    if n <= 20: return "#4a90d9"
    if n <= 30: return "#e74c3c"
    if n <= 40: return "#808080"
    return "#2ecc71"


def render_lotto_sets(sets: list[list[int]]):
    rows = ""
    for numbers in sets:
        balls = "".join(
            f'<div class="lotto-ball-sm" style="background:{lotto_color(n)}">{n}</div>'
            for n in numbers
        )
        rows += f'<div style="display:flex;gap:4px;align-items:center;">{balls}</div>'
    st.markdown(
        f'<div style="display:flex;gap:18px;flex-wrap:wrap;justify-content:center;margin:.6rem 0;">{rows}</div>',
        unsafe_allow_html=True,
    )


def extract_lotto_sets(text: str) -> list[list[int]]:
    """텍스트에서 로또 번호 5세트 추출. 각 세트는 6개 숫자."""
    sets = []
    for line in text.splitlines():
        nums = list(map(int, re.findall(r"\b([1-9]|[1-3]\d|4[0-5])\b", line)))
        seen, unique = set(), []
        for n in nums:
            if n not in seen:
                seen.add(n)
                unique.append(n)
        if len(unique) >= 6:
            sets.append(unique[:6])
    return sets[:5]


def fortune_card(title: str, content: str):
    st.markdown(
        f'<div class="fortune-card">'
        f'<h3>{title}</h3>'
        f'<div class="card-body">{content.replace(chr(10), "<br>")}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_tarot_selector(tarot_cards: list, selected_idx):
    """
    타로카드 선택 패널 (col_t).
    JS로 부모 column에 fortune-card 스타일을 직접 주입 (CSS :has() 미지원 대응).
    """
    # ── 제목 (첫 번째 요소 — 왼쪽 컬럼 제목과 동일 높이에 위치) ──────────────
    st.markdown(
        '<h3 style="color:#d4a8ff;font-size:1.15rem;font-weight:700;'
        'margin:0 0 .5rem;flex-shrink:0;">🎴 타로카드</h3>',
        unsafe_allow_html=True,
    )

    # ── 안내 문구 ─────────────────────────────────────────────────────────────
    if selected_idx is None:
        hint = (
            '<span style="color:#a08aff;font-size:.85rem;">'
            '카드 3장 중 하나를 골라 뒤집어보세요 ✨</span>'
        )
    else:
        c = tarot_cards[selected_idx]
        tarot_done = bool(st.session_state.get("tarot_result"))
        hint = (
            f'<span style="color:#ffd700;font-size:.85rem;font-weight:700;">'
            f'{c["emoji"]} {c["korean"]}</span>'
            f'<span style="color:#a08aff;font-size:.8rem;"> — {c["direction"]}</span>'
            + (
                '&nbsp;<span style="color:#7b5de8;font-size:.78rem;">↓ 아래 해석 확인</span>'
                if tarot_done else
                '&nbsp;<span style="color:#7b5de8;font-size:.78rem;">🔮 해석 중...</span>'
            )
        )
    st.markdown(f'<div style="margin-bottom:.7rem;">{hint}</div>', unsafe_allow_html=True)

    # ── 카드 3장 이미지 ───────────────────────────────────────────────────────
    svgs = []
    for i, card in enumerate(tarot_cards):
        if selected_idx is not None and i == selected_idx:
            svgs.append(make_card_front_svg(card))
        else:
            svgs.append(make_card_back_svg(i, dimmed=(selected_idx is not None)))

    clicked = clickable_images(
        svgs,
        div_style={
            "display":         "flex",
            "justify-content": "space-around",
            "align-items":     "flex-start",
            "width":           "100%",
            "min-height":      "100vh",
            "padding":         "8px 4px 10px",
            "background":      "rgba(26,16,50,0.92)",
            "border-radius":   "10px",
            "box-sizing":      "border-box",
        },
        img_style={
            "width":        "30%",
            "height":       "auto",
            "max-height":   "280px",
            "border-radius": "12px",
            "cursor":       "pointer",
            "display":      "block",
        },
        key=f"tp_{selected_idx}",
    )

    if clicked >= 0 and st.session_state.get("tarot_selected") != clicked:
        st.session_state["tarot_selected"] = clicked
        st.session_state["tarot_result"]   = ""
        st.rerun()

    # ── JS: 부모 column에 fortune-card 스타일 적용 + 높이 동기화 ─────────────
    # 제목/카드 뒤에 배치해서 제목 위치가 왼쪽 컬럼과 동일 높이에 오도록 함
    st.markdown('<div class="tarot-col-inner" style="display:none;"></div>',
                unsafe_allow_html=True)
    st_components.html("""
    <script>
    (function(){
        var doc = window.parent.document;
        var marker = doc.querySelector('.tarot-col-inner');
        if(!marker) return;
        var col = marker.closest('[data-testid="column"]')
               || marker.closest('[data-testid="stColumn"]');
        if(!col) return;

        // 1) 타로 컬럼에 fortune-card 스타일 적용
        col.classList.add('tarot-styled');
        Object.assign(col.style, {
            background:           'rgba(26,16,50,0.92)',
            border:               '1.5px solid rgba(123,47,190,0.65)',
            borderRadius:         '16px',
            padding:              '1.4rem 1.6rem',
            backdropFilter:       'blur(8px)',
            webkitBackdropFilter: 'blur(8px)',
            boxShadow:            '0 4px 28px rgba(0,0,0,.35), 0 0 0 0.5px rgba(200,160,255,.08)',
            boxSizing:            'border-box',
            color:                '#f0e6ff',
            overflow:             'hidden'
        });

        // 2) 4개 카드 전체 높이를 최대값에 맞춤
        function syncAll(){
            var cards = doc.querySelectorAll('.fortune-card');
            var maxH = 0;
            cards.forEach(function(c){ if(c.offsetHeight > maxH) maxH = c.offsetHeight; });
            if(col.offsetHeight > maxH) maxH = col.offsetHeight;
            if(maxH < 200) return;
            cards.forEach(function(c){ c.style.minHeight = maxH + 'px'; });
            col.style.height = maxH + 'px';
        }
        requestAnimationFrame(function(){ requestAnimationFrame(syncAll); });
        setTimeout(syncAll, 400);
        setTimeout(syncAll, 1000);
    })();
    </script>
    """, height=0)


# ── 세션 상태 초기화 ───────────────────────────────────────────────────────────

for key, default in {
    "fortune_done":   False,
    "saju_result":    "",
    "star_result":    "",
    "animal_result":  "",
    "tarot_cards":    None,
    "tarot_selected": None,
    "tarot_result":   "",
    "report_result":  "",
    "lotto_sets":     [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── 헤더 ───────────────────────────────────────────────────────────────────────

st.markdown("""
<div style="text-align:center; padding: 2rem 0 1rem;">
  <div style="font-size:3.5rem;">🔮</div>
  <h1 style="color:#d4a8ff; font-size:2.4rem; margin:.3rem 0;">수리수리 오늘의 운세</h1>
  <p style="color:#9b72ff; font-size:1rem;">생년월일 하나로 오늘의 운명을 탐험하세요</p>
</div>
""", unsafe_allow_html=True)


# ── 입력부 ─────────────────────────────────────────────────────────────────────

with st.form("fortune_form", border=False):
    d_col, g_col, b_col = st.columns([5, 3, 3])
    with d_col:
        birth_input = st.date_input(
            "생년월일", value=date(1995, 1, 1),
            min_value=date(1930, 1, 1), max_value=date.today(),
            label_visibility="collapsed",
        )
    with g_col:
        gender_raw = st.radio(
            "성별", ["남성", "여성"], horizontal=True, label_visibility="collapsed",
        )
    with b_col:
        run_btn = st.form_submit_button("✨ 운세 보기", use_container_width=True, type="primary")

gender = gender_raw


# ── 운세 생성 ─────────────────────────────────────────────────────────────────

if run_btn:
    for key in ["fortune_done","saju_result","star_result","animal_result",
                "tarot_cards","tarot_selected","tarot_result",
                "report_result","lotto_sets"]:
        st.session_state[key] = False if key == "fortune_done" else (
            None if key in ["tarot_cards","tarot_selected"] else
            [] if key == "lotto_sets" else ""
        )
    birth       = birth_input
    saju_info   = get_saju_info(birth)
    star_info   = get_star_sign(birth)
    animal_info = get_animal_sign(birth)
    st.session_state["tarot_cards"] = draw_cards(3)

    st.markdown('<div class="section-title">🌟 오늘의 개별 운세</div>', unsafe_allow_html=True)
    st.markdown('<div class="row1-eq-marker"></div>', unsafe_allow_html=True)
    col_s, col_z = st.columns(2)
    with col_s:
        with st.spinner("🧧 사주 운세 읽는 중..."):
            saju_result = ai.get_saju_fortune(birth, gender, saju_info["summary"], saju_info["dominant_oheng"])
            st.session_state["saju_result"] = saju_result
        oheng_emoji = OHENG_EMOJI.get(saju_info["dominant_oheng"], "")
        fortune_card(f"🧧 사주운세 &nbsp;|&nbsp; {oheng_emoji} {saju_info['dominant_oheng']} 기운", saju_result)
    with col_z:
        with st.spinner("♈ 별자리 운세 읽는 중..."):
            star_result = ai.get_star_fortune(birth, gender, star_info["name"], star_info["symbol"])
            st.session_state["star_result"] = star_result
        fortune_card(f"{star_info['symbol']} 별자리운세 &nbsp;|&nbsp; {star_info['name']} ({star_info['range']})", star_result)

    st.markdown('<div class="row2-spacer"></div>', unsafe_allow_html=True)
    st.markdown('<div class="row2-eq-marker"></div>', unsafe_allow_html=True)
    col_a, col_t = st.columns(2)
    with col_a:
        with st.spinner("🐉 띠 운세 읽는 중..."):
            animal_result = ai.get_animal_fortune(birth, gender, animal_info["name"], animal_info["emoji"], animal_info["compatible"])
            st.session_state["animal_result"] = animal_result
        fortune_card(f"{animal_info['emoji']} 띠운세 &nbsp;|&nbsp; {animal_info['name']}띠", animal_result)
    with col_t:
        render_tarot_selector(st.session_state["tarot_cards"], None)

    st.session_state["fortune_done"] = True
    st.rerun()


# ── 결과 표시 ─────────────────────────────────────────────────────────────────

if st.session_state["fortune_done"] and st.session_state["saju_result"]:
    birth        = birth_input
    saju_info    = get_saju_info(birth)
    star_info    = get_star_sign(birth)
    animal_info  = get_animal_sign(birth)
    tarot_cards  = st.session_state["tarot_cards"]
    selected_idx = st.session_state.get("tarot_selected")

    st.markdown('<div class="section-title">🌟 오늘의 개별 운세</div>', unsafe_allow_html=True)

    # Row 1: 사주 + 별자리
    st.markdown('<div class="row1-eq-marker"></div>', unsafe_allow_html=True)
    col_s, col_z = st.columns(2)
    with col_s:
        oheng_emoji = OHENG_EMOJI.get(saju_info["dominant_oheng"], "")
        fortune_card(
            f"🧧 사주운세 &nbsp;|&nbsp; {oheng_emoji} {saju_info['dominant_oheng']} 기운",
            st.session_state["saju_result"],
        )
    with col_z:
        fortune_card(
            f"{star_info['symbol']} 별자리운세 &nbsp;|&nbsp; {star_info['name']} ({star_info['range']})",
            st.session_state["star_result"],
        )

    # ── Row 2: 띠운세(좌) + 타로카드 선택 패널(우) ─ 동일 min-height 440px ──
    st.markdown('<div class="row2-spacer"></div>', unsafe_allow_html=True)
    st.markdown('<div class="row2-eq-marker"></div>', unsafe_allow_html=True)
    col_a, col_t = st.columns(2)
    with col_a:
        fortune_card(
            f"{animal_info['emoji']} 띠운세 &nbsp;|&nbsp; {animal_info['name']}띠",
            st.session_state["animal_result"],
        )
    with col_t:
        render_tarot_selector(tarot_cards, selected_idx)

    # ── 타로 해석 생성 (카드 선택 직후, 결과 없을 때) ────────────────────────
    if selected_idx is not None and not st.session_state["tarot_result"]:
        chosen = tarot_cards[selected_idx]
        if chosen.get("scary_note"):
            _, col_note = st.columns(2)
            with col_note:
                st.info(chosen["scary_note"])
        with st.spinner(f"🎴 {chosen['korean']} 카드를 해석하는 중..."):
            tarot_result = ai.get_tarot_fortune(
                birth_input, gender,
                chosen["name"], chosen["korean"],
                chosen["emoji"], chosen["direction"],
            )
            st.session_state["tarot_result"] = tarot_result
            st.rerun()

    # ── Row 3: 타로카드 해석 (우측 컬럼, 컴팩트) ─────────────────────────────
    if st.session_state.get("tarot_result") and selected_idx is not None:
        chosen = tarot_cards[selected_idx]
        interp_html = st.session_state["tarot_result"].replace(chr(10), "<br>")
        st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
        _, col_interp = st.columns(2)
        with col_interp:
            st.markdown(
                f'<div class="tarot-interp-compact">'
                f'<h4>{chosen["emoji"]} {chosen["korean"]} &nbsp;|&nbsp; {chosen["direction"]} 해석</h4>'
                f'{interp_html}'
                f'</div>',
                unsafe_allow_html=True,
            )


# ── 종합 리포트 생성 ──────────────────────────────────────────────────────────

if (st.session_state["tarot_result"]
        and st.session_state["saju_result"]
        and not st.session_state["report_result"]):
    tarot_cards = st.session_state["tarot_cards"]
    chosen      = tarot_cards[st.session_state["tarot_selected"]]
    with st.spinner("📋 모든 운명의 조각을 모으는 중... 잠시만요 🔮"):
        report = ai.get_synthesis_report(
            birth_input, gender,
            st.session_state["saju_result"],
            st.session_state["star_result"],
            st.session_state["animal_result"],
            st.session_state["tarot_result"],
            card_label(chosen),
        )
        st.session_state["report_result"] = report
        st.rerun()


# ── 종합 리포트 + 로또 ────────────────────────────────────────────────────────

if st.session_state["report_result"]:
    st.markdown('<div class="section-title">📋 오늘의 종합 리포트</div>', unsafe_allow_html=True)
    report_html = st.session_state["report_result"].replace("\n", "<br>")
    st.markdown(
        f'<div class="report-banner"><div class="report-item">{report_html}</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="text-align:center; font-size:1.3rem; color:#ffd700; margin: 1.5rem 0 .5rem;">'
        '🍀 오늘의 추천 로또번호</div>',
        unsafe_allow_html=True,
    )
    if not st.session_state["lotto_sets"]:
        with st.spinner("🍀 운명의 번호를 뽑는 중..."):
            raw_text = ai.get_lotto_numbers(
                birth_input, gender,
                st.session_state["saju_result"],
                st.session_state["star_result"],
                st.session_state["animal_result"],
                st.session_state["tarot_result"],
            )
            st.session_state["lotto_sets"] = extract_lotto_sets(raw_text)
            st.rerun()

    if st.session_state["lotto_sets"]:
        render_lotto_sets(st.session_state["lotto_sets"])

    st.markdown(
        '<div style="text-align:center; color:#6a5acd; font-size:.8rem; margin-top:2rem;">'
        '⚠️ 이 서비스는 재미를 위한 것이며, 실제 운세나 투자 근거가 아닙니다.</div>',
        unsafe_allow_html=True,
    )
