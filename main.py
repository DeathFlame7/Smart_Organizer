import os
import sys
import logging

# Third-party imports
from PySide6.QtWidgets import QApplication

# Local imports
from gui.main_window import MainWindow
from gui.scrollbar_optimizer import scrollbar_optimizer
from utils.logger import setup_logging

# 主函数
def main():
    # 初始化日志
    config = setup_logging()
    logging.info("程序启动")
    
    # 创建Qt应用程序实例
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 应用滚动条优化
    logging.info("应用滚动条优化")
    scrollbar_optimizer.optimize_all_scrollbars()
    
    # 运行应用程序主循环
    logging.info("程序主循环启动")
    exit_code = app.exec()
    
    logging.info(f"程序退出，退出码: {exit_code}")
    sys.exit(exit_code)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.exception(f"程序发生未处理异常: {e}")
        print(f"程序发生未处理异常: {e}")
        sys.exit(1)
