# -*- coding: utf-8 -*-
"""
江戸川女子中 入試問題 学習アプリ
左：問題ページ画像 / 右：ページ内の単元ごとに関連YouTube動画を縦に並べる
"""
import json
import os
import re
import urllib.parse

import requests
import streamlit as st

APP_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(APP_DIR, "index.json")

SUBJECT_COLOR = {"算数": "#2e7d32", "理科": "#1565c0", "社会": "#e65100"}
VIDEOS_PER_TOPIC = 3  # 各単元で表示する動画の本数

st.set_page_config(page_title="江戸女 入試問題 勉強アプリ", page_icon="📚", layout="wide")

# 左の問題画像は固定したまま、右カラム（動画一覧）の中だけをスクロールできるようにする。
# stImage を含むカラム＝左、stTextInput を含むカラム＝右 を :has() で選び分ける。
st.markdown(
    """
    <style>
    /* 問題画像は画面の高さに収め、全体が見えるようにする */
    div[data-testid="stColumn"]:has([data-testid="stImage"]) [data-testid="stImage"] img {
        max-height: 80vh;
        width: auto !important;
        margin: 0 auto;
        display: block;
    }
    /* 右カラムはカラム内にスクロールバーを出し、動画だけをスクロールさせる */
    div[data-testid="stColumn"]:has([data-testid="stTextInput"]) {
        max-height: 80vh;
        overflow-y: auto;
        padding-right: 12px;
    }
    /* AI先生チャット：右下に常に表示する浮動パネル */
    .st-key-ai_chat {
        position: fixed;
        bottom: 1.2rem;
        right: 1.2rem;
        z-index: 1000;
        width: 390px;
        max-width: 92vw;
        max-height: 78vh;
        overflow-y: auto;
        background: #ffffff;
        border: 2px solid #bbbbbb;
        border-radius: 14px;
        padding: 6px 14px 14px;
        box-shadow: 0 6px 26px rgba(0,0,0,0.28);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------- PINロック
# PINは Streamlit secrets（APP_PIN）で上書き可能。未設定時は下記の既定値を使用。
try:
    APP_PIN = str(st.secrets["APP_PIN"])
except Exception:
    APP_PIN = "1203"


def require_pin():
    """正しいPINを入力するまで、ここから先を表示しない。"""
    if st.session_state.get("authed"):
        return
    st.markdown("<h2>📚 江戸女 入試問題 勉強アプリ</h2>", unsafe_allow_html=True)
    st.write("あいことば（PINコード）を入力してね。")
    pin = st.text_input("PINコード", type="password", label_visibility="collapsed")
    if st.button("はいる ▶"):
        if pin == APP_PIN:
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("PINコードが ちがいます。もう一度入力してね。")
    st.stop()


require_pin()


# ---------------------------------------------------------------- データ読み込み
@st.cache_data(show_spinner=False)
def load_index():
    with open(INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_page_topics(exam_id, page_no, topics):
    """index.json の該当ページの topics リストを丸ごと書き換えて保存する。"""
    with open(INDEX_PATH, encoding="utf-8") as f:
        data = json.load(f)
    for exam in data["exams"]:
        if exam["id"] == exam_id:
            for pg in exam["pages"]:
                if pg["page"] == page_no:
                    pg["topics"] = topics
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    load_index.clear()


# ---------------------------------------------------------------- YouTube 検索
@st.cache_data(ttl=3600, show_spinner=False)
def youtube_search(query, max_results=3):
    """APIキー不要。YouTube検索結果ページから動画IDを抽出する。"""
    if not query.strip():
        return []
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ja,en;q=0.8",
    }
    params = {"search_query": query, "hl": "ja", "gl": "JP"}
    resp = requests.get(
        "https://www.youtube.com/results", params=params, headers=headers, timeout=10
    )
    resp.raise_for_status()
    ids, seen = re.findall(r'"videoId":"([\w-]{11})"', resp.text), []
    for vid in ids:
        if vid not in seen:
            seen.append(vid)
        if len(seen) >= max_results:
            break
    return seen


# ---------------------------------------------------------------- Gemini（AI先生チャット）
try:
    GEMINI_API_KEY = str(st.secrets["GEMINI_API_KEY"])
except Exception:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

GEMINI_MODEL = "gemini-2.5-flash"

CHAT_SYSTEM = (
    "あなたは小学6年生の女の子の中学受験の勉強を手伝う、やさしい家庭教師です。"
    "添付された画像は、その子がいま見ている入試問題のページです。"
    "次のことを守ってください。"
    "・ひらがなを多めに、やさしく短い言葉で説明する。"
    "・いきなり答えを言わず、考え方やヒントを順番に教える。"
    "ただし「答えを教えて」と言われたら、解き方とあわせて答えも教える。"
    "・はげましの言葉をそえる。"
    "・算数の式は文字で書く（例: 3×4=12）。"
    "・勉強と関係ない話題は、やんわり勉強にもどす。"
)


def gemini_chat(image_bytes, unit_labels, history):
    """問題画像と会話履歴を Gemini に渡し、AI先生の返事（文字列）を返す。
    history は [{"role": "user"/"model", "text": str}, ...]（末尾は user）。
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)
    units = "、".join([u for u in unit_labels if u]) or "（未設定）"

    contents = []
    for i, msg in enumerate(history):
        if i == 0:
            # 最初の発言にだけ問題画像と単元情報を添える
            parts = [
                types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                types.Part.from_text(
                    text=f"【いま見ている問題ページ／単元: {units}】\n\n{msg['text']}"),
            ]
        else:
            parts = [types.Part.from_text(text=msg["text"])]
        contents.append(types.Content(role=msg["role"], parts=parts))

    resp = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=CHAT_SYSTEM),
    )
    return (resp.text or "").strip()


def render_chat(exam_id, page_no, img_path, unit_labels):
    """右下に常に表示する AI先生チャット。問題ページごとに会話を分ける。"""
    with st.container(key="ai_chat"):
        st.markdown("### 🤖 AI先生")

        if not GEMINI_API_KEY:
            st.info("AI先生は準備中です（Gemini APIキーが未設定）。")
            return

        st.caption(
            f"いまの問題：{page_no}ページ目／"
            f"{'、'.join([u for u in unit_labels if u]) or '—'}"
        )

        hist_key = f"chat_{exam_id}_{page_no}"
        history = st.session_state.setdefault(hist_key, [])

        for msg in history:
            if msg["role"] == "user":
                with st.chat_message("user", avatar="🧒"):
                    st.markdown(msg["text"])
            else:
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(msg["text"])

        def send(text):
            history.append({"role": "user", "text": text})
            try:
                with open(img_path, "rb") as f:
                    image_bytes = f.read()
                with st.spinner("🤖 AI先生が かんがえています…"):
                    answer = gemini_chat(image_bytes, unit_labels, history)
                history.append({"role": "model",
                                "text": answer or "うまく答えられませんでした。"})
            except Exception as e:
                history.append({"role": "model",
                                "text": f"ごめんね、いま答えられませんでした。({e})"})
            st.rerun()

        # 会話がまだ無いときは、ワンタップで解説を始められるようにする
        if not history:
            if st.button("📖 この問題を解説して",
                         key=f"chat_quick_{exam_id}_{page_no}", width="stretch"):
                send("この問題を、やさしく解説してください。")

        with st.form(key=f"chat_form_{exam_id}_{page_no}", clear_on_submit=True):
            user_msg = st.text_input(
                "しつもん", label_visibility="collapsed",
                placeholder="しつもんを入力してね…",
            )
            fc = st.columns([3, 2])
            sent = fc[0].form_submit_button("送信 ▶", width="stretch")
            cleared = fc[1].form_submit_button("会話をけす", width="stretch")
        if sent and user_msg.strip():
            send(user_msg.strip())
        if cleared:
            st.session_state[hist_key] = []
            st.rerun()


# ---------------------------------------------------------------- サイドバー
data = load_index()
exams = data["exams"]
subjects = sorted({e["subject"] for e in exams}, key=["算数", "理科", "社会"].index)

st.sidebar.title("📚 勉強メニュー")
subject = st.sidebar.radio("科目をえらぶ", subjects, horizontal=True)

rounds = [e for e in exams if e["subject"] == subject]
round_labels = [e["round"] for e in rounds]
round_label = st.sidebar.radio("回をえらぶ", round_labels, horizontal=True)

exam = next(e for e in rounds if e["round"] == round_label)
problems_only = st.sidebar.checkbox("問題ページだけ表示", value=True)

if problems_only:
    pages = [p for p in exam["pages"] if p["kind"] == "problem"]
else:
    pages = exam["pages"]

if not pages:
    st.warning("表示できるページがありません。")
    st.stop()

st.sidebar.divider()
st.sidebar.caption(
    "1ページにいくつかの単元があるときは、単元ごとに動画を並べています。\n"
    "ぴったりの動画が出ないときは、単元の下のキーワード欄を書きかえてね。"
)

# ---------------------------------------------------------------- ページ位置の管理
if st.session_state.get("cur_exam") != exam["id"] or \
        st.session_state.get("cur_mode") != problems_only:
    st.session_state["cur_exam"] = exam["id"]
    st.session_state["cur_mode"] = problems_only
    st.session_state["idx"] = 0

idx = min(st.session_state.get("idx", 0), len(pages) - 1)
page = pages[idx]

# ---------------------------------------------------------------- ヘッダー
color = SUBJECT_COLOR.get(subject, "#333")
st.markdown(
    f"<h2 style='margin-bottom:0'>令和7年度 江戸川女子中学校　"
    f"<span style='color:{color}'>{exam['label']}</span></h2>",
    unsafe_allow_html=True,
)

nav1, nav2, nav3, nav4 = st.columns([1, 1, 3, 2])
with nav1:
    if st.button("⬅️ まえ", width="stretch", disabled=(idx == 0)):
        st.session_state["idx"] = idx - 1
        st.rerun()
with nav2:
    if st.button("つぎ ➡️", width="stretch", disabled=(idx == len(pages) - 1)):
        st.session_state["idx"] = idx + 1
        st.rerun()
with nav3:
    st.markdown(
        f"<div style='text-align:center;font-size:1.2em;padding-top:4px'>"
        f"{idx + 1} / {len(pages)} ページ目</div>",
        unsafe_allow_html=True,
    )
with nav4:
    jump = st.selectbox(
        "ジャンプ", range(len(pages)),
        index=idx,
        format_func=lambda i: f"{i + 1}ページ目（PDF p{pages[i]['page']}）",
        label_visibility="collapsed",
    )
    if jump != idx:
        st.session_state["idx"] = jump
        st.rerun()

st.divider()

# ---------------------------------------------------------------- 本体：左右2カラム
left, right = st.columns([1.15, 1], gap="large")

with left:
    st.subheader("📄 問題")
    img_path = os.path.join(APP_DIR, page["image"].replace("/", os.sep))
    if os.path.exists(img_path):
        st.image(img_path, width="stretch")
    else:
        st.error(f"画像が見つかりません: {page['image']}")

with right:
    st.subheader("🎬 単元ごとの関連動画")

    topics = page.get("topics", [])

    if st.button("🔄 動画をさがしなおす", width="stretch"):
        youtube_search.clear()
        st.rerun()

    if not topics:
        st.info("このページには単元が登録されていません。")

    # 単元ごとに「見出し → キーワード欄 → 動画」を縦に並べる
    edited = False
    for i, topic in enumerate(topics):
        label = topic.get("label", f"単元{i + 1}")
        st.markdown(
            f"<div style='margin-top:18px;padding:6px 10px;border-radius:6px;"
            f"background:{color};color:#fff;font-weight:bold;font-size:1.05em'>"
            f"📘 {label}</div>",
            unsafe_allow_html=True,
        )

        kw_key = f"kw_{exam['id']}_{page['page']}_{i}"
        if kw_key not in st.session_state:
            st.session_state[kw_key] = topic.get("query", "")

        query = st.text_input(
            "🔍 検索キーワード（書きかえると保存されます）",
            key=kw_key,
            label_visibility="collapsed",
        )
        if query != topic.get("query", ""):
            topic["query"] = query
            edited = True

        search_url = "https://www.youtube.com/results?search_query=" + \
            urllib.parse.quote(query)
        st.link_button("▶ この単元をYouTubeで開く", search_url, width="stretch")

        try:
            with st.spinner("動画をさがしています…"):
                video_ids = youtube_search(query, max_results=VIDEOS_PER_TOPIC)
            if video_ids:
                for vid in video_ids:
                    st.video(f"https://www.youtube.com/watch?v={vid}")
            else:
                st.info("動画が見つかりませんでした。キーワードを変えてみてください。")
        except Exception:
            st.warning(
                "動画の取得に失敗しました（ネット接続を確認してください）。\n"
                "上の「YouTubeで開く」から直接さがせます。"
            )

    if edited:
        save_page_topics(exam["id"], page["page"], topics)
        st.toast("キーワードを保存しました ✅")

st.divider()
st.caption(
    f"出典: 江戸川女子中学校 入試問題（{exam['source_pdf']}） / "
    "学習用の個人利用アプリ"
)

# ---------------------------------------------------------------- AI先生チャット（右下フロート）
render_chat(
    exam["id"], page["page"], img_path,
    [t.get("label", "") for t in page.get("topics", [])],
)
