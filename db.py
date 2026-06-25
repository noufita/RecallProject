"""
db.py — كل العمليات مع Supabase
"""
import streamlit as st
from supabase import create_client, Client
from datetime import date
from sm2 import CardState, update_card, quality_from_result


@st.cache_resource
def get_supabase() -> Client:
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_ANON_KEY"]
    )


# ── Auth ──────────────────────────────────────────────────────────────────────

def sign_up(email: str, password: str):
    sb = get_supabase()
    return sb.auth.sign_up({"email": email, "password": password})

def sign_in(email: str, password: str):
    sb = get_supabase()
    return sb.auth.sign_in_with_password({"email": email, "password": password})

def sign_out():
    get_supabase().auth.sign_out()
    st.session_state.clear()

def current_user():
    return get_supabase().auth.get_user()


# ── Cards ─────────────────────────────────────────────────────────────────────

def save_cards(user_id: str, topic: str, questions: list[dict]):
    """حفظ بطاقات جديدة + إنشاء سجل مراجعة لكل بطاقة"""
    sb = get_supabase()
    for q in questions:
        card = sb.table("cards").insert({
            "user_id": user_id,
            "topic": topic,
            "question": q["question"],
            "options": q["options"],
            "correct_index": q["correct_index"],
        }).execute()

        card_id = card.data[0]["id"]
        sb.table("reviews").insert({
            "user_id": user_id,
            "card_id": card_id,
            "ease_factor": 2.5,
            "interval_days": 1,
            "due_date": str(date.today()),
            "repetitions": 0,
        }).execute()


def get_due_cards(user_id: str) -> list[dict]:
    """جلب البطاقات المستحقة اليوم أو قبله"""
    sb = get_supabase()
    today = str(date.today())

    result = sb.table("reviews")\
        .select("*, cards(*)")\
        .eq("user_id", user_id)\
        .lte("due_date", today)\
        .execute()

    return result.data or []


def get_all_topics(user_id: str) -> list[str]:
    sb = get_supabase()
    result = sb.table("cards")\
        .select("topic")\
        .eq("user_id", user_id)\
        .execute()
    topics = list({r["topic"] for r in (result.data or [])})
    return sorted(topics)


def get_stats(user_id: str) -> dict:
    """إحصائيات للـ dashboard"""
    sb = get_supabase()
    today = str(date.today())

    all_reviews = sb.table("reviews").select("*").eq("user_id", user_id).execute().data or []
    due_today   = [r for r in all_reviews if r["due_date"] <= today]
    mastered    = [r for r in all_reviews if r["repetitions"] >= 5]

    return {
        "total": len(all_reviews),
        "due_today": len(due_today),
        "mastered": len(mastered),
        "mastery_pct": int(len(mastered) / len(all_reviews) * 100) if all_reviews else 0,
    }


def submit_review(review_id: str, card: dict, correct: bool):
    """تحديث سجل المراجعة بعد إجابة الطالب (SM-2)"""
    sb = get_supabase()

    state = CardState(
        ease_factor=card["ease_factor"],
        interval_days=card["interval_days"],
        repetitions=card["repetitions"],
    )
    quality = quality_from_result(correct)
    new_state = update_card(state, quality)

    sb.table("reviews").update({
        "ease_factor":   new_state.ease_factor,
        "interval_days": new_state.interval_days,
        "repetitions":   new_state.repetitions,
        "due_date":      str(new_state.due_date),
        "last_quality":  quality,
        "updated_at":    "now()",
    }).eq("id", review_id).execute()
