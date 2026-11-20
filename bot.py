import os
import sys
import logging
import asyncio
from collections import defaultdict
from aiohttp import web
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_KEYS_STR = os.getenv("GROQ_API_KEYS", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

GROQ_KEYS = [k.strip() for k in GROQ_KEYS_STR.split(",") if k.strip()]

if not TOKEN or TOKEN == "your_bot_token_here":
    print("❌ ERROR: DISCORD_TOKEN is missing or not set")
    sys.exit(1)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ==========================================
# SANIN KNOWLEDGE & SYSTEM PROMPT
# ==========================================
SANIN_SYSTEM_PROMPT = """You are San, the official AI assistant for the Sanin (Orochimaru) app community on Discord.
About Sanin:
- Tagline: "Discover. Watch. Track. — built for TV, works on phones and tablets."
- Platforms: Android Phones, Tablets, Android TV, and Amazon Fire TV (requires Android 5.0+ / API 21+).
- GitHub Repo: https://github.com/Shippun58/Orochimaru
- GitHub Releases: https://github.com/Shippun58/Orochimaru/releases
- Discord: https://discord.gg/QCc5xbgbsA
- Telegram: https://t.me/+91YmT3cUqv5iNDRk

Key Features & FAQs:
1. Extensions & Streaming:
   - Sanin is an open-source media player interface; it does NOT host or stream copyrighted content.
   - Streaming is enabled through third-party anime extensions.
   - To install extensions: Open Sanin -> Settings -> Extensions -> Add Repository -> Enter extension repo URL -> Install extensions.
   - If a video doesn't play or buffers: Try changing the stream server, updating the extension, or trying another source.
2. Android TV & Fire TV:
   - Dedicated remote-friendly TV interface with visible D-pad navigation focus states.
   - Fire TV Install: Install the 'Downloader' app from the Amazon Appstore, enter the GitHub release APK link, and install.
   - TV Remote controls: Left/Right to seek, OK/Center to play/pause, Down for subtitles/audio.
   - Note on Samsung & LG: Samsung runs Tizen OS, LG runs webOS. They CANNOT install Android APKs directly. Users must plug in a Firestick, Chromecast with Google TV, or Android TV box.
3. Tracking Accounts:
   - Integrates with AniList, MyAnimeList (MAL), and Simkl for watch progress synchronization.
   - Connect via Settings -> Accounts in the Sanin app.
4. Player:
   - Powered by Media3 ExoPlayer. Supports internal & online subtitles, speed adjustment, PiP (Picture-in-Picture), aspect ratio zoom/fit.

Tone & Guidelines:
- Friendly, helpful, concise, and enthusiastic.
- Use Discord markdown (bold, bullet points, code blocks) for readability.
- If unsure, provide the GitHub releases or recommend checking Settings in the app.
"""

APP_INFO = {
    "name": "Sanin (Orochimaru)",
    "tagline": "Discover. Watch. Track. — built for TV, works on phones and tablets.",
    "github_releases": "https://github.com/Shippun58/Orochimaru/releases",
    "github_repo": "https://github.com/Shippun58/Orochimaru",
}

# ==========================================
# CONVERSATION MEMORY (Per User/Channel)
# ==========================================
# Stores last 6 messages: {channel_id: [{"role": "user"|"assistant", "content": "..."}]}
conversation_history = defaultdict(list)
MAX_HISTORY = 6

def add_to_history(channel_id: int, role: str, content: str):
    history = conversation_history[channel_id]
    history.append({"role": role, "content": content})
    if len(history) > MAX_HISTORY:
        conversation_history[channel_id] = history[-MAX_HISTORY:]

# ==========================================
# AI ENGINE: MULTI-PROVIDER KEY ROTATION
# ==========================================
groq_key_index = 0

async def query_groq(api_key: str, model: str, messages: list) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 450
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=12)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"].strip()
            err_text = await resp.text()
            raise Exception(f"Groq error {resp.status}: {err_text[:120]}")

async def query_gemini(api_key: str, user_text: str) -> str:
    models = ["gemini-flash-latest", "gemini-2.5-flash-lite", "gemini-3.8-flash"]
    for m in models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
            payload = {
                "contents": [
                    {"parts": [{"text": f"{SANIN_SYSTEM_PROMPT}\n\nUser Question: {user_text}"}]}
                ],
                "generationConfig": {"maxOutputTokens": 450, "temperature": 0.7}
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=12)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            logging.warning(f"Gemini {m} failed: {e}")
    raise Exception("All Gemini models failed")

async def get_ai_response(channel_id: int, user_name: str, user_prompt: str) -> str:
    global groq_key_index

    # Build message thread for chat models
    formatted_messages = [{"role": "system", "content": SANIN_SYSTEM_PROMPT}]
    for msg in conversation_history[channel_id]:
        formatted_messages.append(msg)
    formatted_messages.append({"role": "user", "content": f"{user_name}: {user_prompt}"})

    # 1. Try Groq Keys (Round-Robin with failover)
    if GROQ_KEYS:
        for _ in range(len(GROQ_KEYS)):
            current_key = GROQ_KEYS[groq_key_index % len(GROQ_KEYS)]
            groq_key_index += 1
            for model in ["openai/gpt-oss-120b", "qwen/qwen3.8-27b"]:
                try:
                    reply = await query_groq(current_key, model, formatted_messages)
                    add_to_history(channel_id, "user", user_prompt)
                    add_to_history(channel_id, "assistant", reply)
                    return reply
                except Exception as e:
                    logging.warning(f"Groq key attempt failed with model {model}: {e}")

    # 2. Failover to Gemini
    if GEMINI_KEY:
        try:
            reply = await query_gemini(GEMINI_KEY, user_prompt)
            add_to_history(channel_id, "user", user_prompt)
            add_to_history(channel_id, "assistant", reply)
            return reply
        except Exception as e:
            logging.warning(f"Gemini failover failed: {e}")

    # 3. Built-in Offline Fallback
    lower = user_prompt.lower()
    if any(k in lower for k in ["download", "apk", "install"]):
        return f"📥 You can download the latest Sanin APK directly from [GitHub Releases]({APP_INFO['github_releases']})!"
    if any(k in lower for k in ["extension", "source", "repo", "stream"]):
        return "🧩 **Extensions in Sanin:**\nOpen Sanin -> **Settings** -> **Extensions** -> **Add Repository**.\nInstall your favorite extension to resolve streams!"
    if any(k in lower for k in ["samsung", "tizen", "lg"]):
        return "📺 **Samsung & LG TVs:** They cannot install Android APKs directly. Plug in a Firestick or Chromecast with Google TV to run Sanin!"

    return f"Hi {user_name}! I'm San, the assistant for **Sanin**. Type `/guide` to explore the app, or ask me anything!"

# ==========================================
# DISCORD UI COMPONENTS
# ==========================================
GUIDE_SECTIONS = {
    "download": {
        "title": "📥 Download & Installation Guide",
        "color": discord.Color.green(),
        "description": (
            "**Sanin** is available for Android Phones, Tablets, Android TV, and Fire TV devices.\n\n"
            "**Steps to Install:**\n"
            "1. Visit [GitHub Releases](https://github.com/Shippun58/Orochimaru/releases).\n"
            "2. Download the latest `.apk` file for your device.\n"
            "3. On phone/tablet: open the downloaded APK and tap **Install**.\n"
            "4. On Android TV / Fire TV: use the **Downloader** app or send the APK via **Send Files to TV**, then install.\n\n"
            "⚠️ *Note: Samsung TVs (Tizen OS) and LG TVs (webOS) cannot run Android APKs.*"
        ),
        "fields": [
            ("Supported Platforms", "• Android Phones & Tablets\n• Android TV / Google TV\n• Amazon Fire TV / Firestick", True),
            ("Minimum Android Version", "Android 5.0+ (API 21+)", True),
        ]
    },
    "extensions": {
        "title": "🧩 Extensions & Sources Guide",
        "color": discord.Color.purple(),
        "description": (
            "Sanin is an open-source media player and tracker. It **does not host or provide streams** itself.\n\n"
            "**How to Add Extensions:**\n"
            "1. Open **Sanin** and navigate to **Settings** → **Extensions**.\n"
            "2. Tap **Add Repository** and enter a compatible extension repository URL.\n"
            "3. Browse the list and install the extension(s) for your preferred sources.\n"
            "4. When you select a title, Sanin uses your installed extension to resolve video streams.\n\n"
            "💡 *If a stream fails or buffers, try changing the server or checking for extension updates.*"
        ),
        "fields": []
    },
    "tv": {
        "title": "📺 Android TV & Fire TV Navigation",
        "color": discord.Color.orange(),
        "description": (
            "Sanin has a dedicated interface designed for TV screens and remotes:\n\n"
            "• **D-pad Navigation:** All menus, shelves, and player controls are remote-friendly.\n"
            "• **Player Controls:** `Left / Right` to seek, `Center / OK` to play/pause, `Down` for audio/subtitles.\n"
            "• **Fire TV Installation:** Download the 'Downloader' app from the Amazon Appstore, enter the GitHub release link, and install."
        ),
        "fields": []
    },
    "tracking": {
        "title": "📊 Tracking & Account Integration",
        "color": discord.Color.blue(),
        "description": (
            "Sync your watching progress across services:\n\n"
            "• **AniList:** Sync anime watchlist, scores, and episode progress.\n"
            "• **MyAnimeList (MAL):** Connect your MAL profile for synchronized anime tracking.\n"
            "• **Simkl:** Sync anime, movies, and TV show watch history seamlessly.\n\n"
            "**To connect:** Go to **Settings** → **Accounts** in the Sanin app."
        ),
        "fields": []
    },
    "faq": {
        "title": "❓ Frequently Asked Questions (FAQ)",
        "color": discord.Color.teal(),
        "description": (
            "**Q: Why doesn't a video play?**\n"
            "A: Sanin doesn't host media. If a stream doesn't load, switch to another server or extension.\n\n"
            "**Q: Can I install Sanin on Samsung or LG TV?**\n"
            "A: No, Samsung uses Tizen and LG uses webOS. You can plug in a Firestick or Chromecast with Google TV.\n\n"
            "**Q: Where is the source code?**\n"
            "A: It's open-source on [GitHub](https://github.com/Shippun58/Orochimaru)."
        ),
        "fields": []
    }
}

def create_guide_embed(section_key="download"):
    data = GUIDE_SECTIONS.get(section_key, GUIDE_SECTIONS["download"])
    embed = discord.Embed(title=data["title"], description=data["description"], color=data["color"])
    for name, value, inline in data.get("fields", []):
        embed.add_field(name=name, value=value, inline=inline)
    embed.set_footer(text=f"{APP_INFO['name']} • Official Guide")
    return embed

class GuideSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Download & Install", value="download", description="How to install on Phone, TV, or Firestick", emoji="📥"),
            discord.SelectOption(label="Extensions & Sources", value="extensions", description="How to add repos and streaming extensions", emoji="🧩"),
            discord.SelectOption(label="Android TV & Fire TV", value="tv", description="Using Sanin on TV with remote control", emoji="📺"),
            discord.SelectOption(label="Tracking Accounts", value="tracking", description="Connect AniList, MyAnimeList, or Simkl", emoji="📊"),
            discord.SelectOption(label="FAQ & Troubleshooting", value="faq", description="Common questions and quick answers", emoji="❓"),
        ]
        super().__init__(placeholder="👉 Choose a topic to explore...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        embed = create_guide_embed(self.values[0])
        await interaction.response.edit_message(embed=embed, view=self.view)

class GuideView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(GuideSelect())
        self.add_item(discord.ui.Button(label="GitHub Releases", url=APP_INFO["github_releases"], emoji="📦", row=1))
        self.add_item(discord.ui.Button(label="Source Code", url=APP_INFO["github_repo"], emoji="💻", row=1))

# ==========================================
# DISCORD EVENTS
# ==========================================
@bot.event
async def on_ready():
    logging.info(f"✅ Bot is ONLINE as {bot.user.name} (ID: {bot.user.id})")
    for guild in bot.guilds:
        try:
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            logging.info(f"⚡ Synced {len(synced)} slash commands to guild: {guild.name}")
        except Exception as e:
            logging.error(f"Failed to sync to guild {guild.name}: {e}")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    is_mentioned = bot.user in message.mentions
    is_reply_to_bot = (message.reference and message.reference.resolved and 
                       isinstance(message.reference.resolved, discord.Message) and 
                       message.reference.resolved.author == bot.user)
    is_dm = isinstance(message.channel, discord.DMChannel)

    if is_mentioned or is_reply_to_bot or is_dm:
        clean = message.clean_content.replace(f"@{bot.user.name}", "").strip()
        if not clean:
            clean = "Hello!"

        async with message.channel.typing():
            reply_text = await get_ai_response(message.channel.id, message.author.display_name, clean)
            await message.reply(reply_text)
        return

    await bot.process_commands(message)

# ==========================================
# COMMANDS
# ==========================================
@bot.command(name="ping")
async def ping_cmd(ctx):
    await ctx.reply(f"🏓 Pong! Latency: `{round(bot.latency * 1000)}ms`")

@bot.command(name="guide")
async def guide_prefix_cmd(ctx):
    embed = create_guide_embed("download")
    await ctx.send(embed=embed, view=GuideView())

@bot.command(name="download")
async def download_prefix_cmd(ctx):
    embed = create_guide_embed("download")
    await ctx.send(embed=embed)

@bot.command(name="tv")
async def tv_prefix_cmd(ctx):
    embed = create_guide_embed("tv")
    await ctx.send(embed=embed)

@bot.command(name="faq")
async def faq_prefix_cmd(ctx):
    embed = create_guide_embed("faq")
    await ctx.send(embed=embed)

@bot.tree.command(name="ask", description="Ask San anything about Sanin or chat")
@app_commands.describe(question="Your question for San")
async def ask_slash(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    reply = await get_ai_response(interaction.channel_id, interaction.user.display_name, question)
    await interaction.followup.send(reply)

@bot.tree.command(name="guide", description="Interactive guide for Sanin (Orochimaru)")
async def guide_slash(interaction: discord.Interaction):
    embed = create_guide_embed("download")
    await interaction.response.send_message(embed=embed, view=GuideView())

@bot.tree.command(name="download", description="Get download links and install instructions")
async def download_slash(interaction: discord.Interaction):
    embed = create_guide_embed("download")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="tv", description="Guide for Android TV and Firestick")
async def tv_slash(interaction: discord.Interaction):
    embed = create_guide_embed("tv")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="faq", description="Frequently Asked Questions")
async def faq_slash(interaction: discord.Interaction):
    embed = create_guide_embed("faq")
    await interaction.response.send_message(embed=embed)

# ==========================================
# HEALTH-CHECK WEB SERVER
# ==========================================
async def start_health_server():
    app = web.Application()
    async def index(request):
        return web.Response(text="San Discord Bot (AI Powered) is running live!")
    app.router.add_get("/", index)
    app.router.add_get("/healthz", index)
    port = int(os.getenv("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"🌐 Health server running on port {port}")

async def main():
    await start_health_server()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
