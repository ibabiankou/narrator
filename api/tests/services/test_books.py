from io import BytesIO
from unittest.mock import MagicMock
import uuid

from api.models.narration import NarrationManifest, ContentFile, NavigationItem, AudioTrack
from api.services.books import BookService
from api.services.files import FileData
from common_lib.models.tts import FragmentGroups, FragmentGroup, TextFragment, PauseFragment, TrackManifest, FragmentDuration

books_service = BookService(None, None, None)


class TestBooksService:
    def test_master_playlist(self):
        id = uuid.UUID("84efd0c9-80b5-46f4-bf13-44b3726baf25")

        playlist = books_service._generate_master_playlist(id, "kokoro", "am_michael", has_subtitles=True)
        assert 'TYPE=SUBTITLES' in playlist
        assert f'/api/files/{id}/playlists/kokoro_am_michael_subs.m3u8' in playlist
        assert f'/api/files/{id}/playlists/kokoro_am_michael.m3u8' in playlist

        playlist_no_sub = books_service._generate_master_playlist(id, "kokoro", "am_michael", has_subtitles=False)
        assert 'TYPE=SUBTITLES' not in playlist_no_sub

    def test_format_vtt_timestamp(self):
        assert books_service._format_vtt_timestamp(0) == "00:00:00.000"
        assert books_service._format_vtt_timestamp(1.234) == "00:00:01.234"
        assert books_service._format_vtt_timestamp(65.5) == "00:01:05.500"
        assert books_service._format_vtt_timestamp(3661.009) == "01:01:01.009"

    def test_generate_track_vtt(self):
        track = TrackManifest(
            audio_key="book1/audio-files/kokoro/am_michael/0-2.aac",
            track_name="0-2",
            size_bytes=1000,
            timeline=[
                FragmentDuration(id=0, duration=2.5),
                FragmentDuration(id=1, duration=1.0),
                FragmentDuration(id=2, duration=3.0)
            ]
        )
        fragment_map = {
            0: TextFragment(id=0, text="First subtitle sentence."),
            1: PauseFragment(id=1, duration=1.0),
            2: TextFragment(id=2, text="Second subtitle sentence.")
        }
        vtt = books_service._generate_track_vtt(track, fragment_map)
        assert vtt.startswith("WEBVTT\n\n")
        assert "00:00:00.000 --> 00:00:02.500\nn-00000" in vtt
        assert "00:00:03.500 --> 00:00:06.500\nn-00002" in vtt

    def test_generate_subtitles_playlist(self):
        tracks = [
            TrackManifest(
                audio_key="book1/audio-files/kokoro/am_michael/0-2.aac",
                track_name="0-2",
                size_bytes=1000,
                timeline=[FragmentDuration(id=0, duration=2.5), FragmentDuration(id=2, duration=3.0)]
            )
        ]
        playlist = books_service._generate_subtitles_playlist(tracks)
        assert "#EXTM3U" in playlist
        assert "#EXT-X-VERSION:4" in playlist
        assert "#EXT-X-ENDLIST" in playlist
        assert "/api/files/book1/audio-files/kokoro/am_michael/0-2.vtt" in playlist
        assert "#EXTINF:5.5," in playlist

    def test_generate_subtitles_end_to_end(self):
        book_id = uuid.uuid4()
        manifest = NarrationManifest([
            ContentFile(
                href="chapter1.xhtml",
                title="Chapter 1",
                navigation_items=[
                    NavigationItem(
                        title="Chapter 1",
                        audio_tracks=[
                            AudioTrack(
                                name="0-1",
                                fragment_groups=FragmentGroups([
                                    FragmentGroup([
                                        TextFragment(id=0, text="Hello world!"),
                                        TextFragment(id=1, text="Welcome to audio book.")
                                    ])
                                ])
                            )
                        ]
                    )
                ]
            )
        ])

        track_manifest = TrackManifest(
            audio_key=f"{book_id}/audio-files/kokoro/am_michael/0-1.aac",
            track_name="0-1",
            size_bytes=2000,
            timeline=[
                FragmentDuration(id=0, duration=1.5),
                FragmentDuration(id=1, duration=2.0)
            ]
        )

        mock_files = MagicMock()
        mock_files.get_book_file.return_value = BytesIO(manifest.model_dump_json().encode())
        mock_files.list_files.return_value = [f"{book_id}/audio-files/kokoro/am_michael/0-1.json"]
        mock_files.get_object.return_value = FileData(
            body=track_manifest.model_dump_json().encode(),
            content_type="application/json",
            etag="123",
            range=None
        )

        uploaded_files = {}
        def mock_upload(key, body):
            data = body.getvalue() if hasattr(body, 'getvalue') else body
            uploaded_files[key] = data

        mock_files.upload_file.side_effect = mock_upload

        books_service.files_service = mock_files
        books_service._generate_subtitles(book_id)

        # Verify VTT uploaded
        vtt_key = f"{book_id}/audio-files/kokoro/am_michael/0-1.vtt"
        assert vtt_key in uploaded_files
        vtt_text = uploaded_files[vtt_key].decode("utf-8")
        assert "00:00:00.000 --> 00:00:01.500\nn-00000" in vtt_text
        assert "00:00:01.500 --> 00:00:03.500\nn-00001" in vtt_text

        # Verify subtitles playlist uploaded
        sub_key = f"{book_id}/playlists/kokoro_am_michael_subs.m3u8"
        assert sub_key in uploaded_files
        sub_text = uploaded_files[sub_key].decode("utf-8")
        assert f"/api/files/{book_id}/audio-files/kokoro/am_michael/0-1.vtt" in sub_text

        # Verify master playlist updated
        master_key = f"{book_id}/playlists/master.m3u8"
        assert master_key in uploaded_files
        master_text = uploaded_files[master_key].decode("utf-8")
        assert f"/api/files/{book_id}/playlists/kokoro_am_michael_subs.m3u8" in master_text

    def test_generate_subtitles_multiple_tracks(self):
        book_id = uuid.uuid4()
        manifest = NarrationManifest([
            ContentFile(
                href="chapter1.xhtml",
                title="Chapter 1",
                navigation_items=[
                    NavigationItem(
                        title="Chapter 1",
                        audio_tracks=[
                            AudioTrack(
                                name="0-1",
                                fragment_groups=FragmentGroups([
                                    FragmentGroup([
                                        TextFragment(id=0, text="Track 1 text 1"),
                                        TextFragment(id=1, text="Track 1 text 2")
                                    ])
                                ])
                            ),
                            AudioTrack(
                                name="2-3",
                                fragment_groups=FragmentGroups([
                                    FragmentGroup([
                                        TextFragment(id=2, text="Track 2 text 1"),
                                        TextFragment(id=3, text="Track 2 text 2")
                                    ])
                                ])
                            )
                        ]
                    )
                ]
            )
        ])

        track_1 = TrackManifest(
            audio_key=f"{book_id}/audio-files/kokoro/am_michael/0-1.aac",
            track_name="0-1",
            size_bytes=2000,
            timeline=[
                FragmentDuration(id=0, duration=1.0),
                FragmentDuration(id=1, duration=2.0)
            ]
        )
        track_2 = TrackManifest(
            audio_key=f"{book_id}/audio-files/kokoro/am_michael/2-3.aac",
            track_name="2-3",
            size_bytes=3000,
            timeline=[
                FragmentDuration(id=2, duration=3.0),
                FragmentDuration(id=3, duration=4.0)
            ]
        )

        mock_files = MagicMock()
        mock_files.get_book_file.return_value = BytesIO(manifest.model_dump_json().encode())
        mock_files.list_files.return_value = [
            f"{book_id}/audio-files/kokoro/am_michael/2-3.json",
            f"{book_id}/audio-files/kokoro/am_michael/0-1.json",
        ]
        def get_obj(key):
            if "0-1.json" in key:
                return FileData(body=track_1.model_dump_json().encode(), content_type="application/json", etag="1", range=None)
            elif "2-3.json" in key:
                return FileData(body=track_2.model_dump_json().encode(), content_type="application/json", etag="2", range=None)
            return None

        mock_files.get_object.side_effect = get_obj

        uploaded_files = {}
        def mock_upload(key, body):
            data = body.getvalue() if hasattr(body, 'getvalue') else body
            uploaded_files[key] = data

        mock_files.upload_file.side_effect = mock_upload

        books_service.files_service = mock_files
        books_service._generate_subtitles(book_id)

        # Both VTT files generated
        assert f"{book_id}/audio-files/kokoro/am_michael/0-1.vtt" in uploaded_files
        assert f"{book_id}/audio-files/kokoro/am_michael/2-3.vtt" in uploaded_files

        # Subtitles playlist has both tracks in sorted order
        sub_text = uploaded_files[f"{book_id}/playlists/kokoro_am_michael_subs.m3u8"].decode("utf-8")
        idx_1 = sub_text.index("0-1.vtt")
        idx_2 = sub_text.index("2-3.vtt")
        assert idx_1 < idx_2

    def test_generate_subtitles_no_tracks(self):
        book_id = uuid.uuid4()
        manifest = NarrationManifest([])

        mock_files = MagicMock()
        mock_files.get_book_file.return_value = BytesIO(manifest.model_dump_json().encode())
        mock_files.list_files.return_value = []

        uploaded_files = {}
        mock_files.upload_file.side_effect = lambda k, b: uploaded_files.update({k: b})

        books_service.files_service = mock_files
        books_service._generate_subtitles(book_id)

        assert len(uploaded_files) == 0
