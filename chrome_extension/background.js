// This file can be used for background tasks, e.g., communication with popup or content scripts
chrome.runtime.onInstalled.addListener(() => {
  console.log('Instaloader Extension installed');
});
