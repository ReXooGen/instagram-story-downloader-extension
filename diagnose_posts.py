"""
Instagram Post Access Diagnostic Tool
Helps diagnose why posts aren't being retrieved despite profile showing them.
"""
import requests
import json
import sys

API_BASE = "http://localhost:5000"

def test_profile_access(username):
    """Test profile access and post enumeration"""
    print(f"🔍 Testing profile access for: {username}")
    print("=" * 50)
    
    # Test basic download request
    try:
        params = {
            'username': username,
            'limit': 2,  # Small limit for testing
            'include_posts': 1,
            'include_reels': 1,
            'stories': 0,  # Skip stories for now
            'delay': 0
        }
        
        print("📊 Making download request...")
        resp = requests.get(f"{API_BASE}/download", params=params, timeout=60)
        data = resp.json()
        
        print(f"Response Status: {resp.status_code}")
        print(f"Message: {data.get('message', 'No message')}")
        
        # Profile info
        profile_info = data.get('profile_info', {})
        print(f"\n📱 Profile Information:")
        print(f"  Username: {profile_info.get('username', 'unknown')}")
        print(f"  Total Posts: {profile_info.get('mediacount', 'unknown')}")
        print(f"  Private: {profile_info.get('is_private', 'unknown')}")
        print(f"  Logged In: {profile_info.get('logged_in', 'unknown')}")
        
        # Stats
        stats = data.get('stats', {})
        print(f"\n📈 Download Stats:")
        print(f"  Posts Downloaded: {stats.get('posts_downloaded', 0)}")
        print(f"  Reels Downloaded: {stats.get('reels_downloaded', 0)}")
        print(f"  Rate Retries: {stats.get('rate_limit_retries', 0)}")
        
        # Posts metadata
        posts = data.get('posts', [])
        print(f"\n📝 Posts Metadata ({len(posts)} items):")
        for i, post in enumerate(posts[:5]):  # Show first 5
            if 'diagnostic' in post:
                print(f"  🔧 Diagnostic {i+1}:")
                print(f"    Issue: {post.get('diagnostic', 'unknown')}")
                print(f"    Suggestion: {post.get('suggestion', 'none')}")
                if 'workaround' in post:
                    print(f"    Workaround: {post.get('workaround')}")
            elif 'error' in post:
                print(f"  ❌ Error {i+1}: {post.get('error')}")
                if 'shortcode' in post:
                    print(f"    Post: {post.get('shortcode')}")
            else:
                print(f"  ✅ Success {i+1}: {post.get('shortcode', 'unknown')} ({post.get('type', 'unknown')})")
        
        # Error analysis
        if resp.status_code != 200:
            print(f"\n❌ Error Response:")
            print(f"  Error: {data.get('error', 'Unknown error')}")
            if 'suggestion' in data:
                print(f"  Suggestion: {data.get('suggestion')}")
            if 'rate_limited' in data:
                print(f"  Rate Limited: {data.get('rate_limited')}")
                
        return data
        
    except requests.exceptions.Timeout:
        print("⏰ Request timed out - Instagram may be heavily rate limiting")
        return None
    except requests.exceptions.ConnectionError:
        print("🔌 Cannot connect to backend server")
        print("   Make sure backend_server.py is running on localhost:5000")
        return None
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        return None

def test_login_status():
    """Check current login status"""
    try:
        resp = requests.get(f"{API_BASE}/status", timeout=10)
        data = resp.json()
        
        print("🔐 Login Status:")
        print(f"  Logged In: {data.get('logged_in', False)}")
        print(f"  Username: {data.get('logged_in_as', 'None')}")
        print(f"  Status: {data.get('status', 'unknown')}")
        if 'warning' in data:
            print(f"  Warning: {data.get('warning')}")
            
        return data.get('logged_in', False)
        
    except Exception as e:
        print(f"❌ Cannot check login status: {e}")
        return False

if __name__ == "__main__":
    print("🎯 Instagram Post Access Diagnostic Tool")
    print("=" * 50)
    
    # Check login first
    logged_in = test_login_status()
    print()
    
    if not logged_in:
        print("⚠️  Not logged in - some features may not work")
        print("   Use the Chrome extension to login first")
        print()
    
    # Test with provided username or ask for one
    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        username = input("Enter Instagram username to test: ").strip()
    
    if username:
        print()
        result = test_profile_access(username)
        
        print("\n" + "=" * 50)
        print("🔍 ANALYSIS:")
        
        if result:
            profile_info = result.get('profile_info', {})
            posts = result.get('posts', [])
            
            total_posts = profile_info.get('mediacount', 0)
            downloaded = result.get('stats', {}).get('posts_downloaded', 0) + result.get('stats', {}).get('reels_downloaded', 0)
            
            if total_posts > 0 and downloaded == 0:
                print("❌ ISSUE: Profile has posts but none were downloaded")
                print("\nPossible causes:")
                print("  1. Instagram is blocking post enumeration (most common)")
                print("  2. Account requires higher authentication level")
                print("  3. Rate limiting affecting post listing")
                print("  4. Posts are in a format the API doesn't recognize")
                
                print("\nSolutions to try:")
                print("  1. Wait 2-3 hours and try again")
                print("  2. Use a different Instagram account")
                print("  3. Try downloading stories only")
                print("  4. Enable both posts and reels in filters")
                
            elif total_posts == 0:
                print("ℹ️  Profile appears to have no posts")
                
            elif downloaded > 0:
                print(f"✅ SUCCESS: Downloaded {downloaded} out of {total_posts} total posts")
                
        print("\n🎯 Diagnostic complete!")
    else:
        print("No username provided.")
