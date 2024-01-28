import logging
import pathlib
import pickle
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
            caches = pathlib.Path("./cache").glob("yandex_cache_*.pkl")
            currtime = time.time()
            for cache in caches:
                cache_time = int(cache.name.split("_")[2].replace(".pkl", ""))
                if cache_time < currtime - 3600:
                    refresh = True
                else:
                    _log.info(f"Using cached songs at {cache_time}")
                    with open(cache.absolute(), 'rb') as inf:
                        return pickle.loads(inf.read())
            if refresh:
                _log.info("All caches are older than one hour, refreshing")
                caches = pathlib.Path("./cache").glob("yandex_cache_*.pkl")
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
            cmp_song = Song(title, artists, album, None, song)
            result.append(cmp_song)
        with open(pathlib.Path(f"./cache/yandex_cache_{round(time.time())}.pkl").absolute(), "wb") as outf:
            outf.write(pickle.dumps(result))
        return result
    
    def add_to_library(self, song: Song) -> bool:
        return self.client.users_likes_tracks_add(song.original_object.track_id)

    def add_to_playlist(self, song: Song, playlist_name="mixxer") -> bool:
        target_playlist = None
        playlists = self.client.users_playlists_list()
        for playlist in playlists:
            if playlist.title == playlist_name:
                target_playlist = playlist
                break
        if target_playlist is None:
            target_playlist = self.client.users_playlists_create(playlist_name)
        return target_playlist.insert_track(song.original_object.track_id.split(":")[0], song.original_object.track_id.split(":")[1])
    
    def search(self, query) -> Song | None:
        search = self.client.search(query, type_="track").tracks
        if search is None:
            return None
        results = []
        for item in search:
            title = item.title
            artists = ""
            for art in item.artists:
                artists += f"{art.name}, "
            album = item.albums[0].title
            results.append(Song(title, artists, album, None, item))
        return results
