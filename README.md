# IG Story Downloader Chrome Extension

A lightweight Chrome Extension with a local Flask backend to download Instagram stories, posts, and reels directly to your PC. This is a focused fork of Instaloader, specifically designed for easy content downloading through a browser interface.

## Features

- 🔧 **Chrome Extension Interface**: Easy-to-use popup with dark theme
- � **Multi-Account Management**: Save and switch between Instagram accounts (like Instagram app)
- �📱 **Content Selection**: Choose to download posts, reels, and/or stories
- 🔐 **Secure Login**: Uses your Instagram session via Flask backend
- 📁 **Organized Downloads**: Automatically saves to `Pictures/IGStoryDownloader` with timestamped folders
- ⚡ **Rate Limiting**: Built-in delays and intelligent error handling for Instagram's limits
- 🎯 **Focused Functionality**: Simplified from original Instaloader for story/content downloading
- 🔄 **Account Switching**: One-click switching between saved accounts without re-entering credentials

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
2. **Account Management:**
   - **First time**: Enter username/password and click "Login"
   - **Return users**: Select from saved accounts or add new account
   - **Account switching**: Click on any saved account to switch instantly
   - **Current account**: Shows "📱 Logged in as: @username" when logged in
   - **Logout**: Use red "Logout" button to clear current session
3. Enter the target Instagram username
4. Select content types (Posts, Reels, Stories)
5. Set limits and delays if needed
6. Click "Download Selected Content"

> 💡 **Account Management**: The extension saves your credentials securely in Chrome storage and shows them like Instagram's account switcher!

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
- `POST /logout` - Logout current user and reset session (enables account switching)
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

## Troubleshooting

### "Challenge Required" Error

If you encounter a "challenge_required" error, Instagram is asking for additional verification. Here are solutions:

#### Method 1: Browser Cookies (Recommended)
1. Log in to [Instagram.com](https://instagram.com) in your browser
2. Complete any verification challenges that appear
3. Keep the Instagram tab open and logged in
4. In the extension, click "Use Browser Cookies" instead of entering username/password
5. This method bypasses the challenge since you're already verified in the browser

#### Method 2: Wait and Retry
1. Wait 10-15 minutes before trying again
2. Instagram's rate limiting may reset
3. Try downloading from a different account first

#### Method 3: Complete Web Verification
1. Log in to Instagram.com in your browser
2. Complete any phone/email verification requested
3. Try the extension again after verification is complete

### Rate Limiting Issues

**"Please wait a few minutes before you try again" / 401 Unauthorized:**
- Instagram is temporarily blocking requests due to too many API calls
- **Solutions:**
  - Wait 10-15 minutes before retrying
  - Switch to a different account temporarily
  - Increase delay between requests (try 3-5 seconds)
  - Reduce download limits (try 3-5 posts instead of 10+)
  - Increase backoff time (try 30+ seconds)
- **Optimal Settings for Rate Limiting:**
  - Delay: 3-5 seconds
  - Limit: 3-5 posts
  - Backoff: 30 seconds
  - Story Limit: 10-15

### Other Common Issues

**"Cannot login with different account"**: 
- Use the red "Logout" button in the extension first
- This clears the current session and allows switching accounts
- The backend automatically detects different usernames and resets when needed

**"No such file or directory" session error**: 
- This occurs when usernames contain spaces or special characters
- The extension automatically handles this by sanitizing filenames
- Session files are stored in `%LOCALAPPDATA%\Instaloader\` on Windows

**"Profile not found"**: Check the username spelling, or the account may be deleted/suspended.

**"Login required"**: The target account is private. You need to log in and follow them first.

**"Connection timeout"**: Instagram servers may be busy. Wait a few minutes and retry.

**Backend not running**: Make sure you started the Flask server (`python backend_server.py`).

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
