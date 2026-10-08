import shlex
import subprocess
from dataclasses import dataclass
from typing import Optional
import base64
from mutagen import File  # type: ignore
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus
from mutagen.monkeysaudio import MonkeysAudio
from mutagen.wavpack import WavPack
from mutagen.id3 import APIC  # type: ignore


def get_output_codec(ffmpeg_options: str, extension: str) -> Optional[str]:
    """Resolve the requested audio encoder, falling back to unambiguous formats."""
    aliases = {
        "libmp3lame": "mp3", "libshine": "mp3",
        "libfdk_aac": "aac", "libfaac": "aac",
        "libopus": "opus", "libvorbis": "vorbis",
        "libwavpack": "wavpack",
    }
    options = shlex.split(ffmpeg_options)
    codec = None
    for index, option in enumerate(options[:-1]):
        if option in ("-c", "-codec", "-acodec") or option.startswith(
            ("-c:a", "-codec:a")
        ):
            encoder = options[index + 1].lower()
            codec = aliases.get(encoder, encoder)
    if codec is not None:
        return codec
    return {
        "mp3": "mp3", "flac": "flac", "opus": "opus",
        "aac": "aac", "ape": "ape", "wv": "wavpack",
    }.get(extension.lower().lstrip("."))


@dataclass
class CoverArt:
    data: bytes
    mime: str
    description: str = ""


def get_cover_art(path: str) -> Optional[CoverArt]:
    audio = File(path)

    if audio is None:
        return None

    # MP3 / WAV using ID3 APIC frames
    if isinstance(audio, (MP3, WAVE)):
        if audio.tags is None:
            return None

        pictures = audio.tags.getall("APIC")

        if not pictures:
            return None

        # Prefer a front cover (ID3 picture type 3)
        picture = next(
            (picture for picture in pictures if picture.type == 3),
            pictures[0],
        )

        return CoverArt(
            data=picture.data,
            mime=picture.mime,
            description=picture.desc,
        )

    # FLAC
    if isinstance(audio, FLAC):
        if not audio.pictures:
            return None

        picture = next(
            (picture for picture in audio.pictures if picture.type == 3),
            audio.pictures[0],
        )

        return CoverArt(
            data=picture.data,
            mime=picture.mime,
            description=picture.desc,
        )

    # MP4 / M4A / ALAC
    if isinstance(audio, MP4):
        if audio.tags is None:
            return None

        covers = audio.tags.get("covr", [])

        if not covers:
            return None

        cover = covers[0]

        mime = "image/png" if cover.imageformat == cover.FORMAT_PNG else "image/jpeg"

        return CoverArt(
            data=bytes(cover),
            mime=mime,
        )

    # Ogg Vorbis / Opus
    if isinstance(audio, (OggVorbis, OggOpus)):
        if audio.tags is None:
            return None

        pictures = audio.tags.get("metadata_block_picture", [])

        if not pictures:
            return None

        try:
            picture = Picture(base64.b64decode(pictures[0]))
        except Exception:
            return None

        return CoverArt(
            data=picture.data,
            mime=picture.mime,
            description=picture.desc,
        )

    return None


def set_ogg_cover(audio, cover: CoverArt) -> None:
    if audio.tags is None:
        audio.add_tags()

    picture = Picture()
    picture.type = 3
    picture.mime = cover.mime
    picture.desc = cover.description
    picture.data = cover.data

    encoded = base64.b64encode(picture.write()).decode("ascii")

    audio["metadata_block_picture"] = [encoded]
    audio.save()


def set_flac_cover(audio: FLAC, cover: CoverArt) -> None:
    picture = Picture()
    picture.type = 3
    picture.mime = cover.mime
    picture.desc = cover.description
    picture.data = cover.data

    audio.clear_pictures()
    audio.add_picture(picture)
    audio.save()


def set_mp4_cover(audio: MP4, cover: CoverArt) -> None:
    if audio.tags is None:
        audio.add_tags()

    assert audio.tags is not None

    image_format = (
        MP4Cover.FORMAT_PNG if cover.mime == "image/png" else MP4Cover.FORMAT_JPEG
    )

    audio.tags["covr"] = [MP4Cover(cover.data, imageformat=image_format)]

    audio.save()


def set_id3_cover(audio: MP3 | WAVE, cover: CoverArt) -> None:
    if audio.tags is None:
        audio.add_tags()

    assert audio.tags is not None

    # Remove existing artwork
    audio.tags.delall("APIC")

    # Add front cover
    audio.tags.add(
        APIC(
            encoding=3,
            mime=cover.mime,
            type=3,  # Front cover
            desc=cover.description,
            data=cover.data,
        )
    )

    audio.save()


def set_apev2_cover(
    audio: MonkeysAudio | WavPack,
    cover: CoverArt,
) -> None:
    if audio.tags is None:
        audio.add_tags()

    assert audio.tags is not None

    extension = "png" if cover.mime == "image/png" else "jpg"

    audio.tags["Cover Art (Front)"] = (
        f"cover.{extension}".encode("utf-8") + b"\x00" + cover.data
    )

    audio.save()


def set_cover_art(audio: str, cover: CoverArt) -> None:
    audio_file = File(audio)

    if audio_file is None:
        raise ValueError(f"Unsupported audio file: {audio}")

    if isinstance(audio_file, FLAC):
        set_flac_cover(audio_file, cover)

    elif isinstance(audio_file, MP4):
        # M4A / MP4 / ALAC
        set_mp4_cover(audio_file, cover)

    elif isinstance(audio_file, (MP3, WAVE)):
        set_id3_cover(audio_file, cover)

    elif isinstance(audio_file, (OggVorbis, OggOpus)):
        set_ogg_cover(audio_file, cover)

    elif isinstance(audio_file, (MonkeysAudio, WavPack)):
        set_apev2_cover(audio_file, cover)

    else:
        raise ValueError(
            f"Cover art is not supported for {type(audio_file).__name__}: {audio}"
        )


def convert_audio(
    input_path: str,
    output_path: str,
    ffmpeg_options: str,
) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        # Only convert the main audio stream.
        "-map",
        "0:a:0",
        # Carry ordinary metadata into the converted file.
        "-map_metadata",
        "0",
        *shlex.split(ffmpeg_options),
        output_path,
    ]

    subprocess.run(command, check=True)
