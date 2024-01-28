from dataclasses import asdict
import json
import logging
import pathlib
import time

import yandex_music
from services.service import Service

from song import Song

_log = logging.getLogger(__name__)


class YandexLibrary(Service):
    def __init__(self, user_token) -> None:
        self.client = yandex_music.Client(user_token).init()

    def list_library(self, cache=True) -> list[Song]:
        refresh = False
        if cache:
            if not pathlib.Path("./cache").exists():
                pathlib.Path("./cache").mkdir()
            caches = pathlib.Path("./cache").glob("yandex_cache_*.json")
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
                caches = pathlib.Path("./cache").glob("yandex_cache_*.json")
                for cache in caches:
                    cache.unlink()
        _log.info("Requesting Yandex for library")
        songs = [track.fetch_track() for track in self.client.users_likes_tracks()]
        result = []
        for song in songs:
            title = song.title
            artists = ""
            for art in song.artists:
                artists += f"{art.name}, "
            album = song.albums[0].title
            cmp_song = Song(title, artists, album, None)
            result.append(cmp_song)
        with open(pathlib.Path(f"./cache/yandex_cache_{round(time.time())}.json").absolute(), "w", encoding="utf-8") as outf:
            outf.write(json.dumps([asdict(song) for song in result]))
        return result
    
    def add_to_library(self, query) -> bool:
        search = self.client.search(query, type_="track").tracks
        if search is None:
            return False
        best = search.results[0]
        return self.client.users_likes_tracks_add(best.track_id)

    def add_to_playlist(self, query, playlist_name="mixxer") -> bool:
        search = self.client.search(query, type_="track").tracks
        if search is None:
            return False
        best = search.results[0]
        target_playlist = None
        playlists = self.client.users_playlists_list()
        for playlist in playlists:
            if playlist.title == playlist_name:
                target_playlist = playlist
                break
        if target_playlist is None:
            target_playlist = self.client.users_playlists_create(playlist_name)
        return target_playlist.insert_track(best.track_id.split(":")[0], best.track_id.split(":")[1])
    
    def search(self, query) -> Song | None:
        search = self.client.search(query, type_="track").tracks
        if search is None:
            return None
        best = search.results[0]
        title = best.title
        artists = ""
        for art in best.artists:
            artists += f"{art.name}, "
        album = best.albums[0].title
        return Song(title, artists, album, None)
