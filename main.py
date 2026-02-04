import os
import threading
import requests
import re
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.modalview import ModalView
from kivy.uix.carousel import Carousel
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import StringProperty, BooleanProperty, ListProperty, NumericProperty
from kivy.clock import Clock
from kivy.utils import platform
from kivy.loader import Loader

# Set global headers for Kivy's internal image loader to mimic a browser
# This fixes the "X" (403 Forbidden) on many sites that block default python/urllib agents
Loader.headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    # 'Referer': 'https://www.google.com/' # Removed to prevent hotlink blocking
}


# Import our pure python logic
from search_logic import get_engine

# Load KV file
Builder.load_file('images.kv')

class FullScreenViewer(ModalView):
    def __init__(self, data_list, start_index=0, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, 1)
        self.auto_dismiss = False
        self.background_color = (0, 0, 0, 1)
        
        self.data_list = data_list
        self.current_index = start_index

        # Main Layout
        self.main_layout = FloatLayout()
        
        # Carousel
        self.carousel = Carousel(direction='right', loop=False)
        self.carousel.bind(index=self.on_slide_change)
        
        # Populate Carousel
        # To save memory, we could load dynamically, but for <100 items standard is okay.
        # Let's load initially, maybe lazy load in future.
        for item in data_list:
            # Container for image + potential zoom scatter?
            # Keeping it simple with AsyncImage for now
            img = AsyncImage(
                source=item['image_url'], 
                allow_stretch=True, 
                keep_ratio=True,
                nocache=False
            )
            self.carousel.add_widget(img)
            
        self.carousel.index = start_index
        self.main_layout.add_widget(self.carousel)

        # Info Overlay (Bottom)
        self.info_panel = BoxLayout(
            orientation='vertical', 
            size_hint=(1, None), 
            height="100dp",
            pos_hint={'bottom': 1}
        )
        # Semi-transparent bg
        with self.info_panel.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(0, 0, 0, 0.6)
            self.bg_rect = Rectangle(pos=self.info_panel.pos, size=self.info_panel.size)
        self.info_panel.bind(pos=self.update_bg, size=self.update_bg)
        
        # Text Info
        self.info_lbl = Label(
            text="", 
            font_size="16sp",
            halign="center",
            valign="middle",
            size_hint_y=0.6,
            color=(1,1,1,1)
        )
        self.info_panel.add_widget(self.info_lbl)
        
        # Buttons (Close / Download)
        btn_box = BoxLayout(size_hint_y=0.4, spacing="20dp", padding="10dp")
        
        close_btn = Button(text="Close", bold=True, background_color=(0.8, 0.2, 0.2, 1))
        close_btn.bind(on_release=self.dismiss)
        
        dl_btn = Button(text="Download Image", bold=True, background_color=(0.2, 0.8, 0.2, 1))
        dl_btn.bind(on_release=self.download_current)
        
        btn_box.add_widget(close_btn)
        btn_box.add_widget(dl_btn)
        
        self.info_panel.add_widget(btn_box)
        self.main_layout.add_widget(self.info_panel)
        
        self.add_widget(self.main_layout)
        self.update_info(start_index)

    def update_bg(self, *args):
        self.bg_rect.pos = self.info_panel.pos
        self.bg_rect.size = self.info_panel.size

    def on_slide_change(self, instance, value):
        self.current_index = value
        self.update_info(value)

    def update_info(self, index):
        if 0 <= index < len(self.data_list):
            item = self.data_list[index]
            self.info_lbl.text = f"{item['source']}\n{item['title']}"

    def download_current(self, *args):
        if 0 <= self.current_index < len(self.data_list):
            item = self.data_list[self.current_index]
            App.get_running_app().root.trigger_single_download(item['image_url'])

class ImageCard(BoxLayout):
    thumbnail = StringProperty('')
    source = StringProperty('')
    image_url = StringProperty('')
    index = NumericProperty(0) # Track index for viewer
    selected = BooleanProperty(False)
    
    def on_checkbox_active(self, checkbox, value):
        self.selected = value
        App.get_running_app().root.update_selection(self.image_url, value)

    def on_card_click(self):
        # Notify root to open viewer at this index
        App.get_running_app().root.open_viewer(self.index)

class RootWidget(BoxLayout):
    has_results = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.engine = None
        self.results_data = [] 
        self.selected_urls = set()

    def do_search(self):
        query = self.ids.search_input.text.strip()
        engine_name = self.ids.engine_spinner.text.lower()
        size_val = self.ids.size_spinner.text
        
        if not query: return
        if size_val == "Any Size": size_val = None

        self.ids.rv.data = []
        self.results_data = []
        self.selected_urls.clear()
        self.update_download_btn()
        self.has_results = False
        
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
        Clock.schedule_once(lambda dt: self._update_ui_results(new_items))

    def _update_ui_results(self, new_items):
        self.ids.load_more_btn.text = "Load More"
        self.ids.load_more_btn.disabled = False
        
        if not new_items: pass
        
        start_idx = len(self.results_data)
        for i, item in enumerate(new_items):
            self.results_data.append({
                'thumbnail': item.get('thumbnail'),
                'image_url': item.get('image'),
                'source': item.get('source'),
                'title': item.get('title'),
                'selected': False,
                'index': start_idx + i # Assign absolute index
            })
        
        self.ids.rv.data = self.results_data
        self.has_results = True

    def resolve_url(self, item):
        """Resolves the real image URL if it's a view page (like Rule34)."""
        url = item.get('image', '')
        if item.get('is_resolvable', False) or 'rule34.xxx' in url and 'page=post&s=view' in url:
            # It's a view page, scrape it
            print(f"Resolving URL: {url}")
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                res = requests.get(url, headers=headers, timeout=10)
                # Look for <img id="image" src="...">
                # OR <source src="..."> for video? (We only do images for now)
                
                # Rule34: <img src="..." id="image" ...>
                # Using a more flexible regex to find the main image
                # Standard Rule34 view page has id="image"
                m = re.search(r'<img[^>]+src="([^"]+)"[^>]*id="image"', res.text)
                if not m:
                    # Fallback: look for generic larger image or video source (if needed later)
                    m = re.search(r'<img[^>]+id="image"[^>]+src="([^"]+)"', res.text)
                
                if m:
                    real_url = m.group(1)
                    # Handle relative
                    if not real_url.startswith('http'):
                        real_url = "https://rule34.xxx/" + real_url.lstrip("/")
                    # Update item to cache it
                    item['image_url'] = real_url
                    item['image'] = real_url # update both
                    item['is_resolvable'] = False
                    return real_url
                else:
                     print("Failed to find image ID in view page.")
            except Exception as e:
                print(f"Resolution failed: {e}")
        return url

    def open_viewer(self, index):
        if not self.results_data: return
        # Resolve current immediately if needed (blocking briefly, or viewer handles it)
        # Better: Pass resolver to viewer or resolve before opening?
        # Let's resolve in background inside viewer logic?
        # For now, let's resolve PRE-opening for simplicity, or just pass resolution logic.
        
        # We'll resolve the first one synchronously for immediate feedback, then others lazy?
        # Actually sync is bad for UI.
        # Let's simple-hack: Resolve inside the Viewer class?
        # For now, let's just Open the viewer and let the viewer load the 'image_url'.
        # IF 'image_url' is a view page, AsyncImage won't load it.
        # So we MUST resolve.
        
        # Threaded resolution for the clicked item
        threading.Thread(target=self._resolve_and_open, args=(index,), daemon=True).start()

    def _resolve_and_open(self, index):
        try:
            if index < 0 or index >= len(self.results_data):
                print(f"Index {index} out of bounds")
                return

            item = self.results_data[index]
            real_url = self.resolve_url(item)
            
            # Update data list on main thread? 
            # The viewer reads self.results_data. ensure atomic update
            self.results_data[index]['image_url'] = real_url
            
            Clock.schedule_once(lambda dt: self._open_viewer_ui(index))
        except Exception as e:
            print(f"Error in _resolve_and_open: {e}")

    def _open_viewer_ui(self, index):
        try:
            viewer = FullScreenViewer(self.results_data, start_index=index)
            viewer.open()
        except Exception as e:
            print(f"Error opening viewer: {e}")

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
        # We need to map selected URLs back to items to resolve them?
        # Or just resolve if they look like view URLs.
        urls = list(self.selected_urls)
        self.ids.download_btn.text = "Downloading..."
        self.ids.download_btn.disabled = True
        threading.Thread(target=self._download_thread, args=(urls,), daemon=True).start()

    def trigger_single_download(self, url):
        # Url might be unresolved
        self.trigger_download([url])

    def trigger_download(self, urls):
        self.ids.download_btn.text = "Downloading..."
        self.ids.download_btn.disabled = True
        threading.Thread(target=self._download_thread, args=(urls,), daemon=True).start()

    def _download_thread(self, urls):
        if platform == 'android':
            from android.storage import primary_external_storage_path
            path = os.path.join(primary_external_storage_path(), 'Download', 'ImageSearch')
        else:
            path = os.path.join(os.getcwd(), 'downloads')
            
        if not os.path.exists(path):
            try: os.makedirs(path)
            except: pass 
        
        count = 0
        for url in urls:
            try:
                # RESOLVE IF NEEDED
                if 'rule34.xxx' in url and 'page=post&s=view' in url:
                    # We need to resolve. Since we don't have the item dict here easily, create dummy
                    dummy = {'image': url, 'is_resolvable': True}
                    url = self.resolve_url(dummy)
                
                headers = {'User-Agent': 'Mozilla/5.0'}
                filename = url.split('/')[-1].split('?')[0]
                if not filename: filename = f"img_{count}.jpg"
                if '.' not in filename: filename += ".jpg"
                filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in '._-'])
                save_path = os.path.join(path, filename)
                
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

class ImageSearchApp(App):
    def build(self):
        return RootWidget()

    def on_start(self):
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.INTERNET, Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])

if __name__ == '__main__':
    ImageSearchApp().run()
