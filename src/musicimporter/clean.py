from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus
from mutagen.wave import WAVE
from mutagen.monkeysaudio import MonkeysAudio
from mutagen.wavpack import WavPack
from mutagen import File  # type: ignore

# ---------------------------------------------------------------------------
# Vorbis comments
# Used by FLAC, Ogg Vorbis, and Opus
# ---------------------------------------------------------------------------

VORBIS_KEEP = {
    "title",
    "artist",
    "albumartist",
    "album",
    "date",
    "year",
    "tracknumber",
    "tracktotal",
    "totaltracks",
    "discnumber",
    "disctotal",
    "totaldiscs",
    "genre",
    "composer",
    # Cover art
    "metadata_block_picture",
    # Older/nonstandard cover-art convention
    "coverart",
    "coverartmime",
}


def _clean_vorbis_comments(audio):
    if audio.tags is None:
        return

    for key in list(audio.tags.keys()):
        if key.lower() not in VORBIS_KEEP:
            del audio.tags[key]

    audio.save()


def clean_flac(file):
    audio = FLAC(file)

    # FLAC pictures are normally stored separately in FLAC picture blocks,
    # so modifying audio.tags does NOT remove audio.pictures.
    _clean_vorbis_comments(audio)


def clean_ogg(file):
    audio = OggVorbis(file)
    _clean_vorbis_comments(audio)


def clean_opus(file):
    audio = OggOpus(file)
    _clean_vorbis_comments(audio)


# ---------------------------------------------------------------------------
# ID3
# Used by MP3 and, with Mutagen, WAV
# ---------------------------------------------------------------------------

ID3_KEEP = {
    "TIT2",  # title
    "TPE1",  # artist
    "TPE2",  # album artist
    "TALB",  # album
    "TDRC",  # recording date/year
    "TRCK",  # track number / total
    "TPOS",  # disc number / total
    "TCON",  # genre
    "TCOM",  # composer
    "APIC",  # cover art
}


def _clean_id3(audio):
    if audio.tags is None:
        return

    tags = audio.tags

    for key in list(tags.keys()):
        # Some ID3 keys look like:
        # APIC:
        # APIC:Cover
        # TXXX:Something
        #
        # We only care about the actual frame ID before the colon.
        frame_id = key.split(":", 1)[0]

        if frame_id not in ID3_KEEP:
            del tags[key]

    # Mutagen can retain raw ID3 frames that it doesn't recognize.
    # Since the purpose here is to strip everything not explicitly
    # whitelisted, get rid of those too.
    if hasattr(tags, "unknown_frames"):
        tags.unknown_frames.clear()


def clean_mp3(file):
    audio = MP3(file)

    _clean_id3(audio)

    if audio.tags is not None:
        # v1=0 also removes any old ID3v1 tag.
        audio.save(v1=0)


def clean_wav(file):
    audio = WAVE(file)

    _clean_id3(audio)

    if audio.tags is not None:
        audio.save()


# ---------------------------------------------------------------------------
# APEv2
# Used by Monkey's Audio (.ape) and WavPack (.wv)
# ---------------------------------------------------------------------------

APE_KEEP = {
    "title",
    "artist",
    # Both variants occur in the wild.
    "album artist",
    "albumartist",
    "album",
    "year",
    "date",
    "track",
    "tracknumber",
    "tracktotal",
    "totaltracks",
    "disc",
    "discnumber",
    "disctotal",
    "totaldiscs",
    "genre",
    "composer",
}


def _clean_apev2(audio):
    if audio.tags is None:
        return

    for key in list(audio.tags.keys()):
        normalized = key.casefold()

        # APEv2 artwork is commonly named:
        # "Cover Art (Front)"
        # "Cover Art (Back)"
        is_cover = normalized.startswith("cover art (")

        if normalized not in APE_KEEP and not is_cover:
            del audio.tags[key]

    audio.save()


def clean_ape(file):
    audio = MonkeysAudio(file)
    _clean_apev2(audio)


def clean_wv(file):
    audio = WavPack(file)
    _clean_apev2(audio)


def clean_mp4(file):
    audio = File(file)

    if audio is None or audio.tags is None:
        return

    keep = {
        "\xa9nam",  # title
        "\xa9ART",  # artist
        "aART",  # album artist
        "\xa9alb",  # album
        "\xa9day",  # year
        "trkn",  # track
        "disk",  # disc
        "\xa9gen",  # genre
        "\xa9wrt",  # composer
        "covr",  # cover
    }

    tags = audio.tags

    for key in list(tags.keys()):
        if key not in keep:
            del tags[key]

    audio.save()


def clean_audio(file):
    audio = File(file)

    if audio is None:
        raise ValueError(f"Unsupported or unrecognized audio file: {file}")

    if isinstance(audio, MP4):
        # Includes .m4a/.mp4 AAC and ALAC
        clean_mp4(file)

    elif isinstance(audio, FLAC):
        clean_flac(file)

    elif isinstance(audio, MP3):
        clean_mp3(file)

    elif isinstance(audio, OggVorbis):
        clean_ogg(file)

    elif isinstance(audio, OggOpus):
        clean_opus(file)

    elif isinstance(audio, WAVE):
        clean_wav(file)

    elif isinstance(audio, MonkeysAudio):
        clean_ape(file)

    elif isinstance(audio, WavPack):
        clean_wv(file)

    else:
        raise ValueError(
            f"Recognized audio format, but no cleaner is implemented for "
            f"{type(audio).__name__}: {file}"
        )
