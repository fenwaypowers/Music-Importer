# Music Importer

Music Importer is a command-line tool for importing music into an organized music library.

Give Music Importer a folder containing audio files and it will read their metadata, group tracks into albums, organize them into a consistent directory structure, clean unnecessary metadata, and optionally convert them using FFmpeg.

## Features

- Imports audio files from a folder into an organized music library
- Groups tracks by album metadata
- Organizes music by album artist and album
- Normalizes album artist and year metadata
- Removes unnecessary metadata while preserving common tags and cover art
- Preserves embedded album artwork
- Optionally converts audio using custom FFmpeg options
- Supports common formats including:
  - FLAC
  - MP3
  - M4A / ALAC
  - Ogg Vorbis
  - Opus
  - WAV
  - Monkey's Audio (APE)
  - WavPack

## Requirements

- Python 3.10 or newer
- [Mutagen](https://mutagen.readthedocs.io/)
- [FFmpeg](https://ffmpeg.org/) for audio conversion

FFmpeg must be installed and available on your system's `PATH` to use conversion.

## Installation

Clone the repository and install the package:

```bash
git clone <repository-url>
cd musicimporter
pip install .
```

For development, install it in editable mode:

```bash
pip install -e .
```

## Usage

The basic syntax is:

```bash
musicimporter INPUT DESTINATION
```

For example:

```bash
musicimporter ./inbox ~/Music
```

Music Importer will scan the input directory and import the music it finds into the destination.

### Audio Conversion

Music can optionally be converted by providing FFmpeg audio options and an output extension:

```bash
musicimporter ./inbox ~/Music \
    --convert "-c:a libfdk_aac -vbr 4" \
    --extension m4a
```

For example, to convert music to Opus:

```bash
musicimporter ./inbox ~/Music \
    --convert "-c:a libopus -b:a 160k" \
    --extension opus
```

The value passed to `--convert` is passed to FFmpeg as audio encoding options, allowing you to choose the codec and encoding settings yourself.

If `--convert` is not specified, files are copied in their original format.

## Library Structure

Imported music is organized using the album artist and album metadata:

```text
Music/
├── Artist/
│   └── Album/
│       ├── 01. Track One.flac
│       ├── 02. Track Two.flac
│       └── 03. Track Three.flac
└── Various Artists/
    └── Compilation/
        ├── 01. First Song.flac
        └── 02. Second Song.flac
```

Disc numbers are included in filenames when applicable.

## Metadata

Music Importer preserves and normalizes common music metadata, including:

- Title
- Artist
- Album artist
- Album
- Year
- Track number
- Disc number
- Genre
- Composer
- Cover art

Other unnecessary metadata is removed during import.
