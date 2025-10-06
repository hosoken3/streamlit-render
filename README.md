# Streamlit ダミー（Render公開・パスワード保護）

## 機能（ダミー）
- CSV / PDF 読み込み（`data/`配下のサンプルで可）
- 検索UI（企業名・大分類・中分類・ニュース名）
- 3画面タブ：①マッチング実行 ②アイデア生成 ③ファイル作成
- Word出力（`python-docx`）

## ローカル実行
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Render デプロイ
1. 本リポジトリを GitHub（PrivateでOK）へ push
2. Render > New > Web Service > 対象リポジトリを選択
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
5. Environment Variables（任意で追加）:
   - `STREAMLIT_AUTH_PASSWORD=あなたのパスワード`
6. 必要に応じて `.streamlit/secrets.toml` の値を変更/削除

アクセス時にパスワード入力画面が表示されます。
