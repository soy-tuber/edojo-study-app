# -*- coding: utf-8 -*-
"""
edojo_2025 の問題PDFを 1ページ=1枚のPNG画像に変換し、index.json を生成する。
再実行しても安全（画像は上書き、index.json は既存の単元・キーワード編集を引き継ぐ）。

index.json のスキーマ:
  各ページは topics（単元ごとの {label, query} のリスト）を持つ。
  1ページに複数単元の問題があるため、単元ごとに動画を出し分ける。
"""
import json
import os
import re

import fitz  # PyMuPDF

SRC_DIR = r"C:\Users\q0702\edojo_2025"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PAGES_DIR = os.path.join(OUT_DIR, "pages")
INDEX_PATH = os.path.join(OUT_DIR, "index.json")

ZOOM = 2.4  # 約170dpi

# exam_id -> (PDFファイル名, 科目, 回ラベル, 既定の検索キーワード)
EXAMS = [
    ("san_r1",    "20251sanmondai.pdf", "算数", "第1回", "中学受験 算数 解説"),
    ("san_r2",    "20252sanmondai.pdf", "算数", "第2回", "中学受験 算数 解説"),
    ("san_r3",    "20253sanmondai.pdf", "算数", "第3回", "中学受験 算数 解説"),
    ("rika_r1",   "20251rikamondai.pdf", "理科", "第1回", "中学受験 理科 解説"),
    ("rika_r2",   "20252rikamondai.pdf", "理科", "第2回", "中学受験 理科 解説"),
    ("rika_r3",   "20253rikamondai.pdf", "理科", "第3回", "中学受験 理科 解説"),
    ("shakai_r1", "20251shamondai.pdf", "社会", "第1回", "中学受験 社会 解説"),
    ("shakai_r2", "20252shamondai.pdf", "社会", "第2回", "中学受験 社会 解説"),
    ("shakai_r3", "20253shamondai.pdf", "社会", "第3回", "中学受験 社会 解説"),
]


def classify(text: str):
    """ページ種別を返す: 'title' / 'blank' / 'problem'"""
    t = (text or "").strip()
    compact = re.sub(r"\s+", "", t)
    if "計算用紙" in compact and len(compact) < 30:
        return "blank"
    if len(compact) < 12:
        return "blank"
    if "入学試験問題" in compact and ("注意" in compact or "受験番号" in compact):
        return "title"
    return "problem"


def load_existing_topics():
    """既存 index.json から、確定済みの単元（topics）を回収する。"""
    saved = {}
    if os.path.exists(INDEX_PATH):
        try:
            with open(INDEX_PATH, encoding="utf-8") as f:
                data = json.load(f)
            for exam in data.get("exams", []):
                for pg in exam.get("pages", []):
                    if pg.get("topics"):
                        saved[(exam["id"], pg["page"])] = pg["topics"]
        except Exception as e:
            print(f"  (既存 index.json 読み込みスキップ: {e})")
    return saved


def main():
    os.makedirs(PAGES_DIR, exist_ok=True)
    saved_topics = load_existing_topics()
    exams_out = []

    for exam_id, fname, subject, round_label, default_kw in EXAMS:
        src = os.path.join(SRC_DIR, fname)
        if not os.path.exists(src):
            print(f"[SKIP] 見つかりません: {src}")
            continue
        exam_dir = os.path.join(PAGES_DIR, exam_id)
        os.makedirs(exam_dir, exist_ok=True)

        doc = fitz.open(src)
        pages_out = []
        for i, page in enumerate(doc):
            page_no = i + 1
            kind = classify(page.get_text())
            img_name = f"p{page_no:02d}.png"
            pix = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM))
            pix.save(os.path.join(exam_dir, img_name))

            # 単元: 既存 index.json の確定済み topics を引き継ぐ。
            # 未確定の問題ページは科目既定のキーワードを1件だけ入れておく。
            topics = saved_topics.get((exam_id, page_no))
            if topics is None:
                if kind == "problem":
                    topics = [{"label": "解説", "query": default_kw}]
                else:
                    topics = []

            pages_out.append({
                "page": page_no,
                "image": f"pages/{exam_id}/{img_name}",
                "kind": kind,          # title / blank / problem
                "topics": topics,
            })
        doc.close()

        n_problem = sum(1 for p in pages_out if p["kind"] == "problem")
        exams_out.append({
            "id": exam_id,
            "subject": subject,
            "round": round_label,
            "label": f"{subject} {round_label}",
            "source_pdf": fname,
            "pages": pages_out,
        })
        print(f"[OK] {subject} {round_label}: 全{len(pages_out)}ページ (問題{n_problem})")

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump({"exams": exams_out}, f, ensure_ascii=False, indent=2)
    print(f"\nindex.json を書き出しました -> {INDEX_PATH}")


if __name__ == "__main__":
    main()
