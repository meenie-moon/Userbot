# MoonTele / MoonBot Project

## Project Overview

**MoonTele** is a sophisticated Telegram Automation Tool designed to manage multiple accounts and perform broadcast operations. Originally a standalone CLI tool (`MoonTele.py`), it has been refactored into a modular, server-side bot application (**MoonBot**) that runs on a VPS and is controlled via a Telegram Bot interface.

The system allows an administrator (Owner) to approve users, who can then add their own Telegram accounts (Userbots), create target templates, and schedule or send broadcast messages to groups and topics.

### Key Technologies
*   **Language:** Python 3.x
*   **Core Library:** [Telethon](https://docs.telethon.dev/) (MTProto API)
*   **Database:** SQLite (local storage for sessions, users, and templates)
*   **UI/UX:** Rich (for CLI legacy), Telegram Inline Buttons (for Bot interface)

## Architecture

The project is structured as a Python package (`MoonBot`) with a plugin system.

*   **`run.py`**: The main entry point to start the Bot Controller.
*   **`MoonBot/`**: Core package directory.
    *   **`main.py`**: Initializes the bot and loads plugins.
    *   **`client.py`**: Manages the Telethon client instance.
    *   **`config.py`**: Configuration constants (API Tokens, IDs).
    *   **`db_helper.py`**: Database abstraction layer (CRUD operations for Users, Sessions, Templates).
    *   **`plugins/`**: Contains feature-specific logic:
        *   `start.py`: Main menu, navigation, and improved unauthorized user handling.
        *   `login.py`: Logic for adding user accounts (Userbots) and session management.
        *   `manager.py`: Template creation (Smart Link Parsing) and editing.
        *   `tools.py`: Broadcasting logic.
        *   `admin.py`: Owner-only controls (Approve/Block/Revoke users, Broadcast All).
*   **`deploy.py`**: Automation script to zip and deploy the project to a VPS using `sshpass`.
*   **`gen_session.py`**: Utility script to manually generate Telegram string sessions via terminal.

## Setup & Usage

### 1. Installation
Ensure Python 3 and the required packages are installed:

```bash
pip install -r requirements.txt
```

### 2. Configuration
The bot requires a `MoonBot/config.py` (automatically created during setup) containing:
*   `API_TOKEN`: The Bot Token from @BotFather.
*   `OWNER_ID`: The Telegram ID of the admin.

### 3. Running the Bot
To start the bot server:

```bash
python3 run.py
```

### 4. Deployment (VPS)
To deploy automatically to a VPS, create a `data.txt` file (ignored by git) with your VPS credentials, then run:

```bash
python3 deploy.py
```
*Note: `data.txt` format should contain IP, Username, and Password.*

## Features

*   **Multi-Account System:** Users can add multiple Telegram accounts via the bot interface or by importing string sessions.
*   **Smart Template System:** Users can create target lists by simply sending a link to a message. The bot automatically extracts the Group ID and Topic ID.
*   **Broadcasting:** Send messages to stored templates using any registered account.
*   **True Forward Broadcasting:** Meneruskan pesan dari link Telegram (e.g., `https://t.me/channel/123`) sambil menjaga tag "Forwarded from" dan jumlah "Views", serta mendukung pengiriman ke Topik Forum.
*   **Admin Panel v2:**
    *   **User Approval:** Whitelist system to control access.
    *   **Global Broadcast:** Kirim pesan pengumuman ke seluruh user aktif bot.
    *   **List Users:** Menampilkan daftar semua user yang statusnya aktif (whitelist).
    *   **Revoke Access:** Cabut akses user (Soft Ban) tanpa menghapus data mereka, mengembalikan status ke 'Pending'.
    *   **Manual Management:** Tambah user manual via ID.
*   **Safety:** Includes configurable delays and uses official Android API IDs by default to minimize ban risks.

## Development Conventions

*   **Plugin Import:** Plugins are imported in `MoonBot/main.py` after the client is started.
*   **Database:** Always use `db_helper.py` for database transactions to ensure schema consistency (migrations are handled automatically in `get_connection`).
*   **Async/Await:** All Telethon interactions must be asynchronous.
*   **UI Updates:** Prefer `event.edit()` over `event.respond()` for menu navigation to keep the chat clean.