# IG Story Downloader Chrome Extension

A lightweight Chrome Extension with a local Flask backend to download Instagram stories, posts, and reels directly to your PC. This is a focused fork of Instaloader, specifically designed for easy content downloading through a browser interface.

## Features

- 🔧 **Chrome Extension Interface**: Easy-to-use popup with dark theme
- 📱 **Content Selection**: Choose to download posts, reels, and/or stories
- 🔐 **Secure Login**: Uses your Instagram session via Flask backend
- 📁 **Organized Downloads**: Automatically saves to `Pictures/IGStoryDownloader` with timestamped folders
- ⚡ **Rate Limiting**: Built-in delays to respect Instagram's limits
- 🎯 **Focused Functionality**: Simplified from original Instaloader for story/content downloading

## Installation

### Prerequisites
- Python 3.9+
- Chrome/Chromium browser
- pipenv (recommended) or pip

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ReXooGen/instagram-story-downloader-extension.git
   cd instagram-story-downloader-extension
   ```

2. **Install Python dependencies:**
   ```bash
   pipenv install
   ```
   Or with pip:
   ```bash
   pip install flask flask-cors requests browser-cookie3
   ```

3. **Load Chrome Extension:**
   - Open Chrome and go to `chrome://extensions/`
   - Enable "Developer mode" (top right toggle)
   - Click "Load unpacked"
   - Select the `chrome_extension` folder

## Usage

### 1. Start the Backend Server
```bash
pipenv run python backend_server.py
```
Or:
```bash
python backend_server.py
```

The server will start on `http://localhost:5000`

### 2. Use the Chrome Extension
1. Click the extension icon in your browser
2. Enter your Instagram username and password to login
3. Enter the target Instagram username
4. Select content types (Posts, Reels, Stories)
5. Set limits and delays if needed
6. Click "Download Selected Content"

### 3. Find Your Downloads
Downloaded content will be saved to:
```
Pictures/IGStoryDownloader/YYYY-MM-DD_HH-MM-SS/
├── username_posts/
├── username_reels/
└── username_stories/
```

## API Endpoints

- `POST /login` - Authenticate with Instagram
- `GET /download` - Download content with parameters:
  - `username`: Target Instagram username
  - `posts`: Include posts (true/false)
  - `reels`: Include reels (true/false) 
  - `stories`: Include stories (true/false)
  - `limit`: Maximum items per category
  - `delay`: Delay between requests

## Command Line Usage

You can also use the tool directly from command line:

```bash
# Download stories
python -m instastorysaver --login your_username --stories target_username

# Download posts and reels
python -m instastorysaver --login your_username --reels target_username

# See all options
python -m instastorysaver --help
```

## Configuration

### Rate Limiting
The backend includes built-in rate limiting to avoid Instagram restrictions:
- Default delay: 2 seconds between requests
- Configurable via the extension interface

### Download Location
Default: `Pictures/IGStoryDownloader/`
Modify in `backend_server.py` if needed.

## Development

### Project Structure
```
├── chrome_extension/           # Chrome extension files
│   ├── manifest.json          # Extension manifest
│   ├── popup.html             # Extension popup UI
│   ├── popup.js               # Frontend logic
│   └── icons/                 # Extension icons
├── instastorysaver/           # Python package (renamed from instaloader)
│   ├── __init__.py
│   ├── instastorysaver.py     # Main downloader logic
│   └── ...
├── backend_server.py          # Flask API server
├── Pipfile                    # Python dependencies
└── .github/workflows/         # CI/CD workflows
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is a fork of [Instaloader](https://github.com/instaloader/instaloader) and maintains the same MIT license.

## Disclaimer

This tool is for personal use only. Please respect Instagram's Terms of Service and only download content you have permission to access. The developers are not responsible for any misuse of this tool.

## Credits

Based on [Instaloader](https://github.com/instaloader/instaloader) by Alexander Graf and contributors.
Modified and simplified for Chrome extension use by ReXooGen.
