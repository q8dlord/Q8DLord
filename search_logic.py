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
        # Using HTML scraping as it is more reliable for public access without API keys
        url = "https://rule34.xxx/index.php" 
        params = {
            'page': 'post',
            's': 'list',
            'tags': self.query,
            'pid': self.page * 42 # pid is offset by count usually (42 per page default?)
            # Actually standard layout might be 42 or 20. Let's assume pid is page index * 20 for API, 
            # but for HTML 'pid' is usually the *offset* count. 
            # Let's try to detect if we need page number or offset.
            # HTML pagination: index.php?page=post&s=list&tags=...&pid=42
        }
        # Override pid logic for HTML
        params['pid'] = self.page * 42

        try:
            res = requests.get(url, params=params, headers=self.headers, timeout=10)
            
            # Parsing HTML
            # <span class="thumb" ...><a href="..."> <img src="..."> </a></span>
            
            # Find all thumb spans to keep order
            # simpler approach: find all (view_url, thumb_url) pairs
            
            # Regex for <a id="..." href="([^"]+)">\s*<img src="([^"]+)"
            # Note: href is relative often.
            
            # Robust regex for <a><img> structure
            # Finds span with class thumb, then extracts href and src
            # Handles newlines and different attribute orders
            # <span ... class="thumb" ...> <a ... href="..."> <img ... src="...">
            
            thumb_spans = re.findall(r'<span[^>]*class="thumb"[^>]*>.*?</span>', res.text, re.DOTALL)
            
            formatted = []
            seen_ids = set()
            
            for span in thumb_spans:
                # Extract href (view page)
                m_href = re.search(r'<a[^>]+href="([^"]+)"', span)
                if not m_href: continue
                href = m_href.group(1)
                
                # Extract src (thumbnail)
                m_src = re.search(r'<img[^>]+src="([^"]+)"', span)
                if not m_src: continue
                src = m_src.group(1)
                if 'page=post&s=view' not in href: continue
                
                # Construct absolute URL
                if href.startswith('/'):
                    view_url = "https://rule34.xxx" + href
                else:
                    view_url = "https://rule34.xxx/" + href
                    
                # Basic ID extraction for uniqueness
                # id=12345
                m_id = re.search(r'id=(\d+)', view_url)
                if m_id:
                    if m_id.group(1) in seen_ids: continue
                    seen_ids.add(m_id.group(1))
                
                # Thumb URL
                # src might be "thumbnails/..." or full image if preview
                thumb_url = src
                if not thumb_url.startswith('http'):
                    thumb_url = "https://rule34.xxx/" + thumb_url.lstrip('/')

                # For Rule34, we CANNOT easily guess the full image URL without hashing.
                # So we set 'image' = view_url, and let the UI resolve it on click.
                # We flag it internally if possible, or just detect by string.
                
                formatted.append({
                    'image': view_url, # To be resolved
                    'thumbnail': thumb_url, 
                    'title': f"Rule34 {m_id.group(1) if m_id else ''}",
                    'source': 'Rule34',
                    'url': view_url,
                    'is_resolvable': True # Hint for main.py
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
        # Mobile UA sometimes gets easier HTML or different handling
        self.headers['User-Agent'] = "Mozilla/5.0 (Linux; Android 10; SM-G960U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Mobile Safari/537.36"

    def _fetch_more(self):
        if self.page > 0: return []
        
        url = f"https://yandex.com/images/search"
        # Force safe search off? Yandex is tricky. 
        # Adding 'family=no' is a common param for some engines, worth a try.
        params = {'text': self.query, 'family': 'no'} 
        try:
             res = requests.get(url, params=params, headers=self.headers, timeout=10)
             # Regex update for mobile or desktop
             # Looking for img_href or similar in JSON data blobs
             matches = re.findall(r'"hh?tps?://[^"]+"', res.text)
             images = [m.strip('"') for m in matches if any(x in m for x in ['.jpg', '.png', '.jpeg']) and 'avatars.mds.yandex.net' not in m]
             images = list(set(images))
             
             formatted = []
             for img in images[:40]:
                  formatted.append({
                      'image': img,
                      'thumbnail': img, # Yandex scrape doesn't give separate thumb easily yet
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
