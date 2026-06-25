"""
خوارزمية SM-2 — نفس اللي تستخدمها Anki
مصدر: https://www.supermemo.com/en/archives1990-2015/english/ol/sm2
"""

from datetime import date, timedelta
from dataclasses import dataclass

@dataclass
class CardState:
    ease_factor: float = 2.5
    interval_days: int = 1
    repetitions: int = 0
    due_date: date = None

    def __post_init__(self):
        if self.due_date is None:
            self.due_date = date.today()


def quality_from_result(correct: bool, hesitated: bool = False) -> int:
    """
    تحويل إجابة الطالب لتقييم 0-5:
      5 = صح بسهولة
      3 = صح مع تردد
      1 = غلط
    """
    if correct and not hesitated:
        return 5
    elif correct and hesitated:
        return 3
    else:
        return 1


def update_card(state: CardState, quality: int) -> CardState:
    """
    تطبيق خوارزمية SM-2 على البطاقة بعد كل مراجعة.
    quality: 0-5 (أقل من 3 = إجابة خاطئة)
    """
    q = quality

    if q < 3:
        # إجابة خاطئة → أعد من البداية
        state.repetitions = 0
        state.interval_days = 1
    else:
        # إجابة صحيحة → حسب عدد التكرارات
        if state.repetitions == 0:
            state.interval_days = 1
        elif state.repetitions == 1:
            state.interval_days = 6
        else:
            state.interval_days = round(state.interval_days * state.ease_factor)
        state.repetitions += 1

    # تحديث معامل السهولة (لا يقل عن 1.3)
    state.ease_factor = max(
        1.3,
        state.ease_factor + 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)
    )

    state.due_date = date.today() + timedelta(days=state.interval_days)
    return state
