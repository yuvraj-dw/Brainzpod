# BrainzPod 🎧

BrainzPod syncs your ListenBrainz recommendation playlists, downloads pristine audio from **JioSaavn** (as a primary source) and **YouTube** (via yt-dlp as a fallback), embeds highly accurate iTunes metadata + album art, and organizes everything into beautiful playlist folders ready for:

- iPods
- Rockbox
- Foobar2000
- iTunes / Apple Music
- Jellyfin
- offline music libraries

---

# Features ✨

- **Dual-Provider Downloading:** Fetches original `.mp4` audio streams from JioSaavn first for maximum quality, seamlessly falling back to `yt-dlp` (`.mp3`) if the track isn't available.
- **Intelligent Duration Matching:** Verifies JioSaavn search results against official iTunes track lengths. Automatically discards bootlegs, remixes, or fake tracks if the duration is off by more than 10 seconds.
- **Sync ListenBrainz recommendation playlists**
- **Download single songs and full albums**
- **Advanced Metadata Embedding:** Automatically applies iTunes-grade metadata to both `.mp4` and `.mp3` files (including Cover Art, Title, Artist, Album, Genre, and Year) using `mutagen`.
- **Album Artist Support:** Groups soundtracks and compilations perfectly in iPods/iTunes, preventing multi-artist albums (like Bollywood soundtracks) from splitting.
- **Playlist selection CLI**
- **iPod-friendly folder structure**
- **No streaming subscriptions required**

---

# Example Folder Structure

```text
Music/
├── Weekly Jams/
│   ├── Joji - Slow Dancing in the Dark.mp4
│   ├── Kendrick Lamar - luther.mp4
│   └── ...
│
├── Weekly Exploration/
│   ├── Elvis Presley - Can't Help Falling in Love.mp3
│   └── ...
│
├── Qala (Soundtrack from the Netflix Film)/
│   ├── Amit Trivedi - Ghodey Pe Sawaar.mp4
│   └── ...
│
└── Singles/
    └── Nujabes - Aruarian Dance.mp4
```

All files contain:
- Title
- Artist
- Album
- Album Artist (Prevents library splitting)
- Genre
- Release Year
- Embedded Cover Art (500x500 or 1000x1000 Resolution)

---

# Installation ⚙️

## Requirements

- Python 3.10+
- FFmpeg
- yt-dlp

---

## Install FFmpeg

### Windows

Download:
https://ffmpeg.org/download.html

Add FFmpeg to PATH.

Verify:
```bash
ffmpeg -version
```

---

## Install Python dependencies

Install the required modules for audio fetching, metadata parsing, and stream decryption:

```bash
pip install yt-dlp requests mutagen pyDes
```

> **Note:** The `pyDes` module is required to natively decrypt JioSaavn media URLs directly in Python.

---

# Configuration

Create a `config.json` file in the root directory:

```json
{
  "listenbrainz_user": "YOUR_USERNAME",

  "music_dir": "./Music",

  "bad_words": [
    "slowed",
    "reverb",
    "sped up",
    "live",
    "concert",
    "8d",
    "bass boosted",
    "edit"
  ]
}
```

---

# Usage 🚀

## Sync ListenBrainz playlists

```bash
py sync.py
```

You’ll get an interactive playlist selector:

```text
Available playlists:

[1] Weekly Exploration...
[2] Weekly Jams...

Select playlists:
>
```

---

## Download a single song

```bash
py sync.py song "Joji Yeah Right"
```

---

## Download an album

```bash
py sync.py album "Qala"
```

Works flawlessly with:
- Movie soundtracks
- Anime OSTs
- Compilations
- Bollywood albums
- Game soundtracks

---

# How It Works 🧠

```text
ListenBrainz / CLI Input
        ↓
Metadata Enrichment (iTunes API)
        ↓
Primary Source: JioSaavn Search (Verifies via Track Duration)
        ↓
Fallback Source: yt-dlp (YouTube Search)
        ↓
Album Art & ID3/MP4 Metadata Embedding (mutagen)
        ↓
iPod-ready Local Library
```

Metadata and cover art are fetched from:
- Apple Music/iTunes APIs
- JioSaavn Metadata (Fallback)

JioSaavn and YouTube are used solely as the audio delivery systems.

---

# Why BrainzPod Exists

Streaming services solved convenience.
They also quietly deleted:
- ownership
- permanence
- intentional listening
- weird little MP3 rituals

BrainzPod is for people who still enjoy:
- offline libraries
- curated playlists
- retro music players
- open music ecosystems
- syncing music like it’s 2007 but with modern metadata sorcery

---

# Disclaimer ⚠️

BrainzPod does not host or distribute music.

It acts as an automated search tool that retrieves publicly accessible media. Users are responsible for complying with local laws and platform terms of service.

---

# Credits ❤️

Powered by logic and structures originally inspired by:
- ListenBrainz
- MusicBrainz
- yt-dlp
- FFmpeg
- Mutagen
- JioSaavn integration inspired by [Saavn-Downloader](https://github.com/inovachrono/Saavn-Downloader)
