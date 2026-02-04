import os
import threading
import requests
import time
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.modalview import ModalView
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import StringProperty, BooleanProperty, NumericProperty
from kivy.clock import Clock
from kivy.utils import platform
from kivy.loader import Loader

# Header fix for Bing/DDG/Rule34
Loader.headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
}

from search_logic import get_engine

Builder.load_string('''
<ImageCard>:
    orientation: 'vertical'
    size_hint_y: None
    height: "280dp"
    padding: "4dp"
    spacing: "2dp"
    
    canvas.before:
        Color:
            rgba: (0.2, 0.2, 0.2, 1) if not self.selected else (0.2, 0.5, 0.8, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [8,]

    RelativeLayout:
        size_hint_y: 0.85
        
        AsyncImage:
            source: root.thumbnail
            allow_stretch: True
            keep_ratio: True
            nocache: False
            fit_mode: "contain"
            pos_hint: {'center_x': 0.5, 'center_y': 0.5}

        # Main Click -> Open Viewer
        Button:
            background_color: 0, 0, 0, 0
            size_hint: 1, 1
            on_release: root.on_image_click()

        # Checkbox -> Selection
        CheckBox:
            size_hint: None, None
            size: "40dp", "40dp"
            pos_hint: {'top': 1, 'right': 1}
            active: root.selected
            on_active: root.on_checkbox_active(self, self.active)
            canvas.before:
                Color: 
                    rgba: 0, 0, 0, 0.4
                Ellipse:
                    pos: self.pos
                    size: self.size

    Label:
        text: root.source
        size_hint_y: 0.15
        font_size: "11sp"
        color: 0.8, 0.8, 0.8, 1
        text_size: self.size
        halign: 'left'
        valign: 'middle'
        shorten: True
        shorten_from: 'right'
''')

# Robust Single Image Viewer (Replaces Carousel)
class FullScreenViewer(ModalView):
    def __init__(self, data_list, start_index=0, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, 1)
        self.auto_dismiss = True 
        self.background_color = (0, 0, 0, 1)
        self.data_list = data_list
        self.current_index = start_index

        # Layout
        self.layout = FloatLayout()

        # The Image
        self.img = AsyncImage(
            source=self._get_current_url(),
            allow_stretch=True, 
            keep_ratio=True,
            nocache=True, # Prevent caching issues
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.layout.add_widget(self.img)

        # Nav Buttons
        # PREV
        self.btn_prev = Button(
            text="<", 
            font_size="40sp", 
            background_color=(0,0,0,0.3),
            size_hint=(0.15, 1), 
            pos_hint={'x': 0, 'center_y': 0.5}
        )
        self.btn_prev.bind(on_release=self.go_prev)
        self.layout.add_widget(self.btn_prev)

        # NEXT
        self.btn_next = Button(
            text=">", 
            font_size="40sp", 
            background_color=(0,0,0,0.3),
            size_hint=(0.15, 1), 
            pos_hint={'right': 1, 'center_y': 0.5}
        )
        self.btn_next.bind(on_release=self.go_next)
        self.layout.add_widget(self.btn_next)

        # Bottom Bar
        self.bot_bar = BoxLayout(
            orientation='vertical', 
            size_hint=(1, None), 
            height="80dp",
            pos_hint={'bottom': 1}
        )
        with self.bot_bar.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(0, 0, 0, 0.7)
            Rectangle(pos=self.bot_bar.pos, size=self.bot_bar.size)
            
        self.lbl_info = Label(text="", size_hint_y=0.5)
        self.btn_close = Button(text="Close", size_hint_y=0.5, background_color=(0.8, 0.3, 0.3, 1))
        self.btn_close.bind(on_release=self.dismiss)
        
        self.bot_bar.add_widget(self.lbl_info)
        self.bot_bar.add_widget(self.btn_close)
        
        self.layout.add_widget(self.bot_bar)
        self.add_widget(self.layout)
        
        # Load Initial
        self.load_image()

    def _get_current_url(self):
        if 0 <= self.current_index < len(self.data_list):
            return self.data_list[self.current_index]['image']
        return ""

    def load_image(self):
        if not self.data_list: return
        
        item = self.data_list[self.current_index]
        url = item['image']
        
        self.img.source = url
        self.lbl_info.text = f"Image {self.current_index + 1} of {len(self.data_list)}"
        
        # Enable/Disable buttons
        self.btn_prev.disabled = (self.current_index == 0)
        self.btn_next.disabled = (self.current_index == len(self.data_list) - 1)

    def go_prev(self, *args):
        if self.current_index > 0:
            self.current_index -= 1
            self.load_image()

    def go_next(self, *args):
        if self.current_index < len(self.data_list) - 1:
            self.current_index += 1
            self.load_image()

class ImageCard(BoxLayout):
    thumbnail = StringProperty('')
    source = StringProperty('')
    image_url = StringProperty('')
    index = NumericProperty(0)
    selected = BooleanProperty(False)
    
    def on_checkbox_active(self, checkbox, value):
        self.selected = value
        App.get_running_app().root.update_selection(self.index, value)

    def on_image_click(self):
        App.get_running_app().root.open_viewer(self.index)

class RootWidget(BoxLayout):
    has_results = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.engine = None
        self.current_results = [] 
        self.selected_indices = set()
        
    def do_search(self):
        query = self.ids.search_input.text.strip()
        engine_name = self.ids.engine_spinner.text
        size_val = self.ids.size_spinner.text
        
        if not query: return
        
        # Reset
        self.ids.rv.data = []
        self.current_results = []
        self.selected_indices = set()
        self.update_download_btn()
        self.has_results = False
        
        if engine_name.lower() == 'rule34': engine_name = 'rule34'
        elif engine_name.lower() == 'duckduckgo': engine_name = 'ddg'
        else: engine_name = 'bing'
        
        self.engine = get_engine(engine_name, query, size=size_val if size_val != 'Any Size' else None)
        self.load_more()
        
    def load_more(self):
        if not self.engine: return
        self.ids.load_more_btn.text = "Loading..."
        self.ids.load_more_btn.disabled = True
        threading.Thread(target=self._fetch_thread, daemon=True).start()
        
    def _fetch_thread(self):
        new_items = self.engine.fetch_next_batch()
        Clock.schedule_once(lambda dt: self._on_fetch_complete(new_items))
        
    def _on_fetch_complete(self, new_items):
        self.ids.load_more_btn.disabled = False
        self.ids.load_more_btn.text = "Load More"
        
        if not new_items: return

        start_idx = len(self.current_results)
        self.current_results.extend(new_items)
        
        rv_data = []
        for i, item in enumerate(self.current_results):
            rv_data.append({
                'thumbnail': item.get('thumbnail', ''),
                'image_url': item.get('image', ''),
                'source': item.get('source', ''),
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
        self.ids.download_btn.text = "Starting..."
        self.ids.download_btn.disabled = True
        
        items = [self.current_results[i] for i in indices]
        threading.Thread(target=self._download_thread, args=(items,), daemon=True).start()

    def _download_thread(self, items):
        # ANDROID: /storage/emulated/0/Download/ImageSearch
        folder = "."
        if platform == 'android':
            from android.storage import primary_external_storage_path
            folder = os.path.join(primary_external_storage_path(), 'Download', 'ImageSearch')
        else:
            folder = os.path.join(os.getcwd(), 'downloads')
            
        if not os.path.exists(folder):
            try: os.makedirs(folder, exist_ok=True)
            except: pass
            
        count = 0
        for item in items:
            try:
                url = item['image']
                ext = url.split('.')[-1].split('?')[0]
                if len(ext) > 4 or not ext: ext = "jpg"
                
                fname = f"img_{int(time.time())}_{count}.{ext}"
                path = os.path.join(folder, fname)
                
                res = requests.get(url, headers=Loader.headers, timeout=20)
                if res.status_code == 200:
                    with open(path, 'wb') as f:
                        f.write(res.content)
                    count += 1
            except Exception as e:
                print(f"DL duplicate/error: {e}")
                
        Clock.schedule_once(lambda dt: self._finish_download(count))

    def _finish_download(self, count):
        self.ids.download_btn.text = f"Saved {count} files"
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
