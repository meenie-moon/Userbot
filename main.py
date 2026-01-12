import threading
import sys
import io
import logging
from kivy.lang import Builder
from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDFillRoundFlatButton
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout

# Import MoonBot Core
# Kita memodifikasi sedikit cara import agar tidak langsung jalan saat di-import
from MoonBot import config

# KV Layout Design
KV = '''
MDScreen:
    md_bg_color: 0.1, 0.1, 0.1, 1

    MDBoxLayout:
        orientation: "vertical"
        padding: "20dp"
        spacing: "20dp"

        MDLabel:
            text: "MoonBot Mobile"
            halign: "center"
            theme_text_color: "Custom"
            text_color: 1, 1, 1, 1
            font_style: "H4"
            size_hint_y: None
            height: self.texture_size[1]

        MDScrollView:
            md_bg_color: 0.2, 0.2, 0.2, 1
            radius: [10]
            
            MDLabel:
                id: log_label
                text: "Waiting to start..."
                theme_text_color: "Custom"
                text_color: 0.8, 0.8, 0.8, 1
                size_hint_y: None
                height: self.texture_size[1]
                padding: "10dp"

        MDFillRoundFlatButton:
            id: btn_start
            text: "START MOONBOT"
            pos_hint: {"center_x": 0.5}
            on_release: app.toggle_bot()
'''

class RedirectText(object):
    def __init__(self, app_ref):
        self.app_ref = app_ref

    def write(self, string):
        # Kirim text ke fungsi update_log di main thread
        Clock.schedule_once(lambda dt: self.app_ref.update_log(string))

    def flush(self):
        pass

class MoonBotApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "BlueGray"
        self.is_running = False
        return Builder.load_string(KV)

    def update_log(self, text):
        # Fungsi ini dipanggil dari thread lain untuk update UI
        if text.strip():
            self.root.ids.log_label.text += f"\n{text.strip()}"

    def toggle_bot(self):
        if self.is_running:
            self.root.ids.log_label.text += "\n[!] Restarting app required to stop cleanly."
            return

        self.is_running = True
        self.root.ids.btn_start.text = "RUNNING..."
        self.root.ids.btn_start.disabled = True
        
        # Redirect stdout/stderr ke layar aplikasi
        sys.stdout = RedirectText(self)
        sys.stderr = RedirectText(self)

        # Jalankan Bot di Thread terpisah agar UI tidak macet
        threading.Thread(target=self.run_bot_logic, daemon=True).start()

    def run_bot_logic(self):
        try:
            print("--- Initializing MoonBot ---")
            # Setup Config Manual jika perlu (di Android path beda)
            # Jalankan Main Logic
            from MoonBot.client import bot
            from MoonBot.main import main as moonbot_main
            
            # Kita panggil main() yang ada di MoonBot
            # Pastikan MoonBot/main.py dimodifikasi sedikit agar tidak auto-run jika diimport
            moonbot_main()
            
        except Exception as e:
            print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    MoonBotApp().run()
