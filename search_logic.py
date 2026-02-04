import requests
import re
import json
import random

# Global headers to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

class SearchEngine:
    def __init__(self, query, size=None):
        self.original_query = query
        self.size = size
        self.query = self._format_query(query, size)
        self.offset = 0
        self.headers = HEADERS.copy()
        
    def _format_query(self, query, size):
        """Appends size terms for generic engines."""
        if not size or size == "Any":
            return query
        if size == "Wallpaper":
            return f"{query} wallpaper"
        if size in ["2k", "4k", "8k"]:
            return f"{query} {size} wallpaper"
        return f"{query} {size}"

    def fetch_next_batch(self):
        try:
            return self._fetch_more()
        except Exception as e:
            print(f"Engine Error: {e}")
            return []

    def _fetch_more(self):
        raise NotImplementedError

class BingImageSearch(SearchEngine):
    def __init__(self, query, size=None):
        super().__init__(query, size)
        self.offset = 1 

    def _fetch_more(self):
        if self.offset > 1000: return []
        
        url = "https://www.bing.com/images/search"
        # adlt=off disables SafeSearch
        params = {
            'q': self.query,
            'form': 'HDRSC2',
            'first': self.offset,
            'scenario': 'ImageBasicHover',
            'adlt': 'off' 
        }
        
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            
            links = re.findall(r'murl&quot;:&quot;([^&]+)&quot;', resp.text)
            if not links:
                 links = re.findall(r'"murl":"([^"]+)"', resp.text)
            
            formatted_results = []
            for link in links:
                formatted_results.append({
                    'image': link,
                    'thumbnail': link, 
                    'title': 'Bing Image',
                    'source': 'Bing',
                    'url': link
                })
            
            if not formatted_results: return []
            self.offset += len(formatted_results)
            return formatted_results
        except Exception as e:
            print(f"Bing Error: {e}")
            return []

class DuckDuckGoSearch(SearchEngine):
    def __init__(self, query, size=None):
        super().__init__(query, size)
        self.headers['Referer'] = 'https://duckduckgo.com/'

    def _fetch_more(self):
        if self.offset > 0: return []
        
        try:
            # First request to get VQD (safe search off might need params here too)
            # kp=-2 (SafeSearch Off)
            res = requests.get('https://duckduckgo.com/', params={'q': self.query, 'kp': '-2'}, headers=self.headers)
            
            vqd = None
            m = re.search(r'vqd=[\'"]([^\'"]+)[\'"]', res.text)
            if m: vqd = m.group(1)
            
            if not vqd: return []
            
            url = "https://duckduckgo.com/i.js"
            params = {
                'l': 'us-en',
                'o': 'json',
                'q': self.query,
                'vqd': vqd,
                'f': ',,,',
                'p': '1',
                'kp': '-2' # Force SafeSearch Off
            }
            self.headers['Referer'] = 'https://duckduckgo.com/'
            res = requests.get(url, params=params, headers=self.headers)
            
            if res.status_code == 403: return []
                
            data = res.json()
            results = data.get('results', [])
            
            formatted = []
            for r in results:
                formatted.append({
                    'image': r.get('image'),
                    'thumbnail': r.get('thumbnail'),
                    'title': r.get('title', 'DDG Image'),
                    'source': 'DuckDuckGo',
                    'url': r.get('url')
                })
            
            self.offset = 1
            return formatted
        except Exception as e:
            print(f"DDG Error: {e}")
            return []

class Rule34Search(SearchEngine):
    def __init__(self, query, size=None):
        # Rule34 doesn't need "wallpaper" appended, uses tags
        super().__init__(query, size) # Still call super to set defaults
        self.query = query # Revert to raw query (tags)
        self.page = 0
        self.headers['User-Agent'] = f'Mozilla/5.0 (Random{random.randint(1,999)})' # Randomize slightly

    def _fetch_more(self):
        # Using main domain for API access
        url = "https://rule34.xxx/index.php" 
        params = {
            'page': 'dapi',
            's': 'post',
            'q': 'index',
            'json': 1,
            'limit': 20,
            'pid': self.page,
            'tags': self.query
        }
        
        try:
            res = requests.get(url, params=params, headers=self.headers, timeout=10)
            
            if not res.text.strip(): return []
            try:
                data = res.json()
            except: return []
            
            formatted = []
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        # Use 'sample_url' for better loading in grid if available, else file_url
                        # Ideally: Thumbnail = preview_url, Full = file_url
                         formatted.append({
                            'image': item.get('file_url'), # Full res for download/view
                            'thumbnail': item.get('sample_url', item.get('file_url')), # Sample for grid (faster loading)
                            'title': f"Score: {item.get('score', 0)}",
                            'source': 'Rule34',
                            'url': f"https://rule34.xxx/index.php?page=post&s=view&id={item.get('id')}"
                        })
            
            if not formatted: return []
            self.page += 1
            return formatted
        except Exception as e:
            print(f"Rule34 Error: {e}")
            return []

class YandexSearch(SearchEngine):
    def __init__(self, query, size=None):
        super().__init__(query, size)
        self.page = 0

    def _fetch_more(self):
        if self.page > 0: return []
        
        url = f"https://yandex.com/images/search"
        # text=query, isize=eq (?), hidden params for safe search?
        # Yandex safe search is usually a cookie or setting.
        # Try adding 'must=true' or similar. 
        # Actually in scraping, just adding terms like "uncensored" helps if user typed it.
        # We rely on query mainly.
        
        params = {'text': self.query}
        try:
             res = requests.get(url, params=params, headers=self.headers, timeout=10)
             matches = re.findall(r'"hh?tps?://[^"]+"', res.text)
             # Filter more strictly for images
             images = [m.strip('"') for m in matches if any(x in m for x in ['.jpg', '.png', '.jpeg']) and 'avatars.mds.yandex.net' not in m]
             images = list(set(images))
             
             formatted = []
             for img in images[:40]: # increased limit
                  formatted.append({
                      'image': img,
                      'thumbnail': img,
                      'title': 'Yandex Result',
                      'source': 'Yandex',
                      'url': img
                  })
                  
             self.page = 1
             return formatted
        except Exception as e:
            return []

def get_engine(name, query, size=None):
    if name == 'ddg': return DuckDuckGoSearch(query, size)
    if name == 'rule34': return Rule34Search(query, size)
    if name == 'yandex': return YandexSearch(query, size)
    return BingImageSearch(query, size)
