# BrainzPod

Sync your [ListenBrainz](https://listenbrainz.org/) recommendation playlists, download pristine audio from **JioSaavn** (primary) and **YouTube** (via yt-dlp fallback), embed accurate iTunes metadata + album art, and organize everything into ready-to-sync playlist folders.

Works with iPods, Rockbox, Foobar2000, iTunes / Apple Music, Jellyfin, and any offline music library.

---

## Table of Contents

- [Features](#features)
- [Folder Structure](#folder-structure)
- [Installation](#installation)
  - [Requirements](#requirements)
  - [FFmpeg](#ffmpeg)
  - [Python Dependencies](#python-dependencies)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Sync ListenBrainz Playlists](#sync-listenbrainz-playlists)
  - [Download a Single Song](#download-a-single-song)
  - [Download an Album](#download-an-album)
  - [Import a Playlist from URL](#import-a-playlist-from-url)
- [Supported Playlist Sources](#supported-playlist-sources)
- [How It Works](#how-it-works)
- [Why BrainzPod Exists](#why-brainzpod-exists)
- [Troubleshooting](#troubleshooting)
- [Disclaimer](#disclaimer)
- [Credits](#credits)

---

## Features

- **Dual-Provider Downloading** — Fetches original `.mp4` audio streams from JioSaavn first for maximum quality, seamlessly falling back to `yt-dlp` (`.mp3`) if the track isn't available.
- **Intelligent Duration Matching** — Verifies JioSaavn search results against official iTunes track lengths. Automatically discards bootlegs, remixes, or fake tracks if the duration is off by more than 20 seconds.
- **Sync ListenBrainz Recommendation Playlists** — Fetches your personalised playlists (Weekly Jams, Weekly Exploration, etc.) directly from ListenBrainz.
- **Download Single Songs & Full Albums** — Search and download by name or paste an album URL.
- **Import Playlists from External Sources** — Parse track lists from YouTube, Apple Music, Spotify, and JioSaavn playlist URLs.
- **Advanced Metadata Embedding** — iTunes-grade ID3/MP4 tags including Title, Artist, Album, Album Artist, Genre, Year, and Cover Art (500x500 or 1000x1000 resolution) using `mutagen`.
- **Album Artist Support** — Groups soundtracks and compilations correctly in iPods/iTunes, preventing multi-artist albums (e.g. Bollywood soundtracks) from splitting.
- **iPod-Friendly Folder Structure** — Each playlist gets its own folder; files are named by track title.
- **Smart Metadata Priority** — iTunes metadata takes precedence; JioSaavn is used only as a fallback for missing fields.
- **No Streaming Subscriptions Required** — Uses freely available public sources.

---

## Folder Structure

```
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
- Title, Artist, Album
- Album Artist (prevents library splitting)
- Genre, Release Year
- Embedded Cover Art (500x500 or 1000x1000)

---

## Installation

### Requirements

- **Python** 3.10+
- **FFmpeg** (for stream downloading and transcoding)
- **yt-dlp** (YouTube fallback downloader)

### FFmpeg

#### Windows
1. Download from [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extract the archive and add the `bin` folder to your system `PATH`
3. Verify:
   ```bash
   ffmpeg -version
   ```

#### macOS
```bash
brew install ffmpeg
```

#### Linux
```bash
sudo apt install ffmpeg     # Debian/Ubuntu
sudo dnf install ffmpeg     # Fedora
```

### yt-dlp

```bash
pip install yt-dlp
```

### Python Dependencies

```bash
pip install yt-dlp requests mutagen pyDes
```

> `pyDes` is included locally (`pyDes.py`) but can also be installed via pip. It is used to natively decrypt JioSaavn media URLs.

---

## Configuration

Create a `config.json` in the project root:

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

| Key                  | Description                                                    |
| -------------------- | -------------------------------------------------------------- |
| `listenbrainz_user`  | Your ListenBrainz username (used to fetch recommendation playlists) |
| `music_dir`          | Directory where downloaded music will be saved                 |
| `bad_words`          | Keywords that filter out unwanted remixes or bootlegs from search results |

The `bad_words` list is case-insensitive and filters both JioSaavn and YouTube results.

---

## Usage

### Sync ListenBrainz Playlists

```bash
py sync.py
```

You'll be prompted to select which playlists to sync:

```
Available playlists:

[1] Weekly Exploration...
[2] Weekly Jams...

Select playlists:
> 1,2
```

Each playlist folder is recreated fresh on every sync (existing folders are removed before downloading).

---

### Download a Single Song

```bash
py sync.py song "Joji Yeah Right"
```

To specify the artist explicitly, use `Artist - Title` format:

```bash
py sync.py song "Joji - Slow Dancing in the Dark"
```

The file is saved to `Music/Singles/`.

---

### Download an Album

```bash
py sync.py album "Qala"
```

The album is looked up on the iTunes API, all tracks are downloaded, and the folder is named after the album. Works with:
- Movie soundtracks
- Anime OSTs
- Compilations
- Bollywood albums
- Game soundtracks

---

### Import a Playlist from URL

```bash
py sync.py playlist <url>
```

Downloads all tracks from an external playlist URL. Supported sources are detected automatically.

---

## Supported Playlist Sources

| Source       | URL Format Example                                    |
| ------------ | ----------------------------------------------------- |
| **ListenBrainz** | Fetched automatically for your configured user    |
| **YouTube**      | `https://youtube.com/playlist?list=...`            |
| **Apple Music**  | `https://music.apple.com/.../playlist/...`         |
| **Spotify**      | `https://open.spotify.com/playlist/...`            |
| **JioSaavn**     | `https://www.jiosaavn.com/playlist/...`            |

---

## How It Works

```
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
- Apple Music / iTunes APIs (primary)
- JioSaavn Metadata (fallback)

JioSaavn and YouTube are used solely as audio delivery systems. All metadata is independently sourced from iTunes.

### Download Priority

1. **JioSaavn** — Higher quality `.mp4` streams, decrypted and transcoded to `.mp3` via FFmpeg
2. **yt-dlp (YouTube)** — Fallback if JioSaavn fails or duration doesn't match

---

## Why BrainzPod Exists

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
- syncing music like it's 2007 but with modern metadata sorcery

---

## Troubleshooting

| Issue                          | Likely Fix                                                    |
| ------------------------------ | ------------------------------------------------------------- |
| `ffmpeg` not found             | Install FFmpeg and add it to your system `PATH`               |
| `yt-dlp` not found             | `pip install yt-dlp`                                          |
| ImportError: pyDes             | `pip install pyDes` (or ensure `pyDes.py` is in the root)     |
| No playlists found             | Check your ListenBrainz username in `config.json`             |
| JioSaavn download fails        | The script falls back to yt-dlp automatically                |
| Metadata missing               | iTunes API may not have the track; check your internet connection |
| "Failed to fetch tracks"       | The playlist ID may be invalid or private                     |

If downloads consistently fail from JioSaavn, the API endpoints may have changed. Check for project updates.

---

## Disclaimer

BrainzPod does not host or distribute music.

It acts as an automated search tool that retrieves publicly accessible media. Users are responsible for complying with local laws and platform terms of service.

---

## Credits

Powered by logic and structures originally inspired by:
- [ListenBrainz](https://listenbrainz.org/)
- [MusicBrainz](https://musicbrainz.org/)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [FFmpeg](https://ffmpeg.org/)
- [Mutagen](https://mutagen.readthedocs.io/)
- JioSaavn integration inspired by [Saavn-Downloader](https://github.com/inovachrono/Saavn-Downloader)
