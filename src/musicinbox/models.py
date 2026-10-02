import os
import sys
import shutil
from mutagen._file import File
from pathlib import Path
from typing import Optional
from clean import clean_audio

def parse_number(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value.split("/")[0])
    except ValueError:
        return None

def add_to_album(song):
    for album in albums:
        if album.album == song.album:
            album.add_song(song)
            return

    new_album = Album(song.album)
    new_album.add_song(song)
    albums.append(new_album)

def parse_year(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value[:4])
    except ValueError:
        return None

class Song:
    def __init__(self, original_path: str):
        self.original_path: str = original_path

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
        add_to_album(self)


    def load_metadata(self) -> None:
        try:
            audio = File(self.original_path, easy=True)
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
            print(f"Error loading metadata for {self.original_path}: {e}")


    def apply_new_metadata(self, path: str, year: Optional[int] = None, albumartist: Optional[str] = None):
        try:
            audio = File(path, easy=True)
            if audio is not None:
                if year is not None:
                    audio["date"] = year
                if albumartist is not None:
                    audio["albumartist"] = albumartist
                audio.save()

            clean_audio(path)
        except Exception as e:
            print(f"Error applying new metadata for {self.original_path}: {e}")


    def __str__(self):
        return f"Song(title={self.title}, artist={self.artist}, album={self.album}, year={self.year}, tracknumber={self.tracknumber}, genre={self.genre}, comment={self.comment}, albumartist={self.albumartist}, discnumber={self.discnumber})"


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

        # sort songs by tracknumber
        self.songs.sort(
            key=lambda s: s.tracknumber if s.tracknumber is not None else ""
        )

    def export(self, export_path: str, format: str = "copy"):
        if len(self.albumartists) > 1:
            self.albumartist = "Various Artists"
        else:
            self.albumartist = self.albumartists[0] if self.albumartists else "Unknown Artist"

        self.year = min(self.years) if self.years else None

        album_export_path = os.path.join(export_path, self.albumartist, self.album or "Unknown Album")
        os.makedirs(album_export_path, exist_ok=True)

        for song in self.songs:
            formatted_tracknumber = f"{song.tracknumber:02}" if song.tracknumber is not None else "00"
            discnumber_prefix = f"{song.discnumber:02}-" if song.discnumber is not None else ""

            song_export_path = os.path.join(album_export_path, f"{discnumber_prefix}{formatted_tracknumber}. {song.title or 'Unknown Title'}.{format if format != 'copy' else Path(song.original_path).suffix.lstrip('.')}")
            
            if format == "copy":
                shutil.copy2(song.original_path, song_export_path)
            else:
                # TODO: conversion for other formats
                pass

            song.apply_new_metadata(song_export_path, year=self.year, albumartist=self.albumartist)


albums: list[Album] = []

def main():
    song_path = sys.argv[1] if len(sys.argv) > 1 else ""
    if song_path != "":
        song = Song(song_path)
        print(song)


if __name__ == "__main__":
    main()
