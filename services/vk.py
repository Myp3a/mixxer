import logging
import pathlib
import pickle
import time
from functools import wraps

import requests

from services.service import Service
from song import Song

_log = logging.getLogger(__name__)


class Session:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers = {
            "User-Agent": (
                "KateMobileAndroid/110.2 lite-553 (Android 13; SDK 33; arm64-v8a; Xiaomi"
                " M2102K1G; en)"
            )
        }

    def _request(self, func, *args, **kwargs) -> requests.Response:
        done = False
        while not done:
            _log.debug("Doing network request with %s", func)
            with func(*args, **kwargs) as resp:
                _log.debug("Got response with code %s", resp.status_code)
                js = resp.json()
                if js.get("error", False):
                    if js["error"]["error_code"] == 6:
                        _log.warning("Got ratelimited, sleeping a bit")
                        time.sleep(1)
                    elif js["error"]["error_code"] == 14:
                        _log.warning("Got captcha, sleeping for 10s")
                        time.sleep(10)
                    else:
                        error = resp.json()["error"]
                        print(error)
                        assert error is None, error["error_msg"]
                else:
                    done = True
                    return resp

    @wraps(requests.get)
    def get(self, *args, **kwargs) -> requests.Response:
        return self._request(self.session.get, *args, **kwargs)


class VKLibrary(Service):
    def __init__(self, owner_id, user_token) -> None:
        self.owner_id = owner_id
        self.access_token = user_token
        self.session = Session()

    def list_library(self, cache=True) -> list[Song]:
        refresh = False
        if cache:
            if not pathlib.Path("./cache").exists():
                pathlib.Path("./cache").mkdir()
            caches = pathlib.Path("./cache").glob("vk_cache_*.pkl")
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
                caches = pathlib.Path("./cache").glob("vk_cache_*.pkl")
                for cache in caches:
                    cache.unlink()
        _log.info("Requesting VK for library")
        result = []
        done = False
        offset = 0
        while not done:
            with self.session.get(
                "https://api.vk.com/method/audio.get",
                params={
                    "access_token": self.access_token,
                    "owner_id": self.owner_id,
                    "v": "5.141",
                    "count": 200,
                    "offset": offset,
                },
            ) as resp:
                js = resp.json()
                songs = js["response"]["items"]
                for song in songs:
                    cmp_song = Song(song["title"], song["artist"], None, None, song)
                    result.append(cmp_song)
                if js["response"]["count"] < offset:
                    break
                offset += 200
        with open(
            pathlib.Path(f"./cache/vk_cache_{round(time.time())}.pkl").absolute(), "wb"
        ) as outf:
            outf.write(pickle.dumps(result))
        return result

    def add_to_library(self, song: Song) -> bool:
        with self.session.get(
            "https://api.vk.com/method/audio.add",
            params={
                "access_token": self.access_token,
                "access_key": song.original_object["access_key"],
                "owner_id": song.original_object["owner_id"],
                "audio_id": song.original_object["id"],
                "v": "5.141",
            },
            timeout=30,
        ) as resp:
            return resp.json()["response"] == song.original_object["id"]

    def add_to_playlist(self, song: Song, playlist_name="mixxer") -> bool:
        target_playlist = None
        with self.session.get(
            "https://api.vk.com/method/audio.getPlaylists",
            params={
                "access_token": self.access_token,
                "count": 50,
                "owner_id": self.owner_id,
                "v": "5.141",
            },
            timeout=30,
        ) as resp:
            resp = resp.json()
            playlists = resp["response"]["items"]
        for playlist in playlists:
            if playlist["title"] == playlist_name:
                target_playlist = playlist
                break
        if target_playlist is None:
            self.session.get(
                "https://api.vk.com/method/audio.createPlaylist",
                params={
                    "access_token": self.access_token,
                    "v": "5.141",
                    "title": playlist_name,
                    "owner_id": self.owner_id,
                },
                timeout=30,
            )
            return self.add_to_playlist(song, playlist_name)
        with self.session.get(
            "https://api.vk.com/method/audio.addToPlaylist",
            params={
                "access_token": self.access_token,
                "owner_id": self.owner_id,
                "playlist_id": target_playlist["id"],
                "v": "5.141",
                "audio_ids": f'{song.original_object["owner_id"]}_{song.original_object["id"]}',
            },
            timeout=30,
        ) as resp:
            return resp.json()["response"][0]["audio_id"] == song.original_object["id"]

    def search(self, query) -> Song | None:
        search = self.session.get(
            "https://api.vk.com/method/audio.search",
            params={"access_token": self.access_token, "q": query, "v": "5.141", "count": 30},
            timeout=30,
        )
        search = search.json()
        if search["response"]["items"] == []:
            return None
        results = []
        for result in search["response"]["items"]:
            results.append(Song(result["title"], result["artist"], None, None, result))
        return results
