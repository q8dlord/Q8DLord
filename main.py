import os
import sys
import traceback

# -------------------------------------------------------------------------
# CRASH CATCHER: Wrap EVERYTHING in a try/except to show errors on screen
# -------------------------------------------------------------------------
try:
    import threading
    import requests
    import time
    from kivy.app import App
    from kivy.lang import Builder
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.modalview import ModalView
    from kivy.uix.popup import Popup
    from kivy.uix.image import AsyncImage
    from kivy.uix.label import Label
    from kivy.uix.button import Button
    from kivy.uix.floatlayout import FloatLayout
    from kivy.properties import StringProperty, BooleanProperty, NumericProperty
    from kivy.clock import Clock
    from kivy.utils import platform
    from kivy.loader import Loader
    from kivy.core.window import Window

    # 1. Header setup FIRST
    Loader.headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
    }

    # 2. Import Logic
    # If search_logic or api_client fails, we catch it below
    from search_logic import get_engine

    # 3. Load KV
    # Ensure images.kv is in the same folder
    if os.path.exists('images.kv'):
        Builder.load_file('images.kv')
    else:
        raise FileNotFoundError("images.kv file is missing! Please upload it.")

    # --- CLASSES ---

    class FullScreenViewer(ModalView):
        def __init__(self, data_list, start_index=0, **kwargs):
            super().__init__(**kwargs)
            self.size_hint = (1, 1)
            self.auto_dismiss = True 
            self.background_color = (0, 0, 0, 1)
            self.data_list = data_list
            self.current_index = start_index

            self.layout = FloatLayout()

            # Image
            self.img = AsyncImage(
                source="",
                allow_stretch=True, 
                keep_ratio=True,
                nocache=True,
                pos_hint={'center_x': 0.5, 'center_y': 0.5}
            )
            self.layout.add_widget(self.img)

            # Buttons
            self.btn_prev = Button(text="<", font_size="50sp", background_color=(0,0,0,0.3), size_hint=(0.15, 1), pos_hint={'x': 0, 'center_y': 0.5})
            self.btn_prev.bind(on_release=self.go_prev)
            self.layout.add_widget(self.btn_prev)

            self.btn_next = Button(text=">", font_size="50sp", background_color=(0,0,0,0.3), size_hint=(0.15, 1), pos_hint={'right': 1, 'center_y': 0.5})
            self.btn_next.bind(on_release=self.go_next)
            self.layout.add_widget(self.btn_next)

            # Footer
            self.bot_bar = BoxLayout(orientation='vertical', size_hint=(1, None), height="80dp", pos_hint={'bottom': 1})
            with self.bot_bar.canvas.before:
                from kivy.graphics import Color, Rectangle
                Color(0, 0, 0, 0.7)
                Rectangle(pos=self.bot_bar.pos, size=self.bot_bar.size)
                
            self.lbl_info = Label(text="", size_hint_y=0.6)
            self.btn_close = Button(text="Close", size_hint_y=0.4, background_color=(0.8, 0.3, 0.3, 1))
            self.btn_close.bind(on_release=self.dismiss)
            
            self.bot_bar.add_widget(self.lbl_info)
            self.bot_bar.add_widget(self.btn_close)
            self.layout.add_widget(self.bot_bar)
            self.add_widget(self.layout)
            
            self.load_image()

        def load_image(self):
            if not self.data_list: return
            item = self.data_list[self.current_index]
            self.img.source = item['image']
            self.lbl_info.text = f"{self.current_index + 1}/{len(self.data_list)}: {item.get('title', '')}"
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
            try:
                query = self.ids.search_input.text.strip()
                engine_name = self.ids.engine_spinner.text
                size_val = self.ids.size_spinner.text
                if not query: return
                
                self.ids.rv.data = []
                self.current_results = []
                self.selected_indices = set()
                self.update_download_btn()
                self.has_results = False
                
                e_norm = engine_name.lower()
                if e_norm == 'rule34': e_norm = 'rule34'
                elif e_norm == 'duckduckgo': e_norm = 'ddg'
                else: e_norm = 'bing'
                
                self.engine = get_engine(e_norm, query, size=size_val if size_val != 'Any Size' else None)
                self.load_more()
            except Exception as e:
                # Show Error Popup
                p = Popup(title='Search Error', size_hint=(0.8, 0.4))
                p.content = Label(text=str(e), text_size=(p.width-20, None), valign='middle')
                p.open()
                print(f"Search Crash: {e}")
            
        def load_more(self):
            if not self.engine: return
            self.ids.load_more_btn.text = "Loading..."
            self.ids.load_more_btn.disabled = True
            threading.Thread(target=self._fetch_thread, daemon=True).start()
            
        def _fetch_thread(self):
            try:
                new_items = self.engine.fetch_next_batch()
                Clock.schedule_once(lambda dt: self._on_fetch_complete(new_items))
            except Exception as e:
                print(f"Fetch Error: {e}")
                Clock.schedule_once(lambda dt: self._on_error(str(e)))
            
        def _on_error(self, err_msg):
            self.ids.load_more_btn.text = f"Error: {err_msg[:20]}"
            self.ids.load_more_btn.disabled = False
            
        def _on_fetch_complete(self, new_items):
            self.ids.load_more_btn.disabled = False
            self.ids.load_more_btn.text = "Load More"
            if not new_items: return

            start = len(self.current_results)
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
            folder = "."
            success_count = 0
            errors = []

            # 1. Determine Folder
            try:
                if platform == 'android':
                    from android.storage import primary_external_storage_path
                    # Try explicit public path first
                    # /storage/emulated/0/Download/ImageSearch
                    public_path = os.path.join(primary_external_storage_path(), 'Download', 'ImageSearch')
                    if not os.path.exists(public_path):
                        os.makedirs(public_path, exist_ok=True)
                    folder = public_path
                else:
                    folder = os.path.join(os.getcwd(), 'downloads')
                    if not os.path.exists(folder):
                        os.makedirs(folder, exist_ok=True)
            except Exception as e:
                errors.append(f"Storage Error: {e}")
                # Fallback to internal app storage (Android only fallback)
                # folder = ... (not easy to access from Gallery)

            # 2. Download Loop
            for item in items:
                try:
                    url = item['image']
                    ext = url.split('.')[-1].split('?')[0]
                    if len(ext) > 4 or not ext: ext = "jpg"
                    
                    fname = f"img_{int(time.time())}_{success_count}.{ext}"
                    path = os.path.join(folder, fname)
                    
                    # Request with generic headers to avoid blocks
                    res = requests.get(url, headers=Loader.headers, timeout=20)
                    if res.status_code == 200:
                        with open(path, 'wb') as f:
                            f.write(res.content)
                        success_count += 1
                    else:
                        errors.append(f"HTTP {res.status_code}: {url[:20]}...")
                except Exception as e:
                    errors.append(str(e))
            
            # 3. Finish
            Clock.schedule_once(lambda dt: self._finish_download(success_count, errors, folder))

        def _finish_download(self, count, errors, folder):
            self.ids.download_btn.text = f"Saved {count} files"
            self.ids.download_btn.disabled = False
            
            # Show Popup Report
            msg = f"Saved {count} images to:\n{folder}\n"
            if errors:
                msg += f"\nErrors ({len(errors)}):\n" + "\n".join(errors[:3])
                if len(errors) > 3: msg += "\n..."
            
            p = Popup(title='Download Report', size_hint=(0.9, 0.6))
            p.content = Label(text=msg, text_size=(p.width-40, None), valign='middle')
            p.open()

    class ImageSearchApp(App):
        def build(self):
            return RootWidget()
        def on_start(self):
            if platform == 'android':
                from android.permissions import request_permissions, Permission
                request_permissions([Permission.INTERNET, Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])

    if __name__ == "__main__":
        ImageSearchApp().run()

except Exception:
    # --- ERROR HANDLING APP ---
    # This runs if ANY of the above fails (syntax error, missing file, etc)
    error_trace = traceback.format_exc()
    
    # Minimal fallback imports
    try:
        from kivy.app import App
        from kivy.uix.label import Label
        from kivy.uix.scrollview import ScrollView
        from kivy.lang import Builder
    except:
        # If even Kivy fails to import, we can't do anything on Android easily.
        # But usually Kivy is there, just the user code is broken.
        print(error_trace)
        sys.exit(1)

    class ErrorApp(App):
        def build(self):
            # Red background, scrollable white text
            return Builder.load_string(f'''
ScrollView:
    canvas.before:
        Color:
            rgba: 0.8, 0, 0, 1
        Rectangle:
            pos: self.pos
            size: self.size
    Label:
        text: """{error_trace}"""
        size_hint_y: None
        height: self.texture_size[1]
        text_size: self.width, None
        padding: 20, 20
        color: 1, 1, 1, 1
            ''')

    if __name__ == "__main__":
        ErrorApp().run()
