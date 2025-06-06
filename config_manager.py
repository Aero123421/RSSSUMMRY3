import json
import os
from typing import Dict, Any, Optional

class ConfigManager:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込む"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return self.get_default_config()
    
    def save_config(self):
        """設定ファイルを保存"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定を返す"""
        return {
            "discord_token": "",
            "gemini_api_key": "",
            "lmstudio_api_url": "http://localhost:1234/v1/chat/completions",
            "lmstudio_api_key": "lm-studio",
            "admin_user_id": "",
            "default_check_interval": 15,
            "feeds": {},
            "channels": {},
            "ai_model_settings": {
                "translation_model": "gemini",
                "summary_model": "gemini",
                "summary_length": 200
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """設定値を取得"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """設定値を設定"""
        self.config[key] = value
        self.save_config()
    
    def add_feed(self, feed_id: str, feed_data: Dict[str, Any]):
        """RSSフィードを追加"""
        if "feeds" not in self.config:
            self.config["feeds"] = {}
        self.config["feeds"][feed_id] = feed_data
        self.save_config()
    
    def remove_feed(self, feed_id: str):
        """RSSフィードを削除"""
        if "feeds" in self.config and feed_id in self.config["feeds"]:
            del self.config["feeds"][feed_id]
            self.save_config()
    
    def get_feeds(self) -> Dict[str, Any]:
        """全てのRSSフィードを取得"""
        return self.config.get("feeds", {})
    
    def add_channel(self, channel_id: str, channel_data: Dict[str, Any]):
        """チャンネルを追加"""
        if "channels" not in self.config:
            self.config["channels"] = {}
        self.config["channels"][channel_id] = channel_data
        self.save_config()
    
    def get_channels(self) -> Dict[str, Any]:
        """全てのチャンネルを取得"""
        return self.config.get("channels", {})
