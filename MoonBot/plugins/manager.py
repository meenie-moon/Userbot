from telethon import events, Button
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from MoonBot.client import bot
from MoonBot import db_helper

# State untuk input template: {user_id: {'step': 'name'|'content', 'temp_name': '...', 'tpl_id': 1}}
TEMPLATE_STATE = {}

@bot.on(events.CallbackQuery(data=b"menu_templates"))
async def template_menu_callback(event):
    user_id = event.sender_id
    templates = db_helper.get_user_templates(user_id)
    
    msg = f"📝 **Manajemen Template**\nAnda memiliki {len(templates)} template tersimpan.\nKlik nama template untuk melihat detail atau mengedit.\n\n" 
    
    buttons = []
    for t in templates:
        buttons.append([
            Button.inline(f"📄 {t['name']} ({len(t['content'])} target)", f"view_tpl_{t['id']}".encode())
        ])
        
    buttons.append([Button.inline("➕ Buat Template Baru", b"add_template")])
    buttons.append([Button.inline("🔙 Menu Utama", b"main_menu")])
    
    await event.edit(msg, buttons=buttons)

# --- DETAIL TEMPLATE & EDIT ---
@bot.on(events.CallbackQuery(pattern=r"view_tpl_(\d+)"))
async def view_template_handler(event):
    tpl_id = int(event.pattern_match.group(1))
    user_id = event.sender_id
    templates = db_helper.get_user_templates(user_id)
    
    # Cari template
    target_tpl = next((t for t in templates if t['id'] == tpl_id), None)
    if not target_tpl:
        return await event.answer("Template tidak ditemukan!", alert=True)

    # Format List Target
    content_text = ""
    for i, item in enumerate(target_tpl['content'], 1):
        if isinstance(item, dict):
            # Tampilkan Nama Grup (Prioritas Data Baru)
            c_display = item.get('chat_title', item['chat'])
            
            # Tampilkan Nama Topik (Prioritas Data Baru)
            t_display = ""
            if item.get('topic'):
                t_title = item.get('topic_title', item['topic'])
                t_display = f" (Topik: {t_title})"
            
            content_text += f"{i}. **{c_display}**{t_display}\n"
        else:
            content_text += f"{i}. `{item}`\n"
            
    if not content_text: content_text = "(Kosong)"
    
    # Potong jika terlalu panjang
    if len(content_text) > 3000:
        content_text = content_text[:3000] + "\n...(dan lainnya)"

    msg = (
        f"📄 **Template: {target_tpl['name']}**\n"
        f"Total Target: {len(target_tpl['content'])}\n\n"
        f"**Daftar Target:**\n"
        f"{content_text}"
    )
    
    buttons = [
        [Button.inline("➕ Tambah Target", f"add_tgt_{tpl_id}".encode()), Button.inline("🗑️ Hapus Target", f"del_tgt_{tpl_id}".encode())],
        [Button.inline("⚠️ Hapus Template Ini", f"del_tpl_{tpl_id}".encode())],
        [Button.inline("🔙 Kembali", b"menu_templates")]
    ]
    await event.edit(msg, buttons=buttons)

@bot.on(events.CallbackQuery(pattern=r"del_tpl_(\d+)"))
async def delete_template_callback(event):
    tpl_id = int(event.pattern_match.group(1))
    db_helper.delete_template(tpl_id, event.sender_id)
    await event.answer("Template dihapus!")
    await template_menu_callback(event)

# --- ADD TARGET ---
@bot.on(events.CallbackQuery(pattern=r"add_tgt_(\d+)"))
async def add_target_init(event):
    tpl_id = int(event.pattern_match.group(1))
    TEMPLATE_STATE[event.sender_id] = {'step': 'add_target_input', 'tpl_id': tpl_id}
    
    await event.edit(
        "➕ **Tambah Target**\n\n"
        "Silakan kirim Link/ID grup atau topik yang ingin ditambahkan.\n"
        "⚠️ **Untuk Topik:** Salin Link Pesan dari DALAM topik tersebut agar ID terdeteksi.\n\n"
        "Bisa kirim banyak sekaligus (pisahkan baris baru).",
        buttons=[[Button.inline("❌ Batal", f"view_tpl_{tpl_id}".encode())]]
    )

# --- DELETE TARGET ---
@bot.on(events.CallbackQuery(pattern=r"del_tgt_(\d+)"))
async def del_target_init(event):
    tpl_id = int(event.pattern_match.group(1))
    TEMPLATE_STATE[event.sender_id] = {'step': 'del_target_input', 'tpl_id': tpl_id}
    
    await event.edit(
        "🗑️ **Hapus Target**\n\n"
        "Silakan kirim **Nomor Urut** target yang ingin dihapus.\n"
        "Lihat nomornya di daftar sebelumnya.\n"
        "Contoh: `1` atau `3`.",
        buttons=[[Button.inline("❌ Batal", f"view_tpl_{tpl_id}".encode())]]
    )

@bot.on(events.CallbackQuery(data=b"add_template"))
async def add_template_handler(event):
    user_id = event.sender_id
    TEMPLATE_STATE[user_id] = {'step': 'wait_name'}
    
    msg = (
        "➕ **Buat Template Baru**\n\n"
        "Silakan kirim **Nama Template** yang diinginkan.\n"
        "(Contoh: `List Promosi 1`)"
    )
    buttons = [Button.inline("❌ Batal", b"cancel_template")]
    await event.edit(msg, buttons=buttons)

@bot.on(events.CallbackQuery(data=b"cancel_template"))
async def cancel_template_handler(event):
    user_id = event.sender_id
    if user_id in TEMPLATE_STATE:
        del TEMPLATE_STATE[user_id]
    await template_menu_callback(event)

@bot.on(events.NewMessage)
async def template_input_handler(event):
    user_id = event.sender_id
    if user_id not in TEMPLATE_STATE:
        return
        
    state = TEMPLATE_STATE[user_id]
    text = event.text.strip()
    
    # --- LOGIKA TAMBAH/EDIT TARGET ---
    if state['step'] == 'add_target_input':
        import re
        raw_lines = text.split('\n')
        parsed_targets = []
        
        # Regex Patterns
        regex_private_topic = r"t\.me\/c\/(\d+)\/(\d+)\/\d+"
        regex_private_general = r"t\.me\/c\/(\d+)\/\d+"
        regex_public_topic = r"t\.me\/([^\/]+)\/(\d+)\/\d+"
        regex_public_general = r"t\.me\/([^\/]+)\/\d+"

        for line in raw_lines:
            clean = line.strip()
            if not clean: continue
            
            chat_target = None
            topic_target = None
            
            # Parsing Logic (Copy-Paste regex logic agar konsisten)
            match = re.search(regex_private_topic, clean)
            if match:
                chat_target = int(f"-100{match.group(1)}")
                topic_target = int(match.group(2))
            
            if not chat_target:
                match = re.search(regex_private_general, clean)
                if match:
                    chat_target = int(f"-100{match.group(1)}")
                    topic_target = None
            
            if not chat_target:
                match = re.search(regex_public_topic, clean)
                if match:
                    chat_target = match.group(1)
                    if chat_target.lower() != "c": topic_target = int(match.group(2))
                    else: chat_target = None
            
            if not chat_target:
                match = re.search(regex_public_general, clean)
                if match:
                    temp = match.group(1)
                    if temp.lower() != "c": chat_target = temp
            
            if not chat_target:
                if clean.startswith("@") or clean.startswith("-100") or clean.replace("-", "").isdigit():
                    chat_target = clean
            
            if chat_target:
                parsed_targets.append({"chat": chat_target, "topic": topic_target})
        
        if not parsed_targets:
            return await event.respond("⚠️ Tidak ada target valid terdeteksi.")

        # --- FETCH METADATA ---
        status_msg = await event.respond("🔄 Mengambil nama Grup & Topik... Mohon tunggu.")
        final_targets = []
        
        # Ambil Sesi Aktif
        sessions = db_helper.get_user_sessions(user_id)
        active_sess_data = None
        for s in sessions:
            if s['is_default']:
                active_sess_data = db_helper.get_session_data(s['id'])
                break
        
        if not active_sess_data and sessions:
             active_sess_data = db_helper.get_session_data(sessions[0]['id'])
        
        if active_sess_data:
            try:
                # Gunakan sesi untuk fetch info
                async with TelegramClient(StringSession(active_sess_data['session_string']), active_sess_data['api_id'], active_sess_data['api_hash']) as client:
                    for item in parsed_targets:
                        chat_title = item['chat']
                        topic_title = item['topic']
                        
                        try:
                            # 1. Fetch Chat
                            entity = await client.get_entity(item['chat'])
                            if hasattr(entity, 'title'): chat_title = entity.title
                            elif hasattr(entity, 'first_name'): chat_title = entity.first_name
                            
                            # 2. Fetch Topic
                            if item['topic']:
                                try:
                                    # Coba ambil pesan pertama dari topik
                                    msgs = await client.get_messages(entity, ids=item['topic'])
                                    if msgs:
                                        if hasattr(msgs, 'action') and hasattr(msgs.action, 'title'):
                                            topic_title = msgs.action.title
                                        else:
                                            # Jika tidak ada action title, mungkin reply biasa
                                            topic_title = f"Topic {item['topic']}"
                                except:
                                    pass
                        except Exception as e:
                            print(f"Fetch failed for {item['chat']}: {e}")
                        
                        final_targets.append({
                            "chat": item['chat'],
                            "topic": item['topic'],
                            "chat_title": str(chat_title),
                            "topic_title": str(topic_title) if item['topic'] else None
                        })
            except Exception as e:
                await status_msg.edit(f"⚠️ Gagal connect: {e}. Simpan ID saja.")
                final_targets = parsed_targets
        else:
            await status_msg.edit("⚠️ Tidak ada akun aktif. Simpan ID saja.")
            final_targets = parsed_targets

        # Simpan
        templates = db_helper.get_user_templates(user_id)
        current_tpl = next((t for t in templates if t['id'] == state['tpl_id']), None)
        
        if current_tpl:
            updated_content = current_tpl['content'] + final_targets
            db_helper.update_template_content(state['tpl_id'], user_id, updated_content)
            await status_msg.delete()
            await event.respond(f"✅ Berhasil menambah {len(final_targets)} target.", buttons=[[Button.inline("🔙 Kembali ke Template", f"view_tpl_{state['tpl_id']}".encode())]])
        
        del TEMPLATE_STATE[user_id]
        return

    elif state['step'] == 'del_target_input':
        if not text.isdigit(): return await event.respond("⚠️ Masukkan angka nomor urut.")
        idx = int(text) - 1
        
        templates = db_helper.get_user_templates(user_id)
        current_tpl = next((t for t in templates if t['id'] == state['tpl_id']), None)
        
        if current_tpl and 0 <= idx < len(current_tpl['content']):
            del current_tpl['content'][idx]
            db_helper.update_template_content(state['tpl_id'], user_id, current_tpl['content'])
            await event.respond(f"✅ Target nomor {text} dihapus.", buttons=[[Button.inline("🔙 Kembali ke Template", f"view_tpl_{state['tpl_id']}".encode())]])
        else:
            await event.respond("❌ Nomor tidak valid.")
        
        del TEMPLATE_STATE[user_id]
        return

    # --- LOGIKA BUAT TEMPLATE BARU ---
    if state['step'] == 'wait_name':
        state['temp_name'] = text
        state['step'] = 'wait_content'
        
        await event.respond(
            f"✅ Nama: **{text}**\n\n"
            "Sekarang kirim **Daftar Target**.\n"
            "Anda bisa mengirim:\n"
            "1. **Link Pesan** (Otomatis deteksi Grup & Topik)\n"
            "   ⚠️ *Untuk Topik: Ambil link dari pesan di dalam topik.*\n"
            "2. **Username/ID Manual**\n\n"
            "**TIPS:** Gunakan fitur 'Tambah Target' di dalam template nanti jika ingin otomatis mendeteksi nama grup."
        )
        
    elif state['step'] == 'wait_content':
        # Simpan sederhana dulu (hanya ID), user diarahkan pakai Add Target untuk fitur canggih
        # atau kita implementasi logika fetch di sini juga (opsional, tapi saya buat simpel dulu agar tidak duplikat kode berlebih)
        # Sebenarnya bisa panggil fungsi helper, tapi demi kestabilan, saya gunakan parsing basic di sini.
        
        import re
        raw_lines = text.split('\n')
        targets = []
        
        # Regex Basic (sama)
        regex_private_topic = r"t\.me\/c\/(\d+)\/(\d+)\/\d+"
        regex_private_general = r"t\.me\/c\/(\d+)\/\d+"
        regex_public_topic = r"t\.me\/([^\/]+)\/(\d+)\/\d+"
        regex_public_general = r"t\.me\/([^\/]+)\/\d+"

        for line in raw_lines:
            clean = line.strip()
            if not clean: continue
            chat_target = None
            topic_target = None
            
            match = re.search(regex_private_topic, clean)
            if match: chat_target, topic_target = int(f"-100{match.group(1)}"), int(match.group(2))
            
            if not chat_target:
                match = re.search(regex_private_general, clean)
                if match: chat_target, topic_target = int(f"-100{match.group(1)}"), None
            
            if not chat_target:
                match = re.search(regex_public_topic, clean)
                if match:
                    chat_target = match.group(1)
                    if chat_target.lower() != "c": topic_target = int(match.group(2))
                    else: chat_target = None

            if not chat_target:
                match = re.search(regex_public_general, clean)
                if match:
                    temp = match.group(1)
                    if temp.lower() != "c": chat_target = temp

            if not chat_target:
                if clean.startswith("@") or clean.startswith("-100") or clean.replace("-", "").isdigit():
                    chat_target = clean
            
            if chat_target:
                targets.append({"chat": chat_target, "topic": topic_target})
        
        if not targets:
            return await event.respond("⚠️ Tidak ada target valid.")
            
        db_helper.add_template(user_id, state['temp_name'], targets)
        del TEMPLATE_STATE[user_id]
        
        await event.respond(
            f"✅ **Template Berhasil Disimpan!**\n"
            f"Nama: {state['temp_name']}\n"
            f"Total Target: {len(targets)}\n"
            f"Gunakan menu 'Tambah Target' untuk mengambil Nama Grup secara otomatis.",
            buttons=[[Button.inline("📂 Kembali ke Template", b"menu_templates")]]
        )