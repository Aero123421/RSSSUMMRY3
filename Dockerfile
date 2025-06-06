FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムの依存関係をインストール
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係をコピーしてインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションファイルをコピー
COPY . .

# ログディレクトリを作成
RUN mkdir -p logs

# LM Studioへの接続のためにホストネットワークを使用できるよう設定
ENV LM_STUDIO_BASE_URL=http://host.docker.internal:1234/v1

# 管理者制限を無効化（誰でもアクセス可能）
ENV ADMIN_ONLY=false

# ボットを実行
CMD ["python", "bot.py"]
