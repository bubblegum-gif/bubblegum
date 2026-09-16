
import feedparser, random, asyncio, requests, os, time, textwrap, json, pathlib
from datetime import datetime
import edge_tts
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont

# ========== ASETUKSET - VAIN ILMAISET ==========
RSS_FEEDS = [
    "https://www.huffpost.com/section/weird-news/feed",
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.reddit.com/r/nextfuckinglevel/top/.rss?t=day",
    "https://www.reddit.com/r/interestingasfuck/top/.rss?t=day",
    "https://www.reddit.com/r/ThatsInsane/top/.rss?t=day",
    "https://feeds.yle.fi/uutiset/v1/majorHeadlines/YLE_UUTISET.rss",
    "https://www.is.fi/rss/tuoreimmat/"
]

HOOKS = [
    "OKAY THIS IS INSANE",
    "Stop scrolling - you need to see this",
    "No way this actually happened",
    "POV: the news just broke the internet",
    "This is straight out of a movie",
    "Breaking - this is wild"
]

USED_FILE = "used_news.json"
OUTPUT_DIR = "output_videos"
pathlib.Path(OUTPUT_DIR).mkdir(exist_ok=True)

def load_used():
    if pathlib.Path(USED_FILE).exists():
        return set(json.loads(pathlib.Path(USED_FILE).read_text()))
    return set()

def save_used(link):
    used = load_used()
    used.add(link)
    # Keep only last 500
    if len(used) > 500:
        used = set(list(used)[-500:])
    pathlib.Path(USED_FILE).write_text(json.dumps(list(used)))

def get_fresh_news():
    random.shuffle(RSS_FEEDS)
    used = load_used()
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:
                link = getattr(entry, 'link', entry.title)
                if link not in used and len(entry.title) > 15:
                    return entry
        except:
            continue
    return None

def make_script(title, summary):
    hook = random.choice(HOOKS)
    clean = summary[:200].replace("<p>","").replace("</p>","").replace("\n"," ")
    script = f"{hook}! {title}. So basically {clean}. What would YOU do? Follow for more bubblegum news!"
    return script[:380]

async def tts_free(text, output):
    voice = "en-US-JennyNeural" # ILMAINEN viral ääni
    communicate = edge_tts.Communicate(text, voice, rate="+10%")
    await communicate.save(output)
    return output

def make_image_free(news_text, output):
    prompt = f"cute pink bubblegum 3d character shocked, kawaii, pastel background, bubbles, 3d render, ultra cute, {news_text[:70]}"
    safe = requests.utils.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{safe}?width=1080&height=1920&nologo=true&model=flux"
    try:
        r = requests.get(url, timeout=40)
        r.raise_for_status()
        pathlib.Path(output).write_bytes(r.content)
    except Exception as e:
        print(f"Image API fail {e}, using fallback")
        img = Image.new('RGB', (1080, 1920), color=(255, 182, 218))
        ImageDraw.Draw(img).ellipse([200, 400, 880, 1080], fill=(255,107,205))
        img.save(output)
    return output

def add_caption_bar(image_path, script):
    img = Image.open(image_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    # Bubblegum bar
    overlay = Image.new('RGBA', (1080, 500), (255, 107, 205, 230))
    img.paste(overlay, (0, 1420), overlay)
    wrapped = textwrap.fill(script, width=30)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 44)
    except:
        font = ImageFont.load_default()
    draw.text((40, 1450), wrapped, fill=(255,255,255), font=font, stroke_width=3, stroke_fill=(50,0,50))
    # Add branding
    draw.text((30, 30), "BUBBLEGUM VIRALS", fill=(255,255,255), font=font, stroke_width=2, stroke_fill=(0,0,0))
    img.save(image_path)
    return image_path

def make_video(image_path, audio_path, output):
    audio = AudioFileClip(audio_path)
    duration = audio.duration
    # Ensure min 22 sec for monetization, loop image if needed
    if duration < 22:
        duration = 22
    image = ImageClip(image_path).set_duration(duration).set_fps(30).resize((1080,1920))
    final = image.set_audio(audio.set_duration(duration))
    final.write_videofile(output, codec='libx264', audio_codec='aac', fps=30, logger=None)
    return output

async def generate_one_video():
    news = get_fresh_news()
    if not news:
        print("Ei uutta uutista, odotetaan...")
        return None
    title = news.title
    summary = getattr(news, 'summary', title)
    script = make_script(title, summary)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    img_path = f"{OUTPUT_DIR}/frame_{timestamp}.png"
    voice_path = f"{OUTPUT_DIR}/voice_{timestamp}.mp3"
    video_path = f"{OUTPUT_DIR}/bubblegum_{timestamp}.mp4"
    
    print(f"\n--- UUSI VIDEO ---\nUutinen: {title}\nScript: {script}")
    make_image_free(title, img_path)
    add_caption_bar(img_path, script)
    await tts_free(script, voice_path)
    make_video(img_path, voice_path, video_path)
    
    save_used(getattr(news, 'link', title))
    # Delete temp
    try:
        os.remove(img_path)
        os.remove(voice_path)
    except:
        pass
    print(f"VALMIS: {video_path}")
    return video_path

async def loop_nonstop():
    print("🍬 BUBBLEGUM NON-STOP LOOP KÄYNNISTETTY - ILMAINEN")
    print("Paina CTRL+C lopettaaksesi")
    count = 0
    while True:
        try:
            result = await generate_one_video()
            if result:
                count += 1
                print(f"Videoita tehty tässä sessiossa: {count}")
                # TikTok raja: max 1 video / 90 min ettei shadowbannaa
                # Voit muuttaa 5400 sekuntia pienemmäksi testauksessa
                print("Odotetaan 90 minuuttia seuraavaan (monetisointi-turvallinen)...")
                # TESTAUKSESSA: 60 sekuntia, TUOTANNOSSA: 5400 sekuntia
                await asyncio.sleep(90)  # <-- VAIHDA TÄMÄ 5400 TUOTANTOON
            else:
                await asyncio.sleep(300)
        except KeyboardInterrupt:
            print("Loop lopetettu")
            break
        except Exception as e:
            print(f"Virhe: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    # Jos haluat vain 1 videon: asyncio.run(generate_one_video())
    # Jos haluat NON-STOP: asyncio.run(loop_nonstop())
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--loop":
        asyncio.run(loop_nonstop())
    else:
        asyncio.run(generate_one_video())
