import asyncio
from telethon import events, Button
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PasswordHashInvalidError

from MoonBot.client import bot
from MoonBot import db_helper, config

# State dictionary: {user_id: {'step': '...', 'client': ClientObj, 'phone': '...', 'api_id': ..., 'api_hash': ...}}
LOGIN_STATE = {}

@bot.on(events.CallbackQuery(data=b"menu_accounts"))
async def account_menu_callback(event):
    user_id = event.sender_id
    sessions = db_helper.get_user_sessions(user_id)
    
    msg = f"👥 **Manajemen Akun**\nAnda memiliki {len(sessions)} akun terhubung.\nKlik akun untuk opsi lainnya.\n\n"
    
    buttons = []
    for sess in sessions:
        # Tampilkan akun yang ada
        mark = "✅ " if sess['is_default'] else "📱 "
        buttons.append([Button.inline(f"{mark}{sess['name']}", f"view_acc_{sess['id']}".encode())])
        
    buttons.append([Button.inline("➕ Tambah Akun (Login)", b"add_account")])
    buttons.append([Button.inline("🔙 Menu Utama", b"main_menu")])
    
    await event.edit(msg, buttons=buttons)

# --- HANDLER AKSI AKUN ---
@bot.on(events.CallbackQuery(pattern=r"view_acc_(\d+)"))
async def view_account_handler(event):
    sess_id = int(event.pattern_match.group(1))
    data = db_helper.get_session_data(sess_id)
    
    if not data:
        return await event.answer("Data akun tidak ditemukan!", alert=True)
    
    # Status teks
    status_text = "✅ SEDANG AKTIF" if data['is_default'] else "💤 TIDAK AKTIF"
    
    msg = (
        f"📱 **Detail Akun**\n\n"
        f"Nama: `{data['name']}`\n"
        f"Nomor: `{data['phone']}`\n"
        f"API ID: `{data['api_id']}`\n"
        f"Status: **{status_text}**\n\n"
        f"Apa yang ingin Anda lakukan?"
    )
    
    buttons = []
    
    # Hanya tampilkan tombol 'Jadikan Aktif' jika akun BELUM aktif
    if not data['is_default']:
        buttons.append([Button.inline("✅ Jadikan Akun Aktif", f"set_active_{sess_id}".encode())])
        
    buttons.append([Button.inline("🗑️ Hapus Akun", f"del_acc_{sess_id}".encode())])
    buttons.append([Button.inline("🔙 Kembali", b"menu_accounts")])
    
    await event.edit(msg, buttons=buttons)

@bot.on(events.CallbackQuery(pattern=r"set_active_(\d+)"))
async def set_active_handler(event):
    sess_id = int(event.pattern_match.group(1))
    db_helper.set_default_session(event.sender_id, sess_id)
    await event.answer("Akun berhasil diaktifkan!")
    await account_menu_callback(event)

@bot.on(events.CallbackQuery(pattern=r"del_acc_(\d+)"))
async def delete_account_handler(event):
    sess_id = int(event.pattern_match.group(1))
    # Konfirmasi hapus bisa ditambahkan, tapi untuk cepat langsung hapus
    db_helper.delete_session(sess_id, event.sender_id)
    await event.answer("Akun dihapus!")
    await account_menu_callback(event)

@bot.on(events.CallbackQuery(data=b"add_account"))
async def add_account_handler(event):
    user_id = event.sender_id
    
    # Set state awal: Minta API ID
    LOGIN_STATE[user_id] = {
        'step': 'wait_api_id'
    }
    
    msg = (
        "➕ **Tambah Akun Telegram**\n\n"
        "**Langkah 1: Siapkan API ID & Hash**\n"
        "Agar akun Anda aman dari limit/banned, disarankan menggunakan API Key sendiri.\n\n"
        "**Cara mendapatkan API ID:**\n"
        "1. Buka [my.telegram.org/auth](https://my.telegram.org/auth)\n"
        "2. Login dengan nomor HP Anda.\n"
        "3. Pilih menu **'API development tools'**.\n"
        "4. Isi form (App title/Short name bebas).\n"
        "5. Salin **App api_id** dan **App api_hash**.\n\n"
        "1️⃣ **Sekarang, kirim API ID Anda** (Angka).\n"
        "Atau ketik `skip` untuk menggunakan API Default (Telegram Android)."
    )
    buttons = [Button.inline("❌ Batal", b"cancel_login")]
    await event.edit(msg, buttons=buttons)

@bot.on(events.CallbackQuery(data=b"cancel_login"))
async def cancel_login_handler(event):
    user_id = event.sender_id
    if user_id in LOGIN_STATE:
        client = LOGIN_STATE[user_id].get('client')
        if client:
            await client.disconnect()
        del LOGIN_STATE[user_id]
    
    await event.edit("❌ Proses login dibatalkan.", buttons=[[Button.inline("🔙 Kembali", b"menu_accounts")]])

@bot.on(events.NewMessage)
async def login_input_handler(event):
    user_id = event.sender_id
    if user_id not in LOGIN_STATE:
        return
    
    state = LOGIN_STATE[user_id]
    step = state['step']
    text = event.text.strip()
    
    # --- STEP 1: API ID ---
    if step == 'wait_api_id':
        if text.lower() == 'skip':
            state['api_id'] = config.DEFAULT_API_ID
            state['api_hash'] = config.DEFAULT_API_HASH
            # Langsung loncat ke input nomor
            state['step'] = 'wait_phone'
            await event.respond(
                "✅ Menggunakan API Default.\n\n"
                "3️⃣ **Masukkan Nomor HP**\n"
                "Format: KodeNegaraNomor (Contoh: `628123456789`)"
            )
        else:
            if not text.isdigit():
                return await event.respond("⚠️ API ID harus berupa angka.")
            state['api_id'] = int(text)
            state['step'] = 'wait_api_hash'
            await event.respond("2️⃣ **Masukkan API Hash**")
            
    # --- STEP 2: API HASH ---
    elif step == 'wait_api_hash':
        state['api_hash'] = text
        state['step'] = 'wait_phone'
        await event.respond(
            f"✅ API Hash disimpan.\n\n"
            "3️⃣ **Masukkan Nomor HP**\n"
            "Format: KodeNegaraNomor (Contoh: `628123456789`)"
        )

    # --- STEP 3: NOMOR HP ---
    elif step == 'wait_phone':
        if not text.isdigit() or len(text) < 7:
            return await event.respond("⚠️ Nomor tidak valid. Gunakan format internasional tanpa tanda plus (Contoh: 628xxx).")
        
        phone = text
        api_id = state.get('api_id', config.DEFAULT_API_ID)
        api_hash = state.get('api_hash', config.DEFAULT_API_HASH)
        
        await event.respond(f"🔄 Menghubungkan ke Telegram dengan nomor `{phone}`...\n(API ID: {api_id})")
        
        try:
            client = TelegramClient(StringSession(), api_id, api_hash)
            await client.connect()
            
            if not await client.is_user_authorized():
                await client.send_code_request(phone)
                
                state['step'] = 'wait_code'
                state['client'] = client
                state['phone'] = phone
                
                await event.respond(
                    "✅ **Kode OTP Terkirim!**\n\n"
                    "Silakan cek pesan dari Telegram, lalu kirim kodenya di sini.\n"
                    "Contoh: `12345`"
                )
            else:
                await event.respond("⚠️ Nomor ini sepertinya sudah login?")
                await client.disconnect()
                del LOGIN_STATE[user_id]
        
        except Exception as e:
            if 'client' in locals(): await client.disconnect()
            del LOGIN_STATE[user_id]
            await event.respond(f"❌ **Gagal:** {e}\n\nKemungkinan penyebab:\n1. API ID/Hash Salah.\n2. Akun terkena limit/reCAPTCHA.\n3. Koneksi server bermasalah.")

    # --- STEP 4: OTP CODE ---
    elif step == 'wait_code':
        client = state['client']
        phone = state['phone']
        code = text.replace(" ", "")
        
        try:
            await client.sign_in(phone, code)
            await finish_login(user_id, client, phone, event)
            
        except SessionPasswordNeededError:
            state['step'] = 'wait_2fa'
            await event.respond("🔒 **Akun ini dilindungi Password (2FA).**\nSilakan kirim password Anda.")
            
        except PhoneCodeInvalidError:
            await event.respond("❌ Kode OTP salah. Silakan kirim ulang kode yang benar.")
            
        except Exception as e:
            await event.respond(f"❌ Error: {e}")

    # --- STEP 5: 2FA PASSWORD ---
    elif step == 'wait_2fa':
        client = state['client']
        phone = state['phone']
        password = text
        
        try:
            await client.sign_in(password=password)
            await finish_login(user_id, client, phone, event)
            
        except PasswordHashInvalidError:
            await event.respond("❌ Password salah. Silakan coba lagi.")
        except Exception as e:
            await event.respond(f"❌ Error: {e}")

async def finish_login(user_id, client, phone, event):
    try:
        session_string = client.session.save()
        me = await client.get_me()
        
        # Format Nama: "Nama Depan (@username)"
        fullname = f"{me.first_name} {me.last_name or ''}".strip()
        username_part = f"(@{me.username})" if me.username else ""
        final_name = f"{fullname} {username_part}".strip()
        
        state = LOGIN_STATE[user_id]
        
        db_helper.add_session(
            user_id, 
            phone, 
            session_string, 
            state.get('api_id', config.DEFAULT_API_ID), 
            state.get('api_hash', config.DEFAULT_API_HASH), 
            final_name # Simpan nama + username
        )
        
        await client.disconnect()
        if user_id in LOGIN_STATE:
            del LOGIN_STATE[user_id]
        
        await event.respond(
            f"✅ **Login Berhasil!**\n"
            f"Akun: `{final_name}` ({phone})\n"
            f"API ID: `{state.get('api_id', 'Default')}`\n"
            f"Sesi telah disimpan dengan aman.",
            buttons=[[Button.inline("📂 Kembali ke Menu Akun", b"menu_accounts")]]
        )
        
    except Exception as e:
        await event.respond(f"❌ Gagal menyimpan sesi: {e}")