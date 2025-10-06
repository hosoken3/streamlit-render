
import streamlit as st
import pandas as pd
from io import BytesIO
from docx import Document
from PyPDF2 import PdfReader

st.set_page_config(page_title="技術ニーズマッチング（ダミー）", layout="wide")

# -----------------
# Password (simple)
# -----------------
def password_protect():
    st.title("🔒 パスワード認証")
    pwd = st.text_input("パスワードを入力してください", type="password")
    valid_pwd = st.secrets.get("auth", {}).get("password", None)
    # allow env override (Render)
    env_pwd = st.session_state.get("ENV_PWD")
    if env_pwd:
        valid_pwd = env_pwd
    if pwd and valid_pwd and pwd == valid_pwd:
        return True
    if pwd and valid_pwd and pwd != valid_pwd:
        st.error("パスワードが違います。")
    elif pwd and not valid_pwd:
        st.warning("パスワードが設定されていません。secrets.toml か環境変数で設定してください。")
        return True
    return False

# Allow environment override easily (for demo)
import os
if os.getenv("STREAMLIT_AUTH_PASSWORD"):
    if "ENV_PWD" not in st.session_state:
        st.session_state["ENV_PWD"] = os.getenv("STREAMLIT_AUTH_PASSWORD")

if not password_protect():
    st.stop()

st.caption("※ファイルの読み込みは管理者が行います。")

# -----------------
# Data Load (CSV)
# -----------------
@st.cache_data
def load_csv(path="data/sample.csv"):
    try:
        return pd.read_csv(path)
    except Exception as e:
        st.warning(f"CSVの読み込みに失敗しました: {e}")
        return pd.DataFrame()

df = load_csv()

# -----------------
# Sidebar Uploads
# -----------------
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

# -----------------
# Tabs
# -----------------
tab1, tab2, tab3 = st.tabs(["①マッチング実行", "②アイデア生成", "③ファイル作成"])

with tab1:
    st.subheader("マッチング実行")
    col1, col2, col3 = st.columns([2,2,2])
    with col1:
        company = st.text_input("企業名：")
        news = st.text_input("ニュース名：", placeholder="（曖昧検索）")
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
            st.experimental_rerun()

    st.markdown("### 結果一覧")
    # 先頭にチェック列を見せるダミー
    if not df.empty and "番号" in df.columns:
        df_show = df.copy()
        df_show.insert(0, "✔選択", False)
        st.dataframe(df_show, use_container_width=True, height=300)
    else:
        st.info("データがありません。左のサイドバーからCSVをアップロードできます。")

with tab2:
    st.subheader("アイデア生成")
    st.write("（ダミー）元データから類似項目を抽出し、アイデア候補を表示します。")
    if not df.empty:
        idea_df = df.rename(columns={"技術ニュース名":"技術ニーズのニュース名"}).copy()
        idea_df["similarity"] = [0.82, 0.77, 0.69][:len(idea_df)]
        st.dataframe(idea_df, use_container_width=True, height=300)
        if st.button("アイデア生成"):
            st.success("ダミー：アイデアを生成しました。")
    else:
        st.info("CSVデータを読み込むと結果が表示されます。")

with tab3:
    st.subheader("ファイル作成")
    st.write("選択データとPDF抽出テキストから、Wordレポートを作成します。（ダミー）")

    def make_docx(df_in: pd.DataFrame, pdf_text_in: str) -> bytes:
        doc = Document()
        doc.add_heading("技術ニーズ マッチング レポート（ダミー）", level=1)
        doc.add_paragraph("■ 生成日時：自動")
        doc.add_paragraph("■ PDF抽出テキスト（先頭100文字）：")
        doc.add_paragraph((pdf_text_in or "（PDF未読込）")[:100])

        if not df_in.empty:
            doc.add_heading("■ データ要約", level=2)
            for _, row in df_in.head(10).iterrows():
                title = str(row.get("技術ニュース名", "（無題）"))
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
