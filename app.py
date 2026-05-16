# -*- coding: utf-8 -*-
"""
江戸川女子中 入試問題 学習アプリ
左：問題ページ画像 / 右：トピック関連のYouTube動画
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

st.set_page_config(page_title="江戸女 入試問題 勉強アプリ", page_icon="📚", layout="wide")


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


def save_topic(exam_id, page_no, new_topic):
    """index.json の該当ページの topic を書き換えて保存する。"""
    with open(INDEX_PATH, encoding="utf-8") as f:
        data = json.load(f)
    for exam in data["exams"]:
        if exam["id"] == exam_id:
            for pg in exam["pages"]:
                if pg["page"] == page_no:
                    pg["topic"] = new_topic
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    load_index.clear()


# ---------------------------------------------------------------- YouTube 検索
@st.cache_data(ttl=3600, show_spinner=False)
def youtube_search(query, max_results=4):
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
    "右側の動画はキーワード検索で表示しています。\n"
    "ぴったりの動画が出ないときは、問題の下のキーワード欄を書きかえてね。"
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
    st.subheader("🎬 関連動画")
    topic_key = f"topic_{exam['id']}_{page['page']}"
    topic = st.text_input(
        "🔍 動画の検索キーワード（書きかえると保存されます）",
        value=page["topic"],
        key=topic_key,
    )
    if topic != page["topic"]:
        save_topic(exam["id"], page["page"], topic)
        st.toast("キーワードを保存しました ✅")

    cols = st.columns([1, 1])
    with cols[0]:
        refresh = st.button("🔄 動画をさがしなおす", width="stretch")
    with cols[1]:
        search_url = "https://www.youtube.com/results?search_query=" + \
            urllib.parse.quote(topic)
        st.link_button("▶ YouTubeで開く", search_url, width="stretch")

    if refresh:
        youtube_search.clear()

    try:
        with st.spinner("動画をさがしています…"):
            video_ids = youtube_search(topic, max_results=4)
        if video_ids:
            for vid in video_ids:
                st.video(f"https://www.youtube.com/watch?v={vid}")
        else:
            st.info("動画が見つかりませんでした。キーワードを変えてみてください。")
    except Exception as e:
        st.warning(
            "動画の取得に失敗しました（ネット接続を確認してください）。\n"
            "上の「YouTubeで開く」から直接さがせます。"
        )
        st.caption(f"詳細: {e}")

st.divider()
st.caption(
    f"出典: 江戸川女子中学校 入試問題（{exam['source_pdf']}） / "
    "学習用の個人利用アプリ"
)
