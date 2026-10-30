import os
from pathlib import Path
from datetime import datetime
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

# --- Step 1: Auth ---
youtube_api_key = os.environ.get("youtube_api")  # replace with your actual secret name
if not youtube_api_key:
    raise ValueError("YouTube API key not found. Check the secret name and restart your Studio session.")

youtube = build("youtube", "v3", developerKey=youtube_api_key)

# --- Step 2: Resolve the channel handle to a channel ID ---
channel_handle = "NorthLiberty"  # replace with the actual handle, no @ symbol

channel_response = youtube.channels().list(
    part="contentDetails",
    forHandle=channel_handle
).execute()

channel_id = channel_response["items"][0]["id"]
uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

print(f"Channel ID: {channel_id}")
print(f"Uploads playlist ID: {uploads_playlist_id}")

# --- Step 3: Page through the uploads playlist, filtering by date ---
cutoff_date = datetime.strptime("20260101", "%Y%m%d")
filtered_videos = []
next_page_token = None

while True:
    playlist_response = youtube.playlistItems().list(
        part="snippet",
        playlistId=uploads_playlist_id,
        maxResults=50,
        pageToken=next_page_token
    ).execute()

    stop = False
    for item in playlist_response["items"]:
        published_at = datetime.strptime(
            item["snippet"]["publishedAt"], "%Y-%m-%dT%H:%M:%SZ"
        )
        if published_at < cutoff_date:
            stop = True
            break

        video_id = item["snippet"]["resourceId"]["videoId"]
        title = item["snippet"]["title"]
        filtered_videos.append({"id": video_id, "title": title, "published": published_at})
        print(f"Included: {title} ({published_at.date()})")

    if stop or "nextPageToken" not in playlist_response:
        break
    next_page_token = playlist_response["nextPageToken"]

print(f"\nTotal videos to process: {len(filtered_videos)}")

import json
print(json.dumps(filtered_videos, default=str))

# --- Step 4: Fetch transcripts and save them into data/ ---
Path("data").mkdir(exist_ok=True)

successful = 0
failed = []

for video in filtered_videos[:3]:  # start small, remove [:3] once confirmed working
    video_id = video["id"]
    title = video["title"]

    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.fetch(video_id)
        full_text = " ".join(segment.text for segment in transcript_list)

        safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)[:80]
        filepath = Path("data") / f"video_{video_id}_{safe_title}.txt"

        filepath.write_text(
            f"Title: {title}\nPublished: {video['published'].date()}\nVideo ID: {video_id}\n\n{full_text}",
            encoding="utf-8"
        )
        successful += 1
        print(f"✅ Saved: {title}")

    except (TranscriptsDisabled, NoTranscriptFound):
        failed.append(title)
        print(f"⚠️ No transcript available: {title}")
    except Exception as e:
        failed.append(title)
        print(f"❌ Error on '{title}': {e}")

print(f"\nDone. {successful} transcripts saved, {len(failed)} failed.")
if failed:
    print("Failed videos:", failed)