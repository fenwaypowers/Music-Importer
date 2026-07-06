from mutagen._file import File
from typing import Optional

class Song:
    def __init__(self, path: str):
        self.filename: str = path
        self.title: Optional[str] = None
        self.artist: Optional[str] = None
        self.album: Optional[str] = None
        self.year: Optional[str] = None
        self.track_number: Optional[str] = None
        self.genre: Optional[str] = None
        self.comment: Optional[str] = None
        self.album_artist: Optional[str] = None
        self.disc_number: Optional[str] = None
        self.cover_img: Optional[bytes] = None
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
                self.track_number = audio.get('tracknumber', [None])[0]
                self.genre = audio.get('genre', [None])[0]
                self.comment = audio.get('comment', [None])[0]
                self.album_artist = audio.get('albumartist', [None])[0]
                self.disc_number = audio.get('discnumber', [None])[0]

                # Attempt to load cover image
                if 'APIC:' in audio:
                    self.cover_img = audio['APIC:'].data
        except Exception as e:
            print(f"Error loading metadata for {self.filename}: {e}")
        
        self.metadata_loaded = True

    def __str__(self):
        return f"Song(title={self.title}, artist={self.artist}, album={self.album}, year={self.year}, track_number={self.track_number}, genre={self.genre}, comment={self.comment}, album_artist={self.album_artist}, disc_number={self.disc_number})"
    
def main():
    song_path = input("Enter the path to a song file to check its metadata: ")
    song = Song(song_path)
    print(song)

if __name__ == "__main__":
    main()
