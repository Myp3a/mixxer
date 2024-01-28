import logging

import services.apple as apple
import services.yandex as yandex
import services.spotify as spotify
from matcher import Matcher

APPLE_DEV_TOKEN = "dev_token_here"
APPLE_USER_TOKEN = "user_music_token_here"
YANDEX_TOKEN = "yandex_music_token_here"
SPOTIFY_ID = "spotify_app_id_here"
SPOTIFY_SECRET = "spotify_app_secret_here"

logging.basicConfig(level=logging.INFO)

spoty_cli = spotify.SpotifyLibrary(SPOTIFY_ID, SPOTIFY_SECRET)
apple_cli = apple.AppleLibrary(APPLE_DEV_TOKEN, APPLE_USER_TOKEN)
yandex_cli = yandex.YandexLibrary(YANDEX_TOKEN)

matcher = Matcher(apple_cli, yandex_cli)
matcher.match(to_playlist=True)
