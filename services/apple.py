import json
import logging
import pathlib
import time

from dataclasses import asdict

import applemusic

from services.service import Service
from song import Song

_log = logging.getLogger(__name__)


class AppleLibrary(Service):
    def __init__(self, dev_token, user_token) -> None:
        self.client = applemusic.ApiClient(dev_token, user_token)

    def list_library(self, cache=True) -> list[Song]:
        refresh = False
        if cache:
            if not pathlib.Path("./cache").exists():
                pathlib.Path("./cache").mkdir()
            caches = pathlib.Path("./cache").glob("apple_cache_*.json")
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
                caches = pathlib.Path("./cache").glob("apple_cache_*.json")
                for cache in caches:
                    cache.unlink()
        _log.info("Requesting Apple for library")
        songs = self.client.library.songs()
        result = []
        for song in songs:
            try:
                catalog_song = song.get_catalog_song()
            except applemusic.AppleMusicAPIException:
                catalog_song = None
            if catalog_song is not None:
                cmp_song = Song(catalog_song.name, catalog_song.artist_name, catalog_song.album_name, catalog_song.isrc)
            else:
                cmp_song = Song(song.name, song.artist_name, song.album_name, None)
            result.append(cmp_song)
        with open(pathlib.Path(f"./cache/apple_cache_{round(time.time())}.json").absolute(), "w", encoding="utf-8") as outf:
            outf.write(json.dumps([asdict(song) for song in result]))
        return result
    
    def add_to_library(self, query) -> bool:
        search = self.client.catalog.search(query, applemusic.models.meta.CatalogTypes.Songs)
        if search == []:
            return False
        best = search[0]
        return self.client.library.add(best)

    def add_to_playlist(self, query, playlist_name="mixxer") -> bool:
        search = self.client.catalog.search(query, applemusic.models.meta.CatalogTypes.Songs)
        if search == []:
            return False
        best = search[0]
        target_playlist = None
        playlists = self.client.playlist.list_playlists()
        for playlist in playlists:
            if playlist.name == playlist_name:
                target_playlist = playlist
                break
        if target_playlist is None:
            target_playlist = self.client.playlist.create_playlist("mixxer")
        return target_playlist.add_songs([best])

    def search(self, query) -> Song | None:
        search = self.client.catalog.search(query, applemusic.models.meta.CatalogTypes.Songs)
        if search == []:
            return None
        best = search[0]
        return Song(best.name, best.artist_name, best.album_name, best.isrc)
