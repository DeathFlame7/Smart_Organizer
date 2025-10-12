import os
import configparser
from pathlib import Path

class ApplicationConfig:
    """应用程序配置管理类"""
    def __init__(self):
        # 默认配置文件路径
        self.config_dir = Path(os.path.expanduser("~")) / ".smart_organizer"
        self.config_file = self.config_dir / "config.ini"
        
        # 确保配置目录存在
        self.config_dir.mkdir(exist_ok=True)
        
        # 初始化配置解析器
        self.config = configparser.ConfigParser()
        
        # 加载配置
        self.load_config()
        
    def load_config(self):
        """加载配置文件"""
        # 如果配置文件不存在，创建默认配置
        if not self.config_file.exists():
            self._create_default_config()
        
        # 读取配置文件
        self.config.read(self.config_file)
        
    def _create_default_config(self):
        """创建默认配置文件"""
        # 默认配置
        self.config['DEFAULT'] = {
            'log_level': 'INFO',
            'log_file': 'smart_organizer.log',
            'preview_before_action': 'True',
            'auto_update': 'True',
            'max_recent_dirs': '5',
            'theme': 'light',
            'language': 'zh_CN',
            'database_path': 'data/files.db',
            'scan_threads': '4',
            'max_process_files': '0'
        }
        
        # UI配置
        self.config['ui'] = {
            'success_background': '#d4edda',  # 默认浅绿色
            'failure_background': '#f8d7da',  # 默认浅红色
            'undone_background': '#fff3cd',   # 默认浅黄色
            'border_radius': '5',
            'font_family': 'Microsoft YaHei',
            'font_size': '10',
            'table_row_height': '25',
            'header_height': '30',
            'preview_height': '400'
        }
        
        # 分类配置
        self.config['classification'] = {
            'enable_auto_classification': 'True',
            'min_confidence': '0.6',
            'unknown_category': '其他',
            'custom_categories': '合同,财务,项目,技术,报告,说明,新闻,文学,图片'
        }
        
        # 重命名配置
        self.config['renaming'] = {
            'enable_auto_renaming': 'True',
            'use_content_based_names': 'True',
            'include_timestamp': 'True',
            'timestamp_format': '%Y%m%d_%H%M%S',
            'max_name_length': '100'
        }
        
        # 数据库配置
        self.config['database'] = {
            'max_history_items': '1000',
            'backup_interval_days': '7',
            'auto_cleanup': 'True'
        }
        
        # 保存默认配置
        with open(self.config_file, 'w', encoding='utf-8') as f:
            self.config.write(f)
            
    def get(self, section, option, fallback=None, default=None):
        """获取配置值，支持fallback和default两种参数形式"""
        # 优先使用fallback参数，保持向后兼容性
        if fallback is not None:
            default = fallback
        
        try:
            return self.config.get(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default
            
    def getboolean(self, section, option, default=False, fallback=None):
        """获取布尔类型的配置值"""
        # 优先使用fallback参数，保持向后兼容性
        if fallback is not None:
            default = fallback
        
        try:
            return self.config.getboolean(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default
            
    def getint(self, section, option, default=0):
        """获取整数类型的配置值"""
        try:
            return self.config.getint(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default
            
    def getfloat(self, section, option, default=0.0):
        """获取浮点数类型的配置值"""
        try:
            return self.config.getfloat(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default
            
    def set(self, section, option, value):
        """设置配置值"""
        if section not in self.config:
            self.config[section] = {}
        
        self.config[section][option] = str(value)
        
        # 保存配置
        with open(self.config_file, 'w', encoding='utf-8') as f:
            self.config.write(f)
            
# 全局配置实例
_config_instance = None


def load_config():
    """加载全局配置"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ApplicationConfig()
    return _config_instance
    

def get_config_value(section, option, default=None):
    """获取配置值"""
    config = load_config()
    return config.get(section, option, default)
    

def set_config_value(section, option, value):
    """设置配置值"""
    config = load_config()
    config.set(section, option, value)
    

def reset_config():
    """重置配置到默认状态"""
    global _config_instance
    
    # 删除配置文件
    config = load_config()
    if config.config_file.exists():
        config.config_file.unlink()
    
    # 重新初始化配置实例
    _config_instance = None
    return load_config()