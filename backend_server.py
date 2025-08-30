import os
from datetime import datetime, UTC
from typing import Optional, List, Dict
from contextlib import suppress
import time

import instastorysaver
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DOWNLOAD_DIR = os.path.join(os.path.expanduser('~'), 'Pictures', 'IGStoryDownloader')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

_LOADER: Optional[instastorysaver.Instaloader] = None
_LOGIN_USER: Optional[str] = None


def get_loader() -> instastorysaver.Instaloader:
    global _LOADER
    if _LOADER is None:
        _LOADER = instastorysaver.Instaloader(
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            download_video_thumbnails=False,
            post_metadata_txt_pattern="",
            storyitem_metadata_txt_pattern=""
        )
    return _LOADER


def reset_loader():
    """Reset the loader instance to allow login with different accounts."""
    global _LOADER, _LOGIN_USER
    _LOADER = None
    _LOGIN_USER = None


def _cleanup(folder: str):
    if not os.path.isdir(folder):
        return
    for f in os.listdir(folder):
        if not (f.lower().endswith('.jpg') or f.lower().endswith('.mp4')):
            with suppress(Exception):
                os.remove(os.path.join(folder, f))


def download_media(target_username: str,
                   limit: int,
                   include_posts: bool,
                   include_reels: bool,
                   include_stories: bool,
                   delay: float,
                   backoff: float,
                   stories_limit: int):
    L = get_loader()
    
    # Try to get profile with better error handling
    try:
        profile = instastorysaver.Profile.from_username(L.context, target_username)
        L.context.log(f"Profile loaded: {target_username}")
        L.context.log(f"Profile info - Posts: {profile.mediacount}, Private: {profile.is_private}")
        
        # Check if profile is private and we need login
        if profile.is_private and not L.context.is_logged_in:
            raise instastorysaver.exceptions.LoginRequiredException(
                f"Profile '{target_username}' is private and requires login"
            )
            
    except Exception as e:
        error_msg = str(e).lower()
        L.context.log(f"Profile loading error: {e}")
        
        # Check for rate limiting specifically
        if "please wait a few minutes" in error_msg or ("401 unauthorized" in error_msg and "fail" in error_msg):
            raise instastorysaver.exceptions.ConnectionException(
                f"Instagram is heavily rate limiting your account. "
                f"This is why no posts are being detected. "
                f"Please wait 30-60 minutes before trying again. "
                f"Consider using the extension less frequently to avoid this."
            )
        elif "challenge_required" in error_msg:
            raise instastorysaver.exceptions.ConnectionException(
                f"Instagram requires additional verification for this account. "
                f"Try logging in through a web browser first, complete any challenges, "
                f"then try again. Error: {str(e)}"
            )
        elif "not found" in error_msg or "404" in error_msg:
            raise instastorysaver.exceptions.QueryReturnedNotFoundException(f"Profile '{target_username}' not found")
        elif "private" in error_msg or "login" in error_msg:
            raise instastorysaver.exceptions.LoginRequiredException(
                f"Profile '{target_username}' is private and requires login"
            )
        else:
            raise
    timestamp = datetime.now(UTC).strftime('%Y%m%d_%H%M%S')
    session_dir = os.path.join(DOWNLOAD_DIR, target_username, timestamp)
    posts_dir = os.path.join(session_dir, 'posts')
    reels_dir = os.path.join(session_dir, 'reels')
    stories_dir = os.path.join(session_dir, 'stories')
    for d in (posts_dir, reels_dir, stories_dir):
        os.makedirs(d, exist_ok=True)
    L.dirname_pattern = os.path.join(session_dir, '{target}')

    stats: Dict[str, int] = {"posts_downloaded": 0, "reels_downloaded": 0, "rate_limit_retries": 0}
    posts_meta: List[dict] = []
    count = 0
    
    try:
        L.context.log(f"Starting to fetch posts for {target_username} (limit: {limit})")
        post_iterator = profile.get_posts()
        L.context.log("Post iterator created successfully")
        
        posts_found = 0
        for post in post_iterator:
            posts_found += 1
            L.context.log(f"Processing post {posts_found}: {post.shortcode} (is_video: {post.is_video})")
            
            if count >= limit:
                L.context.log(f"Reached limit of {limit} posts")
                break
                
            is_reel_candidate = bool(post.is_video)
            if (is_reel_candidate and not include_reels) or ((not is_reel_candidate) and not include_posts):
                L.context.log(f"Skipping post {post.shortcode} due to type filter")
                continue
                
            attempt = 0
            while True:
                try:
                    sub = 'reels' if is_reel_candidate else 'posts'
                    L.context.log(f"Downloading {post.shortcode} to {sub}")
                    L.download_post(post, target=sub)
                    posts_meta.append({
                        'shortcode': post.shortcode,
                        'date_utc': post.date_utc.isoformat(),
                        'is_video': post.is_video,
                        'type': 'reel' if is_reel_candidate else 'post'
                    })
                    if is_reel_candidate:
                        stats['reels_downloaded'] += 1
                    else:
                        stats['posts_downloaded'] += 1
                    L.context.log(f"Successfully downloaded {post.shortcode}")
                    break
                except instastorysaver.exceptions.ConnectionException as ce:
                    attempt += 1
                    stats['rate_limit_retries'] += 1
                    L.context.log(f"Rate limit hit for {post.shortcode}, attempt {attempt}")
                    time.sleep(backoff * attempt)
                    if attempt >= 3:
                        L.context.log(f"Max retries reached for {post.shortcode}")
                        posts_meta.append({'error': str(ce), 'shortcode': post.shortcode})
                        break
                except Exception as e:
                    L.context.log(f"Error downloading {post.shortcode}: {e}")
                    posts_meta.append({'error': str(e), 'shortcode': post.shortcode})
                    break
            count += 1
            if delay > 0:
                time.sleep(delay)
                
        L.context.log(f"Total posts found: {posts_found}, downloaded: {count}")
        
        if posts_found == 0:
            L.context.log("No posts found - this could be due to:")
            L.context.log("1. Private account requiring login")
            L.context.log("2. Instagram anti-bot protection")
            L.context.log("3. Rate limiting")
            L.context.log("4. Account genuinely has no posts")
            
    except Exception as e:
        L.context.log(f"Error during post iteration: {e}")
        posts_meta.append({'error': f'Post iteration failed: {str(e)}'})
        # Don't raise here, continue to stories if needed

    stories_meta: List[dict] = []
    stories_status = 'not_requested'
    if include_stories:
        if not L.context.is_logged_in:
            stories_status = 'login_required'
            stories_meta.append({'error': 'login_required_for_stories'})
        else:
            grabbed = 0
            found = False
            try:
                for story in L.get_stories(userids=[profile.userid]):
                    found = True
                    for item in story.get_items():
                        if grabbed >= stories_limit:
                            break
                        try:
                            L.download_storyitem(item, target='stories')
                            stories_meta.append({'date_utc': item.date_utc.isoformat(), 'is_video': item.is_video})
                        except Exception as e:
                            stories_meta.append({'error': str(e)})
                        grabbed += 1
                    if grabbed >= stories_limit:
                        break
                stories_status = 'no_stories' if not found else ('empty' if grabbed == 0 else 'downloaded')
            except Exception as e:
                stories_status = 'error'
                stories_meta.append({'error': str(e)})

    for f in (posts_dir, reels_dir, stories_dir):
        _cleanup(f)
    with suppress(Exception):
        for f in os.listdir(stories_dir):
            if f.lower().endswith(('.jpg', '.mp4')) and not f.startswith('story_'):
                os.replace(os.path.join(stories_dir, f), os.path.join(stories_dir, 'story_' + f))

    return {
        'folders': {'base': session_dir, 'posts': posts_dir, 'reels': reels_dir, 'stories': stories_dir},
        'posts_meta': posts_meta,
        'stories_meta': stories_meta,
        'stories_status': stories_status,
        'stats': stats,
        'count': count,
        'profile_info': {
            'username': target_username,
            'mediacount': profile.mediacount if 'profile' in locals() else 'unknown',
            'is_private': profile.is_private if 'profile' in locals() else 'unknown',
            'logged_in': L.context.is_logged_in
        }
    }


@app.route('/login', methods=['POST'])
def login():
    global _LOGIN_USER
    data = request.get_json(force=True, silent=True) or {}
    ig_user = data.get('username')
    ig_pass = data.get('password')
    use_browser_cookies = data.get('use_browser_cookies', False)
    
    if not use_browser_cookies and (not ig_user or not ig_pass):
        return jsonify({"error": "username and password required (or set use_browser_cookies)"}), 400
    
    # Check if we're trying to login with a different user
    if _LOGIN_USER and not use_browser_cookies and ig_user != _LOGIN_USER:
        reset_loader()  # Reset to allow different account login
    elif _LOGIN_USER and use_browser_cookies:
        reset_loader()  # Reset for browser cookies login
    
    L = get_loader()
    try:
        if use_browser_cookies:
            L.context.log("Attempting to load browser cookies...")
            # Try different browsers in order of preference
            browsers = ['chrome', 'edge', 'firefox', 'opera', 'safari']
            success = False
            for browser in browsers:
                try:
                    # Create a safe session name for browser cookies
                    session_name = ig_user or "browser_session"
                    L.load_session_from_file(session_name)
                    if L.context.is_logged_in:
                        success = True
                        break
                    L.context.log(f"Trying {browser} cookies...")
                    L.context.load_cookies_from_browser(browser)
                    if L.context.is_logged_in:
                        _LOGIN_USER = L.context.username or "browser_user"
                        # Save with safe filename
                        try:
                            L.save_session_to_file()
                        except Exception as save_err:
                            L.context.log(f"Warning: Could not save session: {save_err}")
                        success = True
                        break
                except Exception as e:
                    L.context.log(f"Failed to load {browser} cookies: {e}")
                    continue
            
            if not success:
                return jsonify({
                    "error": "Could not load valid Instagram session from any browser. "
                            "Please log in to Instagram.com in your browser first.",
                    "browser_cookies_failed": True
                }), 401
            
            return jsonify({
                "message": f"Logged in using browser cookies as {_LOGIN_USER}", 
                "logged_in": True,
                "method": "browser_cookies"
            })
        else:
            L.context.log("Attempting login with username/password...")
            try:
                # Try to load existing session
                L.load_session_from_file(ig_user)
                if L.context.is_logged_in:
                    # Test if session is still valid with a simple check
                    try:
                        # Try a simple operation that doesn't trigger rate limits
                        current_username = L.test_login()
                        if current_username == ig_user:
                            L.context.log(f"Valid session found for {ig_user}")
                            _LOGIN_USER = ig_user
                            return jsonify({"message": f"Logged in as {ig_user} (existing session)", "logged_in": True})
                        else:
                            L.context.log(f"Session for different user ({current_username}), need fresh login")
                    except Exception as session_test_err:
                        # If testing fails due to rate limiting, don't immediately invalidate
                        if "Please wait a few minutes" in str(session_test_err) or "401 Unauthorized" in str(session_test_err):
                            L.context.log(f"Rate limited during session test, but session might still be valid")
                            _LOGIN_USER = ig_user
                            return jsonify({
                                "message": f"Logged in as {ig_user} (session loaded, rate limited)", 
                                "logged_in": True,
                                "warning": "Instagram is rate limiting - session may work for downloads"
                            })
                        else:
                            L.context.log(f"Session test failed: {session_test_err}")
                
                # If no valid session or session test failed, try fresh login
                L.context.log("Attempting fresh login...")
                L.login(ig_user, ig_pass)
                try:
                    L.save_session_to_file()
                except Exception as save_err:
                    L.context.log(f"Warning: Could not save session to file: {save_err}")
                    
            except FileNotFoundError:
                # No existing session file, try fresh login
                L.context.log("No existing session file, logging in fresh...")
                L.login(ig_user, ig_pass)
                try:
                    L.save_session_to_file()
                except Exception as save_err:
                    L.context.log(f"Warning: Could not save session to file: {save_err}")
            except Exception as session_err:
                L.context.log(f"Session file error: {session_err}")
                # Don't immediately try fresh login if it's a rate limit error
                if "Please wait a few minutes" in str(session_err) or "401 Unauthorized" in str(session_err):
                    return jsonify({
                        "error": "Instagram is currently rate limiting requests. Please wait 10-15 minutes before trying to login again.",
                        "rate_limited": True
                    }), 429
                else:
                    L.context.log("Trying fresh login...")
                    L.login(ig_user, ig_pass)
                    try:
                        L.save_session_to_file()
                    except Exception as save_err:
                        L.context.log(f"Warning: Could not save session to file: {save_err}")
                    
            _LOGIN_USER = ig_user
            return jsonify({"message": f"Logged in as {ig_user}", "logged_in": True})
            
    except Exception as e:
        error_msg = str(e).lower()
        if "challenge_required" in error_msg:
            return jsonify({
                "error": "Instagram requires additional verification (challenge). "
                        "Please log in through Instagram's website/app first, "
                        "complete any required verification, then try again.",
                "challenge_required": True,
                "suggestion": "Try using browser cookies instead of username/password"
            }), 401
        elif "checkpoint_required" in error_msg:
            return jsonify({
                "error": "Instagram checkpoint required. Please log in through "
                        "Instagram's website/app and complete the security check.",
                "checkpoint_required": True
            }), 401
        elif "incorrect" in error_msg or "invalid" in error_msg:
            return jsonify({"error": "Invalid username or password"}), 401
        else:
            return jsonify({"error": str(e)}), 401


@app.route('/logout', methods=['POST'])
def logout():
    """Logout current user and reset session."""
    global _LOGIN_USER
    current_user = _LOGIN_USER
    reset_loader()
    return jsonify({
        "message": f"Logged out {current_user or 'current user'}", 
        "logged_out": True,
        "logged_in_as": None
    })


@app.route('/status')
def status():
    """Get current login status."""
    global L, _LOGIN_USER
    
    try:
        L = get_loader()
        if not L.context.is_logged_in:
            return jsonify({
                "logged_in": False,
                "logged_in_as": None,
                "status": "not_logged_in"
            })
        
        # Try to verify session is still valid
        try:
            current_username = L.test_login()
            return jsonify({
                "logged_in": True,
                "logged_in_as": current_username,
                "status": "ok"
            })
        except Exception as e:
            error_str = str(e)
            # If it's a rate limiting error, still consider as logged in
            if "Please wait a few minutes" in error_str or "401 Unauthorized" in error_str:
                return jsonify({
                    "logged_in": True,
                    "logged_in_as": _LOGIN_USER or "Unknown",
                    "status": "rate_limited",
                    "warning": "Rate limited - session may still work for downloads"
                })
            else:
                return jsonify({
                    "logged_in": False,
                    "logged_in_as": None,
                    "status": "session_error",
                    "error": error_str
                })
    except Exception as e:
        return jsonify({
            "logged_in": False,
            "logged_in_as": None,
            "status": "error",
            "error": str(e)
        })


@app.route('/download')
def download():  # type: ignore
    target = request.args.get('username')
    if not target:
        return jsonify({'error': 'username parameter required'}), 400
    try:
        limit = int(request.args.get('limit', '5'))
        delay = float(request.args.get('delay', '0') or 0)
        backoff = float(request.args.get('backoff', '15') or 15)
        stories_limit = int(request.args.get('stories_limit', '50') or 50)
    except ValueError:
        return jsonify({'error': 'numeric parameters invalid'}), 400
    include_posts = request.args.get('include_posts', '1') in ('1', 'true', 'yes')
    include_reels = request.args.get('include_reels', '1') in ('1', 'true', 'yes')
    include_stories = request.args.get('stories', '0') in ('1', 'true', 'yes')
    try:
        result = download_media(target, limit, include_posts, include_reels, include_stories, delay, backoff, stories_limit)
        
        # Enhanced response message
        profile_info = result.get('profile_info', {})
        profile_mediacount = profile_info.get('mediacount', 'unknown')
        profile_private = profile_info.get('is_private', 'unknown')
        
        message_parts = [f'Downloaded {result["count"]} posts/reels for {target}']
        if include_stories:
            message_parts.append('+ stories')
        message_parts.append(f'Posts:{result["stats"]["posts_downloaded"]} Reels:{result["stats"]["reels_downloaded"]} RateRetries:{result["stats"]["rate_limit_retries"]} Stories: {result["stories_status"]}')
        
        if profile_mediacount != 'unknown':
            message_parts.append(f'Profile has {profile_mediacount} posts total')
        if profile_private != 'unknown':
            message_parts.append(f'Private: {profile_private}')
            
        return jsonify({
            'message': ' | '.join(message_parts),
            'folders': result['folders'],
            'posts': result['posts_meta'],
            'stories': result['stories_meta'],
            'stories_status': result['stories_status'],
            'stats': result['stats'],
            'profile_info': result['profile_info'],
            'selection': {
                'include_posts': include_posts,
                'include_reels': include_reels,
                'include_stories': include_stories
            },
            'logged_in_as': _LOGIN_USER
        })
    except instastorysaver.exceptions.QueryReturnedNotFoundException:
        return jsonify({'error': 'Profile not found'}), 404
    except instastorysaver.exceptions.LoginRequiredException:
        return jsonify({'error': 'Login required to access this profile.'}), 401
    except instastorysaver.exceptions.ConnectionException as e:
        error_msg = str(e).lower()
        if "please wait a few minutes" in error_msg or "heavily rate limiting" in error_msg:
            return jsonify({
                'error': 'Instagram is heavily rate limiting your account. This is why no posts are being detected.',
                'rate_limited': True,
                'suggestion': 'Please wait 30-60 minutes before trying again. Consider using the extension less frequently.',
                'details': str(e)
            }), 429
        elif "challenge_required" in error_msg:
            return jsonify({
                'error': 'Instagram challenge required. Please log in through Instagram web/app first and complete any verification.',
                'challenge_required': True,
                'suggestion': 'Try logging in through Instagram.com, complete any challenges, then retry.'
            }), 429
        else:
            return jsonify({'error': f'Connection error: {str(e)}'}), 503
    except Exception as e:
        error_msg = str(e).lower()
        if "challenge_required" in error_msg:
            return jsonify({
                'error': 'Instagram challenge required. Please log in through Instagram web/app first and complete any verification.',
                'challenge_required': True
            }), 429
        return jsonify({'error': str(e)}), 500


@app.route('/')
def root():  # type: ignore
    return jsonify({
        "status": "ok",
        "info": "IG Story Downloader backend running",
        "logged_in_as": _LOGIN_USER,
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
