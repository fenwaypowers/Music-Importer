import os
import sys
import shutil
from mutagen import File  # type: ignore
from pathlib import Path
from typing import Optional
from clean import clean_audio


def add_to_album(song) -> None:
    for album in albums:
        if album.album == song.album:
            album.add_song(song)
            return

    new_album = Album(song.album)
    new_album.add_song(song)
    albums.append(new_album)


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
        try:
            audio = File(self.path, easy=True)
            if audio is not None:
                self.title = audio.get("title", [None])[0]
                self.artist = audio.get("artist", [None])[0]
                self.album = audio.get("album", [None])[0]
                self.year = parse_year(audio.get("date", [None])[0])

                self.tracknumber = parse_number(audio.get("tracknumber", [None])[0])
                self.genre = audio.get("genre", [None])[0]
                self.comment = audio.get("comment", [None])[0]
                self.albumartist = audio.get("albumartist", [None])[0]
                self.discnumber = parse_number(audio.get("discnumber", [None])[0])
        except Exception as e:
            print(f"Error loading metadata for {self.path}: {e}")

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

        self.year = min(self.years) if self.years else None

    def export(self, export_dir: str, output_format: str = "copy") -> None:
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

            if output_format == "copy":
                extension = Path(song.path).suffix.lstrip(".")
            else:
                extension = output_format

            title = sanitize_filename(song.title or "Unknown Title")

            filename = (
                f"{discnumber_prefix}"
                f"{formatted_tracknumber}. "
                f"{title}.{extension}"
            )

            export_path = os.path.join(album_export_path, filename)

            if output_format == "copy":
                shutil.copy2(song.path, export_path)
            else:
                raise NotImplementedError(
                    f"Conversion to format '{output_format}' is not implemented."
                )

            song.apply_new_metadata(
                export_path, year=self.year, albumartist=self.albumartist
            )

    def __str__(self) -> str:
        return (
            f"Album(album={self.album}, albumartist={self.albumartist}, year={self.year}, "
            f"songs=[{', '.join(str(song.title) for song in self.songs)}])"
        )


albums: list[Album] = []


def main():
    in_path = sys.argv[1] if len(sys.argv) > 1 else ""
    if in_path != "":
        for root, _, files in os.walk(in_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    song = Song(file_path)
                    add_to_album(song)
                except Exception as e:
                    print(f"Error processing file {file_path}: {e}")

    for album in albums:
        album.export("library")
        print(album)

if __name__ == "__main__":
    main()
