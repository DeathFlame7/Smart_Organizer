import sys
import sys
import logging
from pathlib import Path
from utils.application_config import load_config


def setup_logging():
    config = load_config()
    # 从配置文件获取日志级别
    log_level = config.get('DEFAULT', 'log_level', fallback='INFO')
    log_file = config.get('DEFAULT', 'log_file', fallback='smart_organizer.log')
    
    # 确保日志目录存在
    log_dir = Path(log_file).parent
    if log_dir != Path('.'):
        log_dir.mkdir(exist_ok=True)
    
    # 配置根日志记录器
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 降低第三方库的日志级别，减少调试信息
    third_party_loggers = [
        'chardet', 'PIL', 'PIL.PngImagePlugin', 'PIL.Image'
    ]
    for logger_name in third_party_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)
    
    logging.info(f"日志配置完成: 级别={log_level}, 文件={log_file}")
    return config
