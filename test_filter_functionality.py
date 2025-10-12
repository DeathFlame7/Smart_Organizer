import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QTableWidget
from PySide6.QtCore import Qt
import logging
import random
from pathlib import Path

# 设置日志级别
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gui.preview_components.preview_panel_core import PreviewPanel
from gui.preview_panel import PreviewPanel as PreviewPanelWidget

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("筛选功能测试")
        self.resize(1200, 800)
        
        # 创建主布局
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # 创建预览面板
        self.preview_panel = PreviewPanelWidget(parent=self)
        main_layout.addWidget(self.preview_panel)
        
        # 创建测试按钮
        test_layout = QVBoxLayout()
        
        self.test_filter_btn = QPushButton("测试筛选对话框")
        self.test_filter_btn.clicked.connect(self.test_filter_dialog)
        test_layout.addWidget(self.test_filter_btn)
        
        self.test_clear_filter_btn = QPushButton("测试清除筛选")
        self.test_clear_filter_btn.clicked.connect(self.test_clear_filter)
        test_layout.addWidget(self.test_clear_filter_btn)
        
        self.test_multiple_filter_btn = QPushButton("测试多次打开筛选对话框")
        self.test_multiple_filter_btn.clicked.connect(self.test_multiple_filter_dialogs)
        test_layout.addWidget(self.test_multiple_filter_btn)
        
        main_layout.addLayout(test_layout)
        
        self.setCentralWidget(main_widget)
        
        # 生成测试数据
        self.generate_test_data()
        
    def generate_test_data(self):
        """生成测试数据"""
        categories = ["文档", "图片", "视频", "音频", "压缩文件", "程序"]
        statuses = ['default', 'success', 'failed', 'undone']
        
        test_data = []
        for i in range(50):
            file_name = f"test_file_{i}.{random.choice(['txt', 'pdf', 'jpg', 'mp4', 'mp3', 'zip', 'exe'])}"
            category = random.choice(categories)
            confidence = round(random.uniform(0.5, 1.0), 2)
            size = random.randint(1024, 1048576)
            status = random.choice(statuses)
            
            result = {
                'original_name': file_name,
                'new_name': file_name,
                'category': category,
                'confidence': confidence,
                'path': f"D:\\test\\{category}\\{file_name}",
                'type': file_name.split('.')[-1],
                'size': size,
                'status': status,
                'id': i
            }
            test_data.append(result)
        
        # 显示测试数据
        self.preview_panel.core.show_preview(test_data)
        
    def test_filter_dialog(self):
        """测试筛选对话框"""
        try:
            logging.info("测试筛选对话框")
            self.preview_panel.show_filter_dialog()
            logging.info("筛选对话框已关闭")
        except Exception as e:
            logging.error(f"测试筛选对话框失败: {e}")
    
    def test_clear_filter(self):
        """测试清除筛选"""
        try:
            logging.info("测试清除筛选")
            self.preview_panel.clear_filters()
            logging.info("清除筛选成功")
        except Exception as e:
            logging.error(f"测试清除筛选失败: {e}")
    
    def test_multiple_filter_dialogs(self):
        """测试多次打开筛选对话框"""
        try:
            logging.info("测试多次打开筛选对话框")
            # 第一次打开筛选对话框
            self.preview_panel.show_filter_dialog()
            logging.info("第一次筛选对话框已关闭")
            
            # 第二次打开筛选对话框
            self.preview_panel.show_filter_dialog()
            logging.info("第二次筛选对话框已关闭")
            
            # 第三次打开筛选对话框
            self.preview_panel.show_filter_dialog()
            logging.info("第三次筛选对话框已关闭")
            
            logging.info("多次打开筛选对话框测试成功")
        except Exception as e:
            logging.error(f"测试多次打开筛选对话框失败: {e}")

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 创建应用程序
    app = QApplication(sys.argv)
    
    # 创建测试窗口
    window = TestWindow()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec())