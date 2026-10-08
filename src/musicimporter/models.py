import os
from mutagen import File  # type: ignore
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus
from mutagen.monkeysaudio import MonkeysAudio
from mutagen.wavpack import WavPack
from pathlib import Path
from typing import Optional
from .clean import clean_audio
from .convert import set_cover_art
from .convert import CoverArt
from .convert import get_cover_art
from .convert import convert_audio
from .convert import get_output_codec


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

        self.codec: Optional[str] = None

        self.load_metadata()

    def load_metadata(self) -> None:
        audio = File(self.path, easy=True)

        if audio is None:
            raise ValueError(f"Unsupported audio file: {self.path}")

        self.title = audio.get("title", [None])[0] or None
        self.artist = audio.get("artist", [None])[0] or None
        self.album = audio.get("album", [None])[0] or None
        self.year = parse_year(audio.get("date", [None])[0])

        self.tracknumber = parse_number(audio.get("tracknumber", [None])[0])

        self.genre = audio.get("genre", [None])[0] or None
        self.comment = audio.get("comment", [None])[0] or None
        self.albumartist = audio.get("albumartist", [None])[0] or None

        self.discnumber = parse_number(audio.get("discnumber", [None])[0])

        if isinstance(audio, FLAC):
            self.codec = "flac"
        elif isinstance(audio, MP4):
            codec = str(audio.info.codec).lower()
            self.codec = "aac" if codec.startswith("mp4a.40.") else codec
        elif isinstance(audio, MP3):
            self.codec = "mp3"
        elif isinstance(audio, WAVE):
            self.codec = {
                (1, 8): "pcm_u8",
                (1, 16): "pcm_s16le",
                (1, 24): "pcm_s24le",
                (1, 32): "pcm_s32le",
                (3, 32): "pcm_f32le",
                (3, 64): "pcm_f64le",
                (6, 8): "pcm_alaw",
                (7, 8): "pcm_mulaw",
            }.get((audio.info.audio_format, audio.info.bits_per_sample))
        elif isinstance(audio, OggVorbis):
            self.codec = "vorbis"
        elif isinstance(audio, OggOpus):
            self.codec = "opus"
        elif isinstance(audio, MonkeysAudio):
            self.codec = "ape"
        elif isinstance(audio, WavPack):
            self.codec = "wavpack"
        else:
            self.codec = None

    def apply_new_metadata(
        self,
        path: str,
        year: Optional[int] = None,
        albumartist: Optional[str] = None,
        genre: Optional[str] = None,
    ) -> None:
        try:
            audio = File(path, easy=True)

            if audio is None:
                raise ValueError(f"Unsupported audio file: {path}")

            if year is not None:
                audio["date"] = str(year)

            if albumartist is not None:
                audio["albumartist"] = albumartist

            if genre is not None:
                audio["genre"] = genre

            audio["tracknumber"] = (
                str(self.tracknumber) if self.tracknumber is not None else "0"
            )

            audio.save()
            clean_audio(path)

        except Exception as e:
            print(f"Error applying new metadata for {self.path}: {e}")

    def apply_cover_art(self, path: str, cover: Optional[CoverArt] = None) -> None:
        try:
            if cover is None:
                cover = get_cover_art(self.path)

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
        self.genre: Optional[str] = None

        self.cover: Optional[CoverArt] = None

        self.ffmpeg_options: str = "-c:a copy"
        self.extension: str = "copy"
        self.output_codec: Optional[str] = "copy"

        self.albumartists: list[str] = []
        self.years: list[int] = []
        self.genres: list[str] = []

        self.songs: list[Song] = []
        self.resolved: bool = False

    def add_song(self, song: Song) -> None:
        if song.albumartist is not None and song.albumartist not in self.albumartists:
            self.albumartists.append(song.albumartist)

        if song.year is not None and song.year not in self.years:
            self.years.append(song.year)
        if song.genre is not None and song.genre not in self.genres:
            self.genres.append(song.genre)

        self.songs.append(song)

        self.songs.sort(
            key=lambda s: (
                s.tracknumber if s.tracknumber is not None else float("inf"),
                Path(s.path).name.lower(),
            )
        )

    def resolve_metadata(self) -> None:
        if len(self.albumartists) > 1:
            self.albumartist = "Various Artists"
        else:
            self.albumartist = (
                self.albumartists[0] if self.albumartists else "Unknown Artist"
            )

        if (
            self.albumartist == "Unknown Artist"
            or self.albumartist == "Various Artists"
        ):
            artists = []
            for song in self.songs:
                if song.artist is not None and song.artist not in artists:
                    artists.append(song.artist)
            if len(artists) == 1:
                self.albumartist = artists[0]
            elif len(artists) > 1:
                self.albumartist = "Various Artists"

        self.year = min(self.years) if self.years else None
        self.genre = self.genres[0] if self.genres else None

        for song in self.songs:
            temp_cover = get_cover_art(song.path)
            if temp_cover is not None:
                self.cover = temp_cover
                break

        for index, song in enumerate(self.songs):
            if song.tracknumber is None:
                song.tracknumber = index + 1

        self.resolved = True

    def resolve_settings(
        self,
        ffmpeg_options: str = "-c:a copy",
        extension: str = "copy",
    ) -> None:
        """Store conversion settings and resolve the requested output codec."""
        output_codec = get_output_codec(ffmpeg_options, extension)
        self.ffmpeg_options = ffmpeg_options
        self.extension = extension
        self.output_codec = output_codec

    def export(
        self,
        export_dir: str,
        force_reencode: bool = False,
    ) -> list[Song]:
        """Export songs, copying matching codecs unless force_reencode is set."""
        exported: list[Song] = []

        # Empty options use FFmpeg defaults; an unknown codec is valid too.
        if self.ffmpeg_options is None or not self.extension:
            self.resolve_settings()

        if not self.resolved:
            self.resolve_metadata()
            self.resolved = True

        album_export_path = os.path.join(
            export_dir,
            sanitize_filename(self.albumartist or "Unknown Artist"),
            sanitize_filename(self.album or "Unknown Album"),
        )
        os.makedirs(album_export_path, exist_ok=True)

        for index, song in enumerate(self.songs):
            formatted_tracknumber = (
                f"{song.tracknumber:02}"
                if song.tracknumber is not None
                else f"{index+1:02}"
            )
            discnumber_prefix = (
                f"{song.discnumber:02}-" if song.discnumber is not None else ""
            )

            song_extension = (
                Path(song.path).suffix.lstrip(".")
                if self.extension == "copy"
                else self.extension.lstrip(".")
            )

            title = sanitize_filename(song.title or "Unknown Title")

            filename = (
                f"{discnumber_prefix}"
                f"{formatted_tracknumber}. "
                f"{title}.{song_extension}"
            )

            export_path = os.path.join(album_export_path, filename)

            options = self.ffmpeg_options
            if (
                not force_reencode
                and song.codec is not None
                and song.codec == self.output_codec
            ):
                options = "-c:a copy"
            convert_audio(song.path, export_path, options)

            song.apply_new_metadata(
                export_path,
                year=self.year,
                albumartist=self.albumartist,
                genre=self.genre,
            )
            song.apply_cover_art(export_path, self.cover)

            exported.append(song)

        return exported

    def __str__(self) -> str:
        return (
            f"Album(album={self.album}, albumartist={self.albumartist}, year={self.year}, "
            f"songs=[{', '.join(str(song.title) for song in self.songs)}])"
        )
