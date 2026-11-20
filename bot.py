import os
import sys
import re
import json
import logging
import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import quote
from html import unescape
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
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")

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
OFFICIAL_REPO = "https://github.com/Nashon-ops/Sanin"
RELEASES_URL = f"{OFFICIAL_REPO}/releases"

SANIN_SYSTEM_PROMPT = """You are San, the community AI for Sanin.

Identity and links
- Sanin is an open-source media player and tracker for Android phones, tablets, Android TV, and Fire TV.
- The only official source code link is https://github.com/Nashon-ops/Sanin
- The only official download link is https://github.com/Nashon-ops/Sanin/releases
- Never invent URLs. Never mention or link another repository, codename, private or anonymous project, invite, or channel. If you do not have an official link for something, say so plainly.

Personality
- You are a chill, sharp anime and TV nerd who talks like a knowledgeable friend.
- Friendly, concise, and a little witty. Have real opinions when asked, but call them opinions.
- Help people settle debates with facts, compare titles, and explain release info using verified data.

Formatting
- Plain Discord markdown only. Short paragraphs or up to four short bullets.
- No ASCII art, divider lines, rows of dashes, pipes or arrows, tables, or banners.
- At most one emoji per reply. Stay under 500 words.

Accuracy
- Use only the "Verified data" block for current facts, dates, scores, and links.
- If that block has nothing relevant, say you do not have reliable data and suggest /release, /showdown, or /search.
- Never guess a release date and never make up a source.
"""

APP_INFO = {
    "name": "Sanin",
    "tagline": "Discover. Watch. Track. — built for TV, works on phones and tablets.",
    "github_releases": RELEASES_URL,
    "github_repo": OFFICIAL_REPO,
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

ANILIST_QUERY = """query ($q: String) {
  Page(perPage: 3) {
    media(search: $q, type: ANIME) {
      title { romaji english }
      averageScore popularity episodes status format siteUrl
      nextAiringEpisode { airingAt episode }
      genres
    }
  }
}"""

STATUS_LABELS = {
    "FINISHED": "Finished",
    "RELEASING": "Airing",
    "NOT_YET_RELEASED": "Upcoming",
    "CANCELLED": "Cancelled",
    "HIATUS": "On hiatus",
}

def clean_reply(text: str) -> str:
    lines = []
    for line in text.replace("\r", "").split("\n"):
        compact = re.sub(r"\s+", "", line)
        if re.fullmatch(r"[-=~*_|>\u2500-\u257f]{4,}", compact):
            continue
        lines.append(line.rstrip())
    text = "\n".join(lines)
    text = re.sub(r"\|-{3,}>?", "", text)
    text = re.sub(r"(?:[-=~*_]\s*){5,}", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:1900]

def canonical_reply(prompt: str) -> str | None:
    lower = prompt.lower()
    asks_link = any(k in lower for k in ("repo", "repository", "source code", "github", "download", "apk", "link", "official"))
    about_bot = any(k in lower for k in ("sanin", "app", "bot"))
    if asks_link and about_bot:
        return f"Official repo: {OFFICIAL_REPO}\nLatest releases: {RELEASES_URL}"
    return None

def format_date(value) -> str:
    if not value:
        return "not announced"
    text = str(value)
    if text.isdigit():
        return datetime.fromtimestamp(int(text), tz=timezone.utc).strftime("%b %d, %Y")
    return text[:10]

def extract_title(prompt: str) -> str:
    text = re.sub(r"^(hey|hi|hello|san)\b[,\s]+", "", prompt.strip(), flags=re.I)
    text = re.sub(r"[?].*$", "", text)
    leading = r"^(what|when|who|how|is|are|does|do|can|could|would|should|tell me about|info on|information on|estimate|release date of|created|made by|the|a|an|of)\b[\s:]*"
    while True:
        updated = re.sub(leading, "", text, flags=re.I)
        if updated == text:
            break
        text = updated
    text = re.sub(r"\b(release date|air date|next episode|estimated|estimate|release|anime|show|movie|series)\b", " ", text, flags=re.I)
    return " ".join(text.split())[:60]

async def fetch_json(url: str, params: dict | None = None, headers: dict | None = None, timeout: int = 8) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            if resp.status != 200:
                raise Exception(f"HTTP {resp.status}")
            return await resp.json(content_type=None)

async def anilist_search(title: str) -> list:
    payload = {"query": ANILIST_QUERY, "variables": {"q": title}}
    async with aiohttp.ClientSession() as session:
        async with session.post("https://graphql.anilist.co", json=payload, headers={"User-Agent": "SanBot/1.0"}, timeout=aiohttp.ClientTimeout(total=8)) as resp:
            if resp.status != 200:
                raise Exception(f"AniList HTTP {resp.status}")
            data = await resp.json(content_type=None)
    return (data.get("data") or {}).get("Page", {}).get("media") or []

async def tmdb_search(title: str, kind: str = "tv") -> list:
    if not TMDB_API_KEY:
        return []
    data = await fetch_json(
        f"https://api.themoviedb.org/3/search/{kind}",
        params={"api_key": TMDB_API_KEY, "query": title},
        headers={"User-Agent": "SanBot/1.0"},
    )
    results = (data.get("results") or [])[:3]
    for item in results:
        item["_kind"] = kind
    return results

async def tmdb_details(item: dict) -> dict:
    kind = item.get("_kind", "tv")
    data = await fetch_json(
        f"https://api.themoviedb.org/3/{kind}/{item['id']}",
        params={"api_key": TMDB_API_KEY},
        headers={"User-Agent": "SanBot/1.0"},
    )
    data["_kind"] = kind
    return data

async def wiki_search(query: str) -> list:
    data = await fetch_json(
        "https://en.wikipedia.org/w/api.php",
        params={"action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": 3},
        headers={"User-Agent": "SanBot/1.0"},
    )
    results = []
    for item in (data.get("query") or {}).get("search", []):
        title = item.get("title", "")
        snippet = unescape(re.sub(r"<[^>]+>", "", item.get("snippet", "")))
        results.append({"title": title, "snippet": snippet[:220], "url": "https://en.wikipedia.org/wiki/" + quote(title.replace(" ", "_"))})
    return results

def compact_anilist(items: list) -> list:
    out = []
    for item in items[:3]:
        title = item.get("title") or {}
        nxt = item.get("nextAiringEpisode") or {}
        out.append({
            "title": title.get("english") or title.get("romaji"),
            "score": item.get("averageScore"),
            "popularity": item.get("popularity"),
            "episodes": item.get("episodes"),
            "status": item.get("status"),
            "next_episode": nxt.get("episode"),
            "next_airing": nxt.get("airingAt"),
            "url": item.get("siteUrl"),
        })
    return out

def compact_tmdb(items: list) -> list:
    out = []
    for item in items[:3]:
        kind = item.get("_kind", "tv")
        out.append({
            "title": item.get("name") or item.get("title"),
            "score": item.get("vote_average"),
            "votes": item.get("vote_count"),
            "year": (item.get("first_air_date") or item.get("release_date") or "")[:4],
            "kind": kind,
            "url": f"https://www.themoviedb.org/{kind}/{item.get('id')}",
        })
    return out

async def gather_context(prompt: str) -> str:
    lower = prompt.lower()
    parts = [f"Official Sanin repository: {OFFICIAL_REPO}", f"Official downloads: {RELEASES_URL}"]
    title = extract_title(prompt)
    if len(title) < 3:
        return "\n".join(parts)
    jobs = []
    if any(k in lower for k in ("anime", "show", "movie", "series", "release", "air", "episode", "score", "vs", "compare", "better", "season", "when")):
        jobs.append(("anilist", anilist_search(title)))
        if TMDB_API_KEY:
            jobs.append(("tmdb", tmdb_search(title)))
    if any(k in lower for k in ("what", "who", "when", "where", "why", "how", "latest", "news", "current", "update", "search")):
        jobs.append(("wiki", wiki_search(title)))
    if not jobs:
        return "\n".join(parts)
    results = await asyncio.gather(*(job[1] for job in jobs), return_exceptions=True)
    for (name, _), result in zip(jobs, results):
        if isinstance(result, Exception):
            logging.warning(f"{name} lookup failed: {result}")
            continue
        if name == "anilist" and result:
            parts.append("AniList: " + json.dumps(compact_anilist(result), ensure_ascii=False))
        elif name == "tmdb" and result:
            parts.append("TMDB: " + json.dumps(compact_tmdb(result), ensure_ascii=False))
        elif name == "wiki" and result:
            parts.append("Wikipedia: " + json.dumps(result, ensure_ascii=False))
    return "\n".join(parts)

async def query_gemini(api_key: str, messages: list) -> str:
    prompt_text = "\n\n".join(f"{msg['role']}: {msg['content']}" for msg in messages)
    models = ["gemini-flash-latest", "gemini-2.5-flash-lite", "gemini-3.8-flash"]
    for m in models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt_text}]}],
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

async def get_ai_response(channel_id: int, user_name: str, user_prompt: str, context: str | None = None) -> str:
    global groq_key_index

    canned = canonical_reply(user_prompt)
    if canned:
        add_to_history(channel_id, "user", user_prompt)
        add_to_history(channel_id, "assistant", canned)
        return canned

    verified = context if context is not None else await gather_context(user_prompt)
    system_prompt = SANIN_SYSTEM_PROMPT + "\n\nVerified data (use only this for current facts):\n" + verified
    formatted_messages = [{"role": "system", "content": system_prompt}]
    for msg in conversation_history[channel_id]:
        formatted_messages.append(msg)
    formatted_messages.append({"role": "user", "content": f"{user_name}: {user_prompt}"})

    async def finish(reply: str) -> str:
        reply = clean_reply(reply)
        add_to_history(channel_id, "user", user_prompt)
        add_to_history(channel_id, "assistant", reply)
        return reply

    if GROQ_KEYS:
        for _ in range(len(GROQ_KEYS)):
            current_key = GROQ_KEYS[groq_key_index % len(GROQ_KEYS)]
            groq_key_index += 1
            for model in ["openai/gpt-oss-120b", "qwen/qwen3.8-27b"]:
                try:
                    return await finish(await query_groq(current_key, model, formatted_messages))
                except Exception as e:
                    logging.warning(f"Groq key attempt failed with model {model}: {e}")

    if GEMINI_KEY:
        try:
            return await finish(await query_gemini(GEMINI_KEY, formatted_messages))
        except Exception as e:
            logging.warning(f"Gemini failover failed: {e}")

    lower = user_prompt.lower()
    if any(k in lower for k in ["download", "apk", "install"]):
        reply = f"Latest Sanin APK: {RELEASES_URL}"
    elif any(k in lower for k in ["extension", "source", "repo", "stream"]):
        reply = "Extensions: Sanin -> Settings -> Extensions -> Add Repository -> paste a repo URL, then install what you need."
    elif any(k in lower for k in ["samsung", "tizen", "lg"]):
        reply = "Samsung and LG TVs can't install Android APKs directly. Use a Firestick, Chromecast with Google TV, or an Android TV box."
    else:
        reply = f"Hey {user_name}, I'm San. I can help with Sanin, release estimates, title comparisons, and web lookups. Try /guide, /release, /showdown, or /search."
    add_to_history(channel_id, "user", user_prompt)
    add_to_history(channel_id, "assistant", reply)
    return reply

def build_about_embed() -> discord.Embed:
    description = (
        "I'm San, the Sanin community AI. I'm a chill anime and TV nerd who keeps things short, "
        "helps settle debates with real data, and never guesses a release date or invents a link.\n\n"
        "Official repo: " + OFFICIAL_REPO
    )
    embed = discord.Embed(title="About San", description=description, color=discord.Color.blurple())
    embed.add_field(name="Commands", value="/guide, /download, /tv, /faq, /ask, /release, /showdown, /search, /about", inline=False)
    embed.add_field(name="How to talk to me", value="Mention me, reply to one of my messages, or DM me.", inline=False)
    return embed

async def build_release_embed(title: str) -> discord.Embed:
    anime_task = anilist_search(title)
    tmdb_task = tmdb_search(title) if TMDB_API_KEY else asyncio.sleep(0, result=[])
    anime, tv = await asyncio.gather(anime_task, tmdb_task, return_exceptions=True)
    lines = []
    if not isinstance(anime, Exception) and anime:
        for item in anime[:2]:
            names = item.get("title") or {}
            name = names.get("english") or names.get("romaji") or "Unknown"
            nxt = item.get("nextAiringEpisode") or {}
            status = STATUS_LABELS.get(item.get("status"), item.get("status", "Unknown"))
            eta = f"Episode {nxt.get('episode')} expected {format_date(nxt.get('airingAt'))}" if nxt.get("airingAt") else f"Status: {status}"
            score = f"{item.get('averageScore')}%" if item.get("averageScore") is not None else "n/a"
            lines.append(f"**{name}** via AniList\n{eta}\nScore {score} | {item.get('episodes') or '?'} episodes | {item.get('siteUrl')}")
    if not isinstance(tv, Exception) and tv:
        details = []
        for item in tv[:2]:
            try:
                details.append(await tmdb_details(item))
            except Exception as e:
                logging.warning(f"TMDB details failed: {e}")
        for item in details:
            name = item.get("name") or item.get("title") or "Unknown"
            nxt = item.get("next_episode_to_air") or {}
            if nxt.get("air_date"):
                eta = f"Next episode expected {format_date(nxt['air_date'])}"
            elif item.get("release_date"):
                eta = f"Released {format_date(item['release_date'])}"
            else:
                eta = f"Status: {item.get('status', 'Unknown')}"
            kind = item.get("_kind", "tv")
            url = f"https://www.themoviedb.org/{kind}/{item.get('id')}"
            score = f"{item.get('vote_average')}/10" if item.get("vote_average") is not None else "n/a"
            lines.append(f"**{name}** via TMDB\n{eta}\nScore {score} | {item.get('status', 'Unknown')} | {url}")
    description = "\n\n".join(lines) if lines else "No reliable match found. Try a more specific title."
    return discord.Embed(title=f"Release estimate: {title}", description=description, color=discord.Color.blurple())

async def fetch_side(title: str) -> dict:
    anime_task = anilist_search(title)
    tmdb_task = tmdb_search(title) if TMDB_API_KEY else asyncio.sleep(0, result=[])
    anime, tv = await asyncio.gather(anime_task, tmdb_task, return_exceptions=True)
    side = {"title": title, "anime": None, "tmdb": None}
    if not isinstance(anime, Exception) and anime:
        side["anime"] = anime[0]
    if not isinstance(tv, Exception) and tv:
        try:
            side["tmdb"] = await tmdb_details(tv[0])
        except Exception as e:
            logging.warning(f"TMDB details failed: {e}")
            side["tmdb"] = tv[0]
    return side

def side_summary(side: dict) -> dict:
    item = side.get("anime")
    if item:
        names = item.get("title") or {}
        return {
            "name": names.get("english") or names.get("romaji") or side["title"],
            "score": f"{item['averageScore']}%" if item.get("averageScore") is not None else "n/a",
            "popularity": f"{item['popularity']:,}" if item.get("popularity") else "n/a",
            "episodes": item.get("episodes") or "?",
            "status": STATUS_LABELS.get(item.get("status"), "Unknown"),
            "url": item.get("siteUrl"),
            "source": "AniList",
        }
    item = side.get("tmdb")
    if item:
        kind = item.get("_kind", "tv")
        return {
            "name": item.get("name") or item.get("title") or side["title"],
            "score": f"{item['vote_average']}/10" if item.get("vote_average") is not None else "n/a",
            "popularity": f"{item['popularity']:,}" if item.get("popularity") else "n/a",
            "episodes": item.get("number_of_episodes") or "?",
            "status": item.get("status", "Unknown"),
            "url": f"https://www.themoviedb.org/{kind}/{item.get('id')}",
            "source": "TMDB",
        }
    return {"name": side["title"], "score": "n/a", "popularity": "n/a", "episodes": "?", "status": "Unknown", "url": "", "source": "none"}

def summary_line(label: str, data: dict) -> str:
    return f"**{label}** {data['name']} ({data['source']})\nScore {data['score']} | Popularity {data['popularity']} | {data['episodes']} episodes | {data['status']}\n{data['url']}"

async def build_showdown_embed(first: str, second: str, channel_id: int) -> discord.Embed:
    left, right = await asyncio.gather(fetch_side(first), fetch_side(second))
    a = side_summary(left)
    b = side_summary(right)
    description = summary_line(first, a) + "\n\n" + summary_line(second, b)
    context = "Verified data: " + json.dumps({"first": a, "second": b}, ensure_ascii=False)
    try:
        verdict = await get_ai_response(
            channel_id,
            "San",
            f"Give a short friendly verdict comparing {a['name']} and {b['name']} using only the verified data. Under 80 words.",
            context=context,
        )
        description += "\n\n" + verdict
    except Exception as e:
        logging.warning(f"Showdown verdict failed: {e}")
    return discord.Embed(title=f"Showdown: {first} vs {second}", description=description, color=discord.Color.gold())

async def build_search_embed(query: str) -> discord.Embed:
    lines = []
    try:
        results = await wiki_search(query)
    except Exception as e:
        logging.warning(f"Wikipedia search failed: {e}")
        results = []
    for item in results[:3]:
        lines.append(f"**{item['title']}**\n{item['snippet']}\n{item['url']}")
    description = "\n\n".join(lines) if lines else "No results found. Try different wording."
    return discord.Embed(title=f"Search: {query}", description=description, color=discord.Color.blurple())

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
            "1. Visit [GitHub Releases](https://github.com/Nashon-ops/Sanin/releases).\n"
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
            "A: It's open-source on [GitHub](https://github.com/Nashon-ops/Sanin)."
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

@bot.command(name="release")
async def release_prefix_cmd(ctx, *, title: str):
    async with ctx.typing():
        await ctx.reply(embed=await build_release_embed(title))

@bot.command(name="showdown")
async def showdown_prefix_cmd(ctx, *, titles: str):
    parts = re.split(r"\s+(?:vs\.?|versus)\s+", titles, maxsplit=1, flags=re.I)
    if len(parts) != 2:
        await ctx.reply("Use: !showdown Title A vs Title B")
        return
    async with ctx.typing():
        await ctx.reply(embed=await build_showdown_embed(parts[0].strip(), parts[1].strip(), ctx.channel.id))

@bot.command(name="search")
async def search_prefix_cmd(ctx, *, query: str):
    canned = canonical_reply(query)
    if canned:
        await ctx.reply(canned)
        return
    async with ctx.typing():
        await ctx.reply(embed=await build_search_embed(query))

@bot.command(name="about")
async def about_prefix_cmd(ctx):
    await ctx.reply(embed=build_about_embed())

@bot.tree.command(name="ask", description="Ask San anything about Sanin or chat")
@app_commands.describe(question="Your question for San")
async def ask_slash(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    reply = await get_ai_response(interaction.channel_id, interaction.user.display_name, question)
    await interaction.followup.send(reply)

@bot.tree.command(name="guide", description="Interactive guide for Sanin")
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

@bot.tree.command(name="release", description="Estimated release date for an anime or show")
@app_commands.describe(title="Title to look up")
async def release_slash(interaction: discord.Interaction, title: str):
    await interaction.response.defer()
    await interaction.followup.send(embed=await build_release_embed(title))

@bot.tree.command(name="showdown", description="Compare two titles and settle a debate")
@app_commands.describe(first="First title", second="Second title")
async def showdown_slash(interaction: discord.Interaction, first: str, second: str):
    await interaction.response.defer()
    await interaction.followup.send(embed=await build_showdown_embed(first, second, interaction.channel_id))

@bot.tree.command(name="search", description="Look something up online")
@app_commands.describe(query="What to search for")
async def search_slash(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    canned = canonical_reply(query)
    if canned:
        await interaction.followup.send(canned)
        return
    await interaction.followup.send(embed=await build_search_embed(query))

@bot.tree.command(name="about", description="What San is and what it can do")
async def about_slash(interaction: discord.Interaction):
    await interaction.response.send_message(embed=build_about_embed())

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
