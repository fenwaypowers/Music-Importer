import sys

from mutagen._file import File
from pathlib import Path
from typing import Optional

class Song:
    def __init__(self, path: str):
        self.filename: str = path
        self.title: Optional[str] = None
        self.artist: Optional[str] = None
        self.album: Optional[str] = None
        self.year: Optional[str] = None
        self.tracknumber: Optional[str] = None
        self.genre: Optional[str] = None
        self.comment: Optional[str] = None
        self.albumartist: Optional[str] = None
        self.discnumber: Optional[str] = None
        self.metadata_loaded: bool = False

        self.load_metadata()

    def load_metadata(self) -> None:
        try:
            audio = File(self.filename, easy=True)
            if audio is not None:
                self.title = audio.get('title', [None])[0]
                self.artist = audio.get('artist', [None])[0]
                self.album = audio.get('album', [None])[0]
                self.year = audio.get('date', [None])[0]
                self.tracknumber = audio.get('tracknumber', [None])[0]
                self.genre = audio.get('genre', [None])[0]
                self.comment = audio.get('comment', [None])[0]
                self.albumartist = audio.get('albumartist', [None])[0]
                self.discnumber = audio.get('discnumber', [None])[0]
        except Exception as e:
            print(f"Error loading metadata for {self.filename}: {e}")
        
        self.metadata_loaded = True

    def remove_images(self) -> None:
        try:
            audio = File(self.filename)
            if audio is not None and hasattr(audio, 'tags') and audio.tags is not None:
                tags_to_remove = [tag for tag in audio.tags.values() if tag.FrameID == 'APIC']
                for tag in tags_to_remove:
                    del audio.tags[tag.FrameID]
                audio.save()
        except Exception as e:
            print(f"Error removing images from {self.filename}: {e}")

    def __str__(self):
        return f"Song(title={self.title}, artist={self.artist}, album={self.album}, year={self.year}, tracknumber={self.tracknumber}, genre={self.genre}, comment={self.comment}, albumartist={self.albumartist}, discnumber={self.discnumber})"
    
class Album:
    perferred_cover_paths = [
    "cover.jpg",
    "cover.jpeg",
    "cover.png",
    "folder.jpg",
    "folder.jpeg",
    "folder.png",
    "front.jpg",
    "front.jpeg",
    "front.png",
    ]

    image_exts = {".jpg", ".jpeg", ".png"}
    
    def __init__(self, album: str, albumartist: Optional[str] = None, year: Optional[str] = None):
        self.album: str = album
        self.albumartist: Optional[str] = albumartist
        self.year: Optional[str] = year
        self.songs: list[Song] = []
        self.cover_img: Optional[bytes] = None

    def add_song(self, song: Song) -> None:
        self.songs.append(song)

        #sort songs by tracknumber
        self.songs.sort(key=lambda s: s.tracknumber if s.tracknumber is not None else "")

    def load_cover_image(self) -> None:
        # Procedure 1: find image in folder
        for song in self.songs:
            folder = Path(song.filename).parent
            
            images = sorted(
                [
                    f for f in folder.iterdir()
                    if f.is_file()
                    and f.suffix.lower() in self.image_exts
                ]
            )

            for preferred in self.perferred_cover_paths:
                for img in images:
                    if img.name.lower() == preferred:
                        self.cover_img = img.read_bytes()
                        break

                if self.cover_img is not None:
                    break

            if self.cover_img is None and images:
                self.cover_img = images[0].read_bytes()

        if self.cover_img is not None:
            return

        # Procedure 2: find image in metadata
        for song in self.songs:
            try:
                audio = File(song.filename)
                if audio is not None and hasattr(audio, 'tags') and audio.tags is not None:
                    for tag in audio.tags.values():
                        if tag.FrameID == 'APIC':
                            self.cover_img = tag.data
                            return
            except Exception as e:
                print(f"Error loading cover image from {song.filename}: {e}")

def main():
    song_path = sys.argv[1] if len(sys.argv) > 1 else ""
    if song_path != "":
        song = Song(song_path)
        print(song)

if __name__ == "__main__":
    main()
