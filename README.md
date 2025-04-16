# YouTube Multi-Audio Video Processor

A powerful Python tool for processing videos with multiple audio tracks and uploading them to YouTube with proper metadata and language support.

## Features

- Process videos with multiple audio tracks
- Convert mono audio tracks to stereo
- Merge sound effects with audio tracks
- Upload videos to YouTube with proper metadata
- Support for multiple languages
- Configurable video settings

## Prerequisites

- Python 3.7 or higher
- FFmpeg installed on your system
- Google API credentials for YouTube upload

## Installation

1. Clone this repository:
```bash
git clone https://github.com/OkoyaUsman/YouTubeMultiAudioVideoProcessor.git
cd youtube-multi-audio-processor
```

2. Install required Python packages:
```bash
pip install -r requirements.txt
```

3. Install FFmpeg:
- **Windows**: Download from [FFmpeg website](https://ffmpeg.org/download.html)
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt-get install ffmpeg`

4. Set up Google API credentials:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable YouTube Data API v3
   - Create OAuth 2.0 credentials
   - Download the credentials and save as `client_secret.json`

## Configuration

1. Edit `config.ini` with your settings:
```ini
[SETTINGS]
TITLE=Your Video Title
DESCRIPTION=Your video description
TAGS=tag1,tag2,tag3
CATEGORY=22
FOR_KIDS=false
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
```

2. Place your video file in the project directory with "input" in the filename (e.g., `input.mp4`)

3. Add audio tracks to the `tracks` folder:
   - Name files with language codes (e.g., `eng.mp3`, `spa.mp3`)
   - Supported formats: MP3, AAC, WAV

## Usage

1. Run the script:
```bash
python main.py
```

2. Follow the on-screen instructions for authentication

3. The script will:
   - Process your video
   - Add audio tracks
   - Upload to YouTube

## Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For assistance, customization, or further help, contact:
- Telegram: [@okoyausman](https://t.me/okoyausman)

## Acknowledgments

- [Google YouTube Data API](https://developers.google.com/youtube/v3)
- [FFmpeg](https://ffmpeg.org/)
- [Pydub](https://github.com/jiaaro/pydub) 
