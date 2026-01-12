import asyncio
import os
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.toast import toast
from telethon import TelegramClient, errors

# --- KONFIGURASI API (PUBLIC ANDROID KEY) ---
API_ID = 6
API_HASH = "eb06d4abfb49dc3eeb1aeb98ae0f581e"

# --- UI LAYOUT (KV Language) ---
KV = '''
ScreenManager:
    LoginScreen:
    DashboardScreen:

<LoginScreen>:
    name: "login"
    MDBoxLayout:
        orientation: 'vertical'
        padding: "20dp"
        spacing: "20dp"
        pos_hint: {"center_x": .5, "center_y": .6}
        adaptive_height: True

        MDLabel:
            text: "MoonBot Login"
            font_style: "H4"
            halign: "center"
            theme_text_color: "Primary"

        MDTextField:
            id: phone_field
            hint_text: "Phone Number (e.g., +628...)"
            helper_text: "Enter number with country code"
            helper_text_mode: "on_focus"
            icon_right: "phone"
            mode: "rectangle"

        MDTextField:
            id: code_field
            hint_text: "OTP Code"
            icon_right: "message-processing"
            mode: "rectangle"
            disabled: True
            opacity: 0

        MDTextField:
            id: password_field
            hint_text: "2FA Password (If active)"
            icon_right: "lock"
            mode: "rectangle"
            password: True
            disabled: True
            opacity: 0

        MDRaisedButton:
            id: action_button
            text: "GET OTP CODE"
            font_size: "18sp"
            size_hint_x: 1
            padding: "15dp"
            on_release: app.handle_login_action()

        MDLabel:
            id: status_label
            text: "Ready to connect"
            halign: "center"
            theme_text_color: "Secondary"
            font_style: "Caption"

<DashboardScreen>:
    name: "dashboard"
    MDBoxLayout:
        orientation: 'vertical'
        
        MDTopAppBar:
            title: "MoonBot Dashboard"
            right_action_items: [["logout", lambda x: app.logout()]]
            elevation: 4

        MDBoxLayout:
            orientation: 'vertical'
            padding: "20dp"
            spacing: "20dp"
            
            MDLabel:
                id: welcome_label
                text: "Welcome!"
                halign: "center"
                font_style: "H5"

            MDCard:
                orientation: "vertical"
                padding: "15dp"
                spacing: "10dp"
                size_hint: None, None
                size: "280dp", "180dp"
                pos_hint: {"center_x": .5}
                elevation: 2

                MDLabel:
                    text: "Quick Actions"
                    theme_text_color: "Secondary"
                    bold: True
                
                MDRaisedButton:
                    text: "Broadcast Manager (Soon)"
                    size_hint_x: 1
                    disabled: True
                
                MDRaisedButton:
                    text: "Template Manager (Soon)"
                    size_hint_x: 1
                    disabled: True

            Widget:
'''

# --- CLASSES ---
class LoginScreen(Screen):
    pass

class DashboardScreen(Screen):
    pass

class MoonBotMobile(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "DeepPurple"
        self.theme_cls.theme_style = "Dark"
        self.title = "MoonBot Mobile"
        
        # Setup Client Path
        # Menggunakan internal storage path agar writeable di Android
        self.session_path = os.path.join(self.user_data_dir, 'moonbot_client')
        self.client = TelegramClient(self.session_path, API_ID, API_HASH)
        
        # State Variables
        self.phone_number = None
        self.phone_code_hash = None
        self.is_code_sent = False
        
        return Builder.load_string(KV)

    def on_start(self):
        # Memulai Loop Asyncio untuk Telethon
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.connect_client())

    async def connect_client(self):
        """Menghubungkan client dan cek session"""
        try:
            await self.client.connect()
            if await self.client.is_user_authorized():
                self.show_dashboard()
            else:
                toast("Please Login")
        except Exception as e:
            self.root.get_screen('login').ids.status_label.text = f"Error: {e}"

    def handle_login_action(self):
        """Menangani tombol Login (Get OTP atau Sign In)"""
        screen = self.root.get_screen('login')
        
        if not self.is_code_sent:
            # STEP 1: Request OTP
            phone = screen.ids.phone_field.text
            if not phone:
                toast("Please enter phone number!")
                return
            
            screen.ids.status_label.text = "Requesting OTP..."
            self.loop.create_task(self.send_code(phone))
        else:
            # STEP 2: Sign In
            code = screen.ids.code_field.text
            password = screen.ids.password_field.text
            if not code:
                toast("Please enter OTP code!")
                return

            screen.ids.status_label.text = "Signing in..."
            self.loop.create_task(self.sign_in(code, password))

    async def send_code(self, phone):
        try:
            self.phone_number = phone
            sent = await self.client.send_code_request(phone)
            self.phone_code_hash = sent.phone_code_hash
            self.is_code_sent = True
            
            # Update UI
            screen = self.root.get_screen('login')
            screen.ids.phone_field.disabled = True
            screen.ids.code_field.disabled = False
            screen.ids.code_field.opacity = 1
            screen.ids.password_field.disabled = False # Jaga-jaga kalau butuh password
            screen.ids.password_field.opacity = 1
            screen.ids.action_button.text = "SIGN IN"
            screen.ids.status_label.text = "OTP Sent! Check Telegram."
            toast("OTP Sent!")
            
        except Exception as e:
            self.root.get_screen('login').ids.status_label.text = f"Failed: {e}"
            toast(f"Error: {e}")

    async def sign_in(self, code, password):
        try:
            try:
                await self.client.sign_in(self.phone_number, code, phone_code_hash=self.phone_code_hash)
            except errors.SessionPasswordNeededError:
                if not password:
                    toast("2FA Password Required!")
                    self.root.get_screen('login').ids.status_label.text = "Please enter 2FA Password"
                    return
                await self.client.sign_in(password=password)
            
            # Login Success
            toast("Login Successful!")
            self.show_dashboard()
            
        except Exception as e:
            self.root.get_screen('login').ids.status_label.text = f"Login Failed: {e}"
            toast(f"Error: {e}")

    def show_dashboard(self):
        """Pindah ke layar dashboard dan load info user"""
        self.root.current = "dashboard"
        self.loop.create_task(self.load_user_info())

    async def load_user_info(self):
        try:
            me = await self.client.get_me()
            name = me.first_name
            if me.last_name:
                name += f" {me.last_name}"
            
            screen = self.root.get_screen('dashboard')
            screen.ids.welcome_label.text = f"Hi, {name}!\n(+{me.phone})"
        except Exception as e:
            toast(f"Failed to load profile: {e}")

    def logout(self):
        self.loop.create_task(self.client.log_out())
        self.root.current = "login"
        self.is_code_sent = False
        screen = self.root.get_screen('login')
        screen.ids.phone_field.disabled = False
        screen.ids.phone_field.text = ""
        screen.ids.code_field.text = ""
        screen.ids.code_field.disabled = True
        screen.ids.code_field.opacity = 0
        screen.ids.password_field.disabled = True
        screen.ids.password_field.opacity = 0
        screen.ids.action_button.text = "GET OTP CODE"

if __name__ == "__main__":
    MoonBotMobile().run()