import aiohttp
import json
import google.generativeai as genai
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()

class AIProcessor:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.setup_gemini()
    
    def setup_gemini(self):
        """Gemini APIの設定"""
        api_key = os.getenv('GEMINI_API_KEY') or self.config_manager.get('gemini_api_key')
        if api_key:
            genai.configure(api_key=api_key)
            self.gemini_model = genai.GenerativeModel('gemini-pro')
        else:
            self.gemini_model = None
    
    async def translate_text(self, text: str, target_language: str = "ja") -> Optional[str]:
        """テキストを翻訳"""
        model = self.config_manager.get('ai_model_settings', {}).get('translation_model', 'gemini')
        
        if model == 'gemini':
            return await self.translate_with_gemini(text, target_language)
        else:
            return await self.translate_with_lmstudio(text, target_language)
    
    async def summarize_text(self, text: str, max_length: int = 200) -> Optional[str]:
        """テキストを要約"""
        model = self.config_manager.get('ai_model_settings', {}).get('summary_model', 'gemini')
        
        if model == 'gemini':
            return await self.summarize_with_gemini(text, max_length)
        else:
            return await self.summarize_with_lmstudio(text, max_length)
    
    async def classify_genre(self, title: str, content: str) -> Optional[str]:
        """記事のジャンルを分類"""
        model = self.config_manager.get('ai_model_settings', {}).get('summary_model', 'gemini')
        
        if model == 'gemini':
            return await self.classify_with_gemini(title, content)
        else:
            return await self.classify_with_lmstudio(title, content)
    
    async def translate_with_gemini(self, text: str, target_language: str) -> Optional[str]:
        """Geminiで翻訳"""
        if not self.gemini_model:
            return None
        
        try:
            prompt = f"以下のテキストを自然な日本語に翻訳してください。元の意味を正確に保持し、読みやすい文章にしてください。:\n\n{text}"
            response = await self.gemini_model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            print(f"Gemini翻訳エラー: {e}")
            return None
    
    async def summarize_with_gemini(self, text: str, max_length: int) -> Optional[str]:
        """Geminiで要約"""
        if not self.gemini_model:
            return None
        
        try:
            prompt = f"以下のテキストを{max_length}文字以内で要約してください。重要なポイントを含めて、簡潔で分かりやすい要約を作成してください:\n\n{text}"
            response = await self.gemini_model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            print(f"Gemini要約エラー: {e}")
            return None
    
    async def classify_with_gemini(self, title: str, content: str) -> Optional[str]:
        """Geminiでジャンル分類"""
        if not self.gemini_model:
            return None
        
        try:
            prompt = f"""以下の記事のジャンルを分類してください。以下のカテゴリから最も適切なものを1つ選んで答えてください:
- テクノロジー
- ビジネス
- エンターテイメント
- スポーツ
- 政治
- 科学
- 健康
- その他

タイトル: {title}
内容: {content[:500]}...

ジャンル:"""
            response = await self.gemini_model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Geminiジャンル分類エラー: {e}")
            return "その他"
    
    async def translate_with_lmstudio(self, text: str, target_language: str) -> Optional[str]:
        """LM Studioで翻訳"""
        api_url = os.getenv('LMSTUDIO_API_URL') or self.config_manager.get('lmstudio_api_url')
        api_key = os.getenv('LMSTUDIO_API_KEY') or self.config_manager.get('lmstudio_api_key')
        
        if not api_url:
            return None
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        payload = {
            "model": "local-model",
            "messages": [
                {
                    "role": "system",
                    "content": "あなたは高精度な翻訳AIです。与えられたテキストを自然な日本語に翻訳してください。"
                },
                {
                    "role": "user",
                    "content": f"以下のテキストを日本語に翻訳してください:\n{text}"
                }
            ],
            "temperature": 0.3,
            "max_tokens": 2000
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, headers=headers, json=payload, timeout=30) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['choices'][0]['message']['content']
                    else:
                        print(f"LM Studio API エラー: {response.status}")
                        return None
        except Exception as e:
            print(f"LM Studio翻訳エラー: {e}")
            return None
    
    async def summarize_with_lmstudio(self, text: str, max_length: int) -> Optional[str]:
        """LM Studioで要約"""
        api_url = os.getenv('LMSTUDIO_API_URL') or self.config_manager.get('lmstudio_api_url')
        api_key = os.getenv('LMSTUDIO_API_KEY') or self.config_manager.get('lmstudio_api_key')
        
        if not api_url:
            return None
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        payload = {
            "model": "local-model",
            "messages": [
                {
                    "role": "system",
                    "content": f"あなたは優秀な要約AIです。与えられたテキストを{max_length}文字以内で要約してください。"
                },
                {
                    "role": "user",
                    "content": f"以下のテキストを要約してください:\n{text}"
                }
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, headers=headers, json=payload, timeout=30) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['choices'][0]['message']['content']
                    else:
                        print(f"LM Studio API エラー: {response.status}")
                        return None
        except Exception as e:
            print(f"LM Studio要約エラー: {e}")
            return None
    
    async def classify_with_lmstudio(self, title: str, content: str) -> Optional[str]:
        """LM Studioでジャンル分類"""
        api_url = os.getenv('LMSTUDIO_API_URL') or self.config_manager.get('lmstudio_api_url')
        api_key = os.getenv('LMSTUDIO_API_KEY') or self.config_manager.get('lmstudio_api_key')
        
        if not api_url:
            return "その他"
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        payload = {
            "model": "local-model",
            "messages": [
                {
                    "role": "system",
                    "content": """あなたは記事のジャンル分類AIです。以下のカテゴリから最も適切なものを1つ選んで答えてください:
テクノロジー、ビジネス、エンターテイメント、スポーツ、政治、科学、健康、その他"""
                },
                {
                    "role": "user",
                    "content": f"タイトル: {title}\n内容: {content[:500]}...\n\nこの記事のジャンルを分類してください。"
                }
            ],
            "temperature": 0.1,
            "max_tokens": 50
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, headers=headers, json=payload, timeout=30) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['choices'][0]['message']['content'].strip()
                    else:
                        return "その他"
        except Exception as e:
            print(f"LM Studioジャンル分類エラー: {e}")
            return "その他"
