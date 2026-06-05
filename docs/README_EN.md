<p align="center">
  <img src="./assets/Banner.png" alt="Banner" width="100%">
</p>

<h2 align="center">📧 WeeMessenger - A Flexible WeChat Message Sender 🚀</h2>

<p align="center">
  [<a href="../README.md">中文</a>] | [<strong>English</strong>]
</p>

## Core Features

Receives external messages via WebSocket and leverages UI automation to send text, voice messages, and stickers (GIF) through WeChat PC client. Compatible with newer WeChat versions, supports joining group chats, and includes lightweight anti-detection mechanisms to reduce the risk of being flagged.

---

## Requirements

- Windows 10/11
- WeChat PC 4.1.9 or later

---

## Quick Start

### 1. Edit Configuration

Edit `config.yaml` in the project root:

```yaml
# WebSocket server address for receiving send commands
ws_url: "ws://192.168.1.1:1234/ws"

# Mouse wanderer anti-detection parameters
wanderer:
  enabled: true         # Enable mouse wandering
  min_interval: 10.0    # Minimum wander interval (seconds)
  max_interval: 30.0    # Maximum wander interval (seconds)
  times_min: 1          # Minimum moves per wander
  times_max: 3          # Maximum moves per wander

# Log level: DEBUG / INFO / WARNING / ERROR
log_level: "INFO"
```

All configuration options have built-in defaults; only fill in the items you need to override.

### 2. External Setup

* **Voice Messages**: To enable voice messages, download and install VB-Cable to route computer audio through a virtual microphone. Download: https://vb-audio.com/Cable/
* **Upstream Server**: Start your upstream WebSocket server

### 3. Launch!

**Double-click `启动.bat`** — the script will automatically create a virtual environment, install dependencies, display a startup menu. Select **标准模式** to run!

> [!IMPORTANT]
> Before first use, open WeChat, use the shortcut **Ctrl+F**, manually search for the group chat you want to deploy and enter it several times. This ensures the group appears at the **top of the search suggestions**, avoiding interference from "online search results."

## WebSocket Command Protocol

The server sends JSON-formatted commands to this program. Three command types are supported:

### Send Text Message

```json
{
  "type": "send_message",
  "target": "Contact or group chat name",
  "message": "Message content"
}
```

### Send Voice Message

```json
{
  "type": "send_voice",
  "target": "Contact or group chat name",
  "message": "Accompanying text (optional)",
  "voice_data": "<base64 encoded MP3 audio>",
  "format": "mp3"
}
```

Voice message workflow: If accompanying text is provided, the text is sent first, followed by the voice message. Leave the field empty to skip the accompanying text.

### Send Sticker (GIF)

```json
{
  "type": "send_sticker",
  "target": "Contact or group chat name",
  "sticker_data": "<base64 encoded GIF file>"
}
```

## Project Structure

```
WeeMessenger/
├── 启动.bat                 # One-click startup script (recommended)
├── _launcher.py             # Launcher: environment setup, dependency management, menu
├── main.py                  # Program entry point
├── config.yaml              # User configuration file
├── requirements.txt         # Python dependencies
├── LICENSE                  # MIT License
├── README.md                # Project overview (Chinese)
└── src/
    ├── __init__.py
    ├── config.py            # Configuration management
    ├── wechat_sender.py     # Core sender logic
    ├── ws_client.py         # WebSocket client
    ├── voice_sender.py      # Voice message sender
    ├── mouse_wanderer.py    # Mouse wanderer
    └── clipboard_utils.py   # Clipboard utilities
```

## Notes

- **WeChat Window**: WeChat must remain in the foreground or at least not minimized to the system tray, otherwise UI automation may fail to locate controls.
- **Group Chat Search**: Before sending messages to a group for the first time, ensure the group appears under "Frequently Used" in the search bar. Send a few messages in the group or manually search and enter it several times.
- **Exit**: Press `Ctrl+C` to exit safely.
- **Support**: If WeeMessenger is useful to you, please give it a Star! Thanks for your support!
