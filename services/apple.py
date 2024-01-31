import logging
import pathlib
import pickle
import time

import applemusic

from services.service import Service
from song import Song

_log = logging.getLogger(__name__)


class AppleLibrary(Service):
    def __init__(self, dev_token, user_token) -> None:
        self.client = applemusic.ApiClient(dev_token, user_token)

    def invalidate_cache(self) -> None:
        caches = pathlib.Path("./cache").glob("apple_cache_*.pkl")
        for cache in caches:
            cache.unlink()

    def list_library(self, cache=True) -> list[Song]:
        refresh = False
        if cache:
            if not pathlib.Path("./cache").exists():
                pathlib.Path("./cache").mkdir()
            caches = pathlib.Path("./cache").glob("apple_cache_*.pkl")
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
                caches = pathlib.Path("./cache").glob("apple_cache_*.pkl")
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
                cmp_song = Song(
                    catalog_song.name,
                    catalog_song.artist_name,
                    catalog_song.album_name,
                    catalog_song.isrc,
                    catalog_song,
                )
            else:
                cmp_song = Song(song.name, song.artist_name, song.album_name, None, song)
            result.append(cmp_song)
        with open(
            pathlib.Path(f"./cache/apple_cache_{round(time.time())}.pkl").absolute(), "wb"
        ) as outf:
            outf.write(pickle.dumps(result))
        return result

    def add_to_library(self, song: Song) -> bool:
        self.invalidate_cache()
        return self.client.library.add(song.original_object)

    def add_to_playlist(self, song: Song, playlist_name="mixxer") -> bool:
        target_playlist = None
        playlists = self.client.playlist.list_playlists()
        for playlist in playlists:
            if playlist.name == playlist_name:
                target_playlist = playlist
                break
        if target_playlist is None:
            target_playlist = self.client.playlist.create_playlist("mixxer")
        return target_playlist.add_songs([song.original_object])

    def search(self, query) -> Song | None:
        search = self.client.catalog.search(query, applemusic.models.meta.CatalogTypes.Songs)
        if search == []:
            return None
        results = []
        for result in search:
            results.append(
                Song(result.name, result.artist_name, result.album_name, result.isrc, result)
            )
        return results
