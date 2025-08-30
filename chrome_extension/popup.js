const API_BASE = 'http://localhost:5000';

async function login() {
  const u = document.getElementById('loginUser').value.trim();
  const p = document.getElementById('loginPass').value;
  if (!u || !p) {
    document.getElementById('loginStatus').textContent = 'Username & password required';
    return;
  }
  document.getElementById('loginStatus').textContent = 'Logging in...';
  try {
    const resp = await fetch(API_BASE + '/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: u, password: p })
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || 'Login failed');
    document.getElementById('loginStatus').textContent = data.message;
  } catch (e) {
    document.getElementById('loginStatus').textContent = 'Error: ' + e.message;
  }
}

async function downloadSelected() {
  const username = document.getElementById('username').value.trim();
  const limit = document.getElementById('limitInput').value.trim() || '5';
  const delay = document.getElementById('delayInput').value.trim() || '0';
  const storyLimit = document.getElementById('storyLimitInput').value.trim() || '20';
  const backoff = document.getElementById('backoffInput').value.trim() || '15';
  const posts = document.getElementById('postsCheckbox').checked ? '1' : '0';
  const reels = document.getElementById('reelsCheckbox').checked ? '1' : '0';
  const stories = document.getElementById('storiesCheckbox').checked ? '1' : '0';
  if (!username) {
    document.getElementById('result').textContent = 'Target username required';
    return;
  }
  document.getElementById('result').textContent = 'Processing...';
  try {
    const qs = new URLSearchParams({
      username,
      limit,
      delay,
      stories,
      include_posts: posts,
      include_reels: reels,
      stories_limit: storyLimit,
      backoff,
    });
    const resp = await fetch(`${API_BASE}/download?${qs.toString()}`);
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || 'Request failed');
    const postsList = (data.posts || []).map(p => `- ${p.shortcode || ''} ${p.date_utc || ''} ${p.is_video ? '[VIDEO]' : ''}`).join('\n');
    const storiesList = (data.stories || []).map(s => `* STORY ${s.date_utc || ''} ${s.is_video ? '[VIDEO]' : ''}`).join('\n');
    const stats = data.stats ? `Posts:${data.stats.posts_downloaded||0} Reels:${data.stats.reels_downloaded||0} RateRetries:${data.stats.rate_limit_retries||0}` : '';
    const status = data.stories_status ? `Stories: ${data.stories_status}` : '';
    document.getElementById('result').textContent = `${data.message}\n${stats} ${status}\n${postsList}${storiesList? '\nStories:\n'+storiesList:''}\nBase: ${(data.folders && data.folders.base) || ''}`;
  } catch (e) {
    document.getElementById('result').textContent = 'Error: ' + e.message;
  }
}

document.getElementById('loginBtn').addEventListener('click', login);
document.getElementById('downloadBtn').addEventListener('click', downloadSelected);
