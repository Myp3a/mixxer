import logging
from services.service import Service

_log = logging.getLogger(__name__)


class Matcher:
    def __init__(self, from_service: Service, to_service: Service) -> None:
        self.from_service = from_service
        self.to_service = to_service

    def match(self, to_playlist=True, match_level_existing=1, match_level_new=3) -> None:
        from_songs = self.from_service.list_library()[::-1]
        to_songs = self.to_service.list_library()[::-1]
        for from_song in from_songs:
            found = False
            for to_song in to_songs:
                match match_level_existing:
                    case 1:
                        match_function = from_song.match_very_lax
                    case 2:
                        match_function = from_song.match_lax
                    case 3:
                        match_function = from_song.match_mid
                    case 4:
                        match_function = from_song.match_strict
                    case 5:
                        match_function = from_song.match_isrc
                if match_function(to_song):
                    _log.debug(f"{from_song} matched {to_song}")
                    found = True
                    break
            if not found:
                _log.info(f"{from_song.name} - {from_song.artist} ({from_song.album}) not found, searching...")
                results = self.to_service.search(f"{from_song.name} - {from_song.artist}")
                if results is None:
                    _log.warning(f"Not found.")
                    continue
                in_search = False
                match match_level_new:
                    case 1:
                        match_function = from_song.match_very_lax
                    case 2:
                        match_function = from_song.match_lax
                    case 3:
                        match_function = from_song.match_mid
                    case 4:
                        match_function = from_song.match_strict
                    case 5:
                        match_function = from_song.match_isrc
                for result in results:
                    if match_function(result):
                        if to_playlist:
                            self.to_service.add_to_playlist(result)
                            _log.info("Found, adding to playlist.")
                            in_search = True
                            break
                        else:
                            self.to_service.add_to_library(result)
                            _log.info("Found, adding to library.")
                            in_search = True
                            break
                if not in_search:
                    _log.warning(f"Not found. Closest match: {results[0].name} - {results[0].artist} ({results[0].album})")
