"""
사주 천간지지 계산 모듈
생년월일 → 연주·월주·일주 계산 및 오행 분석
"""

from datetime import date

# 천간 (10개)
CHEONGAN = ["갑(甲)", "을(乙)", "병(丙)", "정(丁)", "무(戊)",
            "기(己)", "경(庚)", "신(辛)", "임(壬)", "계(癸)"]

# 지지 (12개)
JIJI = ["자(子)", "축(丑)", "인(寅)", "묘(卯)", "진(辰)", "사(巳)",
        "오(午)", "미(未)", "신(申)", "유(酉)", "술(戌)", "해(亥)"]

# 천간 → 오행
CHEONGAN_OHENG = {
    "갑(甲)": "목(木)", "을(乙)": "목(木)",
    "병(丙)": "화(火)", "정(丁)": "화(火)",
    "무(戊)": "토(土)", "기(己)": "토(土)",
    "경(庚)": "금(金)", "신(辛)": "금(金)",
    "임(壬)": "수(水)", "계(癸)": "수(水)",
}

# 지지 → 오행
JIJI_OHENG = {
    "자(子)": "수(水)", "축(丑)": "토(土)", "인(寅)": "목(木)", "묘(卯)": "목(木)",
    "진(辰)": "토(土)", "사(巳)": "화(火)", "오(午)": "화(火)", "미(未)": "토(土)",
    "신(申)": "금(金)", "유(酉)": "금(金)", "술(戌)": "토(土)", "해(亥)": "수(Water)",
}

# 오행 이모지
OHENG_EMOJI = {
    "목(木)": "🌿",
    "화(火)": "🔥",
    "토(土)": "🪨",
    "금(金)": "⚙️",
    "수(Water)": "💧",
    "수(水)": "💧",
}

# 월 → 월주 지지 (절기 기준 간략화, 양력 월 기준)
MONTH_TO_JIJI_IDX = {
    1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6,
    7: 7, 8: 8, 9: 9, 10: 10, 11: 11, 12: 0
}

# 월주 천간 기준표 (연간 기준으로 월의 천간 결정)
MONTH_CHEONGAN_BASE = {
    0: 2, 1: 2, 2: 4, 3: 6, 4: 8,
    5: 0, 6: 2, 7: 4, 8: 6, 9: 8, 10: 0
}


def get_year_ganjiji(year: int) -> tuple[str, str]:
    """연도 → 연주 천간지지"""
    gan_idx = (year - 4) % 10
    ji_idx = (year - 4) % 12
    return CHEONGAN[gan_idx], JIJI[ji_idx]


def get_month_ganjiji(year: int, month: int) -> tuple[str, str]:
    """연도·월 → 월주 천간지지"""
    year_gan_idx = (year - 4) % 10
    base = MONTH_CHEONGAN_BASE.get(year_gan_idx % 5, 0)
    gan_idx = (base + month - 1) % 10
    ji_idx = (month + 1) % 12
    return CHEONGAN[gan_idx], JIJI[ji_idx]


def get_day_ganjiji(birth: date) -> tuple[str, str]:
    """생년월일 → 일주 천간지지 (율리우스 적일 기준)"""
    a = (14 - birth.month) // 12
    y = birth.year + 4800 - a
    m = birth.month + 12 * a - 3
    jd = birth.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    gan_idx = (jd + 40) % 10
    ji_idx = (jd + 12) % 12
    return CHEONGAN[gan_idx], JIJI[ji_idx]


def get_saju_info(birth: date) -> dict:
    """생년월일 → 사주 전체 정보 딕셔너리 반환"""
    y_gan, y_ji = get_year_ganjiji(birth.year)
    m_gan, m_ji = get_month_ganjiji(birth.year, birth.month)
    d_gan, d_ji = get_day_ganjiji(birth)

    pillars = {
        "연주": {"천간": y_gan, "지지": y_ji},
        "월주": {"천간": m_gan, "지지": m_ji},
        "일주": {"천간": d_gan, "지지": d_ji},
    }

    # 오행 카운트
    oheng_count: dict[str, int] = {"목(木)": 0, "화(火)": 0, "토(土)": 0, "금(金)": 0, "수(水)": 0}
    for pillar in pillars.values():
        for element in [CHEONGAN_OHENG.get(pillar["천간"], ""), JIJI_OHENG.get(pillar["지지"], "")]:
            normalized = element.replace("Water", "水")
            if normalized in oheng_count:
                oheng_count[normalized] += 1

    dominant = max(oheng_count, key=oheng_count.get)

    return {
        "pillars": pillars,
        "oheng_count": oheng_count,
        "dominant_oheng": dominant,
        "summary": f"연주 {y_gan}{y_ji} / 월주 {m_gan}{m_ji} / 일주 {d_gan}{d_ji}",
    }
