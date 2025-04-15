# Import required libraries
import os
import sys
import subprocess
import shutil
import json
from pydub import AudioSegment
import langcodes
import http.client as httplib
import httplib2
import random
import time
import configparser
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run_flow

# Print initialization message
print("Starting video encoding...")

# Configuration flags
mergeEffectsTrack = False  # Set to True to merge sound effects with audio tracks
embedTracksInVideo = True  # Set to True to embed audio tracks in the video
saveMergedTracks = True    # Set to True to save merged tracks with effects

# Get the current directory path
path = os.path.dirname(__file__)

# Find input video file
inputVideo = None
video_formats = [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm"]
for file in os.listdir(path):
    if os.path.isfile(os.path.join(path, file)):
        filename, extension = os.path.splitext(file)
        if "input" in filename.lower() and extension.lower() in video_formats:
                inputVideo = os.path.join(path, file)
if inputVideo is None:
    exit("No input video provided!")

# Set output paths and formats
outputVideo = os.path.join(path, "output.mp4")
outputTracksFormat = "mp3"
defaultLanguage = "eng"
tracksToAddDict = {}
soundEffectsDict = {'effects': os.path.join(path, "effect.wav")}
tempFilesToDelete = []

# Create tracks directory if it doesn't exist
tracksFolder = os.path.join(path, "tracks")
if not os.path.isdir(tracksFolder):
    os.makedirs(tracksFolder, exist_ok=True)

# Read configuration from config.ini
config = configparser.ConfigParser()
config.read(os.path.join(path, "config.ini"))
title = config.get('SETTINGS', 'TITLE')
description = config.get('SETTINGS', 'DESCRIPTION')
tags = config.get('SETTINGS', 'TAGS')
category = config.get('SETTINGS', 'CATEGORY')
client_id = config.get('SETTINGS', 'CLIENT_ID')
client_secret = config.get('SETTINGS', 'CLIENT_SECRET')
forKids = config.getboolean('SETTINGS', 'FOR_KIDS')

# Configure Google API client
client_json = {
    "web": {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uris": ["http://localhost"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://accounts.google.com/o/oauth2/token"
    }
}

# Configure HTTP retry settings
httplib2.RETRIES = 1
MAX_RETRIES = 10
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, httplib.NotConnected, httplib.IncompleteRead, httplib.ImproperConnectionState, httplib.CannotSendRequest, httplib.CannotSendHeader, httplib.ResponseNotReady, httplib.BadStatusLine, IOError)
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
CLIENT_SECRETS_FILE = os.path.join(path, "client_secret.json")
SCOPES = "https://www.googleapis.com/auth/youtube.upload"
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'
VALID_PRIVACY_STATUSES = ('public', 'private', 'unlisted')

# Save client credentials
with open(CLIENT_SECRETS_FILE, 'w') as f:
    f.write(json.dumps(client_json))

# Initialize Google API authentication
flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE, SCOPES)
storage = Storage(os.path.join(path, "oauth2.json"))
credentials = storage.get()
if credentials is None or credentials.invalid:
    credentials = run_flow(flow, storage)
YouTube = build(API_SERVICE_NAME, API_VERSION, http=credentials.authorize(httplib2.Http()))

def uploadYouTube(video):
    """
    Upload a video to YouTube with specified metadata
    Args:
        video (str): Path to the video file to upload
    """
    body = dict(
        snippet = dict(
            title = title,
            description = description,
            tags = tags.split(","),
            categoryId=category
        ),
        status = dict(
            privacyStatus = "private",
            selfDeclaredMadeForKids = forKids
        )
    )
    request = YouTube.videos().insert(part=','.join(body.keys()), body=body, media_body=MediaFileUpload(video, chunksize=-1, resumable=True))
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            print("\nUploading Video to YouTube...")
            status, response = request.next_chunk()
            if response is not None:
                if 'id' in response:
                    video_id = response['id']
                    print(f"\nVideo ID {video_id} was successfully uploaded.")
                else:
                    exit(f"The upload failed with an unexpected response: {response}")
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = f"A retriable HTTP error {e.resp.status} occurred:\n{e.content}"
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = f"A retriable error occurred: {e}"
        if error is not None:
            print(error)
            retry += 1
            if retry > MAX_RETRIES:
                exit("Max retry reached. No longer attempting to retry.")
            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            print(f"Sleeping {sleep_seconds} seconds and then retrying...")
            time.sleep(sleep_seconds)

# Process audio tracks in the tracks folder
for file in os.listdir(tracksFolder):
    if file.endswith(".mp3") or file.endswith(".aac") or file.endswith(".wav"):
        parsedLanguageCode = os.path.splitext(file)[0]
        try:
            langObject = langcodes.get(parsedLanguageCode)
            threeLetterCode = langObject.to_alpha3()
            languageDisplayName = langcodes.get(threeLetterCode).display_name()
            if threeLetterCode in tracksToAddDict.keys():
                print(f"\ERROR while checking {file}: Language '{languageDisplayName}' is already in use by file: {tracksToAddDict[threeLetterCode]}")
                userInput = input("\nPress Enter to exit... ")
                sys.exit()
            tracksToAddDict[threeLetterCode] = file
        except:
            print(f"\nWARNING: Language code '{parsedLanguageCode}' is not valid for file: {file}")
            print("Enter 'y' to skip that track and conitnue, or enter anything else to exit.")
            userInput = input("\nContinue Anyway and Skip File? (y/n): ")
            if userInput.lower() != 'y':
                sys.exit()

# Set up directory paths
tracksFolder = os.path.normpath(tracksFolder)
tempdir = os.path.join(tracksFolder, "temp")
mergedTracksDir = os.path.join(tracksFolder, "Merged Effects Tracks")

def convert_to_stereo(tracksDict):
    """
    Convert mono audio tracks to stereo
    Args:
        tracksDict (dict): Dictionary of language codes and audio file paths
    Returns:
        dict: Updated dictionary with stereo audio file paths
    """
    for langcode, fileName in tracksDict.items():
        filePath = os.path.join(tracksFolder, fileName)
        audio = AudioSegment.from_file(filePath)
        num_channels = audio.channels
        if num_channels == 1:
            if not os.path.exists(tempdir):
                os.makedirs(tempdir)
            fileExtension = os.path.splitext(filePath)[1][1:]
            stereo_file = audio.set_channels(2)
            tempFilePath = f"{os.path.join(tempdir, fileName)}_stereo_temp.{fileExtension}" 
            if fileExtension == "aac":
                formatString = "adts"
            else:
                formatString = fileExtension
            stereo_file.export(tempFilePath, format=formatString, bitrate="128k")
            tracksDict[langcode] = tempFilePath
            if mergeEffectsTrack and saveMergedTracks and langcode != "effects":
                pass
            else:
                tempFilesToDelete.append(tempFilePath)

        else:
            tracksDict[langcode] = filePath
    return tracksDict

# Convert tracks to stereo
print("\nChecking if tracks are stereo...")
tracksToAddDict = convert_to_stereo(tracksToAddDict)

# Process sound effects if enabled
if mergeEffectsTrack:
    soundEffectsDict = convert_to_stereo(soundEffectsDict)
    if not os.path.exists(tempdir):
        os.makedirs(tempdir, exist_ok=True)
    for langcode, filePath in tracksToAddDict.items():
        if "_stereo_temp" not in filePath:
            fileExtension = os.path.splitext(filePath)[1][1:]
            fileName = os.path.basename(filePath)
            appendString = "_temp."+fileExtension
            tempFilePath = os.path.join(tempdir, fileName+appendString)
            shutil.copy(filePath, tempFilePath)
            tracksToAddDict[langcode] = tempFilePath
            if not saveMergedTracks:
                tempFilesToDelete.append(tempFilePath)
    print("\nMerging sound effects...")
    for langcode, trackFilePath in tracksToAddDict.items():
        soundEffects = AudioSegment.from_file(soundEffectsDict['effects'])
        audio = AudioSegment.from_file(trackFilePath)
        combined = audio.overlay(soundEffects)
        if "_temp" in trackFilePath:
            fileExtension = os.path.splitext(trackFilePath)[1][1:]
            outputTracksFormat = outputTracksFormat.lower()
            if outputTracksFormat == "same" and fileExtension.lower() != "aac":
                formatString = fileExtension
            elif outputTracksFormat == "same" and fileExtension.lower() == "aac":
                formatString = "adts"
            elif outputTracksFormat == "mp3":
                formatString = "mp3"
            elif outputTracksFormat == "wav":
                formatString = "wav"
            elif outputTracksFormat == "aac":
                formatString = "adts"
            else:
                formatString = fileExtension
            combined.export(trackFilePath, format=formatString, bitrate="192k")
        else:
            print("\n\nUN3XP3CT3D 3RROR: The script did not create a temporary file - cannot overwrite original file.")
            userInput = input("\nPress Enter to exit... ")
            sys.exit()
        if saveMergedTracks:
            if not os.path.exists(mergedTracksDir):
                os.makedirs(mergedTracksDir, exist_ok=True)
            tempFileName = os.path.basename(trackFilePath)
            ext = os.path.splitext(trackFilePath)[1][1:]
            fileName = fileName.replace("_stereo_temp", "")
            fileName = tempFileName.replace("_temp", "")
            fileName = fileName.replace(f".{ext}.{ext}", f".{ext}")
            nameNoExt = os.path.splitext(fileName)[0]
            parsedLanguageCode = nameNoExt.split('-')[-1].strip()
            fileName = fileName.replace(parsedLanguageCode, f" With Effects-{parsedLanguageCode}")
            newFilePath = os.path.join(mergedTracksDir, fileName)
            shutil.move(trackFilePath, newFilePath)
            tracksToAddDict[langcode] = newFilePath

# Embed audio tracks in video if enabled
if len(tracksToAddDict) > 0 and embedTracksInVideo:
    print("\nAdding audio tracks to video...")
    trackStringsCombined = ""
    mapList = "-map 0"
    metadataCombined = f'-metadata:s:a:0 language={defaultLanguage} -metadata:s:a:0 title="{defaultLanguage}" -metadata:s:a:0 handler_name="{defaultLanguage}"'
    count = 1
    for langcode, filePath in tracksToAddDict.items():
        languageDisplayName = langcodes.get(langcode).display_name()
        trackStringsCombined += f' -i "{filePath}"'
        metadataCombined += f' -metadata:s:a:{count} language={langcode}'
        metadataCombined += f' -metadata:s:a:{count} handler_name={languageDisplayName}'
        metadataCombined += f' -metadata:s:a:{count} title="{languageDisplayName}"'
        mapList += f' -map {count}'
        count+=1

    finalCommand = f'ffmpeg -y -hide_banner -loglevel error -i "{inputVideo}" {trackStringsCombined} {mapList} {metadataCombined} -c:v copy "{outputVideo}"'
    subprocess.run(finalCommand, shell=True, check=True)
    print("\nDeleting temporary files...")
    for file in tempFilesToDelete:
        os.remove(file)
    try:
        if os.path.exists(tempdir):
            os.rmdir(tempdir)
    except OSError as e:
        print("Could not delete temp directory. It may not be empty.")
    uploadYouTube(outputVideo)
    print("\nDone!")