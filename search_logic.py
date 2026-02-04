import requests
import re
import json

# Global headers to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

class SearchEngine:
    def __init__(self, query):
        self.query = query
        self.offset = 0
        self.headers = HEADERS.copy()
        self._buffer = []

    def fetch_next_batch(self):
        """Returns a list of result dicts or empty list."""
        try:
            return self._fetch_more()
        except Exception as e:
            print(f"Engine Error: {e}")
            return []

    def _fetch_more(self):
        raise NotImplementedError

class BingImageSearch(SearchEngine):
    def __init__(self, query):
        super().__init__(query)
        self.offset = 1 # Bing starts at 1

    def _fetch_more(self):
        if self.offset > 1000: return []
        
        url = "https://www.bing.com/images/search"
        params = {
            'q': self.query,
            'form': 'HDRSC2',
            'first': self.offset,
            'scenario': 'ImageBasicHover'
        }
        
        try:
            print(f"Fetching Bing offset {self.offset}...")
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
            print(f"Bing search error: {e}")
            return []

class DuckDuckGoSearch(SearchEngine):
    def __init__(self, query):
        super().__init__(query)
        self.headers['Referer'] = 'https://duckduckgo.com/'

    def _fetch_more(self):
        if self.offset > 0: return []
        
        try:
            print("Fetching DDG VQD...")
            res = requests.get('https://duckduckgo.com/', params={'q': self.query}, headers=self.headers)
            
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
                'p': '1'
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
    def __init__(self, query):
        super().__init__(query)
        self.page = 0

    def _fetch_more(self):
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
            print(f"Fetching Rule34 page {self.page}...")
            res = requests.get(url, params=params, headers=self.headers, timeout=10)
            
            if not res.text.strip(): return []
            try:
                data = res.json()
            except: return []
            
            formatted = []
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                         formatted.append({
                            'image': item.get('file_url'),
                            'thumbnail': item.get('preview_url'),
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
    def __init__(self, query):
        super().__init__(query)
        self.page = 0

    def _fetch_more(self):
        if self.page > 0: return []
        
        url = f"https://yandex.com/images/search"
        params = {'text': self.query}
        try:
             res = requests.get(url, params=params, headers=self.headers, timeout=10)
             matches = re.findall(r'"hh?tps?://[^"]+"', res.text)
             images = [m.strip('"') for m in matches if any(x in m for x in ['.jpg', '.png', '.jpeg']) and 'avatars.mds.yandex.net' not in m]
             images = list(set(images))
             
             formatted = []
             for img in images[:30]:
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

def get_engine(name, query):
    if name == 'ddg': return DuckDuckGoSearch(query)
    if name == 'rule34': return Rule34Search(query)
    if name == 'yandex': return YandexSearch(query)
    return BingImageSearch(query)
