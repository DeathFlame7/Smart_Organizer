import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget, QMessageBox
from PySide6.QtCore import Qt
from pathlib import Path

# 导入项目组件
sys.path.append(str(Path(__file__).parent))
from gui.preview_panel import PreviewPanel
from core.file_processor import FileProcessor
from core.classifier import FileClassifier

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("测试文件选择功能")
        self.resize(800, 600)
        
        # 创建主布局
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        self.setCentralWidget(central_widget)
        
        # 创建文件处理器和分类器
        self.file_processor = FileProcessor()
        self.file_classifier = FileClassifier()
        
        # 创建预览面板
        self.preview_panel = PreviewPanel(
            parent=self,
            file_processor=self.file_processor,
            file_classifier=self.file_classifier
        )
        main_layout.addWidget(self.preview_panel)
        
        # 创建测试按钮
        self.test_button = QPushButton("测试选择功能")
        self.test_button.clicked.connect(self.test_selection)
        main_layout.addWidget(self.test_button)
        
        # 生成测试数据
        self.generate_test_data()
    
    def generate_test_data(self):
        """生成测试数据"""
        test_results = []
        for i in range(5):
            test_results.append({
                'path': f'C:/test/file_{i}.txt',
                'new_name': f'processed_file_{i}.txt',
                'category': '文档',
                'confidence': 0.95,
                'type': 'txt',
                'size': 1024,
                'status': 'success'
            })
        
        # 显示测试数据
        self.preview_panel.show_preview(test_results)
    
    def test_selection(self):
        """测试文件选择功能"""
        # 获取选中的文件
        try:
            selected_files = getattr(self.preview_panel.core.table_operations, 'selected_files', {})
            has_selected = bool(selected_files)
            
            if has_selected:
                # 模拟处理选中的文件
                file_paths = list(selected_files.keys())
                QMessageBox.information(
                    self,
                    "选择测试",
                    f"成功获取到 {len(file_paths)} 个选中的文件:\n" + "\n".join(file_paths)
                )
            else:
                QMessageBox.information(
                    self,
                    "选择测试",
                    "没有选中任何文件"
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "错误",
                f"获取选中文件时出错: {str(e)}"
            )

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())