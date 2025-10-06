# ======================================================
# app.py : Render Secret Files の sample.csv / sample.pdf を読み込み
#   - 認証: 環境変数 USERNAME_i / PASSWORD_i の「ペア一致」照合（例: USERNAME_1 と PASSWORD_1）
#   - データ: Secret Files に置いた sample.csv / sample.pdf を優先読み込み
#   - タブ: ①マッチング実行 ②アイデア生成（Gemini） ③ファイル作成（Word出力）
#   - 依存: streamlit, pandas, python-docx, PyPDF2, google-genai
#   - Secret Files の標準パス: /etc/secrets/<filename>（およびルートにも展開される場合あり）
# ======================================================

import os
from pathlib import Path
import streamlit as st
import pandas as pd
from io import BytesIO
from docx import Document
from PyPDF2 import PdfReader

# ==== Gemini SDK（新）====
# pip install google-genai
from google import genai

st.set_page_config(page_title="技術ニーズマッチング（Secret Files対応）", layout="wide")

# ------------------------------------------------------
# 0) Secret Files の探索ヘルパー
# ------------------------------------------------------
def find_secret_or_local(filename: str) -> Path | None:
    """
    Secret Files (/etc/secrets/<filename>) と カレント(<filename>) を優先的に探索。
    リポジトリ同梱の data/ にも後方互換としてフォールバック。
    """
    candidates = [
        Path("/etc/secrets") / filename,  # Secret Files 標準パス
        Path.cwd() / filename,            # ルートにも展開されることがある
        Path("data") / filename,          # 旧来フォルダ
    ]
    for p in candidates:
        if p.exists():
            return p
    return None

# ------------------------------------------------------
# 1) 環境変数からユーザー一覧を構築（USERNAME_1/PASSWORD_1 … のペアのみ有効）
# ------------------------------------------------------
def load_users_from_env(max_users: int = 50):
    users = []
    for i in range(1, max_users + 1):
        u = os.getenv(f"USERNAME_{i}")
        p = os.getenv(f"PASSWORD_{i}")
        # 片方だけは無効。ペア一致の行のみ採用。
        if u and p:
            users.append({"username": u, "password": p})
    return users

USERS = load_users_from_env()

# ------------------------------------------------------
# 2) Gemini API キー（環境変数）
# ------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None  # UIで警告

# ------------------------------------------------------
# 3) ログインUI（ペア一致必須）
# ------------------------------------------------------
def login_ui():
    st.title("🔐 ログイン")
    st.caption("※ Render の Environment に設定した USERNAME_i / PASSWORD_i のペアで認証します。")
    in_user = st.text_input("ユーザー名")
    in_pass = st.text_input("パスワード", type="password")
    if st.button("ログイン"):
        if any(u["username"] == in_user and u["password"] == in_pass for u in USERS):
            st.session_state["logged_in"] = True
            st.session_state["user_name"] = in_user
            st.success(f"ようこそ、{in_user} さん！")
            st.rerun()
        else:
            st.error("ユーザー名またはパスワードが間違っています。")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not USERS:
    st.error("Environment に USERNAME_1/PASSWORD_1 形式でユーザーが設定されていません。")
    st.stop()

if not st.session_state["logged_in"]:
    login_ui()
    st.stop()

# ログイン後サイドバー
with st.sidebar:
    st.success(f"👤 ログイン中：{st.session_state['user_name']}")
    if st.button("ログアウト"):
        st.session_state.clear()
        st.rerun()

# ------------------------------------------------------
# 4) Secret Files の sample.csv / sample.pdf を読み込み（優先）
#    - なければ data/ などにフォールバック
#    - さらにユーザーアップロードも可（保存はしない：Secret Files は読み取り専用）
# ------------------------------------------------------
def load_default_csv() -> pd.DataFrame:
    # Secret Files 优先
    path = find_secret_or_local("sample.csv")
    if path:
        try:
            return pd.read_csv(path)
        except Exception as e:
            st.warning(f"既定CSVの読み込みに失敗しました: {path} / {e}")
    # 見つからないor失敗時は空
    return pd.DataFrame()

def load_default_pdf_text() -> str:
    path = find_secret_or_local("sample.pdf")
    if path:
        try:
            reader = PdfReader(str(path))
            return "".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            st.warning(f"既定PDFの読み込みに失敗しました: {path} / {e}")
    return ""

df = load_default_csv()
pdf_text = load_default_pdf_text()

# サイドバー：任意アップロード（保存はせず、その場で上書き利用）
st.sidebar.header("📁 ファイル読込（Secret Files を既定に使用）")
st.sidebar.caption("※ Secret Files: /etc/secrets/sample.csv / sample.pdf を既定で読み込みます。アップロードは保存されません。")

uploaded_csv = st.sidebar.file_uploader("CSVを一時的に差し替え（保存しません）", type=["csv"])
if uploaded_csv:
    try:
        df = pd.read_csv(uploaded_csv)
        st.sidebar.success("CSVを読み込みました（セッション限定）。")
    except Exception as e:
        st.sidebar.error(f"CSV読込エラー: {e}")

uploaded_pdf = st.sidebar.file_uploader("PDFを一時的に差し替え（保存しません）", type=["pdf"])
if uploaded_pdf:
    try:
        reader = PdfReader(uploaded_pdf)
        pdf_text = "".join(page.extract_text() or "" for page in reader.pages)
        st.sidebar.success("PDFを読み込みました（セッション限定）。")
    except Exception as e:
        st.sidebar.error(f"PDF読込エラー: {e}")

# ------------------------------------------------------
# 5) メイン画面（3タブ構成）
# ------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["①マッチング実行", "②アイデア生成（Gemini）", "③ファイル作成"])

# ---------------------------
# ① マッチング実行（ダミー）
# ---------------------------
with tab1:
    st.header("マッチング実行")
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        company = st.text_input("企業名：")
        news_kw = st.text_input("ニュース名：", placeholder="（曖昧検索）")
    with col2:
        major = st.selectbox("大分類：", ["", "材料", "機械", "電気"])
    with col3:
        middle = st.selectbox("中分類：", ["", "加工", "AI", "制御"])

    c1, c2 = st.columns([1, 1])
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
            df_show.insert(0, "番号", range(1, len(df_show) + 1))
        df_show.insert(1, "✔選択", False)
        st.dataframe(df_show, use_container_width=True, height=300)
    else:
        st.info("データがありません。Secret Files に sample.csv を配置するか、CSVを一時アップロードしてください。")

# ---------------------------
# ② アイデア生成（Gemini）
# ---------------------------
with tab2:
    st.header("💡 Gemini によるアイデア生成")

    if not GEMINI_API_KEY:
        st.error("GEMINI_API_KEY が設定されていません。Render の Environment に GEMINI_API_KEY を追加してください。")
    else:
        st.write("以下のCSVデータまたはPDF内容をもとにAIが新しいアイデアを生成します。")
        if not df.empty:
            st.dataframe(df.head(5), use_container_width=True)
        elif pdf_text:
            st.info("PDFのテキストが読み込まれています。")
        else:
            st.info("CSVまたはPDF（Secret Files）をご用意いただくか、一時アップロードをご利用ください。")

        prompt = st.text_area(
            "🔧 プロンプト（AIへの指示文）",
            "以下の技術ニュースをもとに、新しい応用技術アイデアを3つ提案してください。"
        )

        if st.button("🚀 Geminiでアイデア生成"):
            with st.spinner("Geminiが考え中..."):
                try:
                    # 入力データの要約テキスト
                    text_summary = ""
                    if not df.empty:
                        text_summary = "\n".join(
                            df.head(3).astype(str).fillna("").apply(lambda row: " ".join(row), axis=1)
                        )
                    elif pdf_text:
                        text_summary = pdf_text[:1500]

                    full_prompt = f"{prompt}\n\n元データ:\n{text_summary}"

                    # モデルは用途に応じて変更可（"gemini-2.0-flash" など）
                    resp = client.models.generate_content(
                        model="gemini-1.5-flash",
                        contents=full_prompt,
                    )
                    out = getattr(resp, "text", None) or getattr(resp, "output_text", "")
                    st.success("💡 アイデア生成完了！")
                    st.write(out if out else str(resp))
                except Exception as e:
                    st.error(f"Geminiエラー: {e}")

# ---------------------------
# ③ ファイル作成（Word出力）
# ---------------------------
with tab3:
    st.header("📄 Wordファイル作成（ダミー）")
    st.write("選択データとPDF内容からWordレポートを生成します。")

    def make_docx(df_in: pd.DataFrame, pdf_text_in: str) -> bytes:
        doc = Document()
        doc.add_heading("技術ニーズ マッチング レポート（ダミー）", level=1)
        doc.add_paragraph(f"■ ログインユーザー：{st.session_state['user_name']}")
        doc.add_paragraph("■ PDF抽出テキスト（先頭150文字）：")
        doc.add_paragraph((pdf_text_in or "（PDF未読込）")[:150])

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
