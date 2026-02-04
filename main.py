import os
import threading
import requests
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, BooleanProperty
from kivy.clock import Clock
from kivy.utils import platform

# Import our pure python logic
from search_logic import get_engine

# Load KV file
Builder.load_file('images.kv')

class ImageCard(BoxLayout):
    thumbnail = StringProperty('')
    source = StringProperty('')
    image_url = StringProperty('')
    selected = BooleanProperty(False)
    
    def on_checkbox_active(self, checkbox, value):
        self.selected = value
        # Notify root to update counter
        App.get_running_app().root.update_selection(self.image_url, value)

class RootWidget(BoxLayout):
    has_results = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.engine = None
        self.results_data = [] # List of dicts for RecycleView
        self.selected_urls = set()

    def do_search(self):
        query = self.ids.search_input.text.strip()
        engine_name = self.ids.engine_spinner.text.lower()
        size_val = self.ids.size_spinner.text
        
        if not query: return
        
        # Clean "Any Size" to None
        if size_val == "Any Size": size_val = None

        # Reset UI
        self.ids.rv.data = []
        self.results_data = []
        self.selected_urls.clear()
        self.update_download_btn()
        self.has_results = False
        
        # Init engine
        if engine_name == 'rule34': engine_name = 'rule34' 
        self.engine = get_engine(engine_name, query, size=size_val)
        
        self.load_more()

    def load_more(self):
        if not self.engine: return
        self.ids.load_more_btn.text = "Loading..."
        self.ids.load_more_btn.disabled = True
        
        threading.Thread(target=self._fetch_thread, daemon=True).start()

    def _fetch_thread(self):
        new_items = self.engine.fetch_next_batch()
        # Schedule UI update on main thread
        Clock.schedule_once(lambda dt: self._update_ui_results(new_items))

    def _update_ui_results(self, new_items):
        self.ids.load_more_btn.text = "Load More"
        self.ids.load_more_btn.disabled = False
        
        if not new_items:
            # Maybe show toast or label
            pass
        
        for item in new_items:
            self.results_data.append({
                'thumbnail': item.get('thumbnail'),
                'image_url': item.get('image'), # Full res
                'source': item.get('source'),
                'selected': False
            })
        
        self.ids.rv.data = self.results_data
        self.has_results = True

    def update_selection(self, url, is_selected):
        if is_selected:
            self.selected_urls.add(url)
        elif url in self.selected_urls:
            self.selected_urls.remove(url)
        self.update_download_btn()

    def update_download_btn(self):
        count = len(self.selected_urls)
        self.ids.download_btn.text = f"Download ({count})"
        self.ids.download_btn.disabled = count == 0

    def download_selected(self):
        urls = list(self.selected_urls)
        self.ids.download_btn.text = "Downloading..."
        self.ids.download_btn.disabled = True
        
        threading.Thread(target=self._download_thread, args=(urls,), daemon=True).start()

    def _download_thread(self, urls):
        # Determine download path
        if platform == 'android':
            from android.storage import primary_external_storage_path
            path = os.path.join(primary_external_storage_path(), 'Download', 'ImageSearch')
        else:
            path = os.path.join(os.getcwd(), 'downloads')
            
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except:
                pass 
        
        count = 0
        for url in urls:
            try:
                # Use a proper User-Agent for downloading too, some sites block defaults
                headers = {'User-Agent': 'Mozilla/5.0'}
                
                filename = url.split('/')[-1].split('?')[0]
                if not filename: filename = f"img_{count}.jpg"
                if '.' not in filename: filename += ".jpg"
                
                # Sanitize
                filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in '._-'])
                
                save_path = os.path.join(path, filename)
                
                # Stream download for large files
                with requests.get(url, stream=True, headers=headers, timeout=20) as r:
                    r.raise_for_status()
                    with open(save_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                    count += 1
            except Exception as e:
                print(f"Download error: {e}")
        
        Clock.schedule_once(lambda dt: self._finish_download(count))

    def _finish_download(self, count):
        self.ids.download_btn.text = f"Saved {count} images"
        self.ids.download_btn.disabled = False
        # Optional: Reset selection after download
        # self.selected_urls.clear()
        # for i in self.results_data: i['selected'] = False
        # self.ids.rv.data = self.results_data
        # self.update_download_btn()

class ImageSearchApp(App):
    def build(self):
        return RootWidget()

    def on_start(self):
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.INTERNET, Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])

if __name__ == '__main__':
    ImageSearchApp().run()
