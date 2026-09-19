import os
from pathlib import Path
from datetime import datetime
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

Path("data").mkdir(exist_ok=True)

successful = 0
failed = []

for video in filtered_videos:
    video_id = video["id"]
    title = video["title"]

    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        full_text = " ".join(segment["text"] for segment in transcript_list)

        # Sanitize title for use as a filename
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