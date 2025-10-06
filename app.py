# ======================================================
# app.py : Gemini対応（google-genai使用）Streamlitアプリ
# ======================================================

import os
import streamlit as st
import pandas as pd
from io import BytesIO
from docx import Document
from PyPDF2 import PdfReader
from google import genai  # ← 新Gemini SDK

# ------------------------------------------------------
# 0. ページ設定
# ------------------------------------------------------
st.set_page_config(page_title="技術ニーズマッチング（Gemini版）", layout="wide")

# ------------------------------------------------------
# 1. ログイン設定（複数ユーザー対応）
# ------------------------------------------------------
# secrets.toml の例：
# [auth]
# users = [
#     { username = "tanaka", password = "pass123" },
#     { username = "sato",   password = "pass456" }
# ]

users = st.secrets["auth"]["users"]

def login():
    """複数ユーザー対応ログイン画面"""
    st.title("🔒 ログイン")
    user = st.text_input("ユーザー名を入力してください")
    pw = st.text_input("パスワードを入力してください", type="password")

    if st.button("ログイン"):
        for u in users:
            if user == u["username"] and pw == u["password"]:
                st.session_state["logged_in"] = True
                st.session_state["user_name"] = user
                st.success(f"ようこそ、{user} さん！")
                st.rerun()
                return
        st.error("ユーザー名またはパスワードが違います。")

# ▼セッション初期化
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# ▼ログイン状態チェック
if not st.session_state["logged_in"]:
    login()
    st.stop()

# ▼ログイン後サイドバー
st.sidebar.success(f"👤 ログイン中：{st.session_state['user_name']}")
if st.sidebar.button("ログアウト"):
    st.session_state["logged_in"] = False
    st.rerun()

# ------------------------------------------------------
# 2. CSV / PDF 読み込み
# ------------------------------------------------------
@st.cache_data
def load_csv(path="data/sample.csv"):
    try:
        return pd.read_csv(path)
    except Exception as e:
        st.warning(f"CSVの読み込みに失敗しました: {e}")
        return pd.DataFrame()

df = load_csv()

st.sidebar.header("📁 ファイル読込（任意）")
uploaded_csv = st.sidebar.file_uploader("CSVをアップロード", type=["csv"])
uploaded_pdf = st.sidebar.file_uploader("PDFをアップロード", type=["pdf"])

if uploaded_csv:
    try:
        df = pd.read_csv(uploaded_csv)
        st.sidebar.success("CSVを読み込みました。")
    except Exception as e:
        st.sidebar.error(f"CSV読込エラー: {e}")

pdf_text = ""
if uploaded_pdf:
    try:
        reader = PdfReader(uploaded_pdf)
        for page in reader.pages:
            pdf_text += page.extract_text() or ""
        st.sidebar.success("PDFを読み込みました。")
    except Exception as e:
        st.sidebar.error(f"PDF読込エラー: {e}")

# ------------------------------------------------------
# 3. メイン画面（3タブ構成）
# ------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["①マッチング実行", "②アイデア生成（Gemini）", "③ファイル作成"])

# ---------------------------
# ① マッチング実行
# ---------------------------
with tab1:
    st.header("マッチング実行")
    col1, col2, col3 = st.columns([2,2,2])
    with col1:
        company = st.text_input("企業名：")
        news_kw = st.text_input("ニュース名：", placeholder="（曖昧検索）")
    with col2:
        major = st.selectbox("大分類：", ["", "材料", "機械", "電気"])
    with col3:
        middle = st.selectbox("中分類：", ["", "加工", "AI", "制御"])

    c1, c2 = st.columns([1,1])
    with c1:
        if st.button("検索"):
            st.success("ダミー検索を実行しました。")
    with c2:
        if st.button("クリア"):
            st.rerun()

    st.markdown("### 結果一覧")
    if not df.empty:
        df_show = df.copy()
        if "番号" not in df_show.columns:
            df_show.insert(0, "番号", range(1, len(df_show)+1))
        df_show.insert(1, "✔選択", False)
        st.dataframe(df_show, use_container_width=True, height=300)
    else:
        st.info("データがありません。左サイドバーからCSVをアップロードできます。")

# ---------------------------
# ② アイデア生成（Gemini）
# ---------------------------
with tab2:
    st.header("💡 Gemini によるアイデア生成")

    gemini_key = st.secrets["api"].get("gemini_key", "")
    if not gemini_key:
        st.error("Gemini APIキーが設定されていません。[api] に gemini_key を追加してください。")
        st.stop()

    # Geminiクライアントの初期化
    client = genai.Client(api_key=gemini_key)

    st.write("以下のCSVデータまたはPDF内容をもとにAIが新しいアイデアを生成します。")
    if not df.empty:
        st.dataframe(df.head(5), use_container_width=True)
    else:
        st.info("CSVをアップロードすると、AIが内容を参照します。")

    prompt = st.text_area(
        "🔧 プロンプト（AIへの指示文）",
        "以下の技術ニュースをもとに、新しい応用技術アイデアを3つ提案してください。"
    )

    if st.button("🚀 Geminiでアイデア生成"):
        with st.spinner("Geminiが考え中..."):
            text_summary = ""
            if not df.empty:
                text_summary = "\n".join(
                    df.head(3).astype(str).fillna("").apply(lambda row: " ".join(row), axis=1)
                )
            elif pdf_text:
                text_summary = pdf_text[:1000]

            full_prompt = f"{prompt}\n\n元データ:\n{text_summary}"

            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash",  # 最新モデル
                    contents=full_prompt,
                )
                output_text = getattr(response, "text", None) or getattr(response, "output_text", "")
                st.success("💡 アイデア生成完了！")
                st.write(output_text if output_text else response)
            except Exception as e:
                st.error(f"Geminiエラー: {e}")

# ---------------------------
# ③ ファイル作成
# ---------------------------
with tab3:
    st.header("📄 Wordファイル作成（ダミー）")
    st.write("選択データとPDF内容からWordレポートを生成します。")

    def make_docx(df_in: pd.DataFrame, pdf_text_in: str) -> bytes:
        doc = Document()
        doc.add_heading("技術ニーズ マッチング レポート（ダミー）", level=1)
        doc.add_paragraph(f"■ ログインユーザー：{st.session_state['user_name']}")
        doc.add_paragraph("■ PDF抽出テキスト（先頭100文字）：")
        doc.add_paragraph((pdf_text_in or "（PDF未読込）")[:100])

        if not df_in.empty:
            doc.add_heading("■ データ要約", level=2)
            for _, row in df_in.head(10).iterrows():
                title = str(row.get("技術ニュース名", row.get("タイトル", "（無題）")))
                company = str(row.get("企業名", ""))
                summary = str(row.get("要約", ""))
                doc.add_paragraph(f"・{title} / {company}")
                if summary:
                    doc.add_paragraph(f"  - 要約: {summary}")
        else:
            doc.add_paragraph("データがありません。")

        bio = BytesIO()
        doc.save(bio)
        bio.seek(0)
        return bio.read()

    if st.button("Word出力"):
        content = make_docx(df, pdf_text)
        st.download_button(
            "📄 ダウンロード（output.docx）",
            data=content,
            file_name="output.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
