import json
import os
from datetime import datetime

import boto3
import spotipy
from spotipy.cache_handler import CacheHandler
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOAuth


SECRETS_MANAGER = boto3.client("secretsmanager")
SECRET_ID = os.environ.get("SPOTIFY_SECRET_ID")
SCOPE = "playlist-read-private playlist-read-collaborative"
REDIRECT_URI = os.environ.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")


def load_secret():
    if not SECRET_ID:
        raise RuntimeError("SPOTIFY_SECRET_ID is not configured")

    response = SECRETS_MANAGER.get_secret_value(SecretId=SECRET_ID)
    return json.loads(response["SecretString"])


class SecretsManagerCacheHandler(CacheHandler):
    def get_cached_token(self):
        config = load_secret()
        token_info = config.get("token_info")
        if not token_info:
            raise RuntimeError("token_info not found in Secrets Manager")
        return token_info

    def save_token_to_cache(self, token_info):
        config = load_secret()
        config["token_info"] = token_info
        SECRETS_MANAGER.update_secret(
            SecretId=SECRET_ID,
            SecretString=json.dumps(config),
        )
        print("Spotify token updated in Secrets Manager")


def get_spotify():
    config = load_secret()

    missing_fields = [field for field in ("client_id", "client_secret", "token_info") if field not in config]
    if missing_fields:
        raise RuntimeError(f"Missing secret fields: {', '.join(missing_fields)}")

    auth_manager = SpotifyOAuth(
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_handler=SecretsManagerCacheHandler(),
        open_browser=False,
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def lambda_handler(event, context):
    try:
        playlist_id = event.get("playlist_id") or "5Sy0vFMwVBfbw8dIez7oIV"
        if not playlist_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "playlist_id missing in event"}),
            }

        config = load_secret()
        token_info = config.get("token_info", {})
        print("Token scopes:", token_info.get("scope"))

        sp = get_spotify()
        me = sp.current_user()
        print("Logged in as:", me.get("display_name"))

        items = []
        results = sp.playlist_items(playlist_id, limit=50)
        items.extend(results["items"])

        while results["next"]:
            results = sp.next(results)
            items.extend(results["items"])

        print("Total playlist items fetched:", len(items))

        s3 = boto3.client("s3")
        filename = "spotify_raw" + str(datetime.now()) + ".json"
        bucket_name = os.environ.get("S3_BUCKET_NAME", "spotify-etm-project-tapas")
        s3.put_object(
            Bucket=bucket_name,
            Key="raw_data/to_processed/" + filename,
            Body=json.dumps(results),
        )

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Spotify data extracted successfully", "items": len(items)}),
        }

    except SpotifyException as exc:
        print("Spotify API error")
        print("HTTP status:", exc.http_status)
        print("Spotify error:", str(exc))
        return {
            "statusCode": exc.http_status or 500,
            "body": json.dumps({
                "error": "Spotify API error",
                "status": exc.http_status,
                "message": str(exc),
                "playlist_id": event.get("playlist_id"),
            }),
        }

    except Exception as exc:
        print("Unexpected error:", repr(exc))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Unexpected error", "message": str(exc)}),
        }
