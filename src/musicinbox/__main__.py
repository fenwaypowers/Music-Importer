import argparse
from pathlib import Path

from .models import Album, Song

albums: list[Album] = []

def add_to_album(song) -> None:
    for album in albums:
        if album.album == song.album:
            album.add_song(song)
            return

    new_album = Album(song.album)
    new_album.add_song(song)
    albums.append(new_album)

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="musicimporter",
        description="Import, organize, and optionally convert music.",
    )

    parser.add_argument(
        "input",
        type=Path,
        help="Directory containing music to import",
    )

    parser.add_argument(
        "destination",
        type=Path,
        help="Destination music library",
    )

    parser.add_argument(
        "--convert",
        "-c",
        type=str,
        help='FFmpeg audio options, e.g. "-c:a libfdk_aac -vbr 4"',
    )

    parser.add_argument(
        "--output-extension",
        "--extension",
        "-e",
        type=str,
        help="Output extension when converting, e.g. m4a",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    input_dir: Path = args.input
    destination_dir: Path = args.destination

    if not input_dir.is_dir():
        raise SystemExit(f"Input directory does not exist: {input_dir}")

    if args.convert and not args.output_extension:
        raise SystemExit(
            "--output-extension is required when using --convert"
        )

    if args.output_extension and not args.convert:
        raise SystemExit(
            "--output-extension can only be used with --convert"
        )

    # Find and load audio files.
    for path in input_dir.rglob("*"):
        if not path.is_file():
            continue

        try:
            song = Song(str(path))
            add_to_album(song)
        except Exception as e:
            print(f"Skipping {path}: {e}")

    if not albums:
        print("No audio files found.")
        return

    # Export albums.
    for album in albums:
        if args.convert:
            album.export(
                str(destination_dir),
                extension=args.output_extension,
                ffmpeg_options=args.convert,
            )
        else:
            album.export(
                str(destination_dir),
                extension = args.output_extension if args.output_extension else "copy",
            )


if __name__ == "__main__":
    main()
