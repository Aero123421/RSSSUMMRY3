import feedparser
import aiohttp
import asyncio
import hashlib
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

class RSSManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.processed_articles_file = "processed_articles.json"

        # ボリュームマウントの設定ミスなどでファイルパスがディレクトリに
        # なっている場合は、そのディレクトリ内にデータ用ファイルを作成する
        if os.path.isdir(self.processed_articles_file):
            self.processed_articles_file = os.path.join(
                self.processed_articles_file, "data.json"
            )

        self.processed_articles = self.load_processed_articles()
    
    def load_processed_articles(self) -> Dict[str, str]:
        """処理済み記事のハッシュを読み込む"""
        if os.path.isfile(self.processed_articles_file):
            try:
                with open(self.processed_articles_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                # ファイルが壊れている場合などは空の状態から始める
                return {}
        return {}
    
    def save_processed_articles(self):
        """処理済み記事のハッシュを保存"""
        directory = os.path.dirname(self.processed_articles_file)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.processed_articles_file, 'w', encoding='utf-8') as f:
            json.dump(self.processed_articles, f, indent=2, ensure_ascii=False)
    
    def generate_article_hash(self, title: str, link: str) -> str:
        """記事のハッシュを生成"""
        content = f"{title}|{link}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def is_article_processed(self, title: str, link: str) -> bool:
        """記事が処理済みかチェック"""
        article_hash = self.generate_article_hash(title, link)
        return article_hash in self.processed_articles
    
    def mark_article_processed(self, title: str, link: str):
        """記事を処理済みとしてマーク"""
        article_hash = self.generate_article_hash(title, link)
        self.processed_articles[article_hash] = datetime.now().isoformat()
        self.save_processed_articles()
    
    async def fetch_feed(self, feed_url: str) -> Optional[feedparser.FeedParserDict]:
        """RSSフィードを取得"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(feed_url, timeout=30) as response:
                    if response.status == 200:
                        content = await response.text()
                        return feedparser.parse(content)
                    else:
                        print(f"フィード取得エラー ({feed_url}): HTTP {response.status}")
                        return None
        except Exception as e:
            print(f"フィード取得エラー ({feed_url}): {e}")
            return None
    
    async def get_new_articles(self, feed_url: str, max_articles: int = 10) -> List[Dict[str, Any]]:
        """新しい記事を取得"""
        feed = await self.fetch_feed(feed_url)
        if not feed:
            return []
        
        new_articles = []
        
        for entry in feed.entries[:max_articles]:
            title = entry.get('title', 'No Title')
            link = entry.get('link', '')
            description = entry.get('description', entry.get('summary', ''))
            published = entry.get('published', entry.get('updated', ''))
            
            # 処理済みチェック
            if not self.is_article_processed(title, link):
                article = {
                    'title': title,
                    'link': link,
                    'description': description,
                    'published': published,
                    'feed_title': feed.feed.get('title', 'Unknown Feed'),
                    'feed_url': feed_url
                }
                new_articles.append(article)
                self.mark_article_processed(title, link)
        
        return new_articles
    
    async def check_all_feeds(self) -> Dict[str, List[Dict[str, Any]]]:
        """全てのフィードをチェック"""
        feeds = self.config_manager.get_feeds()
        results = {}
        
        tasks = []
        for feed_id, feed_data in feeds.items():
            feed_url = feed_data.get('url')
            if feed_url:
                task = self.get_new_articles(feed_url)
                tasks.append((feed_id, task))
        
        # 並行実行
        for feed_id, task in tasks:
            try:
                articles = await task
                if articles:
                    results[feed_id] = articles
            except Exception as e:
                print(f"フィード {feed_id} のチェックでエラー: {e}")
        
        return results
    
    def validate_feed_url(self, url: str) -> Dict[str, Any]:
        """フィードURLを検証"""
        try:
            parsed_url = urlparse(url)
            if not parsed_url.netloc:
                return {"valid": False, "error": "無効なURLです"}
            
            if parsed_url.scheme not in ['http', 'https']:
                return {"valid": False, "error": "HTTPまたはHTTPSのURLを使用してください"}
            
            return {"valid": True, "error": None}
        
        except Exception as e:
            return {"valid": False, "error": f"URL検証エラー: {str(e)}"}
    
    async def test_feed_url(self, url: str) -> Dict[str, Any]:
        """フィードURLをテスト"""
        validation = self.validate_feed_url(url)
        if not validation["valid"]:
            return validation
        
        try:
            feed = await self.fetch_feed(url)
            if not feed:
                return {"valid": False, "error": "フィードを取得できませんでした"}
            
            if not hasattr(feed, 'entries') or len(feed.entries) == 0:
                return {"valid": False, "error": "有効な記事が見つかりませんでした"}
            
            feed_info = {
                "valid": True,
                "title": feed.feed.get('title', 'Unknown Feed'),
                "description": feed.feed.get('description', ''),
                "entries_count": len(feed.entries),
                "latest_entry": feed.entries[0].get('title', '') if feed.entries else ''
            }
            
            return feed_info
        
        except Exception as e:
            return {"valid": False, "error": f"フィードテストエラー: {str(e)}"}
    
    def cleanup_old_processed_articles(self, days: int = 30):
        """古い処理済み記事データをクリーンアップ"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        cleaned_articles = {}
        for article_hash, processed_date_str in self.processed_articles.items():
            try:
                processed_date = datetime.fromisoformat(processed_date_str)
                if processed_date > cutoff_date:
                    cleaned_articles[article_hash] = processed_date_str
            except:
                # 無効な日付形式の場合は削除
                continue
        
        self.processed_articles = cleaned_articles
        self.save_processed_articles()
        
        removed_count = len(self.processed_articles) - len(cleaned_articles)
        return removed_count
