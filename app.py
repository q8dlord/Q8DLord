import os
import requests
import uuid
import re
import json
from flask import Flask, render_template, request, jsonify, Response
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), 'downloads')

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)


# Global cache for search generators
# format: { 'uuid': generator_object }
SEARCH_SESSIONS = {}

class SearchEngine:
    def __init__(self, query):
        self.query = query
        self.offset = 0
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def __iter__(self):
        return self

    def __next__(self):
        if not hasattr(self, '_buffer'):
            self._buffer = []
        
        while not self._buffer:
            new_results = self._fetch_more()
            if not new_results:
                raise StopIteration
            self._buffer.extend(new_results)
        
        return self._buffer.pop(0)

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
        
        # 1. Get VQD
        try:
            print("Fetching DDG VQD...")
            res = requests.get('https://duckduckgo.com/', params={'q': self.query}, headers=self.headers)
            
            vqd = None
            # Regex for vqd
            m = re.search(r'vqd=[\'"]([^\'"]+)[\'"]', res.text)
            if m:
                vqd = m.group(1)
            
            if not vqd:
                # Try simpler search if regex fails or blocked
                print("DDG VQD not found.")
                return []
            
            # 2. Fetch Images
            url = "https://duckduckgo.com/i.js"
            params = {
                'l': 'us-en',
                'o': 'json',
                'q': self.query,
                'vqd': vqd,
                'f': ',,,',
                'p': '1'
            }
            # Referer is crucial
            self.headers['Referer'] = 'https://duckduckgo.com/'
            res = requests.get(url, params=params, headers=self.headers)
            
            if res.status_code == 403:
                print("DDG 403 Forbidden - Bot detected.")
                return []
                
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
        # Use standard Rule34.xxx API (dapi)
        # Note: 'rule34.xyz' might be a different site. 
        # API Url: https://api.rule34.xxx/index.php?page=dapi&s=post&q=index&json=1
        # The 'api.' subdomain sometimes complicates things. The main domain works too?
        # Let's try main domain: https://rule34.xxx/index.php
        
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
            # Some boorus require User-Agent to not look like script, but we have one.
            # Sometimes 'api.' is strict.
            res = requests.get(url, params=params, headers=self.headers, timeout=10)
            
            if res.status_code != 200:
                print(f"Rule34 status: {res.status_code}")
                # Fallback to HTML scraping if API blocks
                return []
            
            # Check if response is empty string (sometimes happens if no results)
            if not res.text.strip():
                return []
                
            try:
                data = res.json()
            except json.JSONDecodeError:
                print("Rule34 returned non-JSON")
                return []
            
            formatted = []
            # data is a list of dicts
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
        # Yandex has difficult scraping protections (CAPTCHA).
        # We can try a very basic scrape of the initial page.
        if self.page > 0: return []
        
        url = f"https://yandex.com/images/search"
        params = {'text': self.query}
        
        try:
             # This is highly likely to get blocked without cookies/selenium
             # But we'll try best effort with a standard header.
             res = requests.get(url, params=params, headers=self.headers, timeout=10)
             
             # Look for JSON data often embedded in data-bem or similar attributes
             # Detailed scraping is complex in one go.
             # Fallback: Regex for commonly exposed image URLs (tse...)
             
             # Matches simplified for yandex
             # This is a weak implementation but "top 3" requirement is hard without APIs.
             matches = re.findall(r'"hh?tps?://[^"]+"', res.text)
             # Filter for image extensions
             images = [m.strip('"') for m in matches if any(x in m for x in ['.jpg', '.png', '.jpeg']) and 'avatars.mds.yandex.net' not in m]
             # Uniq
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
            print(f"Yandex Error: {e}")
            return []

@app.route('/')
def index():
    return render_template('index.html')

def get_next_batch(gen, count=30):
    results = []
    try:
        for _ in range(count):
            r = next(gen)
            results.append({
                'image': r.get('image'),
                'thumbnail': r.get('thumbnail'),
                'title': r.get('title'),
                'source': r.get('source'),
                'url': r.get('url'),
                'width': r.get('width', 0),
                'height': r.get('height', 0)
            })
    except StopIteration:
        pass
    except Exception as e:
        print(f"Error iterating: {e}")
    return results

@app.route('/api/search', methods=['GET'])
def search_images():
    query = request.args.get('q', '')
    size = request.args.get('size', '')
    engine = request.args.get('engine', 'bing')
    
    if not query:
        return jsonify({'error': 'No query provided'}), 400

    try:
        # Handle custom high-res triggers
        search_query = query
        if size in ['2k', '4k', '8k']:
            search_query = f"{query} {size} wallpaper"
            
        # Select Generator
        if engine == 'ddg':
            gen = DuckDuckGoSearch(search_query)
        elif engine == 'rule34':
            gen = Rule34Search(search_query) # Uses tags usually
        elif engine == 'yandex':
            gen = YandexSearch(search_query)
        else:
            gen = BingImageSearch(search_query)
        
        # Create session
        session_id = str(uuid.uuid4())
        SEARCH_SESSIONS[session_id] = gen
        
        # Get first batch
        results = get_next_batch(gen, count=30)
            
    except Exception as e:
        print(f"Search error: {e}")
        return jsonify({'error': str(e)}), 500

    return jsonify({'results': results, 'session_id': session_id})


@app.route('/api/more', methods=['GET'])
def search_more():
    session_id = request.args.get('session_id')
    if not session_id or session_id not in SEARCH_SESSIONS:
        return jsonify({'error': 'Invalid or expired session'}), 400
        
    try:
        gen = SEARCH_SESSIONS[session_id]
        results = get_next_batch(gen, count=30)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
    return jsonify({'results': results})

@app.route('/api/proxy_download', methods=['GET'])
def proxy_download():
    url = request.args.get('url')
    if not url:
        return "No URL provided", 400
    try:
        # Stream the file from the source to the client
        r = requests.get(url, stream=True, timeout=15)
        r.raise_for_status()
        
        # Extract filename
        filename = url.split('/')[-1].split('?')[0]
        if not filename or len(filename) > 50: 
            filename = f"image_{uuid.uuid4().hex[:8]}.jpg"
        
        # Ensure it has an extension
        if '.' not in filename: filename += ".jpg"
            
        return Response(
            r.iter_content(chunk_size=8192),
            content_type=r.headers.get('Content-Type', 'image/jpeg'),
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        return str(e), 500

def download_single_image(url):
    try:
        # Get filename from URL or default
        filename = url.split('/')[-1].split('?')[0]
        if not filename or len(filename) > 200:
            filename = f"image_{abs(hash(url))}.jpg"
            
        # Ensure extension
        if '.' not in filename:
             filename += ".jpg"
             
        # Sanitize filename
        filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in '._- ']).strip()
        
        save_path = os.path.join(DOWNLOAD_FOLDER, filename)
        
        # Avoid overwrites
        counter = 1
        base_name, ext = os.path.splitext(filename)
        while os.path.exists(save_path):
            save_path = os.path.join(DOWNLOAD_FOLDER, f"{base_name}_{counter}{ext}")
            counter += 1

        response = requests.get(url, timeout=15, stream=True)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        return {'url': url, 'status': 'success', 'path': save_path}
    except Exception as e:
        return {'url': url, 'status': 'error', 'error': str(e)}

@app.route('/api/download', methods=['POST'])
def download_images():
    data = request.json
    urls = data.get('urls', [])
    
    if not urls:
        return jsonify({'error': 'No URLs provided'}), 400
        
    results = []
    # Use ThreadPoolExecutor for concurrent downloads
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(download_single_image, urls))
        
    return jsonify({'results': results})

if __name__ == '__main__':
    # Listen on all interfaces
    app.run(host='0.0.0.0', debug=True, port=5000)
