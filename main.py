import os
import threading
import time
import traceback
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.utils import platform

# Import the existing Flask app
try:
    from app import app as flask_app
except Exception as e:
    flask_app = None
    import_error = traceback.format_exc()

class ServerThread(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self)
        self.server = app
        self.daemon = True

    def run(self):
        try:
            # We need to run on localhost for the WebView to access it
            self.server.run(host="127.0.0.1", port=5000, debug=False)
        except Exception as e:
            print(f"Flask Server Error: {e}")

class ImageSearchApp(App):
    def build(self):
        try:
            if flask_app is None:
                return Label(text=f"Error importing app.py:\n{import_error}")

            # Start the Flask server
            self.server_thread = ServerThread(flask_app)
            self.server_thread.start()
            
            # Give the server a moment to start
            time.sleep(1) 
            
            # Create a placeholder widget
            self.root_widget = Widget()
            
            # Schedule the WebView creation
            Clock.schedule_once(self.create_webview, 0)
            return self.root_widget
        except Exception as e:
            return Label(text=f"Critical Error:\n{traceback.format_exc()}")

    def create_webview(self, *args):
        try:
            if platform == 'android':
                from jnius import autoclass
                from android.runnable import run_on_ui_thread

                WebView = autoclass('android.webkit.WebView')
                WebViewClient = autoclass('android.webkit.WebViewClient')
                activity = autoclass('org.kivy.android.PythonActivity').mActivity

                @run_on_ui_thread
                def start_webview():
                    try:
                        webview = WebView(activity)
                        webview.setWebViewClient(WebViewClient())
                        webview.getSettings().setJavaScriptEnabled(True)
                        webview.getSettings().setDomStorageEnabled(True)
                        
                        # Load the local Flask server
                        webview.loadUrl('http://127.0.0.1:5000')
                        
                        # Add to the activity
                        activity.setContentView(webview)
                    except Exception as e:
                        print(f"WebView Error: {e}")
                    
                start_webview()
            else:
                print("Not running on Android. WebView would be created here pointing to http://127.0.0.1:5000")
        except Exception as e:
            print(f"Platform Error: {e}")

    def on_stop(self):
        pass

if __name__ == '__main__':
    try:
        ImageSearchApp().run()
    except Exception as e:
        print(f"Fatal App Error: {e}")
