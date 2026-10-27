# -*- coding: utf-8 -*-
"""
Discord Badge Collection & User Stats Bot (Button UI Panel)
Check your server stats with "My Stats" and badges with "View Badge Collection"!
"""

import discord
from discord.ext import commands
import sqlite3
from datetime import datetime, timezone

# Developer Portalで取得したBotトークンをここに貼り付けてください
TOKEN = "MTU2NDcwNDM1MjUzMzIxNzI5MA.G2ahqp.187WYPhMSxZXx_kGaWhjPKKW1ZXdD5Un5ZtPmA"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- バッジ獲得条件の定義 ---
BADGES_DATA = [
    {
        "id": "1",
        "icon": "💬",
        "title": "First Step",
        "desc": "Send your first message in the server",
        "reqType": "messages",
        "reqValue": 1
    },
    {
        "id": "2",
        "icon": "🗣️",
        "title": "Chatterbox",
        "desc": "Send a total of 50 messages",
        "reqType": "messages",
        "reqValue": 50
    },
    {
        "id": "3",
        "icon": "🎙️",
        "title": "Voice Regular",
        "desc": "Spend a total of 30 minutes in Voice Channels",
        "reqType": "vc_time",
        "reqValue": 30
    },
    {
        "id": "4",
        "icon": "🎉",
        "title": "Veteran Member",
        "desc": "Be a member of the server for at least 30 days",
        "reqType": "server_days",
        "reqValue": 30
    }
]

# --- SQLite データベース初期化 ---
def init_db():
    conn = sqlite3.connect("badges.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_stats (
            user_id INTEGER PRIMARY KEY,
            message_count INTEGER DEFAULT 0,
            vc_minutes INTEGER DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS unlocked_badges (
            user_id INTEGER,
            badge_id TEXT,
            unlocked_at TEXT,
            PRIMARY KEY (user_id, badge_id)
        )
    """)
    
    conn.commit()
    conn.close()

init_db()

# --- ユーザー統計データの取得・更新関数 ---
def get_user_stats(user_id):
    conn = sqlite3.connect("badges.db")
    cursor = conn.cursor()
    cursor.execute("SELECT message_count, vc_minutes FROM user_stats WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"messages": row[0], "vc_minutes": row[1]}
    return {"messages": 0, "vc_minutes": 0}

def update_user_stats(user_id, msg_add=0, vc_add=0):
    conn = sqlite3.connect("badges.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_stats (user_id, message_count, vc_minutes) 
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET 
            message_count = message_count + ?,
            vc_minutes = vc_minutes + ?
    """, (user_id, msg_add, vc_add, msg_add, vc_add))
    conn.commit()
    conn.close()

def get_server_days(member: discord.Member) -> int:
    if not member.joined_at:
        return 0
    now = datetime.now(timezone.utc)
    delta = now - member.joined_at
    return max(0, delta.days)

def get_unlocked_badges(user_id):
    conn = sqlite3.connect("badges.db")
    cursor = conn.cursor()
    cursor.execute("SELECT badge_id FROM unlocked_badges WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

# --- ボタンUIクラス (My Stats & View Badge Collection) ---
class BadgeButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="My Stats", style=discord.ButtonStyle.secondary, emoji="📊", custom_id="btn_my_stats")
    async def my_stats_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        target = interaction.user
        stats = get_user_stats(target.id)
        server_days = get_server_days(target)
        unlocked_list = get_unlocked_badges(target.id)
        
        unlocked_count = len(unlocked_list)
        total_badges = len(BADGES_DATA)
        progress_pct = int((unlocked_count / total_badges) * 100) if total_badges > 0 else 0

        vc_mins = stats['vc_minutes']
        vc_hours = round(vc_mins / 60, 1)

        if target.joined_at:
            now = datetime.now(timezone.utc)
            delta = now - target.joined_at
            total_hours = int(delta.total_seconds() // 3600)
            days = delta.days
            hours = (total_hours % 24)
            playtime_str = f"**{days}d {hours}h** ({total_hours:,} hrs total)"
        else:
            playtime_str = "Unknown"

        embed = discord.Embed(
            title=f"📊 {target.display_name}'s Server Statistics",
            color=0x5865F2,
            description=f"Detailed activity and progress in **{target.guild.name}**."
        )
        embed.add_field(name="🎮 Server Play Time", value=playtime_str, inline=True)
        embed.add_field(name="🎙️ VC Play Time", value=f"**{vc_mins:,}** mins (*~{vc_hours} hrs*)", inline=True)
        embed.add_field(name="💬 Messages Sent", value=f"**{stats['messages']:,}** messages", inline=True)
        embed.add_field(name="🏆 Badges Unlocked", value=f"**{unlocked_count} / {total_badges}** ({progress_pct}%)", inline=True)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(text=f"User ID: {target.id}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="View Badge Collection", style=discord.ButtonStyle.primary, emoji="🏆", custom_id="btn_view_badges")
    async def view_badges_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        target = interaction.user
        stats = get_user_stats(target.id)
        server_days = get_server_days(target)
        unlocked_list = get_unlocked_badges(target.id)

        embed = discord.Embed(
            title=f"🏅 {target.display_name}'s Badge Collection",
            color=0xF0B232,
            description="Here are your badges and unlock progress:"
        )

        for badge in BADGES_DATA:
            is_unlocked = badge['id'] in unlocked_list
            status_icon = "✅" if is_unlocked else "🔒"
            status_text = "Unlocked" if is_unlocked else "Locked"
            
            field_value = f"{badge['desc']}\nStatus: **{status_text}**"
            embed.add_field(name=f"{status_icon} {badge['icon']} {badge['title']}", value=field_value, inline=False)

        embed.set_thumbnail(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

# --- イベントとコマンド ---
@bot.event
async def on_ready():
    bot.add_view(BadgeButtonView())
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # メッセージ送信数を加算
    update_user_stats(message.author.id, msg_add=1)
    await bot.process_commands(message)

@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup_panel(ctx):
    """管理者用コマンド: チャンネルにバッジ案内パネルを送信します"""
    embed = discord.Embed(
        title="🏅 Badge Collection Panel",
        description="This is the badge bot.\nClick the buttons below to check your stats or view your earned badges and progress!",
        color=0x5865F2
    )
    embed.set_footer(text="Badge Collector Bot • Play time & participation rewards")
    
    view = BadgeButtonView()
    await ctx.send(embed=embed, view=view)
    try:
        await ctx.message.delete()
    except:
        pass

# ボットの起動
try:
    bot.run("ここにあなたのBOTトークン")
except Exception as e:
    print("【接続エラー】", e)
    input("Enterキーを押すと終了します...")