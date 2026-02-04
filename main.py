import os
import threading
import requests
import time
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.modalview import ModalView
from kivy.uix.carousel import Carousel
from kivy.uix.image import AsyncImage, Image
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import StringProperty, BooleanProperty, NumericProperty, ListProperty
from kivy.clock import Clock
from kivy.utils import platform
from kivy.loader import Loader

# CRITICAL: Set headers for all Kivy AsyncImages globally
# Removing 'Referer' as it blocks Rule34/other sites
Loader.headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

from search_logic import get_engine

Builder.load_file('images.kv')

class FullScreenViewer(ModalView):
    def __init__(self, data_list, start_index=0, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, 1)
        self.auto_dismiss = True # Allow back button to close
        self.background_color = (0, 0, 0, 1)
        self.data_list = data_list
        self.current_index = start_index

        self.main_layout = FloatLayout()
        
        # Carousel for swiping
        self.carousel = Carousel(direction='right', loop=False)
        self.carousel.bind(index=self.on_slide_change)
        
        # Pre-populate nearby images for smoothness (lazy loading would be better but this is simpler)
        # Limit to +/- 5 images around start_index to save memory if list is huge?
        # For now, load all (AsyncImage handles caching/loading lazily effectively)
        for item in data_list:
            # High Res Image
            img = AsyncImage(
                source=item['image'], # Uses the full resolution URL
                allow_stretch=True, 
                keep_ratio=True,
                nocache=False,
                # Simple loading placeholder setup could go here
            )
            self.carousel.add_widget(img)
            
        self.carousel.index = start_index
        self.main_layout.add_widget(self.carousel)
        
        # Overlay Control
        self.overlay = BoxLayout(
            orientation='vertical', 
            size_hint=(1, None), 
            height="80dp",
            pos_hint={'bottom': 1}
        )
        # Background for text
        with self.overlay.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(0, 0, 0, 0.7)
            self.rect = Rectangle(pos=self.overlay.pos, size=self.overlay.size)
        self.overlay.bind(pos=self._update_rect, size=self._update_rect)

        # Info
        self.lbl = Label(text="Loading...", font_size='14sp', size_hint_y=0.5, color=(1,1,1,1))
        self.overlay.add_widget(self.lbl)
        
        # Close Button
        btn = Button(text="Close", size_hint=(1, 0.5), background_color=(0.8, 0.2, 0.2, 1))
        btn.bind(on_release=self.dismiss)
        self.overlay.add_widget(btn)
        
        self.main_layout.add_widget(self.overlay)
        self.add_widget(self.main_layout)
        self.update_info(start_index)

    def _update_rect(self, *args):
        self.rect.pos = self.overlay.pos
        self.rect.size = self.overlay.size

    def on_slide_change(self, instance, value):
        self.current_index = value
        self.update_info(value)

    def update_info(self, index):
        if 0 <= index < len(self.data_list):
            item = self.data_list[index]
            self.lbl.text = f"{index+1}/{len(self.data_list)}: {item.get('title', 'Image')}"

class ImageCard(BoxLayout):
    thumbnail = StringProperty('')
    source = StringProperty('')
    image_url = StringProperty('')
    index = NumericProperty(0)
    selected = BooleanProperty(False)
    
    def on_checkbox_active(self, checkbox, value):
        self.selected = value
        # Notify root to update selection set
        App.get_running_app().root.update_selection(self.index, value)

    def on_image_click(self):
        # Open Viewer
        App.get_running_app().root.open_viewer(self.index)

class RootWidget(BoxLayout):
    has_results = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.engine = None
        self.current_results = [] # List of dicts
        self.selected_indices = set()
        
    def do_search(self):
        query = self.ids.search_input.text.strip()
        engine_name = self.ids.engine_spinner.text.lower()
        size_val = self.ids.size_spinner.text
        if not query: return
        
        # Reset
        self.ids.rv.data = []
        self.current_results = []
        self.selected_indices = set()
        self.update_download_btn()
        self.has_results = False
        
        if engine_name == 'rule34': engine_name = 'rule34'
        self.engine = get_engine(engine_name, query, size=size_val if size_val != 'Any Size' else None)
        
        self.load_more()
        
    def load_more(self):
        if not self.engine: return
        self.ids.load_more_btn.text = "Loading (Please wait 1s...)"
        self.ids.load_more_btn.disabled = True
        
        threading.Thread(target=self._fetch_thread, daemon=True).start()
        
    def _fetch_thread(self):
        # API client handles throttling (1s delay)
        new_items = self.engine.fetch_next_batch()
        Clock.schedule_once(lambda dt: self._on_fetch_complete(new_items))
        
    def _on_fetch_complete(self, new_items):
        self.ids.load_more_btn.disabled = False
        self.ids.load_more_btn.text = "Load More"
        
        if not new_items:
            # Could be end of results or error
            return

        start_idx = len(self.current_results)
        self.current_results.extend(new_items)
        
        # Prepare data for RecycleView
        rv_data = []
        for i, item in enumerate(self.current_results):
            rv_data.append({
                'thumbnail': item.get('thumbnail') or 'data:image/png;base64,', # fallback
                'image_url': item.get('image'),
                'source': item.get('source'),
                'title': item.get('title'),
                'index': i,
                'selected': i in self.selected_indices
            })
            
        self.ids.rv.data = rv_data
        self.has_results = True

    def open_viewer(self, index):
        if 0 <= index < len(self.current_results):
            viewer = FullScreenViewer(self.current_results, start_index=index)
            viewer.open()

    def update_selection(self, index, is_selected):
        if is_selected:
            self.selected_indices.add(index)
        elif index in self.selected_indices:
            self.selected_indices.remove(index)
        self.update_download_btn()
        
    def update_download_btn(self):
        count = len(self.selected_indices)
        self.ids.download_btn.text = f"Download ({count})"
        self.ids.download_btn.disabled = count == 0

    def download_selected(self):
        indices = list(self.selected_indices)
        if not indices: return
        
        self.ids.download_btn.text = "Downloading..."
        self.ids.download_btn.disabled = True
        
        items_to_download = [self.current_results[i] for i in indices]
        threading.Thread(target=self._download_thread, args=(items_to_download,), daemon=True).start()

    def _download_thread(self, items):
        # Reliable Android Path Logic
        storage_path = "."
        if platform == 'android':
            from android.storage import primary_external_storage_path
            from android.permissions import request_permissions, Permission
            # Standard Download folder
            storage_path = os.path.join(primary_external_storage_path(), 'Download', 'ImageSearchApp')
        else:
            storage_path = os.path.join(os.getcwd(), 'downloads')

        if not os.path.exists(storage_path):
            try:
                os.makedirs(storage_path, exist_ok=True)
            except Exception as e:
                print(f"Failed to create directory: {e}")
                # Fallback?
                
        count = 0
        for item in items:
            url = item['image']
            try:
                # Name file safely
                fname = url.split('/')[-1].split('?')[0]
                if not fname: fname = f"img_{int(time.time())}_{count}.jpg"
                save_path = os.path.join(storage_path, fname)
                
                # Check duplication
                if os.path.exists(save_path):
                    base, ext = os.path.splitext(fname)
                    save_path = os.path.join(storage_path, f"{base}_{int(time.time())}{ext}")

                res = requests.get(url, headers={'User-Agent': Loader.headers['User-Agent']}, timeout=30)
                if res.status_code == 200:
                    with open(save_path, 'wb') as f:
                        f.write(res.content)
                    count += 1
                    # Notify scan mechanism on Android so gallery sees it?
                    if platform == 'android':
                        self._scan_file(save_path)
            except Exception as e:
                print(f"Download Error for {url}: {e}")
                
        Clock.schedule_once(lambda dt: self._finish_download(count))

    def _scan_file(self, path):
         # Tell Android MediaStore about the new file
         # This usually requires Java access via pyjnius
         pass

    def _finish_download(self, count):
        self.ids.download_btn.text = f"Saved {count} Images!"
        self.ids.download_btn.disabled = False
        # Optional: Reset selection?
        # self.selected_indices.clear()
        # self.update_download_btn()

class ImageSearchApp(App):
    def build(self):
        return RootWidget()
    
    def on_start(self):
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.INTERNET, 
                Permission.WRITE_EXTERNAL_STORAGE, 
                Permission.READ_EXTERNAL_STORAGE
            ])

if __name__ == '__main__':
    ImageSearchApp().run()
