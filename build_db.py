# -*- coding: utf-8 -*-
"""
index.json のメタデータ（試験・ページ・単元）と、問題PDFから抽出した問題文を
ひとつの SQLite データベース（edojo.db）にまとめる。

入試PDFはテキストが埋め込まれているため、PyMuPDF でそのまま本文を取り出す
（AI/OCR 不要・高速・取り出せる文字は正確。図や数式画像は対象外）。

再実行すると edojo.db を作り直す。
"""
import json
import os
import sqlite3
import sys

import fitz  # PyMuPDF

sys.stdout.reconfigure(encoding="utf-8")

APP_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(APP_DIR, "index.json")
SRC_DIR = r"C:\Users\q0702\edojo_2025"
DB_PATH = os.path.join(APP_DIR, "edojo.db")

SCHEMA = """
CREATE TABLE exams (
    id          TEXT PRIMARY KEY,   -- 例: san_r1
    subject     TEXT NOT NULL,      -- 算数 / 理科 / 社会
    round       TEXT NOT NULL,      -- 第1回 など
    label       TEXT NOT NULL,
    source_pdf  TEXT NOT NULL
);
CREATE TABLE pages (
    page_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id   TEXT NOT NULL REFERENCES exams(id),
    page_no   INTEGER NOT NULL,     -- PDF内のページ番号（1始まり）
    image     TEXT NOT NULL,        -- ページ画像の相対パス
    kind      TEXT NOT NULL,        -- title / blank / problem
    text      TEXT,                 -- PDFから抽出した問題文
    UNIQUE(exam_id, page_no)
);
CREATE TABLE topics (
    topic_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id   INTEGER NOT NULL REFERENCES pages(page_id),
    ordinal   INTEGER NOT NULL,     -- ページ内での単元の並び順（0始まり）
    label     TEXT NOT NULL,        -- 単元名
    query     TEXT NOT NULL         -- YouTube検索キーワード
);
CREATE INDEX idx_pages_exam   ON pages(exam_id);
CREATE INDEX idx_topics_page  ON topics(page_id);
"""


def extract_pdf_text(pdf_path):
    """PDFの各ページの埋め込みテキストを {ページ番号: 本文} で返す。"""
    texts = {}
    if not os.path.exists(pdf_path):
        return texts
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        texts[i + 1] = page.get_text().strip()
    doc.close()
    return texts


def main():
    with open(INDEX_PATH, encoding="utf-8") as f:
        data = json.load(f)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    n_pages = n_topics = n_text = 0
    for exam in data["exams"]:
        conn.execute(
            "INSERT INTO exams VALUES (?,?,?,?,?)",
            (exam["id"], exam["subject"], exam["round"],
             exam["label"], exam["source_pdf"]),
        )
        pdf_text = extract_pdf_text(os.path.join(SRC_DIR, exam["source_pdf"]))
        if not pdf_text:
            print(f"  [警告] PDFが見つからず本文未取得: {exam['source_pdf']}")

        for pg in exam["pages"]:
            text = pdf_text.get(pg["page"], "")
            cur = conn.execute(
                "INSERT INTO pages (exam_id, page_no, image, kind, text) "
                "VALUES (?,?,?,?,?)",
                (exam["id"], pg["page"], pg["image"], pg["kind"], text),
            )
            page_id = cur.lastrowid
            n_pages += 1
            if text:
                n_text += 1
            for i, topic in enumerate(pg.get("topics", [])):
                conn.execute(
                    "INSERT INTO topics (page_id, ordinal, label, query) "
                    "VALUES (?,?,?,?)",
                    (page_id, i, topic["label"], topic["query"]),
                )
                n_topics += 1

    conn.commit()
    conn.close()

    print(f"SQLite データベースを作成しました -> {DB_PATH}")
    print(f"  exams {len(data['exams'])} 件 / "
          f"pages {n_pages} 件（問題文あり {n_text} 件） / "
          f"topics {n_topics} 件")


if __name__ == "__main__":
    main()
