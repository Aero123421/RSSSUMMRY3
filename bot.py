import discord
from discord.ext import commands
from discord import app_commands
import os
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv

from config_manager import ConfigManager
from rss_manager import RSSManager
from ai_processor import AIProcessor

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

class RSSBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            description='RSS記事を監視し、AI処理してDiscordに投稿するボット'
        )
        
        # マネージャー初期化
        self.config_manager = ConfigManager()
        self.rss_manager = RSSManager(self.config_manager)
        self.ai_processor = AIProcessor(self.config_manager)
        
        # チェックタスク
        self.feed_check_task = None
    
    async def setup_hook(self):
        """Bot起動時の設定"""
        logger.info("Bot setup starting...")
        
        # スラッシュコマンドを同期
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
        
        # フィードチェックタスクを開始
        self.start_feed_checking()
        
        logger.info("Bot setup completed")
    
    async def on_ready(self):
        """Bot準備完了時"""
        logger.info(f'{self.user} has logged in!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
    
    def start_feed_checking(self):
        """フィードチェックタスクを開始"""
        if self.feed_check_task and not self.feed_check_task.done():
            self.feed_check_task.cancel()
        
        self.feed_check_task = asyncio.create_task(self.feed_check_loop())
    
    async def feed_check_loop(self):
        """フィードチェックのメインループ"""
        while True:
            try:
                check_interval = self.config_manager.get('default_check_interval', 15)
                logger.info(f"フィードをチェック中... (間隔: {check_interval}分)")
                
                # 新しい記事をチェック
                new_articles_by_feed = await self.rss_manager.check_all_feeds()
                
                # 記事を処理して投稿
                for feed_id, articles in new_articles_by_feed.items():
                    await self.process_and_post_articles(feed_id, articles)
                
                # 次のチェックまで待機
                await asyncio.sleep(check_interval * 60)
                
            except asyncio.CancelledError:
                logger.info("フィードチェックタスクがキャンセルされました")
                break
            except Exception as e:
                logger.error(f"フィードチェックでエラー: {e}")
                await asyncio.sleep(60)  # エラー時は1分待機
    
    async def process_and_post_articles(self, feed_id: str, articles: list):
        """記事を処理してDiscordに投稿"""
        feeds = self.config_manager.get_feeds()
        feed_info = feeds.get(feed_id, {})
        channel_id = feed_info.get('channel_id')
        
        if not channel_id:
            logger.warning(f"フィード {feed_id} にチャンネルIDが設定されていません")
            return
        
        channel = self.get_channel(int(channel_id))
        if not channel:
            logger.warning(f"チャンネル {channel_id} が見つかりません")
            return
        
        for article in articles:
            try:
                await self.post_article_to_channel(channel, article, feed_info)
                await asyncio.sleep(2)  # レート制限対策
            except Exception as e:
                logger.error(f"記事投稿エラー: {e}")
    
    async def post_article_to_channel(self, channel, article: dict, feed_info: dict):
        """記事をチャンネルに投稿"""
        title = article['title']
        link = article['link']
        description = article['description']
        
        # AI処理
        translated_title = await self.ai_processor.translate_text(title)
        translated_description = await self.ai_processor.translate_text(description)
        summary = await self.ai_processor.summarize_text(
            f"{title}\n{description}", 
            self.config_manager.get('ai_model_settings', {}).get('summary_length', 200)
        )
        genre = await self.ai_processor.classify_genre(title, description)
        
        # Embed作成
        embed = discord.Embed(
            title=translated_title or title,
            url=link,
            description=summary or (translated_description or description)[:500],
            color=self.get_genre_color(genre),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="元タイトル", value=title, inline=False)
        embed.add_field(name="ジャンル", value=genre or "未分類", inline=True)
        embed.add_field(name="フィード", value=feed_info.get('name', article['feed_title']), inline=True)
        
        embed.set_footer(text=f"RSS Bot | {article['feed_title']}")
        
        # 投稿
        await channel.send(embed=embed)
        logger.info(f"記事を投稿しました: {translated_title or title}")
    
    def get_genre_color(self, genre: str) -> int:
        """ジャンルに応じた色を返す"""
        colors = {
            "テクノロジー": 0x00ff00,
            "ビジネス": 0x0080ff,
            "エンターテイメント": 0xff8000,
            "スポーツ": 0xff0080,
            "政治": 0x8000ff,
            "科学": 0x00ffff,
            "健康": 0x80ff00,
        }
        return colors.get(genre, 0x808080)  # デフォルトはグレー

# Cog: 設定コマンド
class ConfigCog(commands.Cog):
    def __init__(self, bot: RSSBot):
        self.bot = bot
    
    @app_commands.command(name="rss_config", description="RSS設定パネルを表示")
    async def rss_config(self, interaction: discord.Interaction):
        """設定パネルを表示"""
        if not self.is_admin(interaction.user.id):
            await interaction.response.send_message("管理者権限が必要です。", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📊 RSS Bot 設定パネル",
            description="設定を変更するには下のボタンを使用してください",
            color=0x0099ff
        )
        
        # 現在の設定を表示
        feeds_count = len(self.bot.config_manager.get_feeds())
        ai_settings = self.bot.config_manager.get('ai_model_settings', {})
        
        embed.add_field(name="登録フィード数", value=f"{feeds_count}個", inline=True)
        embed.add_field(name="チェック間隔", value=f"{self.bot.config_manager.get('default_check_interval', 15)}分", inline=True)
        embed.add_field(name="要約モデル", value=ai_settings.get('summary_model', 'gemini'), inline=True)
        
        view = ConfigView(self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    def is_admin(self, user_id: int) -> bool:
        """管理者権限チェック"""
        # ADMIN_ONLYが無効化されている場合は誰でもアクセス可能
        admin_only = os.getenv('ADMIN_ONLY', 'true').lower() == 'true'
        if not admin_only:
            return True
        
        admin_id = self.bot.config_manager.get('admin_user_id') or os.getenv('ADMIN_USER_ID')
        return str(user_id) == str(admin_id) if admin_id else True

# Cog: RSSコマンド
class RSSCog(commands.Cog):
    def __init__(self, bot: RSSBot):
        self.bot = bot
    
    @app_commands.command(name="addrss", description="RSSフィードを追加")
    @app_commands.describe(
        url="RSSフィードのURL",
        channel_name="投稿先チャンネル名（オプション）"
    )
    async def add_rss(self, interaction: discord.Interaction, url: str, channel_name: str = None):
        """RSSフィードを追加"""
        await interaction.response.defer()
        
        # URL検証
        test_result = await self.bot.rss_manager.test_feed_url(url)
        if not test_result['valid']:
            await interaction.followup.send(f"❌ フィードURLが無効です: {test_result['error']}")
            return
        
        # チャンネル作成または取得
        if channel_name:
            channel = await self.create_or_get_channel(interaction.guild, channel_name)
        else:
            # フィード名からチャンネル名を生成
            feed_title = test_result.get('title', 'rss-feed')
            channel_name = f"rss-{feed_title.lower().replace(' ', '-')}"
            channel = await self.create_or_get_channel(interaction.guild, channel_name)
        
        if not channel:
            await interaction.followup.send("❌ チャンネルの作成に失敗しました")
            return
        
        # フィード追加
        feed_id = f"feed_{len(self.bot.config_manager.get_feeds()) + 1}"
        feed_data = {
            'url': url,
            'name': test_result.get('title', 'Unknown Feed'),
            'channel_id': str(channel.id),
            'added_at': datetime.now().isoformat()
        }
        
        self.bot.config_manager.add_feed(feed_id, feed_data)
        
        embed = discord.Embed(
            title="✅ RSSフィードを追加しました",
            color=0x00ff00
        )
        embed.add_field(name="フィード名", value=feed_data['name'], inline=False)
        embed.add_field(name="URL", value=url, inline=False)
        embed.add_field(name="投稿チャンネル", value=channel.mention, inline=False)
        embed.add_field(name="記事数", value=f"{test_result.get('entries_count', 0)}記事", inline=True)
        
        await interaction.followup.send(embed=embed)
    
    async def create_or_get_channel(self, guild, channel_name: str):
        """チャンネルを作成または取得"""
        # 既存のチャンネルを検索
        for channel in guild.text_channels:
            if channel.name == channel_name:
                return channel
        
        # チャンネルを作成
        try:
            channel = await guild.create_text_channel(channel_name)
            return channel
        except Exception as e:
            logger.error(f"チャンネル作成エラー: {e}")
            return None
    
    @app_commands.command(name="rss_list_feeds", description="登録されているRSSフィードの一覧を表示")
    async def list_feeds(self, interaction: discord.Interaction):
        """フィード一覧を表示"""
        feeds = self.bot.config_manager.get_feeds()
        
        if not feeds:
            await interaction.response.send_message("登録されているRSSフィードはありません。", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📰 登録されているRSSフィード",
            color=0x0099ff
        )
        
        for feed_id, feed_data in feeds.items():
            channel_id = feed_data.get('channel_id')
            channel_mention = f"<#{channel_id}>" if channel_id else "未設定"
            
            embed.add_field(
                name=feed_data.get('name', 'Unknown Feed'),
                value=f"URL: {feed_data.get('url', 'N/A')}\nチャンネル: {channel_mention}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="rss_check_now", description="即座にRSSフィードをチェック")
    async def check_now(self, interaction: discord.Interaction):
        """即時フィードチェック"""
        await interaction.response.defer()
        
        try:
            new_articles_by_feed = await self.bot.rss_manager.check_all_feeds()
            
            total_articles = sum(len(articles) for articles in new_articles_by_feed.values())
            
            if total_articles == 0:
                await interaction.followup.send("新しい記事は見つかりませんでした。")
                return
            
            # 記事を処理して投稿
            for feed_id, articles in new_articles_by_feed.items():
                await self.bot.process_and_post_articles(feed_id, articles)
            
            await interaction.followup.send(f"✅ {total_articles}件の新しい記事を処理しました。")
            
        except Exception as e:
            logger.error(f"即時チェックエラー: {e}")
            await interaction.followup.send(f"❌ エラーが発生しました: {str(e)}")
    
    @app_commands.command(name="rss_status", description="RSSボットのステータスを表示")
    async def rss_status(self, interaction: discord.Interaction):
        """ボットステータス表示"""
        feeds = self.bot.config_manager.get_feeds()
        channels = self.bot.config_manager.get_channels()
        
        embed = discord.Embed(
            title="📊 RSS Bot ステータス",
            color=0x0099ff,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="登録フィード数", value=f"{len(feeds)}個", inline=True)
        embed.add_field(name="監視チャンネル数", value=f"{len(channels)}個", inline=True)
        embed.add_field(name="チェック間隔", value=f"{self.bot.config_manager.get('default_check_interval', 15)}分", inline=True)
        
        # AI設定
        ai_settings = self.bot.config_manager.get('ai_model_settings', {})
        embed.add_field(name="要約モデル", value=ai_settings.get('summary_model', 'gemini'), inline=True)
        embed.add_field(name="翻訳モデル", value=ai_settings.get('translation_model', 'gemini'), inline=True)
        embed.add_field(name="要約長", value=f"{ai_settings.get('summary_length', 200)}文字", inline=True)
        
        embed.set_footer(text="RSS Bot")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ビューとボタンの定義
class ConfigView(discord.ui.View):
    def __init__(self, bot: RSSBot):
        super().__init__(timeout=300)
        self.bot = bot
    
    @discord.ui.button(label="モデル設定", style=discord.ButtonStyle.primary, emoji="🤖")
    async def model_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ModelSettingsModal(self.bot)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="チェック間隔", style=discord.ButtonStyle.secondary, emoji="⏰")
    async def interval_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = IntervalSettingsModal(self.bot)
        await interaction.response.send_modal(modal)

class ModelSettingsModal(discord.ui.Modal, title="AIモデル設定"):
    def __init__(self, bot: RSSBot):
        super().__init__()
        self.bot = bot
        
        ai_settings = bot.config_manager.get('ai_model_settings', {})
        
        self.summary_model = discord.ui.TextInput(
            label="要約モデル (gemini/lmstudio)",
            default=ai_settings.get('summary_model', 'gemini'),
            max_length=20
        )
        self.translation_model = discord.ui.TextInput(
            label="翻訳モデル (gemini/lmstudio)",
            default=ai_settings.get('translation_model', 'gemini'),
            max_length=20
        )
        self.summary_length = discord.ui.TextInput(
            label="要約の最大文字数",
            default=str(ai_settings.get('summary_length', 200)),
            max_length=4
        )
        
        self.add_item(self.summary_model)
        self.add_item(self.translation_model)
        self.add_item(self.summary_length)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            summary_length = int(self.summary_length.value)
            
            ai_settings = {
                'summary_model': self.summary_model.value,
                'translation_model': self.translation_model.value,
                'summary_length': summary_length
            }
            
            self.bot.config_manager.set('ai_model_settings', ai_settings)
            
            await interaction.response.send_message("✅ AIモデル設定を更新しました。", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ 要約文字数は数値で入力してください。", ephemeral=True)

class IntervalSettingsModal(discord.ui.Modal, title="チェック間隔設定"):
    def __init__(self, bot: RSSBot):
        super().__init__()
        self.bot = bot
        
        current_interval = bot.config_manager.get('default_check_interval', 15)
        
        self.interval = discord.ui.TextInput(
            label="チェック間隔（分）",
            placeholder="5, 15, 30, 60のいずれかを入力",
            default=str(current_interval),
            max_length=2
        )
        
        self.add_item(self.interval)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            interval = int(self.interval.value)
            
            if interval not in [5, 15, 30, 60]:
                await interaction.response.send_message("❌ チェック間隔は5, 15, 30, 60分のいずれかを選択してください。", ephemeral=True)
                return
            
            self.bot.config_manager.set('default_check_interval', interval)
            
            # フィードチェックタスクを再起動
            self.bot.start_feed_checking()
            
            await interaction.response.send_message(f"✅ チェック間隔を{interval}分に変更しました。", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ チェック間隔は数値で入力してください。", ephemeral=True)

# Botの実行
async def main():
    bot = RSSBot()
    
    # Cogを追加
    await bot.add_cog(ConfigCog(bot))
    await bot.add_cog(RSSCog(bot))
    
    # Bot起動
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("DISCORD_TOKENが設定されていません")
        return
    
    try:
        await bot.start(token)
    except KeyboardInterrupt:
        logger.info("Bot shutting down...")
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
