import os
import sys
import shutil
from mutagen._file import File
from pathlib import Path
from typing import Optional
from clean import clean_audio

albums: list[Album] = []


class Song:
    def __init__(self, original_path: str):
        self.original_path: str = original_path

        # Metadata fields
        self.title: Optional[str] = None
        self.artist: Optional[str] = None
        self.album: Optional[str] = None
        self.year: Optional[str] = None
        self.tracknumber: Optional[str] = None
        self.genre: Optional[str] = None
        self.comment: Optional[str] = None
        self.albumartist: Optional[str] = None
        self.discnumber: Optional[str] = None

        self.new_path: Optional[str] = None
        self.new_year: Optional[str] = None
        self.new_albumartist: Optional[str] = None

        self.metadata_loaded: bool = False

        self.load_metadata()
        self.add_to_album()

    def load_metadata(self) -> None:
        try:
            audio = File(self.original_path, easy=True)
            if audio is not None:
                self.title = audio.get("title", [None])[0]
                self.artist = audio.get("artist", [None])[0]
                self.album = audio.get("album", [None])[0]
                self.year = audio.get("date", [None])[0]

                # make sure year only includes the year, and no extra info like month/day
                if self.year is not None:
                    self.year = self.year[:4]

                self.tracknumber = audio.get("tracknumber", [None])[0]
                self.genre = audio.get("genre", [None])[0]
                self.comment = audio.get("comment", [None])[0]
                self.albumartist = audio.get("albumartist", [None])[0]
                self.discnumber = audio.get("discnumber", [None])[0]
        except Exception as e:
            print(f"Error loading metadata for {self.original_path}: {e}")

        self.metadata_loaded = True

    def apply_new_metadata(self):
        try:
            audio = File(self.new_path, easy=True)
            if audio is not None:
                if self.new_year is not None:
                    audio["date"] = self.new_year
                if self.new_albumartist is not None:
                    audio["albumartist"] = self.new_albumartist
                audio.save()

            clean_audio(self.new_path)
        except Exception as e:
            print(f"Error applying new metadata for {self.original_path}: {e}")


    def add_to_album(self):
        for album in albums:
            if album.album == self.album:
                album.add_song(self)
                return

        new_album = Album(self.album)
        new_album.add_song(self)
        albums.append(new_album)

    def __str__(self):
        return f"Song(title={self.title}, artist={self.artist}, album={self.album}, year={self.year}, tracknumber={self.tracknumber}, genre={self.genre}, comment={self.comment}, albumartist={self.albumartist}, discnumber={self.discnumber})"


class Album:
    def __init__(self, album: Optional[str]):
        self.album: Optional[str] = album
        self.albumartist: Optional[str] = None
        self.year: Optional[str] = None

        self.albumartists: list[str] = []
        self.years: list[str] = []

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

        self.year = min(self.years, key=int) if self.years else None

        album_export_path = os.path.join(export_path, self.albumartist, self.album or "Unknown Album")
        os.makedirs(album_export_path, exist_ok=True)

        for song in self.songs:
            song.new_year = self.year
            song.new_albumartist = self.albumartist
            formatted_tracknumber = f"{int(song.tracknumber):02}" if song.tracknumber is not None else "00"

            song_export_path = os.path.join(album_export_path, f"{formatted_tracknumber}. {song.title or 'Unknown Title'}")
            
            if format == "copy":
                shutil.copy(song.original_path, song_export_path)

            # TODO: conversion for other formats

            song.new_path = song_export_path
            song.apply_new_metadata()


def main():
    song_path = sys.argv[1] if len(sys.argv) > 1 else ""
    if song_path != "":
        song = Song(song_path)
        print(song)


if __name__ == "__main__":
    main()
