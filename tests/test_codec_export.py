import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from mutagen.mp3 import EasyMP3
from mutagen.easymp4 import EasyMP4
from mutagen.flac import FLAC
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis
from mutagen.wave import WAVE

from musicimporter.convert import get_output_codec
from musicimporter.models import Album, Song
from musicimporter.__main__ import parse_arguments


class CodecTests(unittest.TestCase):
    def test_source_codecs(self):
        for audio_type, info, expected in (
            (EasyMP3, {}, "mp3"),
            (FLAC, {}, "flac"),
            (OggOpus, {}, "opus"),
            (OggVorbis, {}, "vorbis"),
            (EasyMP4, {"codec": "mp4a.40.2"}, "aac"),
            (EasyMP4, {"codec": "alac"}, "alac"),
            (WAVE, {"audio_format": 1, "bits_per_sample": 16}, "pcm_s16le"),
            (WAVE, {"audio_format": 3, "bits_per_sample": 32}, "pcm_f32le"),
        ):
            with self.subTest(codec=expected):
                audio = Mock(spec=audio_type)
                audio.get.return_value = [None]
                audio.info = SimpleNamespace(**info)
                with patch("musicimporter.models.File", return_value=audio):
                    self.assertEqual(Song("song.audio").codec, expected)

    def test_encoder_takes_precedence_over_container(self):
        self.assertEqual(get_output_codec("-c:a alac", "m4a"), "alac")
        self.assertEqual(get_output_codec("-c:a libfdk_aac -vbr 4", "m4a"), "aac")
        self.assertEqual(get_output_codec("-codec:a:0 libmp3lame", "mp3"), "mp3")
        self.assertEqual(get_output_codec("-c:a copy", "mp3"), "copy")
        self.assertEqual(get_output_codec("-c:a unknown", "mp3"), "unknown")
        self.assertIsNone(get_output_codec("-b:a 128k", "m4a"))

    def export(self, codecs, options, extension, force=False):
        album = Album("Album")
        album.resolve_settings(options, extension)
        album.resolved = True
        album.songs = [
            Mock(path=f"track{i}.{suffix}", codec=codec, title=f"Track {i}",
                 tracknumber=i, discnumber=None)
            for i, (codec, suffix) in enumerate(codecs, 1)
        ]
        with tempfile.TemporaryDirectory() as destination:
            with patch("musicimporter.models.convert_audio") as convert:
                with patch.object(album, "resolve_settings") as resolve:
                    album.export(destination, force_reencode=force)
                    resolve.assert_not_called()
                return convert.call_args_list

    def test_mixed_album_copies_only_matching_tracks(self):
        calls = self.export([("mp3", "mp3"), ("flac", "flac"), (None, "mp3")],
                            "-c:a libmp3lame -b:a 192k", "mp3")
        self.assertEqual([call.args[2] for call in calls],
                         ["-c:a copy", "-c:a libmp3lame -b:a 192k",
                          "-c:a libmp3lame -b:a 192k"])

    def test_force_reencode(self):
        calls = self.export([("mp3", "mp3")], "-c:a libmp3lame", "mp3", True)
        self.assertEqual(calls[0].args[2], "-c:a libmp3lame")

    def test_aac_and_alac_are_different(self):
        calls = self.export([("alac", "m4a"), ("aac", "m4a")],
                            "-c:a aac", "m4a")
        self.assertEqual([call.args[2] for call in calls], ["-c:a aac", "-c:a copy"])

    def test_copy_preserves_each_extension(self):
        calls = self.export([("mp3", "mp3"), ("flac", "flac")], "-c:a copy", "copy")
        self.assertEqual([Path(call.args[1]).suffix for call in calls], [".mp3", ".flac"])

    def test_cli_force_reencode(self):
        with patch("sys.argv", ["musicimporter", "inbox", "library",
                                "--convert=-c:a libmp3lame", "-e", "mp3", "--force-reencode"]):
            self.assertTrue(parse_arguments().force_reencode)


if __name__ == "__main__":
    unittest.main()
