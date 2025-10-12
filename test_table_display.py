import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
from PySide6.QtCore import Qt
from pathlib import Path
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 添加项目路径到sys.path，确保能导入模块
sys.path.append('d:\\wai\\Project\\Python\\smart_organizer_1\\.venv')

# 导入需要的组件
from gui.preview_panel import PreviewPanel

class TestApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("表格显示测试")
        self.resize(1200, 800)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        layout = QVBoxLayout(central_widget)
        
        # 创建预览面板
        self.preview_panel = PreviewPanel(self)
        layout.addWidget(self.preview_panel)
        
        # 创建测试按钮
        test_button = QPushButton("加载测试数据")
        test_button.clicked.connect(self.load_test_data)
        layout.addWidget(test_button)
        
    def load_test_data(self):
        """加载测试数据到预览面板"""
        try:
            # 创建测试数据
            test_data = []
            
            # 生成50个测试文件数据，模拟大量数据场景
            for i in range(50):
                # 随机生成不同的状态和分类，测试不同的显示情况
                statuses = ['default', 'success', 'failed', 'undone']
                categories = ['文档', '图片', '视频', '音频', '压缩文件', '程序', '其他']
                
                # 确保包含中文文件名和路径
                file_name = f"测试文件_{i}.txt"
                if i % 5 == 0:
                    file_name = f"中文测试文件_{i}.docx"
                elif i % 5 == 1:
                    file_name = f"图片示例_{i}.jpg"
                elif i % 5 == 2:
                    file_name = f"视频测试_{i}.mp4"
                
                # 生成测试路径
                base_path = "D:\\测试数据\\分类测试\\" + categories[i % len(categories)]
                file_path = os.path.join(base_path, file_name)
                
                # 创建测试数据项
                test_item = {
                    'id': i,
                    'path': file_path,
                    'source_path': file_path,
                    'original_name': file_name,
                    'new_name': file_name,
                    'category': categories[i % len(categories)],
                    'confidence': round(0.5 + (i % 50) / 100, 2),
                    'type': file_name.split('.')[-1].lower(),
                    'size': 1024 * (i + 1),
                    'status': statuses[i % len(statuses)]
                }
                
                test_data.append(test_item)
            
            # 显示测试数据
            self.preview_panel.show_preview(test_data)
            logging.info(f"成功加载{len(test_data)}条测试数据")
            
            # 强制刷新表格以确保完全显示
            self.preview_panel.force_table_refresh()
            
        except Exception as e:
            logging.error(f"加载测试数据时出错: {e}")

if __name__ == "__main__":
    # 创建Qt应用程序
    app = QApplication(sys.argv)
    
    # 创建并显示测试窗口
    window = TestApp()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec())