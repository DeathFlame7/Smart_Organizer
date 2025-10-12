import os
import configparser
import logging
from pathlib import Path

# 默认配置缓存
_DEFAULT_UI_CONFIG = None

def load_config() -> configparser.ConfigParser:
    """增加配置文件损坏处理，明确返回值类型"""
    config = configparser.ConfigParser()
    config_path = Path(__file__).parent.parent / 'config.ini'
    if config_path.exists():
        try:
            # 用UTF-8编码读取，避免解码错误
            with open(config_path, 'r', encoding='utf-8') as f:
                config.read_file(f)
        except configparser.ConfigParserError as e:
            # 配置文件损坏，生成默认配置
            logging.error(f"配置文件损坏: {e}，生成默认配置")
            config = _generate_default_config(config_path)
    else:
        # 无配置文件，生成默认配置
        config = _generate_default_config(config_path)
    return config

def _generate_default_config(config_path: Path) -> configparser.ConfigParser:
    """抽取默认配置生成逻辑，复用代码"""
    config = configparser.ConfigParser()
    config['DEFAULT'] = {
        'database_path': 'data/files.db',
        'log_level': 'INFO',
        'scan_threads': '4',
        'preview_before_action': 'True',
        'max_process_files': '0'
    }
    # 添加UI配置节
    config['ui'] = {
        'success_background': '#d4edda',
        'failure_background': '#f8d7da',
        'undone_background': '#fff3cd',
        'layout_type': 'default',
        'layout_direction': 'horizontal'
    }
    # 生成默认配置文件
    with open(config_path, 'w', encoding='utf-8') as f:
        config.write(f)
    os.makedirs('data', exist_ok=True)
    return config

def get_config_value(config, section: str, key: str, default: str = None) -> str:
    """获取配置项的值，如果不存在则返回默认值
    
    Args:
        config: 配置对象
        section: 配置节
        key: 配置键
        default: 默认值
        
    Returns:
        配置值或默认值
    """
    global _DEFAULT_UI_CONFIG
    
    if section in config and key in config[section]:
        return config[section][key]
    elif section == 'ui':
        # 延迟加载默认UI配置，避免重复生成
        if _DEFAULT_UI_CONFIG is None:
            _DEFAULT_UI_CONFIG = _generate_default_config(Path('dummy'))['ui']
        if key in _DEFAULT_UI_CONFIG:
            return _DEFAULT_UI_CONFIG[key]
    return default

def save_config_value(section: str, key: str, value: str) -> None:
    """保存配置项的值"""
    config_path = Path(__file__).parent.parent / 'config.ini'
    config = load_config()
    
    # 确保section存在
    if section not in config:
        config[section] = {}
    
    # 设置配置值
    config[section][key] = value
    
    # 保存配置文件
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            config.write(f)
    except Exception as e:
        logging.error(f"保存配置文件失败: {e}")
