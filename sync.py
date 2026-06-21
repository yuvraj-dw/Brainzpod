import os
import re
import json
import shutil
import requests
import subprocess
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding="utf-8")
import argparse
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.theme import Theme

console = Console(theme=Theme({
    "info": "cyan",
    "warning": "yellow",
    "danger": "bold red",
    "success": "bold green"
}))

from mutagen.id3 import TPE2
from mutagen.id3 import (
    ID3,
    TIT2,
    TPE1,
    TALB,
    TCON,
    TYER,
    APIC,
)
from mutagen.mp4 import MP4, MP4Cover
import base64
from pyDes import des, ECB, PAD_PKCS5


CONFIG = json.load(open("config.json"))

LB_USER = CONFIG["listenbrainz_user"]
MUSIC_DIR = Path(CONFIG["music_dir"])
BAD_WORDS = [x.lower() for x in CONFIG["bad_words"]]

HEADERS = {
    "User-Agent": "ListenBrainzSync/1.0"
}


def sanitize(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)


def get_playlists():
    url = f"https://api.listenbrainz.org/1/user/{LB_USER}/playlists/createdfor"

    r = requests.get(url, headers=HEADERS)

    if r.status_code != 200:
        print("Failed to fetch playlists")
        return []

    data = r.json()

    playlists = []

    for item in data["playlists"]:

        playlist = item["playlist"]

        title = playlist["title"]

        identifier = playlist["identifier"]

        playlists.append({
            "title": title,
            "id": identifier.split("/")[-1]
        })

    return playlists


def get_tracks(playlist_id):
    url = f"https://api.listenbrainz.org/1/playlist/{playlist_id}"

    r = requests.get(url, headers=HEADERS)

    if r.status_code != 200:
        print(f"Failed to fetch tracks for {playlist_id}")
        return []

    data = r.json()

    tracks = []

    playlist = data.get("playlist", {})

    for t in playlist.get("track", []):

        artist = t.get("creator", "").strip()
        title = t.get("title", "").strip()

        if not artist or not title:
            continue

        tracks.append({
            "artist": artist,
            "title": title
        })

    return tracks

def get_youtube_tracks(url):
    console.print(f"  [info]Parsing YouTube Playlist:[/info] {url}")
    cmd = ["yt-dlp", "--flat-playlist", "--dump-json", url]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    
    if result.returncode != 0:
        console.print("[danger]Failed to fetch YouTube playlist[/danger]")
        return "", []
        
    lines = [line for line in result.stdout.split('\n') if line.strip()]
    tracks = []
    playlist_title = "YouTube Playlist"
    
    for line in lines:
        try:
            data = json.loads(line)
            if not tracks and "playlist_title" in data:
                playlist_title = data["playlist_title"]
            
            title = data.get("title", "").strip()
            artist = data.get("uploader", "").strip()
            if title and title != "[Private video]" and title != "[Deleted video]":
                tracks.append({"title": title, "artist": artist})
        except:
            pass
            
    return playlist_title, tracks

def get_apple_music_tracks(url):
    console.print(f"  [info]Parsing Apple Music Playlist:[/info] {url}")
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    r.encoding = 'utf-8'
    import html
    import json
    playlist_title = "Apple Music Playlist"
    tracks = []
    
    title_match = re.search(r'<meta property="og:title" content="([^"]+)"', r.text)
    if title_match:
        t = html.unescape(title_match.group(1).strip())
        t = t.split(" by ")[0]
        playlist_title = t.replace("\u200e", "").strip()
        
    match = re.search(r'<script type="application/json" id="serialized-server-data">(.*?)</script>', r.text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            
            def extract_songs(obj):
                if isinstance(obj, dict):
                    # Check if it's a song
                    if "artistName" in obj and "playAction" in obj:
                        title = obj.get("title") or obj.get("trackName")
                        artist = obj.get("artistName")
                        if title and artist:
                            tracks.append({"title": html.unescape(title), "artist": html.unescape(artist)})
                    for v in obj.values():
                        extract_songs(v)
                elif isinstance(obj, list):
                    for i in obj:
                        extract_songs(i)
                        
            extract_songs(data)
            
            # Deduplicate while preserving order
            seen = set()
            dedup = []
            for t in tracks:
                k = (t["title"], t["artist"])
                if k not in seen:
                    dedup.append(t)
                    seen.add(k)
            tracks = dedup
        except Exception as e:
            console.print(f"[danger]Apple Music JSON Parse Error:[/danger] {e}")
            
    return playlist_title, tracks

def get_spotify_tracks(url):
    console.print(f"  [info]Parsing Spotify Playlist:[/info] {url}")
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    r.encoding = 'utf-8'
    import html
    playlist_title = "Spotify Playlist"
    tracks = []
    
    title_match = re.search(r'<meta property="og:title" content="([^"]+)"', r.text)
    if title_match:
        playlist_title = html.unescape(title_match.group(1).strip())
        
    rows = r.text.split('data-testid="track-row"')
    for row in rows[1:]:
        # Track title is inside the link to the track itself:
        # href="/track/..." ... ><span ...>TRACK NAME</span>
        t_match = re.search(r'href="/track/[^"]+".*?<span[^>]*>([^<]+)</span>', row)
        a_match = re.search(r'href="/artist/[^"]+">([^<]+)</a>', row)
        if t_match and a_match:
            tracks.append({
                "title": html.unescape(t_match.group(1)),
                "artist": html.unescape(a_match.group(1))
            })
            
    return playlist_title, tracks

def get_jiosaavn_tracks(url):
    console.print(f"  [info]Parsing JioSaavn Playlist:[/info] {url}")
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    r.encoding = 'utf-8'
    import html
    playlist_title = "JioSaavn Playlist"
    tracks = []
    
    title_match = re.search(r'<meta property="og:title" content="([^"]+)"', r.text)
    if title_match:
        t = html.unescape(title_match.group(1).strip())
        t = t.split(" | ")[0]
        playlist_title = t.strip()
        
    # Search for INITIAL_DATA
    match = re.search(r'window\.__INITIAL_DATA__\s*=\s*(.*?});', r.text, re.DOTALL)
    if not match:
        match = re.search(r'window\.__INITIAL_DATA__\s*=\s*(\{.*?\})\n', r.text)
        
    if match:
        try:
            json_str = match.group(1).strip()
            if json_str.endswith('});'):
                json_str = json_str[:-2]
            data = json.loads(json_str)
            playlist = data.get('playlist', {}).get('playlist', {})
            if "title" in playlist:
                 playlist_title = playlist["title"]
            for t in playlist.get('list', []):
                tracks.append({
                    "title": html.unescape(t.get('title', '')),
                    "artist": html.unescape(t.get('subtitle', ''))
                })
        except:
            pass
            
    # HTML Parsing fallback
    if not tracks:
        articles = re.findall(r'<article class="o-snippet o-snippet--draggable".*?</article>', r.text, re.DOTALL)
        for art in articles:
            t_match = re.search(r'href="/song/[^"]+">([^<]+)</a>', art)
            if not t_match:
                continue
            title = html.unescape(t_match.group(1).strip())
            
            a_matches = re.findall(r'href="/artist/[^"]+">\s*(?:<!--.*?-->)?\s*([^<]+)</a>', art)
            artist = html.unescape(", ".join([a.strip() for a in a_matches]))
            tracks.append({"title": title, "artist": artist})
            
    return playlist_title, tracks


def enrich_metadata(track):
    query = f"{track['title']} {track['artist']}"

    url = "https://itunes.apple.com/search"

    params = {
        "term": query,
        "entity": "song",
        "limit": 1
    }

    try:
        r = requests.get(url, params=params)
        data = r.json()

        if data["resultCount"] > 0:
            item = data["results"][0]

            track["album"] = item.get("collectionName")
            track["genre"] = item.get("primaryGenreName")
            track["year"] = item.get("releaseDate", "")[:4]
            track["duration"] = item.get("trackTimeMillis", 0) / 1000.0

            art = item.get("artworkUrl100")

            if art:
                track["cover_url"] = art.replace(
                    "100x100",
                    "1000x1000"
                )

    except Exception as e:
        print("Metadata fetch failed:", e)

    return track


def is_bad_result(text):
    text = text.lower()

    for word in BAD_WORDS:
        if word in text:
            return True

    return False


def search_jiosaavn(query):
    url = "https://www.jiosaavn.com/api.php"
    params = {
        "__call": "search.getResults",
        "q": query,
        "p": 1,
        "n": 5,
        "_format": "json",
        "_marker": 0
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=20)
        if r.status_code == 200:
            data = r.json()
            results = data.get("results", [])
            if results:
                return results[0]
    except Exception as e:
        print("JioSaavn search failed:", e)
    return None

def get_dec_url(enc_url):
    des_cipher = des(b"38346591", ECB, b"\0\0\0\0\0\0\0\0", pad=None, padmode=PAD_PKCS5)
    enc_url = base64.b64decode(enc_url.strip())
    dec_url = des_cipher.decrypt(enc_url, padmode=PAD_PKCS5).decode("utf-8")
    dec_url = dec_url.replace("_96.mp4", "_320.mp4")
    return dec_url

def download_song(track, outdir):
    artist = track["artist"]
    title = track["title"]

    query = f"{title} {artist} official audio"

    console.print(f"  [info]Searching JioSaavn:[/info] {title}")
    saavn_result = search_jiosaavn(title)
    
    import html
    if saavn_result:
        expected_duration = track.get("duration", 0)
        saavn_duration = int(saavn_result.get("duration", 0))
        
        is_duration_match = True
        if expected_duration > 0 and saavn_duration > 0:
            if abs(expected_duration - saavn_duration) > 20:
                is_duration_match = False
                console.print(f"  [warning]Duration mismatch! Expected {expected_duration:.0f}s, got {saavn_duration}s. Falling back to yt-dlp.[/warning]")
                
        if is_duration_match:
            # Only overwrite title and artist if we don't already have a valid artist. 
            # (If we have an artist, it means iTunes or the user provided clean, reliable metadata)
            if "song" in saavn_result and not track.get("artist"):
                track["title"] = html.unescape(saavn_result["song"])
            if "primary_artists" in saavn_result and not track.get("artist"):
                track["artist"] = html.unescape(saavn_result["primary_artists"])
            
            # Prioritize iTunes/existing metadata for Album, Year, and Cover 
            # because JioSaavn search often returns singles or compilation albums instead of the original album.
            if "album" in saavn_result and not track.get("album"):
                track["album"] = html.unescape(saavn_result["album"])
            if "year" in saavn_result and not track.get("year"):
                track["year"] = saavn_result["year"]
            if "image" in saavn_result and not track.get("cover_url"):
                cover_url = re.sub(r'-\d+x\d+\.(jpg|webp)', '-500x500.jpg', saavn_result["image"])
                track["cover_url"] = cover_url
        else:
            saavn_result = None

    safe_name = sanitize(track["title"])

    final_mp3 = outdir / f"{safe_name}.mp3"

    if final_mp3.exists():
        console.print(f"  [dim]Skipping existing:[/dim] {safe_name}")
        return final_mp3

    if saavn_result and "encrypted_media_url" in saavn_result:
        try:
            console.print("  [info]Downloading from JioSaavn...[/info]")
            dec_url = get_dec_url(saavn_result["encrypted_media_url"])
            
            # Use ffmpeg to download the stream and convert directly to mp3
            cmd = [
                "ffmpeg",
                "-y",
                "-i", dec_url,
                "-vn",
                "-c:a", "libmp3lame",
                "-q:a", "0",
                str(final_mp3)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )
            
            if result.returncode == 0 and final_mp3.exists():
                return final_mp3
            else:
                console.print("  [warning]JioSaavn download failed, falling back to yt-dlp[/warning]")
        except Exception as e:
            console.print(f"  [danger]JioSaavn processing failed:[/danger] {e}")
            console.print("  [warning]Falling back to yt-dlp[/warning]")

    console.print(f"  [info]Searching YouTube:[/info] {query}")

    cmd = [
        "yt-dlp",

        f"ytsearch1:{query}",

        "--extract-audio",

        "--audio-format",
        "mp3",

        "--audio-quality",
        "0",

        "--embed-thumbnail",
        "--embed-metadata",

        "--no-playlist",

        "--output",
        str(outdir / f"{safe_name}.%(ext)s")
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore"
    )

    if result.returncode != 0:
        print("yt-dlp failed")
        print(result.stderr[:1000])
        return None

    if final_mp3.exists():
        return final_mp3

    print("MP3 not found after download")
    return None


def embed_metadata(file_path, track):
    file_str = str(file_path)
    if file_str.endswith(".mp4") or file_str.endswith(".m4a"):
        try:
            audio = MP4(file_path)
        except:
            print("Could not load MP4 tags")
            return
            
        if track.get("title"):
            audio["\xa9nam"] = track["title"]
        if track.get("artist"):
            audio["\xa9ART"] = track["artist"]
        
        album_artist = track.get("album_artist", track.get("artist"))
        if album_artist:
            audio["aART"] = album_artist
            
        if track.get("album"):
            audio["\xa9alb"] = track["album"]
        if track.get("genre"):
            audio["\xa9gen"] = track["genre"]
        if track.get("year"):
            audio["\xa9day"] = str(track["year"])
            
        if track.get("cover_url"):
            try:
                img = requests.get(track["cover_url"]).content
                covr_fmt = MP4Cover.FORMAT_PNG if track["cover_url"].endswith("png") else MP4Cover.FORMAT_JPEG
                audio["covr"] = [MP4Cover(img, covr_fmt)]
            except Exception as e:
                print("Cover art failed:", e)
                
        audio.save()
        return

    try:
        audio = ID3(file_path)
    except:
        audio = ID3()

    audio.delall("TIT2")
    audio.delall("TPE1")
    audio.delall("TPE2")
    audio.delall("TALB")
    audio.delall("TCON")
    audio.delall("TYER")
    audio.delall("APIC")

    audio.add(
        TIT2(
            encoding=3,
            text=track["title"]
        )
    )

    audio.add(
        TPE1(
            encoding=3,
            text=track["artist"]
        )
    )

    audio.add(
        TPE2(
            encoding=3,
            text=track.get(
                "album_artist",
                track["artist"]
            )
        )
    )

    if track.get("album"):
        audio.add(
            TALB(
                encoding=3,
                text=track["album"]
            )
        )

    if track.get("genre"):
        audio.add(
            TCON(
                encoding=3,
                text=track["genre"]
            )
        )

    if track.get("year"):
        audio.add(
            TYER(
                encoding=3,
                text=str(track["year"])
            )
        )

    if track.get("cover_url"):
        try:
            img = requests.get(track["cover_url"]).content

            audio.add(
                APIC(
                    encoding=3,
                    mime="image/jpeg",
                    type=3,
                    desc="Cover",
                    data=img
                )
            )

        except Exception as e:
            print("Cover art failed:", e)

    audio.save(file_path)

def download_single_song(query):
    folder = MUSIC_DIR / "Singles"

    folder.mkdir(
        parents=True,
        exist_ok=True
    )

    track = {
        "artist": "",
        "title": query
    }

    parts = query.split(" - ", 1)

    if len(parts) == 2:
        track["artist"] = parts[0]
        track["title"] = parts[1]

    track = enrich_metadata(track)

    mp3 = download_song(track, folder)

    if mp3:
        embed_metadata(mp3, track)
        console.print("[success]Finished single download![/success] 🎉")

def download_album(album_name):
    console.print(f"\n[bold magenta]Searching album:[/bold magenta] {album_name}")

    url = "https://itunes.apple.com/search"

    params = {
        "term": album_name,
        "entity": "album",
        "limit": 1
    }

    r = requests.get(url, params=params)

    data = r.json()

    if data["resultCount"] == 0:
        print("Album not found")
        return

    album = data["results"][0]

    collection_id = album["collectionId"]

    lookup = requests.get(
        "https://itunes.apple.com/lookup",
        params={
            "id": collection_id,
            "entity": "song"
        }
    ).json()

    album_title = sanitize(album["collectionName"])

    folder = MUSIC_DIR / album_title

    folder.mkdir(
        parents=True,
        exist_ok=True
    )

    tracks = lookup["results"][1:]

    console.print(f"[success]Tracks found:[/success] {len(tracks)}\n")

    for idx, t in enumerate(tracks, start=1):

        cover = (
            t.get("artworkUrl100", "")
             .replace("100x100", "1000x1000")
        )

        track = {
            "artist": t.get("artistName", ""),
            "title": t.get("trackName", ""),
            "album": t.get("collectionName", ""),
            "album_artist": album.get("artistName", "Various Artists"),
            "genre": t.get("primaryGenreName", ""),
            "year": t.get("releaseDate", "")[:4],
            "cover_url": cover,
            "duration": t.get("trackTimeMillis", 0) / 1000.0
        }

        console.print(
            f"[bold blue][{idx}/{len(tracks)}][/bold blue] "
            f"[bold white]{track['artist']}[/bold white] - [dim]{track['title']}[/dim]"
        )

        mp3 = download_song(track, folder)

        if mp3:
            embed_metadata(mp3, track)

    console.print("\n[success]Album finished![/success] 🎧")

def select_playlists(playlists):
    console.print(Panel("Available Playlists", expand=False, style="bold cyan"))

    for idx, playlist in enumerate(playlists, start=1):
        console.print(f"[magenta][{idx}][/magenta] {playlist['title']}")

    choice = Prompt.ask("\n[bold yellow]Type playlist numbers (e.g. 1,2) or 'all'[/bold yellow]").strip()

    if choice.lower() == "all":
        return playlists

    selected = []

    try:
        indexes = [
            int(x.strip()) - 1
            for x in choice.split(",")
        ]

        for i in indexes:
            if 0 <= i < len(playlists):
                selected.append(playlists[i])

    except:
        print("Invalid selection")
        return []

    return selected

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "mode",
        nargs="?",
        default="playlist"
    )

    parser.add_argument(
        "query",
        nargs="*"
    )

    args = parser.parse_args()

    query = " ".join(args.query)

    if args.mode == "song":

        if not query:
            print("Provide song name")
            return

        download_single_song(query)
        return

    if args.mode == "album":

        if not query:
            print("Provide album name")
            return

        download_album(query)
        return

    if args.mode == "playlist" and query:
        # Check if it's a URL
        if "http" in query:
            url = query
            if "youtube.com" in url or "youtu.be" in url:
                playlist_title, tracks = get_youtube_tracks(url)
            elif "apple.com" in url:
                playlist_title, tracks = get_apple_music_tracks(url)
            elif "spotify.com" in url:
                playlist_title, tracks = get_spotify_tracks(url)
            elif "jiosaavn.com" in url:
                playlist_title, tracks = get_jiosaavn_tracks(url)
            else:
                print("Unsupported platform URL")
                return
                
            if not tracks:
                print("No tracks found in the playlist.")
                return
                
            playlists = [{"title": playlist_title, "id": "url", "tracks": tracks}]
        else:
            # Maybe they meant 'album' or 'song'? 
            print("To sync a specific playlist URL, use: py sync.py playlist <url>")
            return
    else:
        playlists = get_playlists()
        if not playlists:
            print("No playlists found")
            return
    
        playlists = select_playlists(playlists)
    
        if not playlists:
            print("Nothing selected")
            return

    for playlist in playlists:
        pname = sanitize(playlist["title"])

        console.print(Panel(f"Syncing Playlist: [bold white]{pname}[/bold white]", expand=False, style="bold magenta"))

        folder = MUSIC_DIR / pname

        if folder.exists():
            shutil.rmtree(folder)

        folder.mkdir(
            parents=True,
            exist_ok=True
        )

        if "tracks" in playlist:
            # Tracks were already extracted from URL
            tracks = playlist["tracks"]
        else:
            # Fetch tracks from ListenBrainz
            tracks = get_tracks(playlist["id"])

        console.print(f"[success]Tracks found:[/success] {len(tracks)}\n")

        for idx, track in enumerate(tracks, start=1):

            console.print(
                f"[bold blue][{idx}/{len(tracks)}][/bold blue] "
                f"[bold white]{track['artist']}[/bold white] - [dim]{track['title']}[/dim]"
            )

            track = enrich_metadata(track)

            mp3 = download_song(track, folder)

            if not mp3:
                continue

            embed_metadata(mp3, track)

            print("Finished")


if __name__ == "__main__":
    main()
