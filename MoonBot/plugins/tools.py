import asyncio
import re
from telethon import events, Button
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from telethon.tl.functions.messages import ForwardMessagesRequest

from MoonBot.client import bot
from MoonBot import db_helper, config

# State: {user_id: {'account_id': 1, 'template_id': 2, 'msg_event': event_obj}}
BROADCAST_STATE = {}

@bot.on(events.CallbackQuery(data=b"menu_tools"))
async def tools_menu_callback(event):
    msg = "🚀 **Menu Tools**\nSilakan pilih tool yang ingin dijalankan."
    buttons = [
        [Button.inline("📢 Broadcast Pesan", b"tool_broadcast")],
        [Button.inline("🔙 Menu Utama", b"main_menu")]
    ]
    await event.edit(msg, buttons=buttons)

@bot.on(events.CallbackQuery(data=b"tool_broadcast"))
async def tool_broadcast_start(event):
    user_id = event.sender_id
    sessions = db_helper.get_user_sessions(user_id)
    
    if not sessions:
        return await event.answer("Anda belum menambahkan akun!", alert=True)
    
    msg = "1️⃣ **Pilih Akun Pengirim**\nPesan akan dikirim menggunakan akun ini."
    buttons = []
    for s in sessions:
        buttons.append([Button.inline(f"📱 {s['name']}", f"bc_acc_{s['id']}".encode())])
    buttons.append([Button.inline("🔙 Batal", b"menu_tools")])
    
    await event.edit(msg, buttons=buttons)

@bot.on(events.CallbackQuery(pattern=r"bc_acc_(\d+)"))
async def broadcast_select_account(event):
    acc_id = int(event.pattern_match.group(1))
    user_id = event.sender_id
    
    BROADCAST_STATE[user_id] = {'account_id': acc_id}
    
    # Pilih Template
    templates = db_helper.get_user_templates(user_id)
    if not templates:
        return await event.answer("Anda belum punya template target!", alert=True)
        
    msg = "2️⃣ **Pilih Template Target**\nPesan akan dikirim ke daftar dalam template ini."
    buttons = []
    for t in templates:
        buttons.append([Button.inline(f"📄 {t['name']}", f"bc_tpl_{t['id']}".encode())])
    
    await event.edit(msg, buttons=buttons)

@bot.on(events.CallbackQuery(pattern=r"bc_tpl_(\d+)"))
async def broadcast_select_template(event):
    tpl_id = int(event.pattern_match.group(1))
    user_id = event.sender_id
    
    if user_id in BROADCAST_STATE:
        BROADCAST_STATE[user_id]['template_id'] = tpl_id
        BROADCAST_STATE[user_id]['step'] = 'wait_msg'
        
        await event.edit(
            "3️⃣ **Kirim Pesan Broadcast**\n\n"
            "Silakan kirim pesan (Teks, Gambar, atau Forward) yang ingin disebarkan.\n"
            "Bot akan menyalin pesan Anda (Copy Mode).\n\n"
            "📢 **FITUR BARU: True Forward**\n"
            "Kirim **Link Pesan Telegram** (contoh: `https://t.me/channel/123`) untuk meneruskan pesan dengan tetap menjaga:\n"
            "✅ Tag 'Forwarded From'\n"
            "✅ Jumlah Views\n"
            "✅ Support Topik Forum"
        )

@bot.on(events.NewMessage)
async def broadcast_msg_handler(event):
    user_id = event.sender_id
    if user_id not in BROADCAST_STATE or BROADCAST_STATE[user_id].get('step') != 'wait_msg':
        return
        
    state = BROADCAST_STATE[user_id]
    
    # Ambil data session dan template
    acc_data = db_helper.get_session_data(state['account_id'])
    templates = db_helper.get_user_templates(user_id)
    target_list = []
    
    # Cari konten template
    for t in templates:
        if t['id'] == state['template_id']:
            target_list = t['content']
            break
            
    if not acc_data or not target_list:
        del BROADCAST_STATE[user_id]
        return await event.respond("❌ Data sesi atau template tidak ditemukan/korup.")
        
    # Konfirmasi
    msg_preview = event.text[:50] + "..." if event.text else "[Media]"
    
    # Deteksi True Forward via Link
    link_match = re.search(r"t\.me\/(c\/)?(\w+|\d+)\/(\d+)", event.text.strip())
    is_true_forward = False
    forward_data = {}
    
    if link_match and not event.media:
        # Jika hanya teks link, anggap sebagai request True Forward
        is_true_forward = True
        is_private_c = link_match.group(1) is not None
        chat_part = link_match.group(2)
        msg_id = int(link_match.group(3))
        
        # Normalisasi Chat ID Source
        if is_private_c:
            chat_source = int(f"-100{chat_part}")
        else:
            chat_source = chat_part # Username
            
        forward_data = {'chat': chat_source, 'msg_id': msg_id}
        msg_preview = f"🔗 Link: {event.text.strip()}"
    
    # Gunakan Nama Akun (yang berisi username) jika ada
    sender_display = acc_data.get('name', acc_data['phone'])
    
    mode_info = "✅ **True Forward** (Tag & View Tetap)" if is_true_forward else "📋 **Copy Mode** (Pesan Baru)"
    
    confirm_msg = (
        f"⚠️ **Konfirmasi Broadcast**\n\n"
        f"Akun Pengirim: `{sender_display}`\n"
        f"Jumlah Target: `{len(target_list)}`\n"
        f"Mode: {mode_info}\n"
        f"Pesan: {msg_preview}\n\n"
        f"Ketik /send untuk memulai atau /cancel untuk membatalkan."
    )
    
    # Simpan event pesan untuk diteruskan nanti
    state['message_object'] = event.message
    state['step'] = 'confirm'
    state['target_list'] = target_list
    state['acc_data'] = acc_data
    
    # Simpan Data Forward jika ada
    if is_true_forward:
        state['mode'] = 'true_forward'
        state['forward_data'] = forward_data
    else:
        state['mode'] = 'copy'
    
    await event.respond(confirm_msg)

@bot.on(events.NewMessage(pattern='/send'))
async def run_broadcast(event):
    user_id = event.sender_id
    if user_id not in BROADCAST_STATE or BROADCAST_STATE[user_id].get('step') != 'confirm':
        return

    state = BROADCAST_STATE[user_id]
    acc = state['acc_data']
    targets = state['target_list']
    message = state['message_object']
    
    status_msg = await event.respond("🔄 **Memulai Broadcast...**\nMenghubungkan ke akun Telegram user...")
    
    # Hapus state agar user tidak spam /send
    del BROADCAST_STATE[user_id]

    try:
        # Start User Client
        client = TelegramClient(StringSession(acc['session_string']), acc['api_id'], acc['api_hash'])
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return await status_msg.edit("❌ Sesi Akun Kadaluarsa/Logout. Silakan login ulang.")
            
        success = 0
        failed = 0
        
        # Prepare True Forward Data if needed
        is_true_forward = state.get('mode') == 'true_forward'
        forward_params = {}
        
        if is_true_forward:
            try:
                # Resolve Source Peer Once
                fdata = state['forward_data']
                src_entity = await client.get_entity(fdata['chat'])
                forward_params['from_peer'] = await client.get_input_entity(src_entity)
                forward_params['id'] = [fdata['msg_id']]
                
                # Cek apakah pesan bisa diakses
                # await client.get_messages(src_entity, ids=fdata['msg_id'])
            except Exception as e:
                await client.disconnect()
                return await status_msg.edit(f"❌ Gagal mengakses Pesan Sumber (Link):\n{e}\n\nPastikan akun Userbot sudah bergabung di channel/grup sumber.")

        for item in targets:
            try:
                # Normalisasi Target (Support Format Lama & Baru)
                if isinstance(item, dict):
                    chat_id = item['chat']
                    topic_id = item.get('topic') # Bisa None
                else:
                    # Format lama (hanya string ID/Username)
                    chat_id = item
                    topic_id = None
                
                if is_true_forward:
                    # --- LOGIKA TRUE FORWARD ---
                    # Butuh InputPeer untuk tujuan
                    to_entity = await client.get_entity(chat_id)
                    to_peer = await client.get_input_entity(to_entity)
                    
                    await client(ForwardMessagesRequest(
                        from_peer=forward_params['from_peer'],
                        id=forward_params['id'],
                        to_peer=to_peer,
                        top_msg_id=topic_id if topic_id else None
                    ))
                else:
                    # --- LOGIKA COPY (DEFAULT) ---
                    # Kirim pesan (sebagai copy agar aman)
                    # Gunakan reply_to untuk mengirim ke Topic spesifik
                    await client.send_message(chat_id, message, reply_to=topic_id)
                
                success += 1
                await asyncio.sleep(5) # Delay aman (5 detik)
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds)
            except Exception as e:
                failed += 1
                # Optional: Log error detail per chat if needed
                print(f"Failed {chat_id}: {e}")
                
            # Update status tiap 5 pesan
            if (success + failed) % 5 == 0:
                await status_msg.edit(f"🚀 **Proses Broadcast**\nSukses: {success}\nGagal: {failed}\nSisa: {len(targets) - (success+failed)}")
        
        await client.disconnect()
        await status_msg.edit(f"✅ **Broadcast Selesai!**\n\nSukses: {success}\nGagal: {failed}")
        
        # Update Statistik Total Blast
        db_helper.increment_broadcast_count(user_id)
        
    except Exception as e:
        await status_msg.edit(f"❌ Terjadi kesalahan fatal: {e}")

@bot.on(events.NewMessage(pattern='/cancel'))
async def cancel_broadcast(event):
    user_id = event.sender_id
    if user_id in BROADCAST_STATE:
        del BROADCAST_STATE[user_id]
        await event.respond("✅ Broadcast dibatalkan.", buttons=[[Button.inline("🔙 Menu Utama", b"main_menu")]])
