from telethon import events, Button
from MoonBot.client import bot
from MoonBot import db_helper, config
from datetime import datetime

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    sender = await event.get_sender()
    user_id = sender.id
    name = sender.first_name
    
    status = db_helper.check_user_status(user_id)
    
    # 1. Jika User Baru / Pending
    if status is None or status == 'pending':
        if status is None:
            db_helper.request_access(user_id)
        
        msg = (
            f"👋 Halo **{name}**!\n\n"
            f"Selamat datang di **MoonTele Bot** 🌙\n"
            f"Bot ini adalah alat otomasi canggih untuk Telegram yang memungkinkan Anda:\n"
            f"• Mengelola banyak akun (Userbot) sekaligus.\n"
            f"• Membuat template target broadcast secara instan.\n"
            f"• Mengirim pesan broadcast ke ratusan grup/topik dengan aman.\n\n"
            f"🔒 **Akses Terbatas**\n"
            f"Untuk menjaga kualitas dan keamanan, bot ini menggunakan sistem Whitelist. "
            f"ID Anda (`{user_id}`) belum terdaftar atau sedang menunggu persetujuan admin.\n\n"
            f"Status: **PENDING APPROVAL** ⏳\n"
            f"Silakan hubungi Owner untuk konfirmasi aktivasi akun Anda."
        )
        
        # Tombol kontak owner
        buttons = [
            [Button.url("💬 Hubungi Owner untuk Akses", f"tg://user?id={config.OWNER_ID}")]
        ]
        
        # Notifikasi ke Owner ada user baru
        try:
            await bot.send_message(
                config.OWNER_ID, 
                f"🔔 **User Baru Mendaftar**\nNama: {name}\nID: `{user_id}`\nUsername: @{sender.username or '-'}\n\nSegera cek /admin."
            )
        except:
            pass # Owner mungkin belum start bot

        await event.respond(msg, buttons=buttons)
        return

    # 2. Jika User Dibanned
    if status == 'banned':
        await event.respond("⛔ Maaf, akses Anda telah diblokir oleh admin.")
        return

    # 3. Jika User Aktif (Approved/Owner)
    await show_main_menu(event, name)

async def show_main_menu(event, name=None):
    sender = await event.get_sender()
    # Tentukan Nama (Jika dari callback, ambil nama dari sender event sebelumnya)
    if not name:
        name = sender.first_name
    
    # Ambil Statistik
    user_id = sender.id
    username = f"@{sender.username}" if sender.username else "-"
    stats = db_helper.get_user_stats(user_id)
    
    # Ambil Nama Akun Aktif
    active_account_name = db_helper.get_active_session_name(user_id)
    
    # Format Waktu (Contoh: 26 December 2025 ~ 09:37 WIB)
    now_str = datetime.now().strftime("%d %B %Y ~ %H:%M WIB")

    msg = (
        f"👋 Halo, **{name}**!\n"
        f"Selamat datang di **MoonTele**\n\n"
        f"👤 **Info Pengguna:**\n"
        f"• ID: `{user_id}`\n"
        f"• Username: {username}\n"
        f"• Nama: **{name}**\n\n"
        f"📊 **Statistik Anda:**\n"
        f"• Akun: `{stats['sessions']}`\n"
        f"• Akun Aktif: **{active_account_name}**\n"
        f"• Template Target: `{stats['templates']}`\n"
        f"• Total Broadcast: `{stats['broadcasts']}`\n\n"
        f"⏰ {now_str}\n\n"
        f"Silakan pilih menu di bawah ini:"
    )
    
    buttons = [
        [Button.inline("👥 Akun Saya", b"menu_accounts"), Button.inline("📝 Template Target", b"menu_templates")],
        [Button.inline("🚀 Tools / Broadcast", b"menu_tools")],
        [Button.inline("⚙️ Settings", b"menu_settings"), Button.inline("📚 Tutorial", b"menu_tutorial")]
    ]
    
    # Tambah menu Admin jika Owner
    sender_id = event.sender_id
    if sender_id == config.OWNER_ID:
        buttons.append([Button.inline("🛡️ Admin Panel", b"menu_admin")])
    
    # Deteksi tipe event: CallbackQuery (Edit) atau NewMessage (Respond)
    if hasattr(event, 'data') and event.data:
        await event.edit(msg, buttons=buttons)
    else:
        await event.respond(msg, buttons=buttons)

# --- HANDLER MENU TUTORIAL ---
@bot.on(events.CallbackQuery(data=b"menu_tutorial"))
async def tutorial_handler(event):
    msg = (
        "📚 **Panduan Lengkap MoonTele**\n\n"
        "**1. Persiapan Akun (Login)**\n"
        "• Siapkan API ID & Hash dari [my.telegram.org/auth](https://my.telegram.org/auth).\n"
        "• Masuk menu 'Akun Saya' -> 'Tambah Akun'.\n"
        "• Masukkan API ID, Hash, Nomor HP, dan OTP.\n"
        "• Akun akan disimpan dengan aman di server.\n\n"
        "**2. Membuat Template Target**\n"
        "• Masuk menu 'Template Target'.\n"
        "• Klik 'Buat Template Baru' -> Beri Nama.\n"
        "• Klik 'Tambah Target' di dalam menu template.\n"
        "• **Cara Cepat:** Salin Link Pesan dari grup/topik tujuan (contoh: `https://t.me/c/123/456`).\n"
        "• Bot otomatis mendeteksi ID Grup dan Nama Topik.\n\n"
        "**3. Melakukan Broadcast**\n"
        "• Masuk 'Tools / Broadcast'.\n"
        "• Pilih Akun Pengirim.\n"
        "• Pilih Template Tujuan.\n"
        "• Kirim Pesan Broadcast Anda (Text/Grup/Foto/Video).\n"
        "• Konfirmasi dengan `/send`.\n\n"
        "**Tips Keamanan:**\n"
        "• Gunakan API ID sendiri.\n"
        "• Beri jeda waktu (delay) yang cukup.\n"
        "• Jangan spam berlebihan."
    )
    buttons = [[Button.inline("🔙 Kembali", b"main_menu")]]
    await event.edit(msg, buttons=buttons)

@bot.on(events.CallbackQuery(data=b"main_menu"))
async def callback_main_menu(event):
    await show_main_menu(event)

# --- HANDLER MENU SETTINGS ---
@bot.on(events.CallbackQuery(data=b"menu_settings"))
async def settings_handler(event):
    msg = (
        "⚙️ **Pengaturan Bot**\n\n"
        "Saat ini pengaturan masih menggunakan nilai default sistem:\n"
        "• **Broadcast Delay:** 5 detik (Sangat Aman)\n"
        "• **Database:** SQLite Local\n\n"
        "Fitur pengaturan kustom akan hadir di update berikutnya."
    )
    
    buttons = [
        [Button.url("📚 Baca Panduan", "https://t.me/MoonCiella")], # Contoh link
        [Button.inline("🔙 Kembali", b"main_menu")]
    ]
    await event.edit(msg, buttons=buttons)
