# 使用するベースイメージを指定します
FROM python:3.11-slim

# 作業ディレクトリを設定します
WORKDIR /app

# 必要なファイルをコンテナにコピーします
COPY main.py requirements.txt ./
COPY credentials.json /app/credentials.json

# 依存関係をインストールします
RUN pip install --no-cache-dir -r requirements.txt

# コンテナ起動時に実行されるコマンドを設定します
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "main:app"]
