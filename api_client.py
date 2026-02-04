import time
import requests
import threading

class Rule34Client:
    def __init__(self, api_key=None, user_id=None):
        self.api_key = api_key
        self.user_id = user_id
        # Shared lock for throttling across threads
        self.lock = threading.Lock()
        self.last_request_time = 0
        self.min_delay = 1.1 # 1.1s to be safe (limit is 1s)
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def _wait_for_slot(self):
        """Block until safe to make a request."""
        with self.lock:
            now = time.time()
            elapsed = now - self.last_request_time
            if elapsed < self.min_delay:
                sleep_time = self.min_delay - elapsed
                print(f"[API] Throttling: Sleeping {sleep_time:.2f}s...")
                time.sleep(sleep_time)
            
            self.last_request_time = time.time()

    def search(self, tags, page=0, limit=20):
        url = "https://api.rule34.xxx/index.php"
        params = {
            'page': 'dapi',
            's': 'post',
            'q': 'index',
            'json': 1,
            'limit': limit,
            'pid': page,
            'tags': tags
        }
        
        if self.api_key and self.user_id:
            params['api_key'] = self.api_key
            params['user_id'] = self.user_id
            
        return self._make_request(url, params)

    def _make_request(self, url, params, retries=3):
        for attempt in range(retries):
            self._wait_for_slot()
            
            try:
                print(f"[API] Fetching (Attempt {attempt+1}): {params.get('tags')}")
                res = requests.get(url, params=params, headers=self.headers, timeout=15)
                
                if res.status_code == 200:
                    # Check for empty response (common on last page)
                    if not res.text.strip():
                        return []
                    
                    try:
                        data = res.json()
                        if isinstance(data, list):
                            return data
                        elif isinstance(data, dict):
                             # Sometimes API returns error dict
                             print(f"[API] Response Dict: {data}")
                             return []
                    except Exception as e:
                        # Sometimes XML error is returned despite json=1 if auth fails
                        print(f"[API] JSON Parse Error: {e}, Text: {res.text[:100]}")
                        return []
                
                elif res.status_code == 429:
                    print(f"[API] 429 Too Many Requests. Backing off...")
                    time.sleep(5) # Long pause for backoff
                    continue # Retry
                
                else:
                    print(f"[API] Error {res.status_code}")
                    return []
                    
            except Exception as e:
                print(f"[API] Network Error: {e}")
                
        return []

# Singleton instance for global use
# User provided: &api_key=7270189f5823ed0a95585e2a16dd3cf4dad5e9a2fba1b54f2a6ca89ed52fe57d418619766eac1b050a4a37a9d3a1a773db3a61d5eb9ac5550168f810ca2a1eaf&user_id=5896660
CLIENT = Rule34Client(
    api_key="7270189f5823ed0a95585e2a16dd3cf4dad5e9a2fba1b54f2a6ca89ed52fe57d418619766eac1b050a4a37a9d3a1a773db3a61d5eb9ac5550168f810ca2a1eaf",
    user_id="5896660"
)
