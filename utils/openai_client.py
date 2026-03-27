"""
OpenAI API 호출 모듈
사주·별자리·띠·타로·종합리포트·로또번호 프롬프트 관리
"""

import os
from pathlib import Path
from datetime import date
from openai import OpenAI
from dotenv import load_dotenv

# utils/ 한 단계 위 프로젝트 루트의 .env 를 명시적으로 로드
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=_ROOT / ".env", override=True)

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def _chat(prompt: str, system: str = "당신은 재미있고 친근한 운세 전문가입니다.") -> str:
    resp = get_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.9,
    )
    return resp.choices[0].message.content.strip()


def _stream(prompt: str, system: str = "당신은 재미있고 친근한 운세 전문가입니다."):
    """스트리밍 제너레이터 — st.write_stream() 에 바로 전달 가능"""
    stream = get_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.9,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


# ── 개별 운세 ─────────────────────────────────────────────────────────────────

def get_saju_fortune(birth: date, gender: str, saju_summary: str, dominant_oheng: str,
                     cal_type: str = "양력", lunar_birth: date | None = None) -> str:
    today = date.today().strftime("%Y년 %m월 %d일")
    birth_str = birth.strftime('%Y년 %m월 %d일')
    if cal_type == "음력" and lunar_birth:
        date_info = (
            f"음력 생년월일 {lunar_birth.strftime('%Y년 %m월 %d일')} "
            f"(양력 변환: {birth_str})"
        )
    elif lunar_birth:
        date_info = (
            f"양력 생년월일 {birth_str} "
            f"(음력 변환: {lunar_birth.strftime('%Y년 %m월 %d일')})"
        )
    else:
        date_info = f"생년월일 {birth_str} ({cal_type})"

    prompt = f"""
오늘은 {today}입니다.
{date_info}인 {gender}의 사주를 분석해주세요.
사주 요약: {saju_summary}
주도 오행: {dominant_oheng}

다음 형식으로 재미있고 친근하게 작성해주세요:

🔥 오행 한 줄 요약
(주도 오행의 특성을 한 문장으로)

💕 연애운
(오늘의 연애·인간관계 흐름, 2~3문장)

💰 금전운
(오늘의 금전·사업 흐름, 2~3문장)

🌿 건강운
(오늘 주의할 신체 부위나 컨디션, 2~3문장)
""".strip()
    return _chat(prompt)


def get_star_fortune(birth: date, gender: str, sign_name: str, sign_symbol: str) -> str:
    today = date.today().strftime("%Y년 %m월 %d일")
    prompt = f"""
오늘은 {today}입니다.
{sign_symbol} {sign_name}인 {gender}의 오늘 별자리 운세를 알려주세요.

MZ 감성으로 재치 있게, 다음 형식으로 작성해주세요:

✨ 오늘의 전체운 (2문장)

💞 연애·관계운 (2문장)

💼 직업·학업운 (2문장)

🍀 행운의 아이템
- 색상: 
- 숫자: 
- 한마디 조언: 
""".strip()
    return _chat(prompt)


def get_animal_fortune(birth: date, gender: str, animal_name: str, animal_emoji: str,
                       compatible: list[str]) -> str:
    today = date.today().strftime("%Y년 %m월 %d일")
    compat_str = ", ".join(compatible) if compatible else "없음"
    prompt = f"""
오늘은 {today}입니다.
{animal_emoji} {animal_name}띠인 {gender}의 오늘 운세를 알려주세요.
궁합 좋은 띠: {compat_str}

유머러스하고 재치 있게, 다음 형식으로 작성해주세요:

{animal_emoji} 오늘의 한 줄 운세

⚠️ 오늘 조심할 것 (1~2가지)

🌟 오늘 잘 풀리는 것 (1~2가지)

💑 오늘 궁합 좋은 띠: {compat_str}
(왜 잘 맞는지 한 문장)
""".strip()
    return _chat(prompt)


def get_tarot_fortune(birth: date, gender: str, card_name: str, card_korean: str,
                      card_emoji: str, direction: str) -> str:
    today = date.today().strftime("%Y년 %m월 %d일")
    prompt = f"""
오늘은 {today}입니다.
{birth.strftime('%Y년 %m월 %d일')}생 {gender}이 오늘의 타로카드로
{card_emoji} {card_korean} ({card_name}) — {direction} 을 뽑았습니다.

신비롭고 재미있게, 다음 형식으로 해석해주세요:

{card_emoji} 카드의 핵심 메시지 (한 문장)

❤️ 사랑·관계 관점
(이 카드가 오늘 연애·인간관계에 주는 메시지, 2문장)

💼 일·목표 관점
(이 카드가 오늘 업무·목표에 주는 메시지, 2문장)

🔮 오늘의 조언
(이 카드가 오늘 당신에게 주는 핵심 행동 조언, 2문장)

✨ 타로 한마디
(오늘을 위한 짧은 격언 또는 응원 한 줄)
""".strip()
    return _chat(prompt)


# ── 종합 리포트 + 로또 ─────────────────────────────────────────────────────────

def get_synthesis_report(birth: date, gender: str,
                         saju_result: str, star_result: str,
                         animal_result: str, tarot_result: str,
                         tarot_card_label: str) -> str:
    today = date.today().strftime("%Y년 %m월 %d일")
    prompt = f"""
오늘은 {today}이고, {birth.strftime('%Y년 %m월 %d일')}생 {gender}의 오늘 운세 분석 결과입니다.

[사주운세]
{saju_result}

[별자리운세]
{star_result}

[띠운세]
{animal_result}

[타로카드: {tarot_card_label}]
{tarot_result}

위 네 가지를 모두 종합해서 다음 항목을 재미있고 실용적으로 작성해주세요:

⚠️ 오늘 조심해야 할 것
(구체적으로 2~3가지, 짧고 명확하게)

🎁 오늘의 행운 아이템
(색상 1가지, 음식 1가지, 장소나 물건 1가지)

💡 오늘 이렇게 보내세요
(한 줄 실천 팁)

🎴 타로가 오늘 당신에게 전하는 핵심 메시지
(한 줄, {tarot_card_label} 카드의 관점에서)

🌟 오늘의 한마디
(응원 멘트 또는 오늘 어울리는 명언 한 줄)
""".strip()
    return _chat(prompt)


def get_lotto_numbers(birth: date, gender: str,
                      saju_result: str, star_result: str,
                      animal_result: str, tarot_result: str) -> str:
    """로또 번호 5세트 추천 (번호만, 해석 없음)"""
    today = date.today().strftime("%Y년 %m월 %d일")
    prompt = f"""
오늘은 {today}이고, {birth.strftime('%Y년 %m월 %d일')}생 {gender}의 운세 분석 결과입니다.

[사주]: {saju_result[:200]}
[별자리]: {star_result[:200]}
[띠]: {animal_result[:200]}
[타로]: {tarot_result[:200]}

위 운세를 모두 고려해서, 오늘 이 사람에게 어울리는 로또 번호 5세트를 추천해주세요.
각 세트는 1~45 범위의 서로 다른 숫자 6개입니다.
5세트 모두 서로 다른 번호 조합이어야 합니다.

반드시 아래 형식으로만 답하세요. 이유나 설명은 절대 쓰지 마세요.
숫자만 출력하세요.

A세트: 번호 번호 번호 번호 번호 번호
B세트: 번호 번호 번호 번호 번호 번호
C세트: 번호 번호 번호 번호 번호 번호
D세트: 번호 번호 번호 번호 번호 번호
E세트: 번호 번호 번호 번호 번호 번호
""".strip()
    return _chat(prompt)
