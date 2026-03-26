"""
타로카드 덱 정의 및 랜덤 뽑기 모듈
메이저 아르카나 22장 + 정/역방향
"""

import random

MAJOR_ARCANA = [
    {"id": 0,    "name": "The Fool",         "korean": "바보",        "emoji": "🃏"},
    {"id": 1,    "name": "The Magician",      "korean": "마법사",       "emoji": "🎩"},
    {"id": 2,    "name": "The High Priestess","korean": "여사제",       "emoji": "🌙"},
    {"id": 3,    "name": "The Empress",       "korean": "여황제",       "emoji": "👑"},
    {"id": 4,    "name": "The Emperor",       "korean": "황제",        "emoji": "🏛️"},
    {"id": 5,    "name": "The Hierophant",    "korean": "교황",        "emoji": "📜"},
    {"id": 6,    "name": "The Lovers",        "korean": "연인",        "emoji": "💑"},
    {"id": 7,    "name": "The Chariot",       "korean": "전차",        "emoji": "🏇"},
    {"id": 8,    "name": "Strength",          "korean": "힘",          "emoji": "🦁"},
    {"id": 9,    "name": "The Hermit",        "korean": "은둔자",       "emoji": "🕯️"},
    {"id": 10,   "name": "Wheel of Fortune",  "korean": "운명의 수레바퀴", "emoji": "🎡"},
    {"id": 11,   "name": "Justice",           "korean": "정의",        "emoji": "⚖️"},
    {"id": 12,   "name": "The Hanged Man",    "korean": "매달린 남자",   "emoji": "🙃"},
    {"id": 13,   "name": "Death",             "korean": "죽음",        "emoji": "💀"},
    {"id": 14,   "name": "Temperance",        "korean": "절제",        "emoji": "⚗️"},
    {"id": 15,   "name": "The Devil",         "korean": "악마",        "emoji": "😈"},
    {"id": 16,   "name": "The Tower",         "korean": "탑",          "emoji": "⚡"},
    {"id": 17,   "name": "The Star",          "korean": "별",          "emoji": "⭐"},
    {"id": 18,   "name": "The Moon",          "korean": "달",          "emoji": "🌕"},
    {"id": 19,   "name": "The Sun",           "korean": "태양",        "emoji": "☀️"},
    {"id": 20,   "name": "Judgement",         "korean": "심판",        "emoji": "📯"},
    {"id": 21,   "name": "The World",         "korean": "세계",        "emoji": "🌍"},
]

# 무서운 카드 출력 시 위로 멘트
SCARY_CARD_NOTES = {
    "Death":      "💀 무섭지 않아요! 죽음 카드는 사실 '변화'와 '새로운 시작'을 뜻해요.",
    "The Tower":  "⚡ 탑 카드가 나왔어요. 예상치 못한 변화지만, 더 나은 구조를 위한 해체예요.",
    "The Devil":  "😈 악마 카드는 집착이나 유혹을 인식하고 해방될 기회를 뜻해요.",
    "The Hanged Man": "🙃 매달린 남자는 다른 시각으로 세상을 바라보라는 신호예요.",
}


def draw_cards(n: int = 3) -> list[dict]:
    """메이저 아르카나에서 n장 뽑기 (정/역방향 랜덤)"""
    selected = random.sample(MAJOR_ARCANA, n)
    result = []
    for card in selected:
        direction = random.choice(["정방향", "역방향"])
        note = SCARY_CARD_NOTES.get(card["name"], "")
        result.append({
            **card,
            "direction": direction,
            "display": f"{card['emoji']} {card['korean']} ({card['name']}) — {direction}",
            "scary_note": note,
        })
    return result


def card_label(card: dict) -> str:
    """카드 한 줄 표시용 문자열"""
    return f"{card['emoji']} {card['korean']} ({card['direction']})"
