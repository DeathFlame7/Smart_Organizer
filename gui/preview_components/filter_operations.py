from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton, QDialog, QCheckBox, QSpinBox, QDoubleSpinBox, QDateEdit
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QDoubleSpinBox, QSpinBox, QPushButton, QApplication
import logging
import datetime
from pathlib import Path

class FilterOperations:
    """筛选操作管理类 - 负责表格数据的筛选功能"""
    
    def __init__(self, preview_panel):
        # 直接使用传入的preview_panel实例作为数据容器
        # 根据测试代码，传入的应该是core实例
        self.preview_panel = preview_panel
        self.filters = {}
        
        # 添加调试信息
        import inspect
        module_name = inspect.getmodule(self.preview_panel).__name__
        logging.debug(f"FilterOperations初始化，使用的数据容器模块: {module_name}")
        logging.debug(f"数据容器类型: {self.preview_panel.__class__.__name__}")
        logging.debug(f"数据容器是否有original_results: {hasattr(self.preview_panel, 'original_results')}")
        logging.debug(f"数据容器的original_results数量: {len(self.preview_panel.original_results) if hasattr(self.preview_panel, 'original_results') else 'N/A'}")
    
    def show_filter_dialog(self):
        """显示筛选对话框"""
        try:
            # 创建筛选对话框
            filter_dialog = FilterDialog(self.preview_panel)
            
            # 如果之前有应用过筛选，设置初始值
            if hasattr(self, 'filters'):
                filter_dialog.set_initial_filters(self.filters)
            
            # 连接信号
            filter_dialog.apply_filters.connect(self.apply_filters)
            filter_dialog.clear_filters.connect(self.clear_filters)
            
            # 显示对话框
            filter_dialog.exec()
            
        except Exception as e:
            logging.error(f"显示筛选对话框失败: {e}")
    
    def apply_filters(self, filters=None):
        """应用筛选条件并更新表格显示"""
        try:
            logging.info("===== 开始执行apply_filters方法 =====")
            # 如果没有传入筛选条件，使用当前筛选条件
            if filters is not None:
                self.filters = filters
                logging.info(f"应用筛选条件: {filters}")
                logging.debug(f"应用筛选条件: {filters}")
            
            # 如果没有任何筛选条件，显示所有原始结果
            if not any(self.filters.values()):
                logging.info("没有任何筛选条件，调用clear_filters方法")
                self.clear_filters()
                logging.info("===== 完成执行apply_filters方法 =====")
                return
            
            # 1. 确定正确的数据容器（根据测试代码，传入的应该是core实例）
            data_container = self.preview_panel
            logging.info(f"在apply_filters中使用数据容器: {data_container.__class__.__name__}")
            logging.info(f"数据容器ID: {id(data_container)}")
            
            # 2. 获取原始数据
            original_results = data_container.original_results
            logging.info(f"应用筛选前的原始数据数量: {len(original_results)}")
            
            # 3. 应用筛选
            filtered_results = []
            
            for result in original_results:
                if self._filter_result(result, self.filters):
                    filtered_results.append(result)
            
            logging.info(f"应用筛选后的结果数量: {len(filtered_results)}")
            
            # 4. 更新数据引用
            data_container.current_results = filtered_results
            data_container.filtered_results = filtered_results
            logging.info(f"数据已更新，current_results数量: {len(data_container.current_results)}, filtered_results数量: {len(data_container.filtered_results)}")
            
            # 5. 刷新表格显示
            if hasattr(data_container, 'data_display'):
                data_container.data_display.show_process_results(filtered_results)
                logging.info(f"数据显示已刷新")
            
            # 6. 发送结果更新信号
            if hasattr(data_container, 'results_updated'):
                data_container.results_updated.emit(filtered_results)
                logging.info(f"已发送结果更新信号")
            
            # 7. 启用清除筛选按钮（重要：修复按钮始终禁用的问题）
            # 从preview_panel的父对象中找到clear_filter_btn
            # 根据preview_panel.py的代码，clear_filter_btn是preview_panel的属性，而不是core的属性
            if hasattr(self.preview_panel, 'parent') and hasattr(self.preview_panel.parent(), 'clear_filter_btn'):
                self.preview_panel.parent().clear_filter_btn.setEnabled(True)
                logging.info("已启用清除筛选按钮")
            else:
                logging.info("无法找到clear_filter_btn按钮，可能需要通过其他方式启用")
            
            logging.info("===== 完成执行apply_filters方法 =====")
        except Exception as e:
            logging.error(f"应用筛选条件失败: {e}")
            logging.exception("详细错误信息:")
            
    def _get_data_container(self):
        """获取正确的数据容器"""
        # 从测试文件看，实际的数据存储在preview_panel自身
        return self.preview_panel
    
    def _ensure_data_consistency(self, data_container):
        """确保数据一致性"""
        try:
            # 获取原始数据
            original_results = data_container.original_results
            logging.debug(f"在_ensure_data_consistency中获取的原始数据数量: {len(original_results)}")
            
            # 确保original_results是一个列表
            if not isinstance(original_results, list):
                original_results = list(original_results)
                logging.debug(f"转换原始数据为列表")
            
            # 更新数据容器的数据引用
            data_container.current_results = original_results
            data_container.filtered_results = original_results
            logging.debug(f"更新了数据容器的数据，数量: {len(original_results)}")
            
            return original_results
        except Exception as e:
            logging.error(f"确保数据一致性失败: {e}")
            return data_container.original_results
    
    def _filter_result(self, result, filters):
        """根据筛选条件过滤单个结果"""
        # 分类筛选
        if filters.get('category') and result.get('category') != filters.get('category'):
            return False
        
        # 可信度筛选
        min_confidence = filters.get('min_confidence', 0.0)
        max_confidence = filters.get('max_confidence', 1.0)
        if result.get('confidence', 0.0) < min_confidence or result.get('confidence', 0.0) > max_confidence:
            return False
        
        # 文件类型筛选
        file_type = filters.get('file_type', '').lower()
        if file_type:
            # 从original_name中提取文件扩展名（测试数据中没有type字段）
            original_name = str(result.get('original_name', '')).lower()
            # 检查扩展名是否包含在原始文件名中
            if not any(original_name.endswith(f'.{ext}') for ext in file_type.split(',')):
                return False
        
        # 文件名筛选
        file_name = filters.get('file_name', '').lower()
        if file_name and file_name not in str(result.get('original_name', '')).lower():
            return False
        
        # 文件大小筛选
        min_size = filters.get('min_size', 0)
        max_size = filters.get('max_size', float('inf'))
        if result.get('size', 0) < min_size or result.get('size', 0) > max_size:
            return False
        
        # 文件状态筛选
        status = filters.get('status', '')
        if status and status != result.get('status', 'default'):
            return False
        
        # 路径筛选
        path = filters.get('path', '').lower()
        if path:
            file_path = result.get('path', '') or result.get('source_path', '')
            if path not in str(file_path).lower():
                return False
        
        return True
    
    def clear_filters(self):
        """清除所有筛选条件"""
        try:
            # 添加不依赖于logging配置的输出，以确认方法是否被调用
            print("===== CLEAR_FILTERS METHOD CALLED =====")
            
            # 写入临时文件，以确认方法被调用
            with open('clear_filters_called.txt', 'a') as f:
                f.write(f"{datetime.datetime.now()} - clear_filters called with preview_panel ID: {id(self.preview_panel)}\n")
            
            logging.info("===== 开始执行clear_filters方法 =====")
            
            # 重置筛选条件
            self.filters = {}
            logging.info("已重置筛选条件")
            
            # 1. 直接使用self.preview_panel作为数据容器
            # 根据测试代码，这应该是core实例
            data_container = self.preview_panel
            logging.info(f"在clear_filters中使用数据容器: {data_container.__class__.__name__}")
            logging.info(f"数据容器ID: {id(data_container)}")
            
            # 2. 添加详细的日志信息
            logging.info(f"数据容器的original_results数量: {len(data_container.original_results)}")
            logging.info(f"数据容器的current_results数量: {len(data_container.current_results)}")
            logging.info(f"数据容器的filtered_results数量: {len(data_container.filtered_results)}")
            
            # 3. 直接获取原始数据并更新数据引用
            original_results = data_container.original_results
            
            # 强制创建一个新的列表引用，以确保更新生效
            data_container.current_results = list(original_results)
            data_container.filtered_results = list(original_results)
            
            # 再次检查更新后的数量
            logging.info(f"更新后的数据容器的current_results数量: {len(data_container.current_results)}")
            logging.info(f"更新后的数据容器的filtered_results数量: {len(data_container.filtered_results)}")
            
            # 4. 刷新表格显示
            if hasattr(data_container, 'data_display'):
                data_container.data_display.show_process_results(data_container.current_results)
                logging.info(f"数据显示已刷新")
            
            # 5. 发送结果更新信号
            if hasattr(data_container, 'results_updated'):
                data_container.results_updated.emit(data_container.current_results)
                logging.debug(f"已发送结果更新信号")
            
        except Exception as e:
            logging.error(f"清除筛选条件失败: {e}")
            logging.exception("详细错误信息:")
    
    def get_current_filters(self):
        """获取当前应用的筛选条件"""
        return self.filters.copy()
    
    def has_active_filters(self):
        """检查是否有活动的筛选条件"""
        return any(self.filters.values())

class FilterDialog(QDialog):
    """筛选对话框"""
    # 定义信号
    apply_filters = Signal(dict)
    clear_filters = Signal()
    
    def __init__(self, preview_panel, parent=None):
        super().__init__(parent)
        self.preview_panel = preview_panel
        self.setWindowTitle("筛选文件")
        self.resize(500, 400)
        self.init_ui()
        
    def init_ui(self):
        """初始化筛选对话框UI"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        
        # 创建筛选条件区域
        filters_layout = QVBoxLayout()
        
        # 分类筛选
        category_layout = QHBoxLayout()
        category_label = QLabel("分类:")
        self.category_combo = QComboBox()
        
        # 获取所有分类
        categories = self._get_all_categories()
        self.category_combo.addItem("全部")
        self.category_combo.addItems(categories)
        
        category_layout.addWidget(category_label)
        category_layout.addWidget(self.category_combo)
        filters_layout.addLayout(category_layout)
        
        # 可信度筛选
        confidence_layout = QHBoxLayout()
        confidence_label = QLabel("可信度范围:")
        self.min_confidence = QDoubleSpinBox()
        self.min_confidence.setRange(0.0, 1.0)
        self.min_confidence.setSingleStep(0.05)
        self.max_confidence = QDoubleSpinBox()
        self.max_confidence.setRange(0.0, 1.0)
        self.max_confidence.setSingleStep(0.05)
        self.max_confidence.setValue(1.0)
        confidence_layout.addWidget(confidence_label)
        confidence_layout.addWidget(self.min_confidence)
        confidence_layout.addWidget(QLabel("-", alignment=Qt.AlignCenter))
        confidence_layout.addWidget(self.max_confidence)
        filters_layout.addLayout(confidence_layout)
        
        # 文件类型筛选
        type_layout = QHBoxLayout()
        type_label = QLabel("文件类型:")
        self.file_type_input = QLineEdit(placeholderText="输入文件类型")
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.file_type_input)
        filters_layout.addLayout(type_layout)
        
        # 文件名字段筛选
        name_layout = QHBoxLayout()
        name_label = QLabel("文件名包含:")
        self.file_name_input = QLineEdit(placeholderText="输入文件名关键字")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.file_name_input)
        filters_layout.addLayout(name_layout)
        
        # 文件大小筛选
        size_layout = QHBoxLayout()
        size_label = QLabel("文件大小范围 (KB):")
        self.min_size = QSpinBox()
        self.min_size.setRange(0, 9999999)
        self.min_size.setSingleStep(1)
        self.max_size = QSpinBox()
        self.max_size.setRange(0, 9999999)
        self.max_size.setSingleStep(1)
        self.max_size.setValue(9999999)
        size_layout.addWidget(size_label)
        size_layout.addWidget(self.min_size)
        size_layout.addWidget(QLabel("-", alignment=Qt.AlignCenter))
        size_layout.addWidget(self.max_size)
        filters_layout.addLayout(size_layout)
        
        # 文件状态筛选
        status_layout = QHBoxLayout()
        status_label = QLabel("文件状态:")
        self.status_combo = QComboBox()
        self.status_combo.addItem("全部")
        self.status_combo.addItems(["待处理", "成功", "失败", "已撤销"])
        status_layout.addWidget(status_label)
        status_layout.addWidget(self.status_combo)
        filters_layout.addLayout(status_layout)
        
        # 路径筛选
        path_layout = QHBoxLayout()
        path_label = QLabel("路径包含:")
        self.path_input = QLineEdit(placeholderText="输入路径关键字")
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.path_input)
        filters_layout.addLayout(path_layout)
        
        # 添加筛选条件区域到主布局
        main_layout.addLayout(filters_layout)
        
        # 创建按钮区域
        buttons_layout = QHBoxLayout()
        self.apply_button = QPushButton("应用筛选")
        self.clear_button = QPushButton("清除筛选")
        self.cancel_button = QPushButton("取消")
        
        # 连接按钮信号
        self.apply_button.clicked.connect(self.on_apply_filters)
        self.clear_button.clicked.connect(self.on_clear_filters)
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.apply_button)
        buttons_layout.addWidget(self.clear_button)
        buttons_layout.addWidget(self.cancel_button)
        
        # 添加按钮区域到主布局
        main_layout.addLayout(buttons_layout)
    
    def _get_all_categories(self):
        """获取所有唯一的分类"""
        categories = set()
        for result in self.preview_panel.original_results:
            category = result.get('category')
            if category and category != '未分类':
                categories.add(category)
        return sorted(categories)
    
    def set_initial_filters(self, filters):
        """设置初始筛选条件"""
        # 设置分类筛选
        if filters.get('category') and self.category_combo.findText(filters['category']) >= 0:
            self.category_combo.setCurrentText(filters['category'])
        
        # 设置可信度筛选
        if 'min_confidence' in filters:
            self.min_confidence.setValue(filters['min_confidence'])
        if 'max_confidence' in filters:
            self.max_confidence.setValue(filters['max_confidence'])
        
        # 设置文件类型筛选
        if filters.get('file_type'):
            self.file_type_input.setText(filters['file_type'])
        
        # 设置文件名筛选
        if filters.get('file_name'):
            self.file_name_input.setText(filters['file_name'])
        
        # 设置文件大小筛选 (转换为KB)
        if 'min_size' in filters:
            # 防止整数溢出，确保值在合理范围内
            min_size_kb = min(int(filters['min_size'] / 1024), 9999999)
            self.min_size.setValue(max(0, min_size_kb))
        if 'max_size' in filters:
            # 防止整数溢出，确保值在合理范围内
            max_size_kb = min(int(filters['max_size'] / 1024), 9999999)
            self.max_size.setValue(max(0, max_size_kb))
        
        # 设置文件状态筛选
        status_map = {
            'default': "待处理",
            'success': "成功",
            'failed': "失败",
            'undone': "已撤销"
        }
        if filters.get('status') and status_map.get(filters['status']):
            status_text = status_map[filters['status']]
            if self.status_combo.findText(status_text) >= 0:
                self.status_combo.setCurrentText(status_text)
        
        # 设置路径筛选
        if filters.get('path'):
            self.path_input.setText(filters['path'])
    
    def on_apply_filters(self):
        """应用筛选条件"""
        # 构建筛选条件字典
        filters = {}
        
        # 获取分类筛选
        category = self.category_combo.currentText()
        if category and category != "全部":
            filters['category'] = category
        
        # 获取可信度筛选
        filters['min_confidence'] = self.min_confidence.value()
        filters['max_confidence'] = self.max_confidence.value()
        
        # 获取文件类型筛选
        file_type = self.file_type_input.text().strip()
        if file_type:
            filters['file_type'] = file_type
        
        # 获取文件名筛选
        file_name = self.file_name_input.text().strip()
        if file_name:
            filters['file_name'] = file_name
        
        # 获取文件大小筛选 (转换为字节)
        filters['min_size'] = self.min_size.value() * 1024
        filters['max_size'] = self.max_size.value() * 1024
        
        # 获取文件状态筛选
        status_text = self.status_combo.currentText()
        if status_text and status_text != "全部":
            status_map = {
                "待处理": 'default',
                "成功": 'success',
                "失败": 'failed',
                "已撤销": 'undone'
            }
            if status_text in status_map:
                filters['status'] = status_map[status_text]
        
        # 获取路径筛选
        path = self.path_input.text().strip()
        if path:
            filters['path'] = path
        
        # 发出应用筛选信号
        self.apply_filters.emit(filters)
        
        # 关闭对话框
        self.accept()
    
    def on_clear_filters(self):
        """清除所有筛选条件"""
        # 清除对话框界面上的所有筛选条件
        self.category_combo.setCurrentText("全部")
        self.min_confidence.setValue(0.0)
        self.max_confidence.setValue(1.0)
        self.file_type_input.clear()
        self.file_name_input.clear()
        self.min_size.setValue(0)
        self.max_size.setValue(9999999)
        self.status_combo.setCurrentText("全部")
        self.path_input.clear()
        
        # 发出清除筛选信号
        self.clear_filters.emit()
        
        # 关闭对话框
        self.accept()