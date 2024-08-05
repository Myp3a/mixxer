import logging
import pathlib
import pickle
import time

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from services.service import Service
from song import Song

_log = logging.getLogger(__name__)


class SpotifyLibrary(Service):
    def __init__(self, client_id, client_secret) -> None:
        scopes = (
            "playlist-modify-private,playlist-read-private,user-library-modify,user-library-read"
        )
        self.client = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                scope=scopes,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri="http://localhost:1234",
                show_dialog=True,
                open_browser=False,
            )
        )

    def invalidate_cache(self) -> None:
        caches = pathlib.Path("./cache").glob("spotify_cache_*.pkl")
        for cache in caches:
            cache.unlink()

    def list_library(self, cache=True) -> list[Song]:
        refresh = False
        if cache:
            if not pathlib.Path("./cache").exists():
                pathlib.Path("./cache").mkdir()
            caches = pathlib.Path("./cache").glob("spotify_cache_*.pkl")
            currtime = time.time()
            for cache in caches:
                cache_time = int(cache.name.split("_")[2].replace(".pkl", ""))
                if cache_time < currtime - 3600:
                    refresh = True
                else:
                    _log.info(f"Using cached songs at {cache_time}")
                    with open(cache.absolute(), "rb") as inf:
                        return pickle.loads(inf.read())
            if refresh:
                _log.info("All caches are older than one hour, refreshing")
                caches = pathlib.Path("./cache").glob("spotify_cache_*.pkl")
                for cache in caches:
                    cache.unlink()
        _log.info("Requesting Spotify for library")
        songs = []
        cntr = 0
        while True:
            part_songs = self.client.current_user_saved_tracks(limit=50, offset=cntr * 50)
            cntr += 1
            songs.extend(part_songs["items"])
            if not part_songs.get("next", False):
                break
        result = []
        for song in songs:
            cmp_song = Song(
                song["track"]["name"],
                song["track"]["artists"][0]["name"],
                song["track"]["album"]["name"],
                song["track"]["external_ids"].get("isrc", None),
                song["track"],
            )
            result.append(cmp_song)
        with open(
            pathlib.Path(f"./cache/spotify_cache_{round(time.time())}.pkl").absolute(), "wb"
        ) as outf:
            outf.write(pickle.dumps(result))
        return result

    def add_to_library(self, song: Song) -> bool:
        self.invalidate_cache()
        return self.client.current_user_saved_tracks_add([song.original_object["id"]])

    def add_to_playlist(self, song: Song, playlist_name="mixxer") -> bool:
        target_playlist = None
        playlists = self.client.current_user_playlists()
        for playlist in playlists["items"]:
            if playlist["name"] == playlist_name:
                target_playlist = playlist
                break
        if target_playlist is None:
            user_id = self.client.me()["id"]
            target_playlist = self.client.user_playlist_create(
                user_id, name=playlist_name, public=False
            )
        return self.client.playlist_add_items(target_playlist["id"], [song.original_object["id"]])

    def search(self, query) -> Song | None:
        search = self.client.search(query)["tracks"]["items"]
        if search == []:
            return None
        results = []
        for song in search:
            name = song["name"]
            artist = song["artists"][0]["name"]
            album = song["album"]["name"]
            try:
                isrc = song["external_ids"]["isrc"]
            except:
                isrc = None
            results.append(Song(name, artist, album, isrc, song))
        return results
