import logging
from services.service import Service

_log = logging.getLogger(__name__)


class Matcher:
    def __init__(self, from_service: Service, to_service: Service) -> None:
        self.from_service = from_service
        self.to_service = to_service

    def match(self, to_playlist=True) -> None:
        from_songs = self.from_service.list_library()[::-1]
        to_songs = self.to_service.list_library()[::-1]
        for from_song in from_songs:
            found = False
            for to_song in to_songs:
                if from_song.match_lax(to_song):
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
                for result in results:
                    if result.match_lax(from_song):
                        if to_playlist:
                            self.to_service.add_to_playlist(result)
                            _log.info("Found, adding to playlist.")
                            break
                        else:
                            self.to_service.add_to_library(result)
                            _log.info("Found, adding to library.")
                            break
                if not in_search:
                    _log.warning(f"Not found. Closest match: {results[0].name} - {results[0].artist} ({results[0].album})")
