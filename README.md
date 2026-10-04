# Spotify ETL Pipeline with Python & AWS

## Project description
This project builds a simple end-to-end ETL pipeline for Spotify playlist data. It uses the Spotify API to extract playlist and track metadata, stores raw JSON in Amazon S3, and transforms the data into clean datasets for albums, artists, and songs. The workflow is implemented using Python and AWS services, making it a practical example of a lightweight cloud data pipeline.

## Problem
Music listening habits and playlist metadata are often spread across API responses and difficult to analyze in a clean tabular format. This project addresses that by automating the extraction of playlist data and organizing it into reusable datasets for future analysis, reporting, or data engineering workflows.

## Architecture
The solution follows a basic ETL pattern:

1. Extract
   - A Python-based Lambda function authenticates to Spotify using OAuth and reads playlist data from the Spotify API.
   - Spotify credentials and OAuth tokens are stored in AWS Secrets Manager.
   - Raw playlist JSON is uploaded into an S3 bucket under the `raw_data/to_processed/` path.

2. Transform
   - A second Lambda function reads the raw JSON from S3.
   - The payload is normalized into separate album, artist, and song tables using Python and pandas.
   - Duplicate records are removed, datatypes are standardized, and the transformed outputs are written to `transformed_data/album_data/`, `transformed_data/artist_data/`, and `transformed_data/song_data/`.

3. Load / Storage
   - Transformed CSV files are stored back in Amazon S3.
   - Processed raw files are moved to the processed folder so the pipeline can be rerun safely.

This architecture demonstrates how Python and AWS can be used together for an event-driven, serverless data pipeline.

## Technologies
- Python
- AWS (Lambda, S3, Secrets Manager)
- Spotipy
- pandas
- boto3

## Setup
1. Clone the repository and open the project folder.
2. Create a `.env` file with your Spotify credentials:
   ```bash
   SPOTIPY_CLIENT_ID=your_client_id
   SPOTIPY_CLIENT_SECRET=your_client_secret
   ```
3. Install the required Python packages:
   ```bash
   pip install python-dotenv spotipy boto3 pandas
   ```
4. Configure AWS credentials on your local machine using AWS CLI or environment variables.
5. Create the required AWS resources:
   - S3 bucket for raw and transformed data
   - Secrets Manager secret containing `client_id`, `client_secret`, and `token_info`
   - Lambda functions for the extract and transform stages
6. Run the notebook in `Extract.ipynb` to test the Spotify authentication flow and retrieve playlist data, or deploy the Lambda functions for the automated pipeline.

## Results
The project produces structured data outputs for key Spotify entities:
- `album_data`: album metadata, release date, and track count
- `artist_data`: artist IDs, names, and profile URLs
- `song_data`: track details, timestamps, album reference, and artist reference

These datasets can be used for downstream analysis, reporting, or ingestion into a warehouse or analytics database.

## Demo
This project is a working ETL pipeline example rather than a hosted web app. A practical demo is to run the notebook to authenticate with Spotify and trigger the AWS pipeline flow to write raw and transformed files into S3.
