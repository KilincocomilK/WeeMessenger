"""
配置管理模块
从 config.yaml 读取用户配置，合并内置默认值后返回统一字典。
"""

import os
import logging

logger = logging.getLogger("WeChatSender.Config")

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

# 内置默认值
DEFAULT_CONFIG = {
    "ws_url": "ws://127.0.0.1:9876",
    "wanderer": {
        "enabled": True,
        "min_interval": 10.0,
        "max_interval": 30.0,
        "times_min": 1,
        "times_max": 3,
    },
    "log_level": "INFO",
}


def _deep_merge(base: dict, override: dict) -> dict:
    """递归合并两个字典，override 中的值覆盖 base"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str = None) -> dict:
    """
    加载配置文件并返回合并后的配置字典。
    优先从项目根目录的 config.yaml 加载，合并到默认值之上。
    """
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
        path = os.path.abspath(path)

    config = dict(DEFAULT_CONFIG)

    if os.path.exists(path):
        if not _HAS_YAML:
            logger.warning("[WCAC] PyYAML 未安装，使用默认配置。请执行: pip install pyyaml")
            return config
        try:
            with open(path, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f) or {}
            config = _deep_merge(config, user_config)
            logger.info(f"[WCAC] 已加载配置文件: {path}")
        except Exception as e:
            logger.warning(f"[WCAC] 配置文件读取失败 ({e})，使用默认配置")
    else:
        logger.info(f"[WCAC] 配置文件不存在 ({path})，使用默认配置")

    return config
