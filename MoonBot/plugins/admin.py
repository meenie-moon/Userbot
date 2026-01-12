from telethon import events, Button
from MoonBot.client import bot
from MoonBot import db_helper, config
import asyncio

# State Dictionary untuk menyimpan status input admin
ADMIN_STATE = {}

@bot.on(events.NewMessage(pattern='/admin', from_users=[config.OWNER_ID]))
async def admin_command_handler(event):
    await show_admin_panel(event)

@bot.on(events.CallbackQuery(data=b"menu_admin"))
async def admin_menu_callback(event):
    if event.sender_id != config.OWNER_ID:
        return await event.answer("Akses Ditolak!", alert=True)
    await show_admin_panel(event)

async def show_admin_panel(event):
    # Bersihkan state jika kembali ke menu utama
    if event.sender_id in ADMIN_STATE:
        del ADMIN_STATE[event.sender_id]

    pending_users = db_helper.get_pending_users()
    pending_count = len(pending_users)
    active_users = db_helper.get_all_active_users()
    active_count = len(active_users)
    
    msg = (
        f"🛡️ **Admin Control Panel**\n\n"
        f"👥 User Active: **{active_count}**\n"
        f"⏳ User Pending: **{pending_count}**"
    )
    
    buttons = []
    if pending_count > 0:
        buttons.append([Button.inline(f"✅ Proses Pending ({pending_count})", b"admin_list_pending")])
    
    buttons.append([Button.inline("📋 List Users", b"admin_list_users")])
    buttons.append([Button.inline("🚫 Hapus Whitelist", b"admin_revoke_menu")])
    buttons.append([Button.inline("📢 Broadcast All Users", b"admin_broadcast_start")])
    buttons.append([Button.inline("👤 Tambah User Manual", b"admin_manual")])
    buttons.append([Button.inline("🔙 Kembali", b"main_menu")])
    
    await event.edit(msg, buttons=buttons)

# --- BROADCAST ALL USERS ---

@bot.on(events.CallbackQuery(data=b"admin_broadcast_start"))
async def admin_broadcast_start(event):
    ADMIN_STATE[event.sender_id] = 'wait_broadcast_msg'
    await event.edit(
        "📢 **Broadcast ke Semua User**\n\n"
        "Silakan kirim pesan (Text/Gambar/Video) yang ingin disebarkan ke seluruh pengguna bot.\n\n"
        "Semua user dengan status **Active** akan menerima pesan ini.",
        buttons=[[Button.inline("❌ Batal", b"menu_admin")]]
    )

# --- LIST USERS WHITELIST ---

@bot.on(events.CallbackQuery(data=b"admin_list_users"))
async def list_users_handler(event):
    users = db_helper.get_all_active_users()
    if not users:
        return await event.answer("Tidak ada user aktif.", alert=True)
    
    msg_list = f"📋 **Daftar User Whitelist (Active: {len(users)})**\n\n"
    
    for uid in users:
        try:
            user = await bot.get_entity(uid)
            name = user.first_name or ""
            if user.last_name:
                name += f" {user.last_name}"
            username = f"@{user.username}" if user.username else "-"
            # Format: ID | Name (Username)
            msg_list += f"• `{uid}` | {name} ({username})\n"
        except:
            msg_list += f"• `{uid}` | (Tidak dapat mengambil info)\n"
            
    await event.edit(msg_list, buttons=[[Button.inline("🔙 Kembali", b"menu_admin")]])

# --- MANAJEMEN PENDING USERS ---

@bot.on(events.CallbackQuery(data=b"admin_list_pending"))
async def list_pending_handler(event):
    users = db_helper.get_pending_users()
    if not users:
        return await event.answer("Tidak ada user pending.", alert=True)
    
    await event.edit("⏳ **Daftar User Pending**\nSilakan proses user di bawah ini:")
    
    for uid in users:
        try:
            user = await bot.get_entity(uid)
            info = f"{user.first_name} (@{user.username})"
        except:
            info = f"ID: {uid}"
            
        buttons = [
            [Button.inline("✅ Approve", f"approve_{uid}".encode()), Button.inline("⛔ Block", f"block_{uid}".encode())]
        ]
        await bot.send_message(event.chat_id, f"User Request:\n{info}\nID: `{uid}`", buttons=buttons)
    
    # Tambah tombol kembali di bawah list
    await bot.send_message(event.chat_id, "--- End of List ---", buttons=[Button.inline("🔙 Kembali ke Panel", b"menu_admin")])

@bot.on(events.CallbackQuery(pattern=r"approve_(\d+)"))
async def approve_handler(event):
    user_id = int(event.pattern_match.group(1))
    db_helper.approve_user(user_id)
    await event.answer("User Approved!")
    await event.edit(f"✅ User `{user_id}` telah disetujui.")
    try:
        await bot.send_message(user_id, "✅ **Selamat!** Akses Anda telah disetujui oleh Owner.\nSilakan ketik /start untuk memulai.")
    except:
        pass

@bot.on(events.CallbackQuery(pattern=r"block_(\d+)"))
async def block_handler(event):
    user_id = int(event.pattern_match.group(1))
    db_helper.block_user(user_id)
    await event.answer("User Blocked!")
    await event.edit(f"⛔ User `{user_id}` telah diblokir.")

# --- MANAJEMEN HAPUS WHITELIST (REVOKE) ---

@bot.on(events.CallbackQuery(data=b"admin_revoke_menu"))
async def admin_revoke_menu(event):
    ADMIN_STATE[event.sender_id] = 'wait_revoke_id'
    active_users = db_helper.get_all_active_users()
    
    msg = (
        "🚫 **Hapus Whitelist User**\n\n"
        "Kirimkan **ID User** yang ingin dicabut aksesnya.\n"
        "Status mereka akan kembali menjadi **Pending**.\n"
        "Data user (Sesi & Template) **TIDAK** akan dihapus.\n\n"
        f"Total Active Users: {len(active_users)}"
    )
    
    buttons = [[Button.inline("❌ Batal", b"menu_admin")]]
    await event.edit(msg, buttons=buttons)

# --- MANAJEMEN USER MANUAL (ADD) ---

@bot.on(events.CallbackQuery(data=b"admin_manual"))
async def admin_manual_handler(event):
    ADMIN_STATE[event.sender_id] = 'wait_add_id'
    await event.edit(
        "👤 **Tambah User Manual**\n\n"
        "Silakan kirim **ID Telegram** (Angka) user yang ingin di-whitelist.\n"
        "Contoh: `123456789`",
        buttons=[[Button.inline("❌ Batal", b"menu_admin")]]
    )

# --- UNIVERSAL INPUT HANDLER (ADMIN) ---

@bot.on(events.NewMessage(from_users=[config.OWNER_ID]))
async def admin_input_handler(event):
    sender_id = event.sender_id
    if sender_id not in ADMIN_STATE:
        return

    state = ADMIN_STATE[sender_id]
    
    # 1. HANDLE BROADCAST
    if state == 'wait_broadcast_msg':
        users = db_helper.get_all_active_users()
        sent_count = 0
        fail_count = 0
        
        progress_msg = await event.respond(f"🚀 Memulai broadcast ke {len(users)} user...")
        
        for uid in users:
            if uid == config.OWNER_ID: continue # Skip diri sendiri jika mau, atau biarkan
            try:
                # Copy pesan dari admin ke user
                await bot.send_message(uid, event.message)
                sent_count += 1
            except Exception as e:
                fail_count += 1
            await asyncio.sleep(0.1) # Flood prevention
            
        await progress_msg.edit(
            f"✅ **Broadcast Selesai**\n\n"
            f"Sukses: {sent_count}\n"
            f"Gagal: {fail_count}",
            buttons=[[Button.inline("🔙 Kembali", b"menu_admin")]]
        )
        del ADMIN_STATE[sender_id]
        return

    # 2. HANDLE MANUAL ADD
    if state == 'wait_add_id':
        text = event.text.strip()
        if not text.isdigit():
            return await event.respond("⚠️ ID harus berupa angka valid.")

        target_id = int(text)
        status = db_helper.check_user_status(target_id)
        
        if status == 'active':
            await event.respond(f"ℹ️ User `{target_id}` sudah dalam status **AKTIF**.")
        else:
            conn = db_helper.get_connection()
            c = conn.cursor()
            if status is None:
                c.execute("INSERT INTO users (user_id, role, status) VALUES (?, 'user', 'active')", (target_id,))
                action_msg = "ditambahkan ke database"
            else:
                c.execute("UPDATE users SET status='active' WHERE user_id=?", (target_id,))
                action_msg = "diperbarui statusnya"
            conn.commit()
            conn.close()
            
            await event.respond(
                f"✅ User `{target_id}` berhasil {action_msg} menjadi **AKTIF**.",
                buttons=[[Button.inline("🔙 Kembali", b"menu_admin")]]
            )
        del ADMIN_STATE[sender_id]
        return

    # 3. HANDLE REVOKE (HAPUS WHITELIST)
    if state == 'wait_revoke_id':
        text = event.text.strip()
        if not text.isdigit():
            return await event.respond("⚠️ ID harus berupa angka valid.")
            
        target_id = int(text)
        if target_id == config.OWNER_ID:
            return await event.respond("⚠️ Tidak bisa menghapus whitelist Owner sendiri!")
            
        status = db_helper.check_user_status(target_id)
        
        if status != 'active':
            await event.respond(f"⚠️ User `{target_id}` tidak dalam status Aktif (Status: {status or 'Tidak Dikenal'}).")
        else:
            db_helper.revoke_user(target_id)
            await event.respond(
                f"🚫 Akses User `{target_id}` telah **DICABUT**.\nStatus kembali menjadi Pending.",
                buttons=[[Button.inline("🔙 Kembali", b"menu_admin")]]
            )
        del ADMIN_STATE[sender_id]
        return
