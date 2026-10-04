import json
import os
from datetime import datetime
from io import StringIO

import boto3
import pandas as pd


def album(data):
    album_list = []
    for item in data["items"]:
        track = item["item"]["album"]
        album_elements = {
            "album_id": track["id"],
            "album_name": track["name"],
            "album_release_date": track["release_date"],
            "album_total_tracks": track["total_tracks"],
            "album_spotify_url": item["item"]["external_urls"]["spotify"],
        }
        album_list.append(album_elements)
    return album_list


def artist(data):
    artists_list = []
    for row in data["items"]:
        item = row["item"]
        for artist in item.get("artists", []):
            artist_dict = {
                "artist_id": artist["id"],
                "artist_name": artist["name"],
                "external_url": artist["href"],
            }
            artists_list.append(artist_dict)
    return artists_list


def songs(data):
    song_list = []
    for row in data["items"]:
        item = row["item"]
        song_dict = {
            "song_id": item["id"],
            "song_name": item["name"],
            "song_duration": item["duration_ms"],
            "song_url": item["external_urls"]["spotify"],
            "song_added_at": row["added_at"],
            "album_id": item["album"]["id"],
            "artist_id": item["artists"][0]["id"],
        }
        song_list.append(song_dict)
    return song_list


def lambda_handler(event, context):
    s3 = boto3.client("s3")
    bucket = os.environ.get("S3_BUCKET_NAME", "spotify-etm-project-tapas")
    prefix = "raw_data/to_processed/"

    spotify_data = []
    spotify_keys = []
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    for file in response.get("Contents", []):
        file_key = file["Key"]
        if file_key.lower().endswith(".json"):
            obj = s3.get_object(Bucket=bucket, Key=file_key)
            spotify_data.append(json.loads(obj["Body"].read()))
            spotify_keys.append(file_key)

    for data in spotify_data:
        album_list = album(data)
        artist_list = artist(data)
        songs_list = songs(data)

        album_df = pd.DataFrame.from_dict(album_list).drop_duplicates(subset=["album_id"])
        artist_df = pd.DataFrame.from_dict(artist_list).drop_duplicates(subset=["artist_id"])
        song_df = pd.DataFrame.from_dict(songs_list)

        album_df["album_release_date"] = pd.to_datetime(album_df["album_release_date"])
        song_df["song_added_at"] = pd.to_datetime(song_df["song_added_at"])

        if not song_df.empty:
            song_buffer = StringIO()
            song_df.to_csv(song_buffer, index=False)
            s3.put_object(
                Bucket=bucket,
                Key="transformed_data/song_data/" + str(datetime.now()) + ".csv",
                Body=song_buffer.getvalue(),
            )

        if not album_df.empty:
            album_buffer = StringIO()
            album_df.to_csv(album_buffer, index=False)
            s3.put_object(
                Bucket=bucket,
                Key="transformed_data/album_data/" + str(datetime.now()) + ".csv",
                Body=album_buffer.getvalue(),
            )

        if not artist_df.empty:
            artist_buffer = StringIO()
            artist_df.to_csv(artist_buffer, index=False)
            s3.put_object(
                Bucket=bucket,
                Key="transformed_data/artist_data/" + str(datetime.now()) + ".csv",
                Body=artist_buffer.getvalue(),
            )

    s3_resource = boto3.resource("s3")
    for key in spotify_keys:
        copy_source = {"Bucket": bucket, "Key": key}
        target_key = "raw_data/processed/" + key.split("/")[-1]
        s3_resource.meta.client.copy(copy_source, bucket, target_key)
        s3_resource.Object(bucket, key).delete()

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Spotify data transformed and loaded successfully"}),
    }
