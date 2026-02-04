import requests
import re
import json
import random
import time
from urllib.parse import unquote

class SearchEngine:
    def __init__(self, query, size=None):
        self.original_query = query
        self.size = size
        self.query = self._format_query(query, size)
        self.offset = 0
        self.offset = 0
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
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
        self.headers['Accept'] = '*/*'

    def _fetch_more(self):
        if self.offset > 1000: return []
        
        # Bing safe search OFF -> adlt=off
        url = "https://www.bing.com/images/search"
        params = {
            'q': self.query,
            'first': self.offset,
            'count': 35,
            'adlt': 'off', # OFF safe search
            'form': 'HDRSC2'
        }
        
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            
            # Bing often gives "murl" (Main URL) and "turl" (Thumbnail URL)
            links = re.findall(r'murl&quot;:&quot;([^&]+)&quot;', resp.text)
            if not links:
                 links = re.findall(r'"murl":"([^"]+)"', resp.text)
            
            # Thumbnails: turl
            thumbs = re.findall(r'turl&quot;:&quot;([^&]+)&quot;', resp.text)
            if not thumbs:
                thumbs = re.findall(r'"turl":"([^"]+)"', resp.text)
            
            formatted_results = []
            for i, link in enumerate(links):
                # Clean URL
                full_url = unquote(link)
                # Ensure thumbnail is available
                thumb_url = unquote(thumbs[i]) if i < len(thumbs) else full_url

                formatted_results.append({
                    'image': full_url,
                    'thumbnail': thumb_url, 
                    'title': 'Bing Image',
                    'source': 'Bing',
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
            # Force SAFE SEARCH OFF: kp=-2
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
                'kp': '-2' # OFF
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
                    'source': 'DuckDuckGo'
                })
            
            self.offset = 1
            return formatted
        except Exception as e:
            print(f"DDG Error: {e}")
            return []


from api_client import CLIENT

class Rule34Search(SearchEngine):
    def __init__(self, query, size=None):
        super().__init__(query, size)
        self.query = query # Tags
        self.page = 0

    def _fetch_more(self):
        # Use the rate-limited client
        data = CLIENT.search(self.query, page=self.page)
        
        formatted = []
        for item in data:
            # API returns fields: file_url, preview_url, score, etc.
            # Handle potential missing fields
            if 'file_url' not in item: continue
            
            # API URL might be http, upgrading to https
            full_url = item.get('file_url', '').replace('http:', 'https:')
            thumb_url = item.get('preview_url', '').replace('http:', 'https:')
            
            # If thumb is missing, use full (dangerous for bandwidth but better than nothing)
            if not thumb_url: thumb_url = full_url
            
            formatted.append({
                'image': full_url,
                'thumbnail': thumb_url,
                'title': f"Score: {item.get('score', 0)}",
                'source': 'Rule34',
                'url': full_url, # Direct link
                'is_resolvable': False # API gives direct links!
            })
            
        if formatted:
            self.page += 1
            
        return formatted


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
