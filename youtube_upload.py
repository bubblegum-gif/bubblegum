
import os, pathlib, json, random
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Lue token secretsistä
def get_youtube_client():
    token_json = os.environ.get('YOUTUBE_TOKEN_JSON')
    if not token_json:
        print("YOUTUBE_TOKEN_JSON puuttuu - skipataan auto-upload")
        return None
    creds = Credentials.from_authorized_user_info(json.loads(token_json), ['https://www.googleapis.com/auth/youtube.upload'])
    return build('youtube', 'v3', credentials=creds)

def upload_to_youtube(video_path, title, description, tags):
    try:
        youtube = get_youtube_client()
        if not youtube:
            return False
        
        # Turvallinen maksimi 3/päivä - YouTube tarkistaa
        body = {
            "snippet": {
                "title": title[:100],  # Shorts max 100 merkkiä
                "description": description[:5000],
                "tags": tags[:15],
                "categoryId": "24"  # Entertainment
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        }
        
        media = MediaFileUpload(video_path, mimetype='video/mp4', resumable=True)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = request.execute()
        print(f"YOUTUBE UPLOADED: https://youtube.com/watch?v={response['id']}")
        return True
    except Exception as e:
        print(f"YouTube upload virhe (quota täynnä tai token vanha): {e}")
        return False

def make_viral_meta(title_text):
    hooks = ["?! 😱", " NO WAY!", " - You Won't Believe This", " BREAKING"]
    viral_titles = [
        f"{title_text[:60].strip()}{random.choice(hooks)} #shorts",
        f"POV: {title_text[:50]} #shorts",
        f"{title_text[:55]} is INSANE #shorts"
    ]
    title = random.choice(viral_titles)
    desc = f"""{title_text}

This bubblegum viral story is insane! 🤯

#shorts #viral #news #bubblegumvirals #funny #wtf #breaking #trending

Source: RSS News
Follow for more bubblegum news daily!

Subscribe @bubblegum-r2w
"""
    tags = ["shorts","viral","news","funny","bubblegum","breaking","trending","wtf","omg"]
    return title, desc, tags
