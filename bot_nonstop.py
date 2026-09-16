
import feedparser, random, asyncio, requests, os, time, textwrap, json, pathlib, re
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
    "https://feeds.yle.fi/uutiset/v1/majorHeadlines/YLE_UUTISET.rss",
    "https://www.is.fi/rss/tuoreimmat/"
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

def clean_text(text):
    text = re.sub(r'<[^<]+?>', '', text)
    text = text.replace("&amp;", " and ").replace("&quot;", "").replace("&#39;", "'")
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def make_prompt_from_news(title, summary):
    clean = clean_text(title + " " + summary).lower()
    styles = [
        "funny parody, exaggerated meme style, absurd humor",
        "dramatic breaking news, cinematic lighting, shocked expression",
        "cute kawaii chibi, pastel bubblegum world, 3d pixar render",
        "viral tiktok style, ultra cute, big eyes, funny"
    ]
    style = random.choice(styles)
    if any(x in clean for x in ["house","home","building","istanbul","apartment","city","room"]):
        base = f"bubblegum cute house with big kawaii eyes in {clean[:50]}, {style}, pink roof, shocked house"
    elif any(x in clean for x in ["cat","dog","bear","animal","bird","puppy","kitten"]):
        base = f"hero bubblegum {clean[:40]} animal wearing superhero cape, {style}, saving the day"
    elif any(x in clean for x in ["car","plane","rocket","crash","explosion"]):
        base = f"bubblegum {clean[:50]} in pink pastel world, {style}, funny explosion of bubbles"
    elif any(x in clean for x in ["elon","trump","biden","musk","celebrity","man","woman","person"]):
        base = f"bubblegum chibi parody of {clean[:50]}, pink bob hair, big blue eyes, {style}, NOT photorealistic, cute caricature"
    else:
        base = f"bubblegum viral news illustration: {title[:80]}, {style}, pink and purple pastel, ultra cute 3d"
    final_prompt = f"{base}, bubblegum 3d character, kawaii, 1080x1920 vertical, pastel purple background, soft lighting, no text, no watermark"
    return final_prompt

def make_script(title, summary):
    clean = clean_text(summary)[:180]
    title_clean = clean_text(title)
    hook = random.choice(HOOKS)
    script = f"{hook}! {title_clean}. So basically {clean}. What would YOU do? Follow for more bubblegum news!"
    return script[:380]

async def tts_free(text, output):
    voice = "en-US-JennyNeural"
    communicate = edge_tts.Communicate(text, voice, rate="+10%")
    await communicate.save(output)
    return output

def make_image_free(news_title, news_summary, output):
    prompt = make_prompt_from_news(news_title, news_summary)
    print(f"PROMPT: {prompt}")
    safe = requests.utils.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{safe}?width=1080&height=1920&nologo=true&model=flux&seed={random.randint(1,999999)}"
    try:
        r = requests.get(url, timeout=50)
        r.raise_for_status()
        pathlib.Path(output).write_bytes(r.content)
    except Exception as e:
        print(f"Image API fail {e}, fallback")
        img = Image.new('RGB', (1080, 1920), color=(255, 182, 218))
        ImageDraw.Draw(img).ellipse([200, 400, 880, 1080], fill=(255,107,205))
        img.save(output)
    return output

def add_caption_bar(image_path, script):
    img = Image.open(image_path).convert("RGBA")
    w, h = img.size
    overlay = Image.new('RGBA', (w, 420), (255, 107, 205, 235))
    img.paste(overlay, (0, h-420), overlay)
    top_overlay = Image.new('RGBA', (w, 100), (0,0,0,120))
    img.paste(top_overlay, (0, 0), top_overlay)
    draw = ImageDraw.Draw(img)
    wrapped = textwrap.fill(script, width=28)
    try:
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38)
    except:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()
    draw.text((30, 20), "BUBBLEGUM VIRALS", fill=(255,255,255), font=font_big, stroke_width=3, stroke_fill=(0,0,0))
    draw.text((40, h-380), wrapped, fill=(255,255,255), font=font_small, stroke_width=3, stroke_fill=(50,0,50))
    img.save(image_path)
    return image_path

def make_video_MOVING(image_path, audio_path, output):
    audio = AudioFileClip(audio_path)
    duration = audio.duration
    def zoom(t):
        return 1.0 + 0.18 * (t / duration) + 0.02 * (t % 1)
    clip = ImageClip(image_path).set_duration(duration).resize(lambda t: zoom(t)).set_position(('center','center'))
    clip = clip.resize(height=1920).set_position(('center','center')).crop(x_center=540, y_center=960, width=1080, height=1920)
    final = clip.set_audio(audio).set_fps(24)
    final.write_videofile(output, codec='libx264', audio_codec='aac', fps=24, preset='ultrafast', logger=None)
    return output

def try_youtube_upload(video_path, title):
    try:
        token_json = os.environ.get('YOUTUBE_TOKEN_JSON')
        if not token_json:
            print("YOUTUBE_TOKEN_JSON puuttuu - skipataan auto-upload (video tallennettu artifactsiin)")
            return False
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        creds = Credentials.from_authorized_user_info(json.loads(token_json), ['https://www.googleapis.com/auth/youtube.upload'])
        youtube = build('youtube', 'v3', credentials=creds)
        yt_title = f"{title[:60]}?! 😱 #shorts"
        desc = f"{title}\n\nThis bubblegum viral story is insane! 🤯\n\n#shorts #viral #news #bubblegumvirals\n\nSource: RSS News\n@bubblegum-r2w\n"
        body = {
            "snippet": {"title": yt_title[:100], "description": desc[:5000], "tags": ["shorts","viral","news","funny"], "categoryId": "24"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
        }
        media = MediaFileUpload(video_path, mimetype='video/mp4', resumable=True)
        req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        resp = req.execute()
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
    title = clean_text(news.title)
    summary = clean_text(getattr(news, 'summary', title))
    script = make_script(title, summary)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    img_path = f"{OUTPUT_DIR}/frame_{timestamp}.png"
    voice_path = f"{OUTPUT_DIR}/voice_{timestamp}.mp3"
    video_path = f"{OUTPUT_DIR}/bubblegum_{timestamp}.mp4"
    print(f"--- UUSI VIDEO v3 ---\\nUutinen: {title}\\nScript: {script}")
    make_image_free(title, summary, img_path)
    add_caption_bar(img_path, script)
    await tts_free(script, voice_path)
    make_video_MOVING(img_path, voice_path, video_path)
    save_used(getattr(news, 'link', title))
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

