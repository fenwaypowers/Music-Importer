import os
from mutagen import File  # type: ignore
from pathlib import Path
from typing import Optional
from clean import clean_audio
from convert import set_cover_art
from convert import CoverArt
from convert import get_cover_art
from convert import convert_audio


def parse_number(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None

    try:
        return int(value.split("/", 1)[0])
    except ValueError:
        return None


def parse_year(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None

    try:
        return int(value[:4])
    except ValueError:
        return None


def sanitize_filename(name: str) -> str:
    invalid = '<>:"/\\|?*'
    sanitized = "".join("_" if char in invalid else char for char in name)
    return sanitized.strip().rstrip(".")


class Song:
    def __init__(self, path: str):
        self.path: str = path

        # Metadata fields
        self.title: Optional[str] = None
        self.artist: Optional[str] = None
        self.album: Optional[str] = None
        self.year: Optional[int] = None
        self.tracknumber: Optional[int] = None
        self.genre: Optional[str] = None
        self.comment: Optional[str] = None
        self.albumartist: Optional[str] = None
        self.discnumber: Optional[int] = None

        self.load_metadata()

    def load_metadata(self) -> None:
        audio = File(self.path, easy=True)

        if audio is None:
            raise ValueError("Unsupported audio file")

        self.title = audio.get("title", [None])[0] or None
        self.artist = audio.get("artist", [None])[0] or None
        self.album = audio.get("album", [None])[0] or None
        self.year = parse_year(audio.get("date", [None])[0])

        self.tracknumber = parse_number(
            audio.get("tracknumber", [None])[0]
        )

        self.genre = audio.get("genre", [None])[0] or None
        self.comment = audio.get("comment", [None])[0] or None
        self.albumartist = audio.get("albumartist", [None])[0] or None

        self.discnumber = parse_number(
            audio.get("discnumber", [None])[0]
        )

    def apply_new_metadata(
        self,
        path: str,
        year: Optional[int] = None,
        albumartist: Optional[str] = None,
    ) -> None:
        try:
            audio = File(path, easy=True)

            if audio is None:
                raise ValueError(f"Unsupported audio file: {path}")

            if year is not None:
                audio["date"] = str(year)

            if albumartist is not None:
                audio["albumartist"] = albumartist

            audio.save()
            clean_audio(path)

        except Exception as e:
            print(f"Error applying new metadata for {self.path}: {e}")

    def apply_cover_art(self, path: str) -> None:
        try:
            cover: Optional[CoverArt] = get_cover_art(self.path)
            if cover is not None:
                set_cover_art(path, cover)

        except Exception as e:
            print(f"Error setting cover art for {path}: {e}")

    def __str__(self) -> str:
        return (
            f"Song(title={self.title}, artist={self.artist}, album={self.album}, "
            f"year={self.year}, tracknumber={self.tracknumber}, genre={self.genre}, "
            f"comment={self.comment}, albumartist={self.albumartist}, discnumber={self.discnumber})"
        )


class Album:
    def __init__(self, album: Optional[str]):
        self.album: Optional[str] = album
        self.albumartist: Optional[str] = None
        self.year: Optional[int] = None

        self.albumartists: list[str] = []
        self.years: list[int] = []

        self.songs: list[Song] = []

    def add_song(self, song: Song) -> None:
        if song.albumartist is not None and song.albumartist not in self.albumartists:
            self.albumartists.append(song.albumartist)

        if song.year is not None and song.year not in self.years:
            self.years.append(song.year)

        self.songs.append(song)

        # TODO: sort songs by filename
        self.songs.sort(key=lambda s: Path(s.path).name.lower())

    def resolve_metadata(self) -> None:
        if len(self.albumartists) > 1:
            self.albumartist = "Various Artists"
        else:
            self.albumartist = (
                self.albumartists[0] if self.albumartists else "Unknown Artist"
            )

        if self.albumartist == "Unknown Artist" or self.albumartist == "Various Artists":
            artists = []
            for song in self.songs:
                if song.artist is not None and song.artist not in artists:
                    artists.append(song.artist)
            if len(artists) == 1:
                self.albumartist = artists[0]
            elif len(artists) > 1:
                self.albumartist = "Various Artists"

        self.year = min(self.years) if self.years else None

    def export(self, export_dir: str, ffmpeg_options: str = "-c:a copy", extension: str = "copy") -> None:
        self.resolve_metadata()

        album_export_path = os.path.join(
            export_dir,
            sanitize_filename(self.albumartist or "Unknown Artist"),
            sanitize_filename(self.album or "Unknown Album"),
        )
        os.makedirs(album_export_path, exist_ok=True)

        for song in self.songs:
            formatted_tracknumber = (
                f"{song.tracknumber:02}" if song.tracknumber is not None else "00"
            )
            discnumber_prefix = (
                f"{song.discnumber:02}-" if song.discnumber is not None else ""
            )

            if extension == "copy":
                extension = Path(song.path).suffix.lstrip(".")

            title = sanitize_filename(song.title or "Unknown Title")

            filename = (
                f"{discnumber_prefix}"
                f"{formatted_tracknumber}. "
                f"{title}.{extension}"
            )

            export_path = os.path.join(album_export_path, filename)

            convert_audio(song.path, export_path, ffmpeg_options)

            song.apply_new_metadata(
                export_path, year=self.year, albumartist=self.albumartist
            )
            song.apply_cover_art(export_path)

    def __str__(self) -> str:
        return (
            f"Album(album={self.album}, albumartist={self.albumartist}, year={self.year}, "
            f"songs=[{', '.join(str(song.title) for song in self.songs)}])"
        )
