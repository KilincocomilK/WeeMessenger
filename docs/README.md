<p align="center">
  <img src=".\assets\Banner.png" alt="Banner" width="100%">
</p>

<h2 align="center">📧小信使 - 一个灵活的微信消息发送器🚀</h2>

## 核心功能

通过 WebSocket 接收外部消息，利用自动化操作，实现微信文字、语音、表情包的自动发送。适用于高版本微信，支持加入群聊，拥有轻量的防检测机制，避免风控。

---

## 环境要求

- Windows 10/11
- 微信 4.1.9 及更新的版本

---

## 快速开始

### 1. 编辑配置

编辑项目根目录的 `config.yaml`：

```yaml
# WebSocket 服务器地址（接收发送指令）
ws_url: "ws://192.168.71.8:4191/ws"

# 鼠标自然漫游参数
wanderer:
  enabled: true         # 是否启用鼠标漫游防检测
  min_interval: 10.0    # 漫游最小间隔（秒）
  max_interval: 30.0    # 漫游最大间隔（秒）
  times_min: 1          # 单次漫游移动次数下限
  times_max: 3          # 单次漫游移动次数上限

# 日志级别: DEBUG / INFO / WARNING / ERROR
log_level: "INFO"
```

所有配置项均有内置默认值，只需填写需要覆盖的项即可

### 2. 外部配置

* **语音功能**：若要开启语音功能，请下载 VB-Cable 并安装，从而通过虚拟麦克风录制电脑音频，实现语音功能。下载地址：https://vb-audio.com/Cable/
* **开启上游**：开启您的上游 WebSocket 服务器

### 3. 启动！

**双击 `启动.bat`**，脚本会自动创建虚拟环境、安装依赖，然后显示启动菜单，选择**正常模式**即可运行！
> [!IMPORTANT]
初次使用前，请先打开微信客户端，使用快捷键 **Crtl + F** ，手动搜索需要部署的群聊名并进入几次，确保群聊出现在**搜索候选栏的首位**，避免受到“搜索网络结果”的影响~

## WebSocket 指令协议

服务端向本程序发送 JSON 格式的指令，支持以下三种类型：

### 发送文字

```json
{
  "type": "send_message",
  "target": "联系人或群聊名称",
  "message": "消息内容"
}
```

### 发送语音

```json
{
  "type": "send_voice",
  "target": "联系人或群聊名称",
  "message": "伴随文字（可选）",
  "voice_data": "<base64编码的MP3音频>",
  "format": "mp3"
}
```

语音消息处理流程：若有伴随文字，则优先发送伴随文字，再发送语音；若不发送伴随文字，留空即可

### 发送表情包

```json
{
  "type": "send_sticker",
  "target": "联系人或群聊名称",
  "sticker_data": "<base64编码的GIF文件>"
}
```

## 项目结构

```
WeeMessenger/
├── 启动.bat                 # 一键启动脚本（推荐）
├── main.py                  # 程序入口
├── config.yaml              # 用户配置文件
├── requirements.txt         # Python 依赖
├── README.md                # 项目概述（本文件）
└── src/
    ├── __init__.py
    ├── config.py            # 配置管理
    ├── wechat_sender.py     # 核心发送器
    ├── ws_client.py         # WebSocket 客户端
    ├── voice_sender.py      # 语音发送
    ├── mouse_wanderer.py    # 鼠标漫游
    └── clipboard_utils.py   # 剪贴板工具
```

## 注意事项

- **微信窗口**：微信需保持前台或至少不最小化到托盘，否则 UI 自动化可能找不到控件~
- **群聊搜索**：初次在某一群聊中发送消息前，需要在搜索栏中将群聊置于“最常使用”，在群中发几条消息或者手动搜索该群聊并进入几次即可~
- **退出程序**：按 `Ctrl+C` 即可安全退出~
- **支持**：如果感觉小信使对您有用，就点个 Star 叭！感谢支持~
- **许愿**：希望麻花疼不会顺着网线来把这个项目干掉，还有祝自己高考顺利~
