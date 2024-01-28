import logging

from song import Song

_log = logging.getLogger(__name__)


class Service:
    def list_library(self, cache=True) -> list[Song]:
        _log.error("Not implemented")
    
    def add_to_library(self, song: Song) -> bool:
        _log.error("Not implemented")

    def add_to_playlist(self, song: Song, playlist_name="mixxer") -> bool:
        _log.error("Not implemented")

    def search(self, query) -> list[Song] | None:
        _log.error("Not implemented")
