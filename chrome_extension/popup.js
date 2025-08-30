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
    if (!resp.ok) {
      if (data.challenge_required || data.checkpoint_required) {
        document.getElementById('loginStatus').textContent = 
          '⚠️ ' + data.error + '\n\n' +
          '📱 Steps to fix:\n' +
          '1. Open Instagram.com in your browser\n' +
          '2. Log in and complete any verification\n' +
          '3. Return here and try again';
        document.getElementById('loginStatus').style.fontSize = '11px';
        document.getElementById('loginStatus').style.whiteSpace = 'pre-line';
      } else {
        throw new Error(data.error || 'Login failed');
      }
      return;
    }
    document.getElementById('loginStatus').textContent = data.message;
    document.getElementById('loginStatus').style.fontSize = '';
    document.getElementById('loginStatus').style.whiteSpace = '';
    // Clear password field on successful login for security
    document.getElementById('loginPass').value = '';
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
    if (!resp.ok) {
      if (data.challenge_required) {
        document.getElementById('result').textContent = 
          '⚠️ Instagram Challenge Required\n\n' +
          '📱 Please follow these steps:\n' +
          '1. Open Instagram.com in your browser\n' +
          '2. Log in to your account\n' +
          '3. Complete any verification/challenges\n' +
          '4. Return here and try again\n\n' +
          '💡 Tip: Try waiting 10-15 minutes before retrying';
        document.getElementById('result').style.fontSize = '11px';
        document.getElementById('result').style.whiteSpace = 'pre-line';
        return;
      }
      throw new Error(data.error || 'Request failed');
    }
    const postsList = (data.posts || []).map(p => `- ${p.shortcode || ''} ${p.date_utc || ''} ${p.is_video ? '[VIDEO]' : ''}`).join('\n');
    const storiesList = (data.stories || []).map(s => `* STORY ${s.date_utc || ''} ${s.is_video ? '[VIDEO]' : ''}`).join('\n');
    const stats = data.stats ? `Posts:${data.stats.posts_downloaded||0} Reels:${data.stats.reels_downloaded||0} RateRetries:${data.stats.rate_limit_retries||0}` : '';
    const status = data.stories_status ? `Stories: ${data.stories_status}` : '';
    document.getElementById('result').textContent = `${data.message}\n${stats} ${status}\n${postsList}${storiesList? '\nStories:\n'+storiesList:''}\nBase: ${(data.folders && data.folders.base) || ''}`;
    document.getElementById('result').style.fontSize = '';
    document.getElementById('result').style.whiteSpace = '';
  } catch (e) {
    document.getElementById('result').textContent = 'Error: ' + e.message;
    document.getElementById('result').style.fontSize = '';
    document.getElementById('result').style.whiteSpace = '';
  }
}

async function loginWithBrowser() {
  document.getElementById('loginStatus').textContent = 'Loading browser cookies...';
  try {
    const resp = await fetch(API_BASE + '/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ use_browser_cookies: true })
    });
    const data = await resp.json();
    if (!resp.ok) {
      if (data.browser_cookies_failed) {
        document.getElementById('loginStatus').textContent = 
          '⚠️ Browser cookies failed\n\n' +
          '📱 Please:\n' +
          '1. Log in to Instagram.com in your browser\n' +
          '2. Make sure you stay logged in\n' +
          '3. Try this button again\n\n' +
          'Or use username/password login instead';
        document.getElementById('loginStatus').style.fontSize = '11px';
        document.getElementById('loginStatus').style.whiteSpace = 'pre-line';
      } else {
        throw new Error(data.error || 'Browser login failed');
      }
      return;
    }
    document.getElementById('loginStatus').textContent = data.message;
    document.getElementById('loginStatus').style.fontSize = '';
    document.getElementById('loginStatus').style.whiteSpace = '';
  } catch (e) {
    document.getElementById('loginStatus').textContent = 'Error: ' + e.message;
  }
}

async function logout() {
  document.getElementById('loginStatus').textContent = 'Logging out...';
  try {
    const resp = await fetch(API_BASE + '/logout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.error || 'Logout failed');
    }
    document.getElementById('loginStatus').textContent = data.message;
    document.getElementById('loginUser').value = '';
    document.getElementById('loginPass').value = '';
    document.getElementById('result').textContent = '';
  } catch (e) {
    document.getElementById('loginStatus').textContent = 'Error: ' + e.message;
  }
}

document.getElementById('loginBtn').addEventListener('click', login);
document.getElementById('logoutBtn').addEventListener('click', logout);
document.getElementById('downloadBtn').addEventListener('click', downloadSelected);
