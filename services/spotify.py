import json
import logging
import pathlib
import time

from dataclasses import asdict

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from services.service import Service
from song import Song

_log = logging.getLogger(__name__)


class SpotifyLibrary(Service):
    def __init__(self, client_id, client_secret) -> None:
        scopes = "playlist-modify-private,playlist-read-private,user-library-modify,user-library-read"
        self.client = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scopes, client_id=client_id, client_secret=client_secret, redirect_uri="http://localhost:1234", show_dialog=True, open_browser=False))

    def list_library(self, cache=True) -> list[Song]:
        refresh = False
        if cache:
            if not pathlib.Path("./cache").exists():
                pathlib.Path("./cache").mkdir()
            caches = pathlib.Path("./cache").glob("spotify_cache_*.json")
            currtime = time.time()
            for cache in caches:
                cache_time = int(cache.name.split("_")[2].replace(".json", ""))
                if cache_time < currtime - 3600:
                    refresh = True
                else:
                    _log.info(f"Using cached songs at {cache_time}")
                    with open(cache.absolute(), 'r', encoding="utf-8") as inf:
                        return [Song(**js) for js in json.loads(inf.readline())]
            if refresh:
                _log.info("All caches are older than one hour, refreshing")
                caches = pathlib.Path("./cache").glob("spotify_cache_*.json")
                for cache in caches:
                    cache.unlink()
        _log.info("Requesting Spotify for library")
        songs = []
        cntr = 0
        while True:
            part_songs = self.client.current_user_saved_tracks(limit=50, offset=cntr*50)
            cntr += 1
            songs.extend(part_songs["items"])
            if not part_songs.get("next", False):
                break
        result = []
        for song in songs:
            cmp_song = Song(song["track"]["name"], song["track"]["artists"][0]["name"], song["track"]["album"]["name"], song["track"]["external_ids"]["isrc"])
            result.append(cmp_song)
        with open(pathlib.Path(f"./cache/spotify_cache_{round(time.time())}.json").absolute(), "w", encoding="utf-8") as outf:
            outf.write(json.dumps([asdict(song) for song in result]))
        return result
    
    def add_to_library(self, query) -> bool:
        search = self.client.search(query)["tracks"]["items"]
        if search == []:
            return False
        best = search[0]
        return self.client.current_user_saved_tracks_add([best["id"]])

    def add_to_playlist(self, query, playlist_name="mixxer") -> bool:
        search = self.client.search(query)["tracks"]["items"]
        if search == []:
            return False
        best = search[0]
        target_playlist = None
        playlists = self.client.current_user_playlists()
        for playlist in playlists["items"]:
            if playlist["name"] == playlist_name:
                target_playlist = playlist
                break
        if target_playlist is None:
            user_id = self.client.me()['id']
            target_playlist = self.client.user_playlist_create(user_id, name=playlist_name,public=False)
        return self.client.playlist_add_items(target_playlist["id"], [best["id"]])

    def search(self, query) -> Song | None:
        search = self.client.search(query)["tracks"]["items"]
        if search == []:
            return None
        best = search[0]
        return Song(best["name"], best["artists"][0]["name"], best["album"]["name"], best["external_ids"]["isrc"])
