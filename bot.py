import os
import sys
import re
import json
import base64
import time
import random
import logging
import asyncio
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import quote, urlparse, parse_qs, unquote, urljoin
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
GH_TOKEN = os.getenv("GH_TOKEN", "")
MEMORY_REPO = os.getenv("MEMORY_REPO", "Shippun58/sanin-discord-bot")
MEMORY_BRANCH = os.getenv("MEMORY_BRANCH", "memory")
LOCAL_MEMORY_FILE = Path(__file__).with_name("memory.json")
DEV_ID = os.getenv("DEV_ID", os.getenv("OWNER_ID", "1464266754980315324"))
MANUAL_PATH = Path(__file__).with_name("sanin_manual.md")
WEB_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SaninBot/1.0; +https://sanin-discord-bot.onrender.com/healthz)",
    "Accept-Language": "en-US,en;q=0.8",
}
REPO_URL_RE = re.compile(r"https?://[^\s<>()]+", re.I)
PHISHER_REPO = "https://raw.githubusercontent.com/phisher98/cloudstream-extensions-phisher/refs/heads/builds/repo.json"
CNC_REPO = "https://raw.githubusercontent.com/NivinCNC/CNCVerse-Cloud-Stream-Extension/refs/heads/builds/CNC.json"
YUZONO_ANIME_REPO = "https://raw.githubusercontent.com/yuzono/anime-repo/repo/index.min.json"
LANGUAGE_HINTS = ("spanish","español","espanol","es","castellano","french","francais","français","italian","italiano","german","deutsch","japanese","nihongo","portuguese","brazilian","korean","chinese","mandarin","arabic","hindi","urdu","bengali","tamil","telugu","malayalam","indonesian","thai","vietnamese","turkish","russian","polish","dutch","swedish","norwegian","danish","finnish","greek","hebrew","filipino")
WAIT_LINES = (
    "Hold on, checking a few repos.",
    "Gimme a minute, testing these.",
    "On it, checking which one actually works.",
    "One sec, verifying a repo.",
    "Hang on, testing a couple of options.",
)

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

SANIN_SYSTEM_PROMPT = """You are San, a helper in the Sanin Discord.

Identity
- Sanin is an open-source media player and tracker for Android phones, tablets, Android TV, and Fire TV.
- If someone asks who made you, answer in one plain sentence: built around Sanin by its developers and open-source contributors. No speech, no mascot intro.
- Official repo: https://github.com/Nashon-ops/Sanin
- Official releases: https://github.com/Nashon-ops/Sanin/releases
- Only include those two links when the user explicitly asks for the repo, source code, GitHub, release page, download link, or latest version. Never attach them to normal answers and never repeat a refusal policy.
- Extension repositories are different: use Wotaku, live search results, and owner notes. Do not confuse them with the Sanin app repo.
- For every other topic, do not bring up Sanin or its links at all.

Voice
- Sound like a person chatting in Discord, not a bot, mascot, or support agent.
- Never open with "Hey! I'm San", "community AI", "here to help", "friendly extension", or any self-description unless they ask who you are.
- Skip filler and forced positivity. Have opinions, be concise, get to the answer.
- No emojis unless the user uses them first. Short replies beat polished ones.

Sanin support
- If someone gives a specific bug, answer with the smallest useful steps. Do not ask if they want help.
- If someone only says they are stuck, lost, or something is not working, ask one short question about the exact screen, error, or mode. Do not dump the manual or list every possible fix.
- Use the support manual only when it directly matches the reported issue. Never paste or summarize whole manual sections.
- Match the user's language; if the user writes in Spanish, reply in Spanish. Do not translate into English unless the user asked for English.
- Adult/NSFW content is supported by Sanin when enabled. If asked how to enable it or why it is hidden, give the exact toggles from the manual. Do not refuse, moralize, or pretend the feature does not exist.
- For adult title recommendations, give a short list of titles that fit the request and label them NSFW. Use AniList adult anime data for anime and live results for movies/TV. Keep descriptions non-explicit; no graphic sexual detail.
- For NSFW repos or plugins, use the same repo search and verification flow. List plugin names only when they came from the verified manifest.
- Identify mode (Anime or Movie & TV), device, and whether audio and controls work only when it changes the fix. Do not interrogate them.
- Black video in Anime: switch server/source first, then Settings > Playback & App Behaviour > Player & Sync > Player Settings > Video, Video output to TextureView, then Decoder to Hardware+, then Software. Clear cache if relevant, never clear app data.
- Black video in Movie & TV: switch server/source/quality first. Anime Decoder and Video output do not apply to that player.
- If only one server is black, suspect a dead source or bad codec. If every server is black, ask for Log Manager logs and the exact source/server/quality.
- Do not claim Sanin hosts streams or subtitles, that Add-ons are streaming sources, or that the app updates itself.
- If you genuinely cannot answer after using the manual and your own knowledge, reply with exactly CANNOT_HELP and nothing else. Let the bot handle it.

Sanin app facts
- It does not host media. Streams come from installed extensions/add-ons or local downloads.
- Anime mode uses AniList or MAL. Movie & TV mode uses Simkl for tracking and TMDB for metadata. They have different home, library, search, and player screens.
- Extensions are under Settings > Utilities > Management > Extension Manager, and the right-rail Extensions button. Modes are Aniyomi, CloudStream, and Stremio.
- Anime sources are Aniyomi extensions or native parsers. Movie & TV sources are CloudStream plugins and Stremio add-ons. CloudStream has no sites installed by default.
- Settings > Utilities > Management > Add-ons is a legacy empty screen. Do not send users there for streams.
- The anime player has gestures, subtitles, speed, PiP, and decoder controls. The Movie & TV player is simple ExoPlayer with far fewer controls.
- Samsung/LG TVs cannot install Android APKs. Use an Android TV box, Google TV device, or Fire TV Stick.
- Current source needs Android 7.0+ (API 24). No working in-app app updater; update the APK manually.

Formatting
- Plain Discord markdown. No ASCII art, divider lines, rows of dashes, pipes or arrows, tables, or banners.
- Use bold headings only when a list actually needs one. Avoid heavy formatting.
- Do not use emojis as bullets, markers, or decoration.

Accuracy
- Live web search results may be provided. Check them and answer from them. Never dump the result list, raw snippets, or a wall of URLs.
- Never say you cannot search the web. If results are missing, answer from your own knowledge and say it may be outdated.
- "Verified data" and the manual are helpful context, not a cage. Use your own knowledge freely for anime, characters, rumors, and theories.
- Talk about rumors as rumors: what is known, what is reported, and what is still speculation. Never brush off a question just because it is not about Sanin.
- Answer directly. If a current number is not in the data, give your best knowledge-based answer and flag it as possibly outdated instead of telling the user where to look.
- Treat short follow-ups and replies as continuations of the conversation. When someone asks "what about X" or replies to your last message, stay on the same topic and resolve X against the previous exchange instead of answering the words literally.
- Never fabricate a link or present a guessed release date as fact.
"""

APP_INFO = {
    "name": "Sanin",
    "tagline": "Discover. Watch. Track. — built for TV, works on phones and tablets.",
}

SANIN_LINK_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/Nashon-ops/Sanin(?:/releases)?/?", re.I)
SANIN_MD_LINK_RE = re.compile(r"\[[^\]]*\]\(\s*(?:https?://)?(?:www\.)?github\.com/Nashon-ops/Sanin[^)]*\)", re.I)

def wants_sanin_links(prompt: str) -> bool:
    lower = prompt.lower().strip()
    terms = ("repo", "repository", "source code", "source", "github", "releases", "release page", "download", "apk", "latest version")
    if "sanin" in lower and any(term in lower for term in terms):
        return True
    if re.search(r"\b(your|you|ur)\b", lower) and any(term in lower for term in terms):
        return True
    if any(phrase in lower for phrase in ("the app repo", "this app repo", "app source", "app github")):
        return True
    return any(phrase in lower for phrase in ("official repo", "official source", "official github", "official releases", "official release page", "official download link", "official apk"))

def sanitize_sanin_links(text: str) -> str:
    if not text:
        return text
    text = SANIN_MD_LINK_RE.sub("the official release channel", text)
    text = SANIN_LINK_RE.sub("the official release channel", text)
    return re.sub(r"[ \t]{2,}", " ", text)

# ==========================================
# SANIN SUPPORT MANUAL RETRIEVAL
# ==========================================
manual_sections = []

def load_manual_sections() -> list:
    if manual_sections:
        return manual_sections
    try:
        text = MANUAL_PATH.read_text(encoding="utf-8")
    except Exception as e:
        logging.warning(f"Manual load failed: {e}")
        return []
    for part in re.split(r"(?m)^## ", text)[1:]:
        title, _, body = part.partition("\n")
        body = body.strip()
        manual_sections.append({"title": title.strip(), "body": body, "lower": body.lower()})
    return manual_sections

MANUAL_STOPWORDS = {"about", "after", "again", "could", "does", "from", "have", "into", "just", "like", "make", "more", "most", "much", "only", "other", "please", "sanin", "should", "some", "that", "there", "they", "this", "very", "what", "when", "where", "which", "with", "would", "your"}

MANUAL_RULES = (
    ("11.", r"\b(nsfw|adult(?: content| only)?|hide private|extensions?|add-?ons?|plugins?|repos?|repositories?|aniyomi|cloudstream|stremio)\b"),
    ("19.", r"\b(logs?|logging|diagnostics?)\b"),
    ("12.", r"\b(downloads?|offline)\b"),
    ("14.", r"\b(audio|sound|voice|subtitles?|subs|captions?|sync)\b"),
    ("13.", r"\b(black|video|player|playback|decoder|buffer|stutter|server|quality)\b"),
    ("17.", r"\b(slow|lag|performance|animations?|motion|appearance|theme|blur|oled)\b"),
    ("18.", r"\b(network|dns|proxy|vpn|backup|restore)\b"),
    ("20.", r"\b(fire ?tv|firestick|android tv|remote)\b"),
    ("15.", r"\b(account|tracker|tracking|mal|anilist|comments?)\b"),
    ("16.", r"\b(notifications?|subscriptions?|subscribe)\b"),
    ("21.", r"\b(trailers?|reels?)\b"),
    ("1.", r"\b(install|installation|first launch|apk|update)\b"),
    ("22.", r"\b(crash|crash(es|ing)?|error)\b"),
)

def manual_context(prompt: str) -> str:
    sections = load_manual_sections()
    if not sections:
        return ""
    lower = prompt.lower()
    support_words = ("sanin", "player", "extension", "source", "add-on", "addon", "nsfw", "adult", "black", "video", "audio", "subtitle", "crash", "error", "buffer", "install", "update", "apk", "fire tv", "android tv", "settings", "tracker", "log", "stremio", "cloudstream", "movie & tv")
    if not any(word in lower for word in support_words):
        return ""
    nsfw = any(k in lower for k in ("nsfw", "adult", "hentai", "explicit"))
    title_rec = nsfw and any(k in lower for k in ("recommend", "suggest", "title", "titles", "watch", "give me", "show me"))
    chosen = []
    seen = set()
    for prefix, pattern in MANUAL_RULES:
        if prefix == "11." and title_rec and not any(k in lower for k in ("extension", "addon", "add-on", "plugin", "repo")):
            continue
        if not re.search(pattern, lower):
            continue
        section = next((s for s in sections if s["title"].startswith(prefix)), None)
        if section and section["title"] not in seen:
            chosen.append(section)
            seen.add(section["title"])
        if len(chosen) >= 2:
            break
    if not chosen:
        words = {word for word in re.findall(r"[a-z0-9]+", lower) if len(word) >= 4 and word not in MANUAL_STOPWORDS}
        scored = []
        for section in sections:
            score = sum(1 for word in words if word in section["lower"])
            if any(word in section["title"].lower() for word in words):
                score += 3
            if score:
                scored.append((score, section))
        scored.sort(key=lambda item: -item[0])
        if scored and scored[0][0] >= 4:
            chosen.append(scored[0][1])
    if not chosen:
        return ""
    chunks = [f"[{section['title']}]\n{section['body'][:1400]}" for section in chosen]
    return sanitize_sanin_links("\n\n".join(chunks)[:5000])

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
# OWNER LEARNED MEMORY
# ==========================================
memory_cache = {"data": None, "checked_at": 0.0}

def is_owner(user) -> bool:
    owner_id = os.getenv("OWNER_ID", "").strip()
    if owner_id:
        return str(user.id) == owner_id
    owner = getattr(bot.application, "owner", None)
    if owner is None:
        return False
    if hasattr(owner, "id"):
        return user.id == owner.id
    members = getattr(owner, "members", None)
    return bool(members and any(user.id == member.id for member in members))

def github_headers() -> dict:
    return {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Sanin-Discord-Bot/1.0",
    }

def normalize_memory(data) -> dict:
    if isinstance(data, list):
        return {"facts": data, "users": {}}
    if not isinstance(data, dict):
        return {"facts": [], "users": {}}
    data.setdefault("facts", [])
    data.setdefault("users", {})
    return data

async def load_memory() -> dict:
    now = time.time()
    if memory_cache["data"] is not None and now - memory_cache["checked_at"] < 60:
        return normalize_memory(memory_cache["data"])
    data = {"facts": [], "users": {}}
    if GH_TOKEN:
        url = f"https://api.github.com/repos/{MEMORY_REPO}/contents/memory.json"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params={"ref": MEMORY_BRANCH}, headers=github_headers(), timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        raw = await resp.json()
                        decoded = base64.b64decode(raw.get("content", "")).decode("utf-8", errors="replace")
                        data = normalize_memory(json.loads(decoded))
                    else:
                        logging.warning(f"Memory load returned {resp.status}")
        except Exception as e:
            logging.warning(f"Memory load failed: {e}")
    if not data["facts"] and not data["users"]:
        try:
            data = normalize_memory(json.loads(LOCAL_MEMORY_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
    memory_cache.update(data=data, checked_at=now)
    return normalize_memory(data)

async def save_memory(data: dict) -> bool:
    data = normalize_memory(data)
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    if GH_TOKEN:
        url = f"https://api.github.com/repos/{MEMORY_REPO}/contents/memory.json"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params={"ref": MEMORY_BRANCH}, headers=github_headers(), timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    sha = (await resp.json()).get("sha") if resp.status == 200 else None
                body = {
                    "message": "Update San learned memory",
                    "content": base64.b64encode(payload.encode("utf-8")).decode("ascii"),
                    "branch": MEMORY_BRANCH,
                }
                if sha:
                    body["sha"] = sha
                async with session.put(url, json=body, headers=github_headers(), timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status not in (200, 201):
                        text = await resp.text()
                        logging.warning(f"Memory save returned {resp.status}: {text[:120]}")
                        return False
        except Exception as e:
            logging.warning(f"Memory save failed: {e}")
            return False
    else:
        try:
            LOCAL_MEMORY_FILE.write_text(payload, encoding="utf-8")
        except Exception as e:
            logging.warning(f"Local memory save failed: {e}")
            return False
    memory_cache.update(data=data, checked_at=time.time())
    return True

def extract_user_fact(content: str) -> str:
    text = content.strip()
    low = text.lower()
    for marker in ("remember that ", "remember "):
        if low.startswith(marker):
            rest = text[len(marker):].strip().rstrip(".!").strip()
            if 3 <= len(rest) <= 100:
                return rest
    match = re.match(r"^i (?:really )?(like|love|enjoy|prefer|hate|dislike)\s+(.{3,80})$", text, re.I)
    if match:
        verb, thing = match.group(1).lower(), match.group(2).strip().rstrip(".!")
        return f"likes {thing}" if verb in ("like", "love", "enjoy", "prefer") else f"dislikes {thing}"
    return ""

async def remember_user(user, fact: str) -> bool:
    fact = fact.strip()
    if not fact:
        return False
    data = await load_memory()
    entry = data["users"].setdefault(str(user.id), {"name": getattr(user, "display_name", str(user)), "facts": []})
    entry["name"] = getattr(user, "display_name", entry.get("name", str(user)))
    if fact in entry["facts"]:
        return False
    entry["facts"] = (entry["facts"] + [fact])[-20:]
    return await save_memory(data)

def detect_tone(content: str) -> str:
    low = content.lower()
    profanity = ("fuck", "shit", "damn", "bitch", "wtf", "bullshit", "crap", "asshole")
    harsh = ("idiot", "stupid", "trash", "garbage", "shut up", "dumb", "loser")
    curse_hits = sum(1 for word in profanity if word in low)
    harsh_hits = sum(1 for word in harsh if word in low)
    if curse_hits >= 1 and harsh_hits >= 1:
        return "throws curse words and is blunt; match their energy, stay sharp and informal"
    if curse_hits:
        return "throws curse words sometimes; keep it casual and don't be stiff or preachy"
    if harsh_hits:
        return "harsh and blunt; skip pleasantries and give it to them straight"
    return ""

async def remember_tone(user, tone: str) -> bool:
    tone = tone.strip()
    if not tone:
        return False
    data = await load_memory()
    entry = data["users"].setdefault(str(user.id), {"name": getattr(user, "display_name", str(user)), "facts": [], "tone": ""})
    entry["name"] = getattr(user, "display_name", entry.get("name", str(user)))
    if entry.get("tone") == tone:
        return False
    entry["tone"] = tone
    return await save_memory(data)

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
        "max_tokens": 2048
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

ANILIST_QUERY = """query ($q: String, $type: MediaType) {
  Page(perPage: 3) {
    media(search: $q, type: $type) {
      title { romaji english }
      averageScore popularity episodes status format siteUrl
      nextAiringEpisode { airingAt episode }
      genres
    }
  }
}"""

ANILIST_ADULT_QUERY = """query {
  Page(perPage: 5) {
    media(type: ANIME, isAdult: true, sort: POPULARITY_DESC) {
      title { romaji english }
      averageScore popularity siteUrl
    }
  }
}"""

ANILIST_CHARACTER_QUERY = """query ($q: String) {
  Character(search: $q) {
    id
    name { full native }
    favourites
    siteUrl
    description
    media(sort: POPULARITY_DESC, perPage: 3) { nodes { title { romaji english } } }
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
    return text.strip()

def split_message(text: str, limit: int = 1900) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks = []
    while len(text) > limit:
        cut = text.rfind("\n\n", 0, limit)
        if cut < limit // 2:
            cut = text.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = text.rfind(" ", 0, limit)
        if cut < 1:
            cut = limit
        chunks.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    if text:
        chunks.append(text)
    return chunks

def fit_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text.rfind(" ", 0, limit - 1)
    if cut < limit // 2:
        cut = limit - 1
    return text[:cut].rstrip() + "…"

def canonical_reply(prompt: str, learned_facts: list | None = None) -> str | None:
    lower = prompt.lower()
    if wants_sanin_links(prompt):
        return f"Repo: {OFFICIAL_REPO}\nReleases: {RELEASES_URL}"
    if learned_facts and any(any(k in fact.lower() for k in ("repo", "wotaku", "extension", "source")) for fact in learned_facts):
        if any(k in lower for k in ("repo", "extension", "source")):
            return None
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
    leading = r"^(who would win|who wins|would win|rumors of|rumour of|rumors about|rumours about|rumors|rumours|leaks on|leak of|news on|news about|what do you think about|do you think about|what about|thoughts on|what|when|who|how many|how much|how|many|much|episodes|episode|chapters|chapter|volumes|volume|is|are|does|do|can|could|would|should|win|wins|winner|stronger|better|tell me about|info on|information on|estimate|release date of|created|made by|the|a|an|of)\b[\s:]*"
    while True:
        updated = re.sub(leading, "", text, flags=re.I)
        if updated == text:
            break
        text = updated
    text = re.sub(r"\b(release date|air date|next episode|estimated|estimate|release|episodes|episode|chapters|chapter|volumes|volume|count|have|has|anime|manga|show|movie|series)\b", " ", text, flags=re.I)
    return " ".join(text.split())[:60]

async def fetch_json(url: str, params: dict | None = None, headers: dict | None = None, timeout: int = 8) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            if resp.status != 200:
                raise Exception(f"HTTP {resp.status}")
            return await resp.json(content_type=None)

async def fetch_text(url: str, headers: dict | None = None, timeout: int = 10) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            if resp.status != 200:
                raise Exception(f"HTTP {resp.status}")
            return await resp.text()

async def anilist_search(title: str, media_type: str = "ANIME") -> list:
    payload = {"query": ANILIST_QUERY, "variables": {"q": title, "type": media_type}}
    async with aiohttp.ClientSession() as session:
        async with session.post("https://graphql.anilist.co", json=payload, headers={"User-Agent": "SanBot/1.0"}, timeout=aiohttp.ClientTimeout(total=8)) as resp:
            if resp.status != 200:
                raise Exception(f"AniList HTTP {resp.status}")
            data = await resp.json(content_type=None)
    return (data.get("data") or {}).get("Page", {}).get("media") or []

async def anilist_adult() -> list:
    payload = {"query": ANILIST_ADULT_QUERY}
    async with aiohttp.ClientSession() as session:
        async with session.post("https://graphql.anilist.co", json=payload, headers={"User-Agent": "SanBot/1.0"}, timeout=aiohttp.ClientTimeout(total=8)) as resp:
            if resp.status != 200:
                raise Exception(f"AniList adult HTTP {resp.status}")
            data = await resp.json(content_type=None)
    return (data.get("data") or {}).get("Page", {}).get("media") or []

async def anilist_character(name: str) -> dict | None:
    payload = {"query": ANILIST_CHARACTER_QUERY, "variables": {"q": name}}
    async with aiohttp.ClientSession() as session:
        async with session.post("https://graphql.anilist.co", json=payload, headers={"User-Agent": "SanBot/1.0"}, timeout=aiohttp.ClientTimeout(total=8)) as resp:
            if resp.status != 200:
                raise Exception(f"AniList character HTTP {resp.status}")
            data = await resp.json(content_type=None)
    return (data.get("data") or {}).get("Character")

def clean_markup(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return " ".join(text.replace("__", "").replace("*", "").replace("~!", "").replace("!~", "").split())

def compact_character(item: dict | None) -> dict:
    if not item:
        return {}
    names = item.get("name") or {}
    nodes = ((item.get("media") or {}).get("nodes") or [])[:3]
    series = []
    for node in nodes:
        titles = node.get("title") or {}
        series.append(titles.get("english") or titles.get("romaji"))
    return {
        "name": names.get("full") or names.get("native"),
        "favourites": item.get("favourites"),
        "series": series,
        "url": item.get("siteUrl"),
        "description": clean_markup(item.get("description"))[:320],
    }

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
        headers=WEB_HEADERS,
    )
    results = []
    for item in (data.get("query") or {}).get("search", []):
        title = item.get("title", "")
        snippet = unescape(re.sub(r"<[^>]+>", "", item.get("snippet", "")))
        results.append({"title": title, "snippet": snippet[:220], "url": "https://en.wikipedia.org/wiki/" + quote(title.replace(" ", "_"))})
    return results

def decode_search_url(href: str) -> str:
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        target = parse_qs(parsed.query).get("uddg")
        if target:
            return unquote(target[0])
    return href

async def web_search(query: str) -> list:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://lite.duckduckgo.com/lite/",
            params={"q": query},
            headers=WEB_HEADERS,
            timeout=aiohttp.ClientTimeout(total=12),
        ) as resp:
            if resp.status != 200:
                raise Exception(f"search HTTP {resp.status}")
            html = await resp.text()
    links = re.findall(r"<a[^>]+href=\"([^\"]+)\"[^>]*class=['\"]result-link['\"][^>]*>(.*?)</a>", html, re.S)
    snippets = re.findall(r"<td class=['\"]result-snippet['\"]>(.*?)</td>", html, re.S)
    results = []
    for index, (href, title) in enumerate(links[:5]):
        title = " ".join(unescape(re.sub(r"<[^>]+>", "", title)).split())
        snippet = snippets[index] if index < len(snippets) else ""
        snippet = " ".join(unescape(re.sub(r"<[^>]+>", "", snippet)).split())[:300]
        url = decode_search_url(href)
        if title and url.startswith("http"):
            results.append({"title": title, "snippet": snippet, "url": url})
    return results

def is_public_repo_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith((".local", ".internal")):
        return False
    if host.startswith(("127.", "10.", "192.168.", "169.254.", "0.")):
        return False
    if host.startswith("172."):
        try:
            if 16 <= int(host.split(".")[1]) <= 31:
                return False
        except (IndexError, ValueError):
            pass
    return host not in ("::1",) and not host.startswith(("fc", "fd", "fe80"))

async def inspect_repo(url: str) -> dict:
    url = url.strip().rstrip(".,;")
    result = {"url": url, "ok": False, "count": 0, "valid_urls": 0, "names": [], "sample": "", "error": ""}
    if not is_public_repo_url(url):
        result["error"] = "not a public http(s) URL"
        return result
    try:
        data = await fetch_json(url, headers=WEB_HEADERS, timeout=20)
    except Exception as e:
        result["error"] = str(e)[:120]
        return result
    items = data if isinstance(data, list) else None
    if isinstance(data, dict):
        for key in ("plugins", "extensions", "items", "data"):
            if isinstance(data.get(key), list):
                items = data[key]
                break
        if items is None and isinstance(data.get("pluginLists"), list):
            items = []
            for plugin_list in data["pluginLists"][:4]:
                try:
                    target = urljoin(url, str(plugin_list))
                    extra = await fetch_json(target, headers=WEB_HEADERS, timeout=20)
                    if isinstance(extra, list):
                        items.extend(extra)
                except Exception:
                    continue
        if items is None and (data.get("id") or data.get("name")):
            items = [data]
    if not isinstance(items, list):
        result["error"] = "no plugin list found"
        return result
    if not items:
        result["error"] = "manifest has no plugins"
        return result
    names = [
        str(item.get("name") or item.get("internalName") or item.get("pkg") or item.get("id") or "unnamed")[:50]
        for item in items if isinstance(item, dict)
    ]
    first = items[0] if items and isinstance(items[0], dict) else {}
    mature = any(
        item.get("mature") or item.get("nsfw") or item.get("adult") or item.get("isAdult")
        for item in items if isinstance(item, dict)
    )
    score = first.get("rating") or first.get("score") or first.get("averageScore")
    if not score and isinstance(data, dict):
        score = data.get("rating") or data.get("score")
    catalogs = data.get("catalogs") if isinstance(data, dict) else first.get("catalogs")
    types = data.get("types") if isinstance(data, dict) else first.get("types")
    result.update(
        ok=True,
        count=len(items),
        valid_urls=sum(1 for item in items if isinstance(item, dict) and str(item.get("url", "")).startswith("http")),
        names=names,
        sample=", ".join(names[:8]),
        mature=bool(mature),
        score=score,
        catalogs=len(catalogs) if isinstance(catalogs, list) else 0,
        types=len(types) if isinstance(types, list) else 0,
    )
    return result

async def test_repo(url: str) -> str:
    result = await inspect_repo(url)
    if not result["ok"]:
        return f"Repo check failed: {result['error']}."
    suffix = f" Sample: {result['sample']}" if result.get("sample") else ""
    return f"Repo OK: {result['count']} entries, {result['valid_urls']} with valid plugin URLs.{suffix}"

def extract_repo_urls(text: str) -> list:
    text = unescape(text or "")
    found = re.findall(r"https?://[^\s\"'<>\)\]]+", text)
    urls = []
    for url in found:
        url = url.rstrip(".,;:`")
        if "github.com/" in url and "/blob/" in url:
            url = url.replace("github.com/", "raw.githubusercontent.com/").replace("/blob/", "/")
        if not url.endswith(".json") or url.lower().endswith(("package.json", "package-lock.json")):
            continue
        if url not in urls:
            urls.append(url)
    return urls

def asks_extension_repo(prompt: str) -> bool:
    lower = prompt.lower()
    if wants_sanin_links(prompt):
        return False
    if any(k in lower for k in ("how to add", "how do i add", "how can i add")):
        return False
    if any(k in lower for k in ("repo", "repository")):
        return True
    if REPO_URL_RE.search(prompt):
        return any(k in lower for k in ("test", "check", "valid", "work", "broken"))
    if any(k in lower for k in ("nsfw", "adult", "hentai")) and any(k in lower for k in ("extension", "addon", "add-on", "plugin")):
        return True
    return "extension" in lower and any(k in lower for k in ("find", "recommend", "suggest", "which", "best", "good", "working"))

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
            "chapters": item.get("chapters"),
            "volumes": item.get("volumes"),
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

async def wotaku_repos(prompt: str) -> str:
    lower = prompt.lower()
    if "stremio" in lower:
        categories = ["stremio"]
    elif "novel" in lower:
        categories = ["lnreader", "ireader"]
    elif "manga" in lower:
        categories = ["mihon"]
    elif any(k in lower for k in ("anime", "movie", "live action", "source", "cloudstream", "sanin")):
        categories = ["cloudstream", "aniyomi"]
    else:
        categories = ["cloudstream", "aniyomi"]
    lines = []
    for category in categories:
        url = f"https://raw.githubusercontent.com/wotakumoe/wotaku/main/docs/ext/{category}.md"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        continue
                    text = await resp.text()
        except Exception as e:
            logging.warning(f"Wotaku lookup failed for {category}: {e}")
            continue
        name = ""
        source_url = ""
        for line in text.splitlines():
            if line.startswith("== "):
                name = line[3:].strip()
                source_url = ""
            elif line.startswith("- url:") and name:
                source_url = line.split(":", 1)[1].strip()
            elif line.startswith("- raw:") and name:
                raw_url = line.split(":", 1)[1].strip()
                lines.append(f"{name} ({category}): {raw_url} | {source_url}")
                name = ""
                source_url = ""
    if not lines:
        return "Wotaku wiki had no matching extension repo list."
    return "Wotaku wiki extension repos: " + "; ".join(lines[:8])

async def repo_page_text(url: str) -> str:
    parsed = urlparse(url)
    if parsed.hostname == "github.com":
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2:
            owner, repo = parts[0], parts[1]
            for branch in ("HEAD", "main", "master"):
                try:
                    return await fetch_text(f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md")
                except Exception:
                    continue
    try:
        return await fetch_text(url, timeout=8)
    except Exception as e:
        logging.warning(f"Repo page fetch failed for {url}: {e}")
        return ""

def repo_relevance_score(item: dict, prompt: str) -> int:
    ignore = {"repo", "repository", "extension", "plugin", "cloudstream", "aniyomi", "stremio", "sanin", "best", "good", "working", "work", "please", "find", "give", "recommend", "which", "what", "where", "for", "with", "and"}
    words = {word for word in re.findall(r"[a-z0-9]{3,}", prompt.lower()) if word not in ignore}
    haystack = f"{item.get('title', '')} {item.get('snippet', '')}".lower()
    return sum(1 for word in words if word in haystack)

def repo_mode(prompt: str) -> str:
    lower = prompt.lower()
    if "stremio" in lower or "movie" in lower or "movies" in lower:
        return "stremio"
    if "aniyomi" in lower or "anime" in lower:
        return "aniyomi"
    return "cloudstream"

def language_hint(prompt: str) -> str:
    lower = prompt.lower()
    for hint in LANGUAGE_HINTS:
        if re.search(rf"(?<![a-z]){re.escape(hint)}(?![a-z])", lower):
            return hint
    return ""

PLUGIN_INTENTS = {
    "4k": ("4k", "uhd", "2160"),
    "nsfw": ("nsfw", "adult", "hentai", "18", "xxx", "porn"),
    "rating": ("imdb", "rating", "score", "metadata", "tmdb"),
    "metadata": ("metadata", "imdb", "tmdb", "trailer"),
    "live": ("live", "sport", "tv"),
    "anime": ("anime", "ani"),
    "dub": ("dub", "dubbed"),
    "sub": ("sub", "subtitle"),
}

def plugin_score(name: str, prompt: str) -> int:
    lower = prompt.lower()
    name_lower = name.lower()
    terms = set()
    for key, aliases in PLUGIN_INTENTS.items():
        if key in lower:
            terms.update(aliases)
    for word in re.findall(r"[a-z0-9]{4,}", lower):
        if word not in {"repo", "repository", "extension", "plugin", "cloudstream", "aniyomi", "stremio", "sanin", "best", "good", "working", "show", "give", "find", "which", "that", "with", "from"}:
            terms.add(word)
    return sum(1 for term in terms if term in name_lower)

def best_plugin_score(check: dict, prompt: str) -> int:
    scores = [plugin_score(name, prompt) for name in check.get("names", [])]
    return max(scores) if scores else 0

def pick_plugin_names(names: list, prompt: str) -> list:
    scored = sorted(((plugin_score(name, prompt), name) for name in names), key=lambda item: -item[0])
    matches = [name for score, name in scored if score > 0]
    if matches:
        return matches[:3]
    return names[:2]

def format_repo_checks(checks: list, prompt: str = "") -> str | None:
    verified = [check for check in checks if check.get("ok")]
    unverified = [check for check in checks if not check.get("ok")]
    if not verified and not unverified:
        return None
    lang = language_hint(prompt)
    mode = repo_mode(prompt)
    def repo_rank(check: dict) -> int:
        url = check["url"].lower()
        if mode == "aniyomi":
            return 0 if "yuzono" in url else 1
        if mode == "cloudstream":
            if "phisher" in url:
                return 0
            if "cnc" in url:
                return 1
            return 2
        if mode == "stremio":
            return 0 if ("stremio" in url or "manifest.json" in url) else 1
        return 2
    if verified:
        verified.sort(key=lambda check: (
            0 if lang and re.search(rf"(?<![a-z]){re.escape(lang)}(?![a-z])", (check["url"] + " " + " ".join(check.get("names", []))).lower()) else (1 if lang else 0),
            repo_rank(check),
            -best_plugin_score(check, prompt),
            -check.get("count", 0),
        ))
    lines = []
    if verified:
        first = verified[0]
        lines.append(f"Here's one I verified: {first['url']} ({first['count']} plugins).")
        if first.get("mature"):
            lines.append("Mature: yes")
        if first.get("score"):
            lines.append(f"Rating: {first['score']}")
        if first.get("types"):
            lines.append(f"Types: {first['types']}")
        if first.get("catalogs"):
            lines.append(f"Catalogs: {first['catalogs']}")
        names = pick_plugin_names(first.get("names", []), prompt)
        if names:
            lines.append("Plugins: " + ", ".join(names))
        if len(verified) > 1:
            lines.append("Also verified: " + ", ".join(check["url"] for check in verified[1:2]))
    else:
        lines.append("I couldn't verify a working repo from those results.")
    if unverified:
        lines.append("Unverified: " + ", ".join(check["url"] for check in unverified[:3]))
    return "\n".join(lines)

async def repo_recommendation(prompt: str) -> str | None:
    if not asks_extension_repo(prompt):
        return None
    direct = REPO_URL_RE.search(prompt)
    if direct:
        return await test_repo(direct.group(0))

    lower = prompt.lower()
    mode = repo_mode(prompt)
    lang = language_hint(prompt)
    queries = [prompt]
    if mode == "aniyomi":
        queries.append(prompt + " aniyomi repo")
    elif mode == "stremio":
        queries.append(prompt + " stremio addon")
    elif "cloudstream" not in lower:
        queries.append(prompt + " cloudstream")
    if lang:
        queries.append(f"{lang} {mode} repo")
    if "reddit" not in lower:
        queries.append(prompt + " reddit")
    queries = list(dict.fromkeys(queries))[:3]

    results = await asyncio.gather(
        *(web_search(query) for query in queries),
        wotaku_repos(lower),
        return_exceptions=True,
    )

    if mode == "aniyomi":
        candidates = [YUZONO_ANIME_REPO]
    elif mode == "cloudstream":
        candidates = [PHISHER_REPO, CNC_REPO]
    else:
        candidates = []
    pages = []
    def add_urls(text: str):
        for url in extract_repo_urls(text):
            if url not in candidates:
                candidates.append(url)

    for result in results:
        if isinstance(result, Exception):
            logging.warning(f"Repo search failed: {result}")
            continue
        if isinstance(result, str):
            add_urls(result)
        elif isinstance(result, list):
            for item in result:
                if not isinstance(item, dict):
                    continue
                add_urls(item.get("snippet", ""))
                add_urls(item.get("url", ""))
                if item.get("url") and not item["url"].endswith(".json"):
                    pages.append(item)

    unique_pages = []
    seen_pages = set()
    for item in sorted(pages, key=lambda entry: -repo_relevance_score(entry, prompt)):
        url = item.get("url", "")
        if url and url not in seen_pages:
            seen_pages.add(url)
            unique_pages.append(url)
    page_texts = await asyncio.gather(
        *(repo_page_text(url) for url in unique_pages[:4]),
        return_exceptions=True,
    )
    for text in page_texts:
        if isinstance(text, str) and text:
            add_urls(text)

    if lang:
        candidates.sort(key=lambda url: 0 if re.search(rf"(?<![a-z]){re.escape(lang)}(?![a-z])", url.lower()) else 1)
    candidates = candidates[:6]
    if not candidates:
        return None
    checks = await asyncio.gather(*(inspect_repo(url) for url in candidates), return_exceptions=True)
    clean_checks = [check for check in checks if isinstance(check, dict)]
    return format_repo_checks(clean_checks, prompt)

async def gather_context(prompt: str) -> str:
    lower = prompt.lower()
    parts = []
    jobs = []
    if len(prompt.split()) >= 2 and not re.fullmatch(r"(hi|hello|hey|yo|thanks|thank you|ok|okay)[!. ]*", lower):
        jobs.append(("web", web_search(prompt)))
    if (
        any(k in lower for k in ("nsfw", "adult", "hentai", "explicit"))
        and any(k in lower for k in ("recommend", "suggest", "title", "titles", "watch", "give me", "show me"))
        and "anime" in lower
    ):
        jobs.append(("adult_anime", anilist_adult()))
    if any(k in lower for k in (" vs ", " versus ", "showdown", "who would win", "character", "debate")):
        sides = re.split(r"\s+(?:vs\.?|versus)\s+", prompt, maxsplit=1, flags=re.I)
        for side in sides[:2]:
            name = extract_title(side)
            if len(name) >= 2:
                jobs.append((f"character:{name}", anilist_character(name)))
                jobs.append((f"charwiki:{name}", wiki_search(name)))
    else:
        title = extract_title(prompt)
        if len(title) >= 2:
            jobs.append(("wiki", wiki_search(title)))
            if any(k in lower for k in ("repo", "extension", "source")) and not any(k in lower for k in ("source code", "github repo")):
                jobs.append(("wotaku", wotaku_repos(lower)))
            if any(k in lower for k in ("anime", "manga", "show", "movie", "series", "release", "air", "episode", "episodes", "chapter", "chapters", "how many", "score", "compare", "better", "season", "when", "rumor", "rumour", "leak", "form", "next", "long")):
                jobs.append(("anilist_anime", anilist_search(title, "ANIME")))
                jobs.append(("anilist_manga", anilist_search(title, "MANGA")))
                if TMDB_API_KEY:
                    jobs.append(("tmdb_tv", tmdb_search(title, "tv")))
                    jobs.append(("tmdb_movie", tmdb_search(title, "movie")))
    if not jobs:
        return "\n".join(parts)
    results = await asyncio.gather(*(job[1] for job in jobs), return_exceptions=True)
    for (name, _), result in zip(jobs, results):
        if isinstance(result, Exception):
            logging.warning(f"{name} lookup failed: {result}")
            continue
        if name.startswith("character:"):
            data = compact_character(result)
            if data:
                parts.append(f"Character {name.split(':', 1)[1]} via AniList: " + json.dumps(data, ensure_ascii=False))
        elif name.startswith("charwiki:"):
            if result:
                parts.append(f"Character {name.split(':', 1)[1]} via Wikipedia: " + json.dumps(result[:2], ensure_ascii=False))
        elif name.startswith("anilist_") and result:
            parts.append(f"AniList {name.split('_', 1)[1]}: " + json.dumps(compact_anilist(result), ensure_ascii=False))
        elif name.startswith("tmdb_") and result:
            parts.append(f"TMDB {name.split('_', 1)[1]}: " + json.dumps(compact_tmdb(result), ensure_ascii=False))
        elif name == "wiki" and result:
            parts.append("Wikipedia: " + json.dumps(result, ensure_ascii=False))
        elif name == "wotaku" and result:
            parts.append(result)
        elif name == "web" and result:
            parts.append("Web search results (use these facts to answer; do not dump the list): " + json.dumps(result, ensure_ascii=False))
        elif name == "adult_anime" and result:
            parts.append("AniList adult anime (label NSFW; titles/scores only, no explicit descriptions): " + json.dumps(compact_anilist(result), ensure_ascii=False))
    return "\n".join(parts) if parts else "No preloaded data for this topic; answer from your own knowledge."

async def query_gemini(api_key: str, messages: list) -> str:
    prompt_text = "\n\n".join(f"{msg['role']}: {msg['content']}" for msg in messages)
    models = ["gemini-flash-latest", "gemini-2.5-flash-lite", "gemini-3.8-flash"]
    for m in models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt_text}]}],
                "generationConfig": {"maxOutputTokens": 2048, "temperature": 0.7}
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=12)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            logging.warning(f"Gemini {m} failed: {e}")
    raise Exception("All Gemini models failed")

async def get_ai_response(channel_id: int, user_name: str, user_prompt: str, context: str | None = None, user_id: int | None = None, status=None) -> str:
    global groq_key_index

    session_key = f"{channel_id}:{user_id or user_name}"
    memory = await load_memory()
    canned = canonical_reply(user_prompt, memory["facts"])
    if canned:
        add_to_history(session_key, "user", user_prompt)
        add_to_history(session_key, "assistant", canned)
        return sanitize_sanin_links(canned)

    if asks_extension_repo(user_prompt):
        if status:
            await status()
        repo_answer = await repo_recommendation(user_prompt)
        if repo_answer:
            add_to_history(session_key, "user", user_prompt)
            add_to_history(session_key, "assistant", repo_answer)
            return repo_answer

    verified = context if context is not None else await gather_context(user_prompt)
    system_prompt = SANIN_SYSTEM_PROMPT + "\n\nVerified data (helpful context, not a limit):\n" + verified
    manual = manual_context(user_prompt)
    if manual:
        system_prompt += "\n\nSanin support manual (use these exact paths and facts):\n" + manual
    if memory["facts"]:
        system_prompt += "\n\nOwner notes (trusted, highest priority, override defaults when they conflict):\n" + "\n".join(f"- {sanitize_sanin_links(fact)}" for fact in memory["facts"][-25:])
    if user_id:
        user_entry = memory["users"].get(str(user_id))
        if user_entry:
            details = []
            if user_entry.get("facts"):
                details.extend(f"- {sanitize_sanin_links(fact)}" for fact in user_entry["facts"][-20:])
            if user_entry.get("tone"):
                details.append(f"- Style: {user_entry['tone']}. Adapt your tone to match, without being preachy.")
            if details:
                system_prompt += f"\n\nAbout {user_name} (remembered):\n" + "\n".join(details)
    formatted_messages = [{"role": "system", "content": system_prompt}]
    for msg in conversation_history[session_key]:
        formatted_messages.append(msg)
    formatted_messages.append({"role": "user", "content": f"{user_name}: {user_prompt}"})

    async def finish(reply: str) -> str:
        if re.search(r"\bCANNOT_HELP\b", reply, re.I):
            reply = f"Unfortunately I can't help with that. Ask <@{DEV_ID}> if you need a hand."
        else:
            reply = clean_reply(reply)
            if not wants_sanin_links(user_prompt):
                reply = sanitize_sanin_links(reply)
        add_to_history(session_key, "user", user_prompt)
        add_to_history(session_key, "assistant", reply)
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
    if wants_sanin_links(user_prompt):
        reply = f"Repo: {OFFICIAL_REPO}\nReleases: {RELEASES_URL}"
    elif any(k in lower for k in ["extension", "source", "repo", "stream"]):
        reply = "Extensions: Sanin -> Settings -> Extensions -> Add Repository -> paste a repo URL, then install what you need."
    elif any(k in lower for k in ["samsung", "tizen", "lg"]):
        reply = "Samsung and LG TVs can't install Android APKs directly. Use a Firestick, Chromecast with Google TV, or an Android TV box."
    else:
        reply = f"Hey {user_name}, I'm San. I can help with Sanin, release estimates, character showdowns, and web lookups. Try /guide, /release, /showdown, or /search."
    add_to_history(session_key, "user", user_prompt)
    add_to_history(session_key, "assistant", reply)
    return reply

def build_about_embed() -> discord.Embed:
    description = (
        "I'm San, the Sanin community AI. I'm a chill anime and TV nerd who keeps things short, "
        "settles character debates with data and reasoning, and never invents links or dates."
    )
    embed = discord.Embed(title="About San", description=description, color=discord.Color.blurple())
    embed.add_field(name="Commands", value="/guide, /download, /tv, /movies, /faq, /ask, /release, /showdown, /search, /about, /memory, /tone, /write", inline=False)
    embed.add_field(name="How to talk to me", value="Mention me, reply to one of my messages, or DM me.", inline=False)
    return embed

async def build_release_embed(title: str) -> discord.Embed:
    jobs = [("anime", anilist_search(title, "ANIME")), ("manga", anilist_search(title, "MANGA"))]
    if TMDB_API_KEY:
        jobs.extend([("tv", tmdb_search(title, "tv")), ("movie", tmdb_search(title, "movie"))])
    results = await asyncio.gather(*(job[1] for job in jobs), return_exceptions=True)
    found = {label: result for (label, _), result in zip(jobs, results) if not isinstance(result, Exception) and result}
    lines = []
    for label in ("anime", "manga"):
        for item in found.get(label, [])[:2]:
            names = item.get("title") or {}
            name = names.get("english") or names.get("romaji") or "Unknown"
            nxt = item.get("nextAiringEpisode") or {}
            status = STATUS_LABELS.get(item.get("status"), item.get("status", "Unknown"))
            if nxt.get("airingAt"):
                eta = f"Episode {nxt.get('episode')} expected {format_date(nxt.get('airingAt'))}"
            elif label == "manga":
                eta = f"{item.get('chapters') or '?'} chapters | {item.get('volumes') or '?'} volumes | {status}"
            else:
                eta = f"Status: {status}"
            score = f"{item.get('averageScore')}%" if item.get("averageScore") is not None else "n/a"
            lines.append(f"**{name}** via AniList {label}\n{eta}\nScore {score} | {item.get('siteUrl')}")
    for label in ("tv", "movie"):
        for item in found.get(label, [])[:1]:
            try:
                detail = await tmdb_details(item)
            except Exception as e:
                logging.warning(f"TMDB details failed: {e}")
                continue
            name = detail.get("name") or detail.get("title") or "Unknown"
            nxt = detail.get("next_episode_to_air") or {}
            if nxt.get("air_date"):
                eta = f"Next episode expected {format_date(nxt['air_date'])}"
            elif detail.get("release_date"):
                eta = f"Released {format_date(detail['release_date'])}"
            else:
                eta = f"Status: {detail.get('status', 'Unknown')}"
            url = f"https://www.themoviedb.org/{label}/{detail.get('id')}"
            score = f"{detail.get('vote_average')}/10" if detail.get("vote_average") is not None else "n/a"
            lines.append(f"**{name}** via TMDB {label}\n{eta}\nScore {score} | {detail.get('status', 'Unknown')} | {url}")
    description = "\n\n".join(lines) if lines else "No reliable match found. Try a more specific title."
    return discord.Embed(title=f"Release estimate: {title}", description=fit_text(description, 4000), color=discord.Color.blurple())

async def fetch_character_side(name: str) -> dict:
    jobs = [("anilist", anilist_character(name)), ("wiki", wiki_search(name))]
    results = await asyncio.gather(*(job[1] for job in jobs), return_exceptions=True)
    side = {"query": name, "anilist": {}, "wiki": []}
    for (label, _), result in zip(jobs, results):
        if isinstance(result, Exception):
            logging.warning(f"{label} character lookup failed: {result}")
            continue
        if label == "anilist":
            side["anilist"] = compact_character(result)
        elif label == "wiki":
            side["wiki"] = result[:2]
    return side

def character_line(side: dict) -> str:
    data = side["anilist"]
    name = data.get("name") or side["query"]
    favourites = f"{data['favourites']:,}" if data.get("favourites") else "n/a"
    series = ", ".join(data.get("series") or []) or "unknown"
    lines = [f"**{name}**", f"AniList favourites: {favourites} | From: {series}"]
    if data.get("description"):
        lines.append(data["description"][:220])
    if data.get("url"):
        lines.append(data["url"])
    for item in side.get("wiki") or []:
        lines.append(f"Wikipedia: {item['title']} — {item['snippet'][:160]}")
    return "\n".join(lines)

async def build_showdown_embed(first: str, second: str, channel_id: int) -> discord.Embed:
    left, right = await asyncio.gather(fetch_character_side(first), fetch_character_side(second))
    description = character_line(left) + "\n\n" + character_line(right)
    context = "Character data: " + json.dumps({"first": left, "second": right}, ensure_ascii=False)
    try:
        verdict = await get_ai_response(
            channel_id,
            "San",
            f"Give your honest, reasoned verdict on {first} vs {second}. Use the character data and your own knowledge of these characters, label it as your opinion, and never invent links or dates.",
            context=context,
        )
        description += "\n\n" + verdict
    except Exception as e:
        logging.warning(f"Showdown verdict failed: {e}")
    return discord.Embed(title=f"Showdown: {first} vs {second}", description=fit_text(description, 4000), color=discord.Color.gold())

async def build_search_embed(query: str) -> discord.Embed:
    lines = []
    try:
        results = await web_search(query)
    except Exception as e:
        logging.warning(f"Web search failed: {e}")
        results = []
    if not results:
        try:
            results = await wiki_search(query)
        except Exception as e:
            logging.warning(f"Wikipedia search failed: {e}")
            results = []
    for item in results[:5]:
        lines.append(f"**{item['title']}**\n{item['snippet']}\n{item['url']}")
    description = "\n\n".join(lines) if lines else "No results found. Try different wording."
    return discord.Embed(title=f"Search: {query}", description=description, color=discord.Color.blurple())

# ==========================================
# DISCORD UI COMPONENTS
# ==========================================
GUIDE_SECTIONS = {
    "download": {
        "title": "Download and Installation",
        "color": discord.Color.green(),
        "description": (
            "**Install on phone or tablet**\n"
            "1. Get the latest APK from the official release channel.\n"
            "2. Download the latest APK for your device.\n"
            "3. Open the downloaded file and tap Install.\n\n"
            "**Install on Android TV or Fire TV**\n"
            "1. Use the Downloader app, or send the APK with Send Files to TV.\n"
            "2. Open the APK and install it.\n\n"
            "**Compatibility**\n"
            "Sanin requires Android 7.0 or newer. Samsung Tizen and LG webOS TVs cannot install Android APKs."
        ),
        "fields": [
            ("Platforms", "Android phones and tablets\nAndroid TV / Google TV\nAmazon Fire TV / Firestick", True),
            ("Minimum Android", "7.0+ (API 24+)", True),
        ]
    },
    "extensions": {
        "title": "Extensions and Sources",
        "color": discord.Color.purple(),
        "description": (
            "Sanin does not host or provide streams. Playback depends on the extensions and repositories you add.\n\n"
            "**Open the extension manager**\n"
            "Use the right-rail Extensions button, or open Settings > Utilities > Management > Extension Manager.\n\n"
            "**Add a repository**\n"
            "1. Choose Aniyomi for anime, CloudStream for Movies and TV, or Stremio for add-ons.\n"
            "2. Tap Add Repository.\n"
            "3. Enter a trusted repo shortcode like `username/repo/branch`, or a raw `index.min.json` URL.\n"
            "4. Install the extension you want, then pick a source or server from the title page.\n\n"
            "**Important**\n"
            "CloudStream has no sites installed by default. The Add-ons screen is legacy and empty, so do not install streams there. Only add repositories you trust. If a repo will not load, try a VPN."
        ),
        "fields": []
    },
    "movies": {
        "title": "Movies and TV",
        "color": discord.Color.gold(),
        "description": (
            "**Play a movie or episode**\n"
            "1. Switch to Movie and TV mode.\n"
            "2. Pick a title, then tap Play Movie or choose an episode.\n"
            "3. Switch servers or extensions if a stream fails.\n\n"
            "**No sources installed**\n"
            "Open the Extensions screen, switch to CloudStream mode, add a trusted repository, and install a source extension.\n\n"
            "**Black video**\n"
            "Switch server, source, or quality first. The simple Movie and TV player does not use the anime Decoder and Video output settings.\n\n"
            "**Add-ons**\n"
            "Settings > Utilities > Management > Add-ons is legacy and empty. Stremio add-ons are installed from the Stremio mode of the Extensions screen."
        ),
        "fields": []
    },
    "tv": {
        "title": "TV Navigation",
        "color": discord.Color.orange(),
        "description": (
            "**Remote controls**\n"
            "- Left and right seek.\n"
            "- Center or OK plays and pauses.\n"
            "- Down opens audio and subtitle options.\n\n"
            "**Fire TV installation**\n"
            "Install the Downloader app from the Amazon Appstore, download the latest APK with it, and install it."
        ),
        "fields": []
    },
    "tracking": {
        "title": "Tracking and Accounts",
        "color": discord.Color.blue(),
        "description": (
            "**Services**\n"
            "- **AniList:** Anime watchlist, scores, and episode progress.\n"
            "- **MyAnimeList:** Anime tracking through an AniList login.\n"
            "- **Simkl:** Movie and TV tracking.\n\n"
            "**Connect an account**\n"
            "Open Settings > Account > Accounts. MAL requires AniList first."
        ),
        "fields": []
    },
    "faq": {
        "title": "FAQ and Troubleshooting",
        "color": discord.Color.teal(),
        "description": (
            "**Why is my video black?**\n"
            "For Anime, switch server or source first. Then open Settings > Playback & App Behaviour > Player & Sync > Player Settings > Video. Set Video output to TextureView, then Decoder to Hardware+, then Software. Reopen the episode. For Movies and TV, switch server, source, or quality first because the simple player does not use those anime decoder settings.\n\n"
            "**Why does a video fail to play?**\n"
            "Sanin does not host media. Switch to another server or extension.\n\n"
            "**Can I install Sanin on a Samsung or LG TV?**\n"
            "No. Samsung uses Tizen and LG uses webOS. Use a Fire TV Stick, Chromecast with Google TV, or Android TV box.\n\n"
            "**How do I add movie sources?**\n"
            "Switch to Movie and TV, open Extensions, use CloudStream mode, add a trusted repository, and install a source extension. Add-ons are not streams."
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

def add_official_links(embed: discord.Embed) -> discord.Embed:
    embed.add_field(name="Official links", value=f"[Releases]({RELEASES_URL})\n[Source]({OFFICIAL_REPO})", inline=False)
    return embed

class GuideSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Download & Install", value="download", description="How to install on phone, TV, or Firestick"),
            discord.SelectOption(label="Extensions & Sources", value="extensions", description="How to add repos and streaming extensions"),
            discord.SelectOption(label="Movies & TV", value="movies", description="How to add a movie source and play"),
            discord.SelectOption(label="Android TV & Fire TV", value="tv", description="Using Sanin on TV with remote control"),
            discord.SelectOption(label="Tracking Accounts", value="tracking", description="Connect AniList, MyAnimeList, or Simkl"),
            discord.SelectOption(label="FAQ & Troubleshooting", value="faq", description="Common questions and quick answers"),
        ]
        super().__init__(placeholder="Choose a topic to explore", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        embed = create_guide_embed(self.values[0])
        await interaction.response.edit_message(embed=embed, view=self.view)

class GuideView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(GuideSelect())

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
    is_reply_to_bot = False
    reply_context = ""
    if message.reference:
        try:
            referenced = message.reference.resolved or await message.channel.fetch_message(message.reference.message_id)
            if referenced and referenced.author == bot.user:
                is_reply_to_bot = True
                reply_context = referenced.clean_content.strip()
        except Exception:
            pass
    is_dm = isinstance(message.channel, discord.DMChannel)

    if is_mentioned or is_reply_to_bot or is_dm:
        clean = message.clean_content.replace(f"@{bot.user.name}", "").strip()
        if not clean:
            clean = "Hello!"
        if reply_context:
            clean = f"Replying to your previous message '{reply_context}'. Follow-up: {clean}"
        fact = extract_user_fact(message.clean_content)
        if fact:
            await remember_user(message.author, fact)
        tone = detect_tone(message.clean_content)
        if tone:
            await remember_tone(message.author, tone)

        async def status():
            await message.reply(random.choice(WAIT_LINES))

        async with message.channel.typing():
            reply_text = await get_ai_response(message.channel.id, message.author.display_name, clean, user_id=message.author.id, status=status)
            chunks = split_message(reply_text)
            if chunks:
                await message.reply(chunks[0])
                for chunk in chunks[1:]:
                    await message.channel.send(chunk)
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
    embed = add_official_links(create_guide_embed("download"))
    await ctx.send(embed=embed)

@bot.command(name="tv")
async def tv_prefix_cmd(ctx):
    embed = create_guide_embed("tv")
    await ctx.send(embed=embed)

@bot.command(name="faq")
async def faq_prefix_cmd(ctx):
    embed = create_guide_embed("faq")
    await ctx.send(embed=embed)

@bot.command(name="movies")
async def movies_prefix_cmd(ctx):
    embed = create_guide_embed("movies")
    await ctx.send(embed=embed)

@bot.command(name="release")
async def release_prefix_cmd(ctx, *, title: str):
    async with ctx.typing():
        await ctx.reply(embed=await build_release_embed(title))

@bot.command(name="showdown")
async def showdown_prefix_cmd(ctx, *, characters: str):
    parts = re.split(r"\s+(?:vs\.?|versus)\s+", characters, maxsplit=1, flags=re.I)
    if len(parts) != 2:
        await ctx.reply("Use: !showdown Character A vs Character B")
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

@bot.command(name="learn")
async def learn_prefix_cmd(ctx, *, fact: str):
    if not is_owner(ctx.author):
        await ctx.reply("Owner only.")
        return
    target = ctx.message.mentions[0] if ctx.message.mentions else None
    if target:
        fact = re.sub(r"^<@!?\d+>\s*", "", fact).strip()
    fact = fact.strip()
    if not fact:
        await ctx.reply("Give me something to remember.")
        return
    data = await load_memory()
    if target:
        entry = data["users"].setdefault(str(target.id), {"name": target.display_name, "facts": []})
        entry["facts"].append(fact)
    else:
        data["facts"].append(fact)
    if await save_memory(data):
        await ctx.reply(f"Saved for {target.display_name if target else 'everyone'}.")
    else:
        await ctx.reply("Couldn't save that right now.")

@bot.command(name="forget")
async def forget_prefix_cmd(ctx, number: int):
    if not is_owner(ctx.author):
        await ctx.reply("Owner only.")
        return
    data = await load_memory()
    target = ctx.message.mentions[0] if ctx.message.mentions else None
    facts = data["users"].get(str(target.id), {}).get("facts", []) if target else data["facts"]
    if not 1 <= number <= len(facts):
        await ctx.reply(f"Give a number from 1 to {len(facts)}. Check with !memory.")
        return
    removed = facts.pop(number - 1)
    if await save_memory(data):
        await ctx.reply(f"Forgot: {removed}")
    else:
        await ctx.reply("Couldn't save that right now.")

@bot.command(name="memory")
async def memory_prefix_cmd(ctx):
    data = await load_memory()
    target = ctx.message.mentions[0] if ctx.message.mentions else ctx.author
    lines = []
    if data["facts"]:
        lines.append("General")
        lines.extend(f"{i}. {fact}" for i, fact in enumerate(data["facts"], 1))
    entry = data["users"].get(str(target.id))
    if entry and (entry.get("facts") or entry.get("tone")):
        lines.append(entry.get("name", "User"))
        lines.extend(f"{i}. {fact}" for i, fact in enumerate(entry.get("facts", []), 1))
        if entry.get("tone"):
            lines.append(f"Style: {entry['tone']}")
    if not lines:
        await ctx.reply("Nothing learned yet.")
        return
    for chunk in split_message("\n".join(lines)):
        await ctx.reply(chunk)

@bot.command(name="tone")
async def tone_prefix_cmd(ctx, *, description: str):
    if not is_owner(ctx.author):
        await ctx.reply("Owner only.")
        return
    target = ctx.message.mentions[0] if ctx.message.mentions else None
    if target:
        description = re.sub(r"^<@!?\d+>\s*", "", description).strip()
    description = description.strip()
    if not description:
        await ctx.reply("Give me a style to remember.")
        return
    data = await load_memory()
    entry = data["users"].setdefault(str(target.id if target else ctx.author.id), {"name": (target or ctx.author).display_name, "facts": [], "tone": ""})
    entry["tone"] = description
    if await save_memory(data):
        await ctx.reply(f"Saved style for {entry['name']}.")
    else:
        await ctx.reply("Couldn't save that right now.")

@bot.tree.command(name="ask", description="Ask San anything about Sanin or chat")
@app_commands.describe(question="Your question for San")
async def ask_slash(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    fact = extract_user_fact(question)
    if fact:
        await remember_user(interaction.user, fact)
    tone = detect_tone(question)
    if tone:
        await remember_tone(interaction.user, tone)

    async def status():
        await interaction.followup.send(random.choice(WAIT_LINES))

    reply = await get_ai_response(interaction.channel_id, interaction.user.display_name, question, user_id=interaction.user.id, status=status)
    chunks = split_message(reply)
    if chunks:
        await interaction.followup.send(chunks[0])
        for chunk in chunks[1:]:
            await interaction.followup.send(chunk)

@bot.tree.command(name="guide", description="Interactive guide for Sanin")
async def guide_slash(interaction: discord.Interaction):
    embed = create_guide_embed("download")
    await interaction.response.send_message(embed=embed, view=GuideView())

@bot.tree.command(name="download", description="Get install instructions")
async def download_slash(interaction: discord.Interaction):
    embed = add_official_links(create_guide_embed("download"))
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="tv", description="Guide for Android TV and Firestick")
async def tv_slash(interaction: discord.Interaction):
    embed = create_guide_embed("tv")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="faq", description="Frequently Asked Questions")
async def faq_slash(interaction: discord.Interaction):
    embed = create_guide_embed("faq")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="movies", description="How to add a movie source and watch movies")
async def movies_slash(interaction: discord.Interaction):
    embed = create_guide_embed("movies")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="release", description="Estimated release date for an anime or show")
@app_commands.describe(title="Title to look up")
async def release_slash(interaction: discord.Interaction, title: str):
    await interaction.response.defer()
    await interaction.followup.send(embed=await build_release_embed(title))

@bot.tree.command(name="showdown", description="Settle a character debate with data and a reasoned opinion")
@app_commands.describe(first="First character", second="Second character")
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

@bot.tree.command(name="learn", description="Teach San a fact or rule (owner only)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(fact="What San should remember", user="Store this for a specific user")
async def learn_slash(interaction: discord.Interaction, fact: str, user: discord.User | None = None):
    if not is_owner(interaction.user):
        await interaction.response.send_message("Owner only.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    fact = fact.strip()
    if not fact:
        await interaction.followup.send("Give me something to remember.", ephemeral=True)
        return
    data = await load_memory()
    if user:
        entry = data["users"].setdefault(str(user.id), {"name": user.display_name, "facts": []})
        entry["facts"].append(fact)
    else:
        data["facts"].append(fact)
    if await save_memory(data):
        await interaction.followup.send(f"Saved for {user.display_name if user else 'everyone'}.", ephemeral=True)
    else:
        await interaction.followup.send("Couldn't save that right now.", ephemeral=True)

@bot.tree.command(name="forget", description="Remove something San learned (owner only)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(number="Memory number, check with /memory", user="Forget a fact about this user")
async def forget_slash(interaction: discord.Interaction, number: int, user: discord.User | None = None):
    if not is_owner(interaction.user):
        await interaction.response.send_message("Owner only.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    data = await load_memory()
    facts = data["users"].get(str(user.id), {}).get("facts", []) if user else data["facts"]
    if not 1 <= number <= len(facts):
        await interaction.followup.send(f"Give a number from 1 to {len(facts)}. Check with /memory.", ephemeral=True)
        return
    removed = facts.pop(number - 1)
    if await save_memory(data):
        await interaction.followup.send(f"Forgot: {removed}", ephemeral=True)
    else:
        await interaction.followup.send("Couldn't save that right now.", ephemeral=True)

@bot.tree.command(name="memory", description="Show what San has learned")
@app_commands.describe(user="Show this user's remembered facts")
async def memory_slash(interaction: discord.Interaction, user: discord.User | None = None):
    await interaction.response.defer()
    data = await load_memory()
    target = user or interaction.user
    lines = []
    if data["facts"]:
        lines.append("General")
        lines.extend(f"{i}. {fact}" for i, fact in enumerate(data["facts"], 1))
    entry = data["users"].get(str(target.id))
    if entry and (entry.get("facts") or entry.get("tone")):
        lines.append(entry.get("name", "User"))
        lines.extend(f"{i}. {fact}" for i, fact in enumerate(entry.get("facts", []), 1))
        if entry.get("tone"):
            lines.append(f"Style: {entry['tone']}")
    if not lines:
        await interaction.followup.send("Nothing learned yet.")
        return
    chunks = split_message("\n".join(lines))
    await interaction.followup.send(chunks[0])
    for chunk in chunks[1:]:
        await interaction.followup.send(chunk)

@bot.tree.command(name="write", description="Post a message as San (owner only)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(message="Exact message to post", channel="Channel to post in (defaults to here)", role="Role to ping", release="Format as a release post")
async def write_slash(interaction: discord.Interaction, message: str, channel: discord.TextChannel | None = None, role: discord.Role | None = None, release: bool = False):
    if not is_owner(interaction.user):
        await interaction.response.send_message("Owner only.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    text = message.strip()
    if not text:
        await interaction.followup.send("Give me a message to post.", ephemeral=True)
        return
    mention = role.mention if role else ""
    chunks = split_message(text, 3900)
    target = channel or interaction.channel
    try:
        first = None
        for index, chunk in enumerate(chunks):
            embed = discord.Embed(description=chunk, color=discord.Color.gold() if release else discord.Color.blurple())
            if index == 0 and release:
                embed.title = "Sanin update"
            sent = await target.send(content=mention if index == 0 and mention else None, embed=embed)
            if first is None:
                first = sent
        await interaction.followup.send(f"Posted to {target.mention}: {first.jump_url}", ephemeral=True)
    except Exception as e:
        logging.warning(f"/write failed: {e}")
        await interaction.followup.send("Couldn't post that. Check my permissions in the channel.", ephemeral=True)

@bot.tree.command(name="tone", description="Set a user's remembered conversation style (owner only)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(description="How should San talk to this user?", user="User to set the style for")
async def tone_slash(interaction: discord.Interaction, description: str, user: discord.User | None = None):
    if not is_owner(interaction.user):
        await interaction.response.send_message("Owner only.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    description = description.strip()
    if not description:
        await interaction.followup.send("Give me a style to remember.", ephemeral=True)
        return
    target = user or interaction.user
    data = await load_memory()
    entry = data["users"].setdefault(str(target.id), {"name": target.display_name, "facts": [], "tone": ""})
    entry["tone"] = description
    if await save_memory(data):
        await interaction.followup.send(f"Saved style for {target.display_name}.", ephemeral=True)
    else:
        await interaction.followup.send("Couldn't save that right now.", ephemeral=True)

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
