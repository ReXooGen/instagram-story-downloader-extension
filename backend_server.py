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
    profile = instastorysaver.Profile.from_username(L.context, target_username)
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
    for post in profile.get_posts():
        if count >= limit:
            break
        is_reel_candidate = bool(post.is_video)
        if (is_reel_candidate and not include_reels) or ((not is_reel_candidate) and not include_posts):
            continue
        attempt = 0
        while True:
            try:
                sub = 'reels' if is_reel_candidate else 'posts'
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
                break
            except instastorysaver.exceptions.ConnectionException as ce:
                attempt += 1
                stats['rate_limit_retries'] += 1
                time.sleep(backoff * attempt)
                if attempt >= 3:
                    posts_meta.append({'error': str(ce)})
                    break
            except Exception as e:
                posts_meta.append({'error': str(e)})
                break
        count += 1
        if delay > 0:
            time.sleep(delay)

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
        'count': count
    }


@app.route('/login', methods=['POST'])
def login():
    global _LOGIN_USER
    data = request.get_json(force=True, silent=True) or {}
    ig_user = data.get('username')
    ig_pass = data.get('password')
    if not ig_user or not ig_pass:
        return jsonify({"error": "username and password required"}), 400
    L = get_loader()
    try:
        L.context.log("Attempting login...")
        L.load_session_from_file(ig_user)  # try existing session file first
        if not L.context.is_logged_in or L.test_login() != ig_user:
            L.context.log("Session file invalid or for different user, logging in fresh...")
            L.login(ig_user, ig_pass)
            L.save_session_to_file()
        _LOGIN_USER = ig_user
        return jsonify({"message": f"Logged in as {ig_user}", "logged_in": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 401


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
        return jsonify({
            'message': f'Downloaded {result["count"]} posts/reels for {target}' + (' + stories' if include_stories else ''),
            'folders': result['folders'],
            'posts': result['posts_meta'],
            'stories': result['stories_meta'],
            'stories_status': result['stories_status'],
            'stats': result['stats'],
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
    except Exception as e:
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
