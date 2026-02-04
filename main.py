import os
import threading
import requests
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, BooleanProperty, ListProperty
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
        if not query: return

        # Reset
        self.ids.rv.data = []
        self.results_data = []
        self.selected_urls.clear()
        self.update_download_btn()
        
        # Init engine
        if engine_name == 'rule34': engine_name = 'rule34' # spinner text match
        self.engine = get_engine(engine_name, query)
        
        self.load_more()

    def load_more(self):
        if not self.engine: return
        
        # Run in thread
        threading.Thread(target=self._fetch_thread, daemon=True).start()

    def _fetch_thread(self):
        new_items = self.engine.fetch_next_batch()
        # Schedule UI update on main thread
        Clock.schedule_once(lambda dt: self._update_ui_results(new_items))

    def _update_ui_results(self, new_items):
        if not new_items:
            # Maybe show toast?
            pass
        
        for item in new_items:
            self.results_data.append({
                'thumbnail': item.get('thumbnail'),
                'image_url': item.get('image'),
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
        self.ids.download_btn.text = f"Download Selected ({count})"
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
            msg = "Downloading..."
            # Simple path: /sdcard/Download/ImageSearch
            path = os.path.join(primary_external_storage_path(), 'Download', 'ImageSearch')
        else:
            path = os.path.join(os.getcwd(), 'downloads')
            
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except:
                pass # Can fail on android if not permitted yet
        
        count = 0
        for url in urls:
            try:
                filename = url.split('/')[-1].split('?')[0]
                if not filename: filename = f"img_{count}.jpg"
                if '.' not in filename: filename += ".jpg"
                
                # Sanitize
                filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in '._-'])
                
                save_path = os.path.join(path, filename)
                
                r = requests.get(url, timeout=20)
                if r.status_code == 200:
                    with open(save_path, 'wb') as f:
                        f.write(r.content)
                    count += 1
            except Exception as e:
                print(f"Download error: {e}")
        
        Clock.schedule_once(lambda dt: self._finish_download(count))

    def _finish_download(self, count):
        self.ids.download_btn.text = f"Downloaded {count} files"
        self.ids.download_btn.disabled = False
        # Clear selection logic if desired, or keep it

class ImageSearchApp(App):
    def build(self):
        return RootWidget()

    def on_start(self):
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.INTERNET, Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])

if __name__ == '__main__':
    ImageSearchApp().run()
