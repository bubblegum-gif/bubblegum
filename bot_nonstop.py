
import feedparser, random, asyncio, requests, os, textwrap, json, pathlib, re, html
from datetime import datetime
import edge_tts
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont

RSS_FEEDS = [
    "https://www.huffpost.com/section/weird-news/feed",
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.reddit.com/r/nextfuckinglevel/top/.rss?t=day",
    "https://www.reddit.com/r/interestingasfuck/top/.rss?t=day",
    "https://www.reddit.com/r/ThatsInsane/top/.rss?t=day",
]

HOOKS = ["OKAY THIS IS INSANE","Stop scrolling - you need to see this","No way this actually happened","POV: the news just broke the internet","This is straight out of a movie","Breaking - this is wild"]
USED_FILE = "used_news.json"
OUTPUT_DIR = "output_videos"
pathlib.Path(OUTPUT_DIR).mkdir(exist_ok=True)

def load_used():
    if pathlib.Path(USED_FILE).exists():
        try:
            return set(json.loads(pathlib.Path(USED_FILE).read_text()))
        except:
            return set()
    return set()
def save_used(link):
    used = load_used()
    used.add(link)
    if len(used) > 500:
        used = set(list(used)[-500:])
    pathlib.Path(USED_FILE).write_text(json.dumps(list(used)))

def get_fresh_news():
    random.shuffle(RSS_FEEDS)
    used = load_used()
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:15]:
                link = getattr(entry, 'link', entry.title)
                if link not in used and len(entry.title) > 15:
                    return entry
        except:
            continue
    return None

def clean_text_SUPER(text):
    """SUPER siivous - poistaa KAIKKI koodit"""
    if not text:
        return ""
    # 1. HTML unescape &#32; -> välilyönti, &amp; -> and jne
    text = html.unescape(text)
    # 2. Poista kaikki HTML tagit <a href...>, <img...>, <table> jne
    text = re.sub(r'<[^>]+>', ' ', text)
    # 3. Poista Reddit roskat: /u/username, /r/subreddit, [link], [comments], submitted by
    text = re.sub(r'/u/\w+', '', text)
    text = re.sub(r'/r/\w+', '', text)
    text = re.sub(r'\[link\]', '', text, flags=re.I)
    text = re.sub(r'\[comments\]', '', text, flags=re.I)
    text = re.sub(r'submitted by.*', '', text, flags=re.I)
    text = re.sub(r'https?://\S+', '', text)  # poista linkit
    text = re.sub(r'&#\d+;?', ' ', text)  # &#32; jäänteet
    text = re.sub(r'&[a-z]+;?', ' ', text)  # &amp; jäänteet
    # 4. Siisti välit
    text = re.sub(r'\s+', ' ', text).strip()
    # 5. Jos vieläkin pitkä ja roskainen, ota vain ensimmäinen lause
    if len(text) > 250 or "u/" in text.lower() or "r/" in text.lower():
        sentences = text.split('.')
        text = sentences[0] if sentences else text
    return text[:250]

def extract_real_image_from_entry(entry):
    try:
        if hasattr(entry, 'summary'):
            m = re.search(r'src="(https://preview\.redd\.it/[^"]+)"', entry.summary)
            if m:
                return m.group(1)
            m2 = re.search(r'src="(https://i\.redd\.it/[^"]+)"', entry.summary)
            if m2:
                return m2.group(1)
        if hasattr(entry, 'media_content'):
            for mc in entry.media_content:
                if 'url' in mc:
                    return mc['url']
        if hasattr(entry, 'media_thumbnail'):
            for mt in entry.media_thumbnail:
                if 'url' in mt:
                    return mt['url']
    except:
        pass
    return None

def search_pexels_image(query, api_key):
    try:
        if not api_key:
            return None
        headers = {"Authorization": api_key}
        q = query[:80]
        url = f"https://api.pexels.com/v1/search?query={requests.utils.quote(q)}&per_page=3&orientation=portrait"
        r = requests.get(url, headers=headers, timeout=15).json()
        if 'photos' in r and len(r['photos']) > 0:
            return r['photos'][0]['src']['large2x']
    except Exception as e:
        print(f"Pexels fail: {e}")
    return None

def make_script_CLEAN(title, summary):
    title_clean = clean_text_SUPER(title)
    summary_clean = clean_text_SUPER(summary)
    
    # Jos summary on vieläkin roskaa tai liian lyhyt, käytä vain titleä ja keksi lisä
    if len(summary_clean) < 20 or "&#" in summary_clean or "/u/" in summary_clean:
        summary_clean = f"people are freaking out about this house in Istanbul. It looks normal but something crazy is happening inside"
    
    hook = random.choice(HOOKS)
    script = f"{hook}! {title_clean}. So basically {summary_clean}. What would YOU do? Follow for more bubblegum news!"
    # Viimeinen siivous scriptille
    script = re.sub(r'[^\w\s\!\?\.\,\-]', ' ', script)
    script = re.sub(r'\s+', ' ', script)
    return script[:380]

async def tts_free(text, output):
    voice = "en-US-JennyNeural"
    communicate = edge_tts.Communicate(text, voice, rate="+10%")
    await communicate.save(output)
    return output

def get_image_for_news(title, summary, entry, output):
    api_key = os.environ.get('PEXELS_API_KEY')
    # 1. Oikea kuva
    real_url = extract_real_image_from_entry(entry)
    if real_url:
        try:
            r = requests.get(real_url, timeout=20, headers={'User-Agent':'Mozilla/5.0'})
            if r.status_code == 200 and len(r.content) > 10000:
                pathlib.Path(output).write_bytes(r.content)
                print("1. Oikea kuva uutisesta")
                return output
        except:
            pass
    # 2. Pexels
    if api_key:
        # Hae talo Istanbulista jne
        places = re.findall(r'\b(?:Istanbul|house|building|river|lake|brothers|city)\b', title, re.I)
        term = " ".join(places[:2]) if places else clean_text_SUPER(title)[:30]
        pexels_url = search_pexels_image(term, api_key)
        if pexels_url:
            try:
                r = requests.get(pexels_url, timeout=20)
                if r.status_code == 200:
                    pathlib.Path(output).write_bytes(r.content)
                    print(f"2. PEXELS: {term}")
                    return output
            except:
                pass
    # 3. Fallback AI realistinen
    prompt = f"real photo documentary of {clean_text_SUPER(title)[:60]}, photojournalism, 8k vertical"
    safe = requests.utils.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{safe}?width=1080&height=1920&nologo=true&model=turbo&seed={random.randint(1,999999)}"
    r = requests.get(url, timeout=40)
    pathlib.Path(output).write_bytes(r.content)
    return output

def add_caption_bar(image_path, script):
    img = Image.open(image_path).convert("RGB")
    img = img.resize((1080, 1920), Image.LANCZOS)
    overlay = Image.new('RGBA', (1080, 500), (0,0,0,190))
    img_rgba = img.convert("RGBA")
    img_rgba.paste(overlay, (0, 1920-500), overlay)
    top = Image.new('RGBA', (1080, 110), (0,0,0,160))
    img_rgba.paste(top, (0,0), top)
    draw = ImageDraw.Draw(img_rgba)
    wrapped = textwrap.fill(script, width=32)
    try:
        fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
        fs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    except:
        fb = fs = ImageFont.load_default()
    draw.text((30, 25), "BUBBLEGUM VIRALS", fill=(255,255,255), font=fb, stroke_width=3, stroke_fill=(0,0,0))
    draw.text((35, 1420), wrapped, fill=(255,255,255), font=fs, stroke_width=3, stroke_fill=(0,0,0))
    img_rgba.convert("RGB").save(image_path)
    return image_path

def make_video_REAL_MOVING(image_path, audio_path, output):
    audio = AudioFileClip(audio_path)
    duration = max(audio.duration, 8)
    base = ImageClip(image_path).set_duration(duration)
    clip = base.resize(lambda t: 1.0 + 0.6 * t / duration).set_position(lambda t: ('center', 80 + 60*t/duration))
    clip = clip.resize(height=2200).crop(x_center=540, y_center=960, width=1080, height=1920).set_fps(30)
    final = clip.set_audio(audio)
    final.write_videofile(output, codec='libx264', audio_codec='aac', fps=30, preset='ultrafast', logger=None)
    return output

def try_youtube_upload(video_path, title):
    try:
        token_json = os.environ.get('YOUTUBE_TOKEN_JSON')
        if not token_json:
            return False
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        creds = Credentials.from_authorized_user_info(json.loads(token_json), ['https://www.googleapis.com/auth/youtube.upload'])
        youtube = build('youtube', 'v3', credentials=creds)
        body = {"snippet": {"title": f"{clean_text_SUPER(title)[:60]}?! #shorts", "description": f"{clean_text_SUPER(title)}\n\n#shorts", "tags": ["shorts","viral"], "categoryId": "24"}, "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
        media = MediaFileUpload(video_path, mimetype='video/mp4', resumable=True)
        resp = youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
        print(f"YOUTUBE UPLOADED: https://youtube.com/watch?v={resp['id']}")
        return True
    except Exception as e:
        print(f"YouTube skip: {e}")
        return False

async def generate_one_video():
    news = get_fresh_news()
    if not news:
        print("Ei uutta uutista")
        return None
    raw_title = news.title
    raw_summary = getattr(news, 'summary', raw_title)
    
    title = clean_text_SUPER(raw_title)
    summary = clean_text_SUPER(raw_summary)
    script = make_script_CLEAN(raw_title, raw_summary)
    
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    img_path = f"{OUTPUT_DIR}/frame_{ts}.png"
    voice_path = f"{OUTPUT_DIR}/voice_{ts}.mp3"
    video_path = f"{OUTPUT_DIR}/bubblegum_{ts}.mp4"
    print(f"--- V6 CLEAN ---\\nUutinen RAW: {raw_title[:100]}\\nSiivottu: {title}\\nScript: {script}")
    get_image_for_news(raw_title, raw_summary, news, img_path)
    add_caption_bar(img_path, script)
    await tts_free(script, voice_path)
    make_video_REAL_MOVING(img_path, voice_path, video_path)
    save_used(getattr(news, 'link', raw_title))
    try:
        os.remove(img_path)
        os.remove(voice_path)
    except:
        pass
    try_youtube_upload(video_path, title)
    print(f"VALMIS: {video_path}")
    return video_path

if __name__ == "__main__":
    asyncio.run(generate_one_video())

