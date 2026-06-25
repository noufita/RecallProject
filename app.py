import streamlit as st
import json, re
from datetime import date
from groq import Groq
from pypdf import PdfReader
import db

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="RecallAI", page_icon="🧠", layout="wide", initial_sidebar_state="collapsed")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@500;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.stApp{background:#080c14;}
#MainMenu,footer,header{visibility:hidden;}
.block-container{padding:0 2rem 4rem;max-width:960px;margin:0 auto;}

.hero{text-align:center;padding:3rem 1rem 1.5rem;}
.hero-badge{display:inline-block;background:rgba(99,102,241,.12);border:1px solid rgba(99,102,241,.3);color:#a5b4fc;font-size:.7rem;font-weight:600;letter-spacing:.12em;text-transform:uppercase;padding:5px 14px;border-radius:100px;margin-bottom:1rem;}
.hero-title{font-family:'Space Grotesk',sans-serif;font-size:clamp(2rem,5vw,3.2rem);font-weight:700;line-height:1.1;margin:0 0 .8rem;background:linear-gradient(135deg,#e2e8f0 30%,#818cf8 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.hero-sub{font-size:.95rem;color:#64748b;max-width:460px;margin:0 auto 1.5rem;line-height:1.6;}

.card{background:#0e1420;border:1px solid #1e293b;border-radius:16px;padding:1.4rem;margin-bottom:.8rem;}
.card-title{font-family:'Space Grotesk',sans-serif;font-size:.7rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#475569;margin-bottom:.8rem;}

.stat-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:.8rem;margin-bottom:1.2rem;}
.stat-box{background:#0e1420;border:1px solid #1e293b;border-radius:14px;padding:1.2rem;text-align:center;}
.stat-num{font-family:'Space Grotesk',sans-serif;font-size:2rem;font-weight:700;color:#e2e8f0;line-height:1;}
.stat-label{font-size:.72rem;color:#475569;margin-top:.3rem;text-transform:uppercase;letter-spacing:.08em;}

.q-card{background:#0b1120;border:1px solid #1e293b;border-radius:14px;padding:1.4rem 1.6rem;margin-bottom:1rem;}
.q-num{font-size:.68rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#6366f1;margin-bottom:.5rem;}
.q-text{font-size:1rem;font-weight:500;color:#e2e8f0;margin-bottom:1rem;line-height:1.5;}

.chips-wrap{display:flex;flex-wrap:wrap;gap:8px;}
.chip{background:rgba(99,102,241,.08);border:1px solid rgba(99,102,241,.2);color:#a5b4fc;font-size:.82rem;padding:5px 14px;border-radius:100px;}

.nav-tab{display:inline-flex;background:#0e1420;border:1px solid #1e293b;border-radius:12px;padding:4px;margin-bottom:1.5rem;}
.nav-btn{padding:8px 20px;border-radius:9px;border:none;background:transparent;color:#475569;font-size:.85rem;font-weight:500;cursor:pointer;transition:all .15s;}
.nav-btn.active{background:linear-gradient(135deg,#4f46e5,#7c3aed);color:white;}

.due-badge{display:inline-block;background:rgba(251,191,36,.1);border:1px solid rgba(251,191,36,.3);color:#fbbf24;font-size:.7rem;font-weight:700;padding:3px 10px;border-radius:100px;margin-left:8px;}

.score-banner{background:linear-gradient(135deg,#0f172a,#1a1040);border:1px solid #312e81;border-radius:20px;padding:2rem;text-align:center;margin:1rem 0;}
.score-num{font-family:'Space Grotesk',sans-serif;font-size:3.5rem;font-weight:700;line-height:1;}

.stButton>button{background:linear-gradient(135deg,#4f46e5,#7c3aed)!important;color:white!important;border:none!important;border-radius:10px!important;padding:.6rem 1.8rem!important;font-weight:600!important;font-size:.9rem!important;width:100%;}
.stButton>button:hover{opacity:.85!important;}
[data-testid="stRadio"] label{color:#94a3b8!important;font-size:.9rem;}
hr{border-color:#1e293b!important;margin:1.2rem 0!important;}
.stProgress>div>div{background:linear-gradient(90deg,#6366f1,#a855f7)!important;}
[data-testid="stExpander"]{background:#0e1420!important;border:1px solid #1e293b!important;border-radius:12px!important;}
input[type="text"],input[type="password"]{background:#0e1420!important;border:1px solid #1e293b!important;color:#e2e8f0!important;border-radius:8px!important;}
</style>
""", unsafe_allow_html=True)

# ── Groq ──────────────────────────────────────────────────────────────────────
try:
    groq = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.error("⚠️ أضيفي GROQ_API_KEY في Streamlit Secrets.")
    st.stop()

# ── Helpers ───────────────────────────────────────────────────────────────────
def extract_pdf_text(f) -> str:
    reader = PdfReader(f)
    return "\n".join(p.extract_text() or "" for p in reader.pages)

def truncate(t, n=8000): return t[:n]

def ai_generate_cards(text: str, topic: str, num: int) -> list[dict]:
    prompt = f"""Generate {num} spaced-repetition flashcard questions from this study material about "{topic}".
Return ONLY a valid JSON array, no explanation, no markdown.
Format:
[{{"question":"...?","options":["A","B","C","D"],"correct_index":0}}]
correct_index is 0-based.
Text: {truncate(text)}
JSON:"""
    response = groq.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    raw = re.sub(r"```json|```", "", response.choices[0].message.content.strip()).strip()
    try:
        m = re.search(r'\[.*\]', raw, re.DOTALL)
        return json.loads(m.group()) if m else []
    except: return []

# ── Auth State ────────────────────────────────────────────────────────────────
if "user" not in st.session_state:
    st.session_state["user"] = None

def try_get_user():
    try:
        res = db.current_user()
        st.session_state["user"] = res.user if res else None
    except:
        st.session_state["user"] = None

if st.session_state["user"] is None:
    try_get_user()

user = st.session_state["user"]

# ══════════════════════════════════════════════════════════════════════════════
#  AUTH SCREEN
# ══════════════════════════════════════════════════════════════════════════════
if user is None:
    st.markdown("""
    <div class="hero">
        <div class="hero-badge">AI Study Tool</div>
        <div class="hero-title">Turn notes into<br>lasting knowledge.</div>
        <div class="hero-sub">مراجعة متباعدة ذكية — كل سؤال يظهر في الوقت المثالي لتتذكره.</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        tab = st.radio("", ["تسجيل دخول", "حساب جديد"], horizontal=True, label_visibility="collapsed")
        st.markdown("<br>", unsafe_allow_html=True)

        email    = st.text_input("البريد الإلكتروني", placeholder="student@example.com")
        password = st.text_input("كلمة المرور", type="password", placeholder="••••••••")
        st.markdown("<br>", unsafe_allow_html=True)

        if tab == "تسجيل دخول":
            if st.button("دخول →", use_container_width=True):
                try:
                    res = db.sign_in(email, password)
                    st.session_state["user"] = res.user
                    st.rerun()
                except Exception as e:
                    st.error(f"خطأ: {e}")
        else:
            if st.button("إنشاء حساب →", use_container_width=True):
                try:
                    db.sign_up(email, password)
                    st.success("تم إنشاء الحساب! سجل دخولك.")
                except Exception as e:
                    st.error(f"خطأ: {e}")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APP (بعد تسجيل الدخول)
# ══════════════════════════════════════════════════════════════════════════════
user_id = user.id

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"**{user.email}**")
    st.divider()
    if st.button("تسجيل خروج"):
        db.sign_out()
        st.rerun()

# ── Navigation ────────────────────────────────────────────────────────────────
stats = db.get_stats(user_id)
due_label = f" ({stats['due_today']})" if stats['due_today'] > 0 else ""

if "page" not in st.session_state:
    st.session_state["page"] = "today"

col_n1, col_n2, col_n3, col_n4 = st.columns([1,1,1,3])
with col_n1:
    if st.button(f"📅 اليوم{due_label}", use_container_width=True):
        st.session_state["page"] = "today"
with col_n2:
    if st.button("📄 إضافة PDF", use_container_width=True):
        st.session_state["page"] = "upload"
with col_n3:
    if st.button("📊 تقدمي", use_container_width=True):
        st.session_state["page"] = "progress"

page = st.session_state["page"]
st.divider()

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: TODAY — المراجعة اليومية
# ══════════════════════════════════════════════════════════════════════════════
if page == "today":
    st.markdown(f"""
    <div style="margin-bottom:1.2rem">
        <div style="font-family:'Space Grotesk',sans-serif;font-size:1.4rem;font-weight:700;color:#e2e8f0">
            مراجعة اليوم
        </div>
        <div style="font-size:.82rem;color:#475569;margin-top:.3rem">{date.today().strftime('%A, %d %B %Y')}</div>
    </div>
    """, unsafe_allow_html=True)

    due_cards = db.get_due_cards(user_id)

    if not due_cards:
        st.markdown("""
        <div class="card" style="text-align:center;padding:3rem">
            <div style="font-size:3rem">🎉</div>
            <div style="color:#e2e8f0;font-weight:600;font-size:1.1rem;margin:.5rem 0">كل البطاقات مراجَعة!</div>
            <div style="color:#475569;font-size:.85rem">لا يوجد شيء مستحق اليوم — أضيفي PDF جديد أو عودي لاحقاً.</div>
        </div>
        """, unsafe_allow_html=True)

    else:
        # Session للمراجعة اليومية
        if "review_idx" not in st.session_state:
            st.session_state["review_idx"] = 0
            st.session_state["review_results"] = []
            st.session_state["show_answer"] = False

        idx = st.session_state["review_idx"]

        # Progress bar
        progress = idx / len(due_cards)
        st.progress(min(progress, 1.0))
        st.caption(f"{idx} / {len(due_cards)} بطاقة")
        st.markdown("<br>", unsafe_allow_html=True)

        if idx >= len(due_cards):
            # النتيجة النهائية
            results = st.session_state["review_results"]
            correct = sum(1 for r in results if r)
            total   = len(results)
            pct     = int(correct / total * 100) if total else 0

            if pct >= 80:   emoji, msg, color = "🏆", "ممتاز!", "#4ade80"
            elif pct >= 50: emoji, msg, color = "📈", "استمري!", "#fbbf24"
            else:           emoji, msg, color = "📚", "راجعي مجدداً.", "#f87171"

            st.markdown(f"""
            <div class="score-banner">
                <div style="font-size:2.5rem">{emoji}</div>
                <div class="score-num" style="color:{color}">{correct}<span style="font-size:2rem;color:#334155"> / {total}</span></div>
                <div style="font-size:1rem;color:#94a3b8;margin:.3rem 0">{pct}%</div>
                <div style="color:#64748b;font-size:.85rem">{msg}</div>
            </div>
            """, unsafe_allow_html=True)

            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🔄 راجع مجدداً", use_container_width=True):
                    del st.session_state["review_idx"]
                    del st.session_state["review_results"]
                    del st.session_state["show_answer"]
                    st.rerun()
            with col_b:
                if st.button("📄 أضف PDF جديد", use_container_width=True):
                    st.session_state["page"] = "upload"
                    del st.session_state["review_idx"]
                    del st.session_state["review_results"]
                    del st.session_state["show_answer"]
                    st.rerun()

        else:
            entry   = due_cards[idx]
            card    = entry["cards"]
            review  = entry

            # topic badge
            st.markdown(f'<span class="chip">📚 {card["topic"]}</span>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            # السؤال
            st.markdown(f"""
            <div class="q-card">
                <div class="q-num">بطاقة {idx+1} من {len(due_cards)}</div>
                <div class="q-text">{card['question']}</div>
            </div>
            """, unsafe_allow_html=True)

            selected = st.radio("اختاري إجابتك:", card["options"], key=f"rev_{idx}", label_visibility="collapsed")
            sel_idx  = card["options"].index(selected)

            st.markdown("<br>", unsafe_allow_html=True)
            col_a, col_b, col_c = st.columns([1,2,1])
            with col_b:
                if st.button("تأكيد الإجابة ←", use_container_width=True):
                    correct = (sel_idx == card["correct_index"])
                    db.submit_review(review["id"], review, correct)
                    st.session_state["review_results"].append(correct)
                    st.session_state["review_idx"] += 1
                    st.rerun()

            # SM-2 info
            interval = review["interval_days"]
            reps     = review["repetitions"]
            next_lbl = "غداً" if interval == 1 else f"بعد {interval} يوم"
            st.markdown(f"""
            <div style="margin-top:1rem;font-size:.75rem;color:#334155;text-align:center">
                🔁 تكرارات: {reps} &nbsp;|&nbsp; ⏳ المراجعة القادمة بعد الإجابة: {next_lbl}
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: UPLOAD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "upload":
    st.markdown("""
    <div style="font-family:'Space Grotesk',sans-serif;font-size:1.4rem;font-weight:700;color:#e2e8f0;margin-bottom:1.2rem">
        إضافة مادة جديدة
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader("📄 ارفع الـ PDF", type=["pdf"], label_visibility="collapsed")

    if uploaded:
        with st.spinner("قراءة الملف..."):
            text = extract_pdf_text(uploaded)

        if not text.strip():
            st.error("ما قدرت أقرأ النص. تأكدي إن الـ PDF نصي وليس صور.")
            st.stop()

        word_count = len(text.split())
        st.markdown(f"""
        <div class="card" style="display:flex;align-items:center;gap:1rem">
            <div style="font-size:2rem">📄</div>
            <div>
                <div style="color:#e2e8f0;font-weight:600">{uploaded.name}</div>
                <div style="color:#475569;font-size:.8rem">{word_count:,} كلمة مستخرجة</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("معاينة النص"):
            st.text_area("", text[:2000], height=180, label_visibility="collapsed")

        st.markdown("<br>", unsafe_allow_html=True)
        topic = st.text_input("اسم الموضوع / المادة", placeholder="مثال: الفصل ٣ — المشتقات")
        num_q = st.select_slider("عدد البطاقات", options=[5, 10, 15, 20], value=10)
        st.markdown("<br>", unsafe_allow_html=True)

        col_a, col_b, col_c = st.columns([1,2,1])
        with col_b:
            if st.button("⚡ توليد البطاقات وحفظها", use_container_width=True):
                if not topic.strip():
                    st.warning("أدخلي اسم الموضوع أولاً.")
                    st.stop()
                with st.spinner(f"توليد {num_q} بطاقة..."):
                    cards = ai_generate_cards(text, topic, num_q)
                if not cards:
                    st.error("ما قدر يولّد بطاقات. حاولي مجدداً.")
                    st.stop()
                with st.spinner("حفظ البطاقات..."):
                    db.save_cards(user_id, topic, cards)
                st.success(f"✅ تم حفظ {len(cards)} بطاقة لمراجعة «{topic}»!")
                st.balloons()

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: PROGRESS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "progress":
    st.markdown("""
    <div style="font-family:'Space Grotesk',sans-serif;font-size:1.4rem;font-weight:700;color:#e2e8f0;margin-bottom:1.2rem">
        تقدمي
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="stat-grid">
        <div class="stat-box">
            <div class="stat-num" style="color:#818cf8">{stats['total']}</div>
            <div class="stat-label">إجمالي البطاقات</div>
        </div>
        <div class="stat-box">
            <div class="stat-num" style="color:#fbbf24">{stats['due_today']}</div>
            <div class="stat-label">مستحقة اليوم</div>
        </div>
        <div class="stat-box">
            <div class="stat-num" style="color:#4ade80">{stats['mastered']}</div>
            <div class="stat-label">بطاقات متقنة</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if stats["total"] > 0:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">نسبة الإتقان الكلية</div>
            <div style="font-family:'Space Grotesk',sans-serif;font-size:2.5rem;font-weight:700;color:#4ade80">{stats['mastery_pct']}%</div>
        </div>
        """, unsafe_allow_html=True)
        st.progress(stats["mastery_pct"] / 100)

    topics = db.get_all_topics(user_id)
    if topics:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""<div class="card-title" style="margin-bottom:.5rem">المواد المضافة</div>""", unsafe_allow_html=True)
        chips = "".join(f'<span class="chip">📚 {t}</span>' for t in topics)
        st.markdown(f'<div class="chips-wrap">{chips}</div>', unsafe_allow_html=True)
    else:
        st.info("ما أضفتِ أي مادة بعد. ابدأ بـ «إضافة PDF».")