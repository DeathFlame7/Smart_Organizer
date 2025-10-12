import sys
import logging
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QTableWidget, QTableWidgetItem
from PySide6.QtCore import Qt

# 设置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# 导入被测模块
sys.path.append('d:\\wai\\Project\\Python\\smart_organizer_1\\.venv')
from gui.preview_panel import PreviewPanel
from gui.preview_components.filter_operations import FilterDialog, FilterOperations

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("清除筛选功能测试")
        self.resize(1000, 700)
        
        # 创建主布局
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # 创建预览面板（用于模拟真实环境）
        self.preview_panel = PreviewPanel()
        
        # 生成测试数据
        self.test_data = self._generate_test_data()
        
        # 设置预览面板的测试数据
        self.preview_panel.core.original_results = self.test_data
        self.preview_panel.core.current_results = self.test_data
        self.preview_panel.core.filtered_results = self.test_data
        
        # 同时设置外层preview_panel的数据引用（用于调试）
        self.preview_panel.original_results = self.test_data
        self.preview_panel.current_results = self.test_data
        self.preview_panel.filtered_results = self.test_data
        
        # 刷新预览面板显示
        self.preview_panel.core.data_display.show_process_results(self.test_data)
        
        # 创建测试按钮
        self.test_dialog_clear_btn = QPushButton("测试筛选对话框中的清除筛选按钮")
        self.test_dialog_clear_btn.clicked.connect(self._test_dialog_clear_filter)
        
        self.test_panel_clear_btn = QPushButton("测试预览面板中的清除筛选按钮")
        self.test_panel_clear_btn.clicked.connect(self._test_panel_clear_filter)
        
        # 添加到布局
        main_layout.addWidget(self.test_dialog_clear_btn)
        main_layout.addWidget(self.test_panel_clear_btn)
        main_layout.addWidget(self.preview_panel)
        
        self.setCentralWidget(main_widget)
        
        # 记录测试结果
        logging.info("测试窗口已初始化")
        logging.info(f"生成了{len(self.test_data)}条测试数据")
    
    def _generate_test_data(self):
        """生成测试数据"""
        data = []
        categories = ["文档", "图片", "音频", "视频", "压缩包"]
        statuses = ["待处理", "成功", "失败", "已撤销"]
        
        for i in range(1, 21):
            item = {
                'id': i,
                'original_name': f"测试文件{i}.{['txt', 'jpg', 'mp3', 'mp4', 'zip'][i % 5]}",
                'category': categories[i % 5],
                'confidence': 0.8 + (i % 20) * 0.01,
                'path': f"D:\\测试路径\\文件夹{i % 5}\\测试文件{i}.{['txt', 'jpg', 'mp3', 'mp4', 'zip'][i % 5]}",
                'status': statuses[i % 4],
                'size': (i * 100) + 100  # KB
            }
            data.append(item)
        
        return data
    
    def _test_dialog_clear_filter(self):
        """测试筛选对话框中的清除筛选按钮"""
        try:
            # 先应用一些筛选条件
            logging.info("开始测试筛选对话框中的清除筛选功能")
            logging.info("1. 显示筛选对话框")
            
            # 创建筛选对话框
            filter_dialog = FilterDialog(self.preview_panel.core)
            
            # 手动设置一些筛选条件（模拟用户输入）
            logging.info("2. 设置筛选条件：分类=图片, 可信度>0.9, 文件类型=jpg")
            filter_dialog.category_combo.setCurrentText("图片")
            filter_dialog.min_confidence.setValue(0.9)
            filter_dialog.file_type_input.setText("jpg")
            
            # 连接信号以便观察
            filter_dialog.clear_filters.connect(self._on_dialog_clear_filters)
            
            # 记录设置的筛选条件
            logging.info(f"设置后的分类: {filter_dialog.category_combo.currentText()}")
            logging.info(f"设置后的最小可信度: {filter_dialog.min_confidence.value()}")
            logging.info(f"设置后的文件类型: {filter_dialog.file_type_input.text()}")
            
            # 显示对话框
            filter_dialog.exec()
            
        except Exception as e:
            logging.error(f"测试筛选对话框中的清除筛选功能失败: {e}")
    
    def _test_panel_clear_filter(self):
        """测试预览面板中的清除筛选按钮"""
        try:
            # 先应用一些筛选条件
            logging.info("开始测试预览面板中的清除筛选功能")
            
            # 模拟应用筛选
            filters = {
                'category': '文档',
                'min_confidence': 0.85,
                'file_type': 'txt'
            }
            
            # 应用筛选
            logging.info(f"应用筛选条件: {filters}")
            self.preview_panel.core.filter_operations.apply_filters(filters)
            
            # 延迟一下，让筛选生效
            QApplication.processEvents()
            
            # 点击清除筛选按钮
            logging.info("点击预览面板上的清除筛选按钮")
            self.preview_panel.clear_filter_btn.click()
            
            # 添加调试信息
            logging.info(f"清除筛选后core中的数据量: {len(self.preview_panel.core.current_results)}")
            logging.info(f"清除筛选后外层preview_panel的数据量: {len(self.preview_panel.current_results) if hasattr(self.preview_panel, 'current_results') else 'N/A'}")
            logging.info(f"原始数据量: {len(self.preview_panel.core.original_results)}")
            
            # 额外显示core的其他属性
            logging.info(f"core的类型: {self.preview_panel.core.__class__.__name__}")
            logging.info(f"core的filtered_results数量: {len(self.preview_panel.core.filtered_results)}")
            
            # 查看FilterOperations实例的引用
            logging.info(f"FilterOperations的preview_panel类型: {type(self.preview_panel.core.filter_operations.preview_panel).__name__}")
            
            # 检查是否恢复到原始数据
            if len(self.preview_panel.core.current_results) == len(self.preview_panel.core.original_results):
                logging.info("测试成功：预览面板中的清除筛选按钮功能正常工作！")
            else:
                logging.warning("测试失败：预览面板中的清除筛选按钮未能完全恢复原始数据！")
                
        except Exception as e:
            logging.error(f"测试预览面板中的清除筛选功能失败: {e}")
    
    def _on_dialog_clear_filters(self):
        """处理对话框发出的清除筛选信号"""
        logging.info("接收到对话框的清除筛选信号")
        logging.info("测试成功：筛选对话框中的清除筛选按钮功能正常工作！")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    
    # 添加一些提示信息到日志
    logging.info("测试说明:")
    logging.info("1. 点击'测试筛选对话框中的清除筛选按钮' - 将会打开筛选对话框，自动设置一些筛选条件，然后你需要手动点击'清除筛选'按钮")
    logging.info("2. 点击'测试预览面板中的清除筛选按钮' - 将自动测试预览面板上的清除筛选功能")
    logging.info("3. 观察日志输出，确认两个按钮的功能是否一致")
    
    sys.exit(app.exec())