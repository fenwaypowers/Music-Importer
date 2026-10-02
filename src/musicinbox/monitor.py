from pathlib import Path
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Audio formats we care about
AUDIO_EXTS = {
    ".flac",
    ".mp3",
    ".m4a",
    ".aac",
    ".ogg",
    ".opus",
    ".wav",
    ".alac",
    ".ape",
    ".wv",
    ".mp4",
    ".mka",
}


class AudioWatcher(FileSystemEventHandler):
    def __init__(self, callback, settle_time=5.0):
        """
        callback(path: Path) -> None
        """

        self.callback = callback
        self.settle_time = settle_time
        self.processing = set()

    def on_created(self, event):
        if event.is_directory:
            return

        self._handle(Path(str(event.src_path)))

    def on_moved(self, event):
        if event.is_directory:
            return

        self._handle(Path(str(event.dest_path)))

    def _handle(self, path: Path):

        path = path.resolve()

        if path.suffix.lower() not in AUDIO_EXTS:
            return

        if path.name.startswith("."):
            return

        if path.name.startswith("~"):
            return

        if path in self.processing:
            return

        self.processing.add(path)

        try:

            print(f"Detected {path}")

            if wait_until_complete(path, self.settle_time):
                self.callback(path)
            else:
                print(f"Timed out waiting for {path}")

        finally:
            self.processing.remove(path)


def wait_until_complete(path: Path, stable_seconds: float = 5, timeout: float = 600):
    """
    Wait until the file size has stopped changing.
    """

    start = time.time()

    previous_size = -1
    stable_since = None

    while True:

        if not path.exists():
            return False

        try:
            size = path.stat().st_size
        except PermissionError:
            time.sleep(1)
            continue

        if size == previous_size:

            if stable_since is None:
                stable_since = time.time()

            if time.time() - stable_since >= stable_seconds:
                return True

        else:

            previous_size = size
            stable_since = None

        if time.time() - start > timeout:
            return False

        time.sleep(1)


def start_watch(folder, callback):
    """
    Blocks forever.
    """

    folder = Path(folder).resolve()

    observer = Observer()

    observer.schedule(
        AudioWatcher(callback),
        str(folder),
        recursive=True,
    )

    observer.start()

    print(f"Watching {folder}")

    try:

        while True:
            time.sleep(1)

    except KeyboardInterrupt:

        observer.stop()

    observer.join()


if __name__ == "__main__":

    def demo(path):
        print("READY:", path)

    start_watch(
        r"D:\Incoming",
        demo,
    )
