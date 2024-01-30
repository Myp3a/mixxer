import re

from dataclasses import dataclass

from transliterate import translit

@dataclass
class Song:
    name: str
    artist: str
    album: str
    isrc: str | None
    original_object: object

    def clean(self, string) -> str:
        lower = string.lower()
        replacements = lower.replace(" and ", " & ")
        remove_parenthesis = re.sub(r"\(.*?\)", "", replacements)
        remove_braces = re.sub(r"\[.*?\]", "", remove_parenthesis)
        remove_punctuation = re.sub(r"\W", "", remove_braces)
        trans = translit(remove_punctuation, "ru", reversed=True).strip()
        return trans

    def match_isrc(self, other: "Song") -> bool:
        """Useful for good services that provide a lot of information about songs.
        Should always match the same song.
        """
        if self.isrc is not None and other.isrc is not None:
            return self.isrc == other.isrc
        return False
    
    def match_strict(self, other: "Song") -> bool:
        """Strict match when ISRC is not available.
        """
        return (
            self.name.lower() == other.name.lower() 
            and self.artist.lower() == other.artist.lower() 
            and self.album.lower() == other.album.lower()
        )
    
    def match_mid(self, other: "Song") -> bool:
        """An attempt to match song with good confidence, not allowing different versions or artists of it."""
        return (
            self.clean(self.name) == self.clean(other.name) 
            and self.clean(self.artist) == self.clean(other.artist)
            and self.clean(self.album) == self.clean(other.album)
        )
    
    def match_lax(self, other: "Song") -> bool:
        """If you don't care about the same album, otherwise like match_mid."""
        return (
            self.clean(self.name) == self.clean(other.name) 
            and self.clean(self.artist) == self.clean(other.artist)
        )
    
    def match_very_lax(self, other: "Song") -> bool:
        """If there's vast differences between naming - can produce a lot 
        of false positives, but useful for already existing songs."""
        return self.clean(self.name) == self.clean(other.name)
    
    def __eq__(self, __value: "Song") -> bool:
        if self.match_isrc(__value):
            return True
        if self.match_strict(__value):
            return True
        if self.match_mid(__value):
            return True
        return False
        