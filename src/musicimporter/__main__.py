import argparse
from pathlib import Path
from .models import Song

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


def confirm_delete() -> bool:
    response = input("\nDelete the original files? [y/N]: ").strip().lower()

    return response in ("y", "yes")


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

    parser.add_argument(
        "--force-reencode",
        "-fr",
        action="store_true",
        help="Apply --convert options even when the source codec already matches",
    )

    parser.add_argument(
        "--delete",
        "-d",
        action="store_true",
        help="Delete original files after a successful import without prompting",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    input_dir: Path = args.input
    destination_dir: Path = args.destination

    imported_files: list[Song] = []
    song_count = 0

    if not input_dir.is_dir():
        raise SystemExit(f"Input directory does not exist: {input_dir}")

    if args.convert and not args.output_extension:
        raise SystemExit("--output-extension is required when using --convert")
    if args.force_reencode and not args.convert:
        raise SystemExit("--force-reencode requires --convert")

    # Find and load audio files.
    for path in input_dir.rglob("*"):
        if not path.is_file():
            continue

        try:
            song = Song(str(path))
            add_to_album(song)
            song_count += 1
        except Exception as e:
            print(f"Skipping {path}: {e}")

    if not albums:
        print("No audio files found.")
        return

    # Export albums.
    for album in albums:
        album.resolve_settings(
            ffmpeg_options=args.convert or "-c:a copy",
            extension=args.output_extension or "copy",
        )
        exported_files = album.export(
            str(destination_dir),
            force_reencode=args.force_reencode,
        )

        imported_files.extend(exported_files)

    print("\n----------------\n")

    if imported_files:
        print(f"Imported {len(imported_files)} files.")

        failed_count = song_count - len(imported_files)

        if failed_count == 1:
            print("1 file failed.")
        else:
            print(f"{failed_count} files failed.")

        should_delete = args.delete or confirm_delete()

        if should_delete:
            for song in imported_files:
                try:
                    Path(song.path).unlink()
                except OSError as e:
                    print(f"Could not delete {song.path}: {e}")
    else:
        print("No files were imported.")


if __name__ == "__main__":
    main()
