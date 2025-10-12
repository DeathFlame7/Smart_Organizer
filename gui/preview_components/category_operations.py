from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton, QDialog, QTableWidgetItem
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QDialog
import logging
from pathlib import Path

class CategoryOperations:
    """分类操作管理类 - 负责文件分类的编辑和管理功能"""
    
    def __init__(self, preview_panel):
        self.preview_panel = preview_panel
    
    def edit_category(self, selected_files=None):
        """编辑选中文件的分类"""
        try:
            # 如果没有指定选中文件，使用表格当前选中的文件
            if selected_files is None:
                selected_files = self.preview_panel.table_operations.selected_files
            
            if not selected_files:
                logging.warning("没有选中任何文件")
                return
            
            # 获取当前所有唯一的分类
            categories = set()
            for result in self.preview_panel.current_results:
                category = result.get('category')
                if category and category != '未分类':
                    categories.add(category)
            
            # 创建分类编辑对话框
            dialog = CategoryEditDialog(sorted(categories))
            
            # 显示对话框并获取结果
            if dialog.exec() == QDialog.Accepted:
                new_category = dialog.get_selected_category()
                if not new_category:
                    return
                
                # 处理选中文件的分类更新
                self._update_file_categories(selected_files, new_category)
                
                # 刷新表格显示
                self.preview_panel.data_display.show_process_results(self.preview_panel.current_results)
                
                # 发送文件更新信号
                self.preview_panel.file_updated.emit(self.preview_panel.current_results, {'category': new_category})
                
        except Exception as e:
            logging.error(f"编辑分类时出错: {e}")
    
    def _update_file_categories(self, selected_files, new_category):
        """更新选中文件的分类信息"""
        try:
            # 更新原始结果中的分类
            for file_key in selected_files:
                # 查找对应的文件结果
                for result in self.preview_panel.original_results:
                    if self._get_file_identifier(result) == file_key:
                        # 更新分类
                        result['category'] = new_category
                        # 如果文件状态已处理，标记为已编辑
                        if result.get('status') == 'success':
                            result['status'] = 'edited'
                        break
            
            # 同时更新当前结果（可能是筛选后的）
            for file_key in selected_files:
                for result in self.preview_panel.current_results:
                    if self._get_file_identifier(result) == file_key:
                        result['category'] = new_category
                        if result.get('status') == 'success':
                            result['status'] = 'edited'
                        break
            
            # 更新自定义分类映射
            if not hasattr(self.preview_panel, 'custom_categories'):
                self.preview_panel.custom_categories = {}
                
            for file_key in selected_files:
                self.preview_panel.custom_categories[file_key] = new_category
                
            # 如果启用了学习功能，通知学习系统
            if hasattr(self.preview_panel, 'learning_system') and self.preview_panel.learning_system:
                self.preview_panel.learning_system.learn_file_category(
                    {file_key: new_category for file_key in selected_files}
                )
                
        except Exception as e:
            logging.error(f"更新文件分类时出错: {e}")
    
    def _get_file_identifier(self, result):
        """获取文件的唯一标识符"""
        # 尝试使用path或source_path作为唯一标识符
        return result.get('path') or result.get('source_path') or str(result.get('id', ''))
    
    def edit_row_properties(self, row):
        """编辑表格中单行的属性"""
        try:
            # 检查行索引是否有效
            if row < 0 or row >= len(self.preview_panel.current_results):
                logging.warning(f"无效的行索引: {row}")
                return
            
            # 获取当前行对应的文件结果
            result = self.preview_panel.current_results[row]
            file_key = self._get_file_identifier(result)
            
            # 创建属性编辑对话框
            dialog = PropertiesEditDialog(result)
            
            # 显示对话框并获取结果
            if dialog.exec() == dialog.Accepted:
                updated_properties = dialog.get_updated_properties()
                
                # 更新文件属性
                if 'category' in updated_properties:
                    # 只更新当前文件的分类
                    self._update_file_categories([file_key], updated_properties['category'])
                
                if 'new_name' in updated_properties:
                    new_name_value = updated_properties['new_name']
                    # 更新文件名
                    if not hasattr(self.preview_panel, 'custom_categories'):
                        self.preview_panel.custom_categories = {}
                    
                    self.preview_panel.custom_categories[f"{file_key}_name"] = new_name_value
                    
                    # 更新原始结果中的文件名
                    for original_result in self.preview_panel.original_results:
                        if self._get_file_identifier(original_result) == file_key:
                            original_result['new_name'] = new_name_value
                            if original_result.get('status') == 'success':
                                original_result['status'] = 'edited'
                            break
                    
                    # 更新当前结果中的文件名
                    result['new_name'] = new_name_value
                    if result.get('status') == 'success':
                        result['status'] = 'edited'
                
                # 刷新表格显示
                self.preview_panel.data_display.show_process_results(self.preview_panel.current_results)
                
                # 发送文件更新信号
                self.preview_panel.file_updated.emit(self.preview_panel.current_results, {'updated': True})
                
        except Exception as e:
            logging.error(f"编辑行属性时出错: {e}")
    
    def reset_categories(self, selected_files=None):
        """重置选中文件的分类为原始分类"""
        try:
            # 如果没有指定选中文件，使用表格当前选中的文件
            if selected_files is None:
                selected_files = self.preview_panel.table_operations.selected_files
            
            if not selected_files:
                logging.warning("没有选中任何文件")
                return
            
            # 重置分类
            for file_key in selected_files:
                # 从自定义分类映射中移除
                if hasattr(self.preview_panel, 'custom_categories') and file_key in self.preview_panel.custom_categories:
                    del self.preview_panel.custom_categories[file_key]
                
                # 同时移除文件名自定义
                name_key = f"{file_key}_name"
                if hasattr(self.preview_panel, 'custom_categories') and name_key in self.preview_panel.custom_categories:
                    del self.preview_panel.custom_categories[name_key]
                
                # 更新原始结果状态
                for result in self.preview_panel.original_results:
                    if self._get_file_identifier(result) == file_key:
                        if result.get('status') == 'edited':
                            result['status'] = 'success'
                        break
                
                # 更新当前结果状态
                for result in self.preview_panel.current_results:
                    if self._get_file_identifier(result) == file_key:
                        if result.get('status') == 'edited':
                            result['status'] = 'success'
                        break
            
            # 刷新表格显示
            self.preview_panel.data_display.show_process_results(self.preview_panel.current_results)
            
            # 发送文件更新信号
            self.preview_panel.file_updated.emit(self.preview_panel.current_results, {'reset': True})
            
        except Exception as e:
            logging.error(f"重置分类时出错: {e}")

class CategoryEditDialog(QDialog):
    """分类编辑对话框"""
    
    def __init__(self, existing_categories, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑分类")
        self.resize(300, 200)
        self.existing_categories = existing_categories
        self.current_category = ""
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        
        # 分类选择
        category_label = QLabel("选择或输入新分类:")
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        
        # 添加现有分类
        if self.existing_categories:
            self.category_combo.addItems(self.existing_categories)
        
        # 创建按钮区域
        buttons_layout = QHBoxLayout()
        self.apply_button = QPushButton("应用")
        self.cancel_button = QPushButton("取消")
        
        # 连接按钮信号
        self.apply_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        # 添加到布局
        buttons_layout.addWidget(self.apply_button)
        buttons_layout.addWidget(self.cancel_button)
        
        main_layout.addWidget(category_label)
        main_layout.addWidget(self.category_combo)
        main_layout.addLayout(buttons_layout)
    
    def get_selected_category(self):
        """获取选中的分类"""
        return self.category_combo.currentText().strip()

class PropertiesEditDialog(QDialog):
    """属性编辑对话框"""
    
    def __init__(self, file_result, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑文件属性")
        self.resize(350, 250)
        self.file_result = file_result
        self.updated_properties = {}
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        
        # 原文件名显示
        original_name_layout = QHBoxLayout()
        original_name_label = QLabel("原文件名:")
        self.original_name_value = QLabel(self.file_result.get('original_name', ''))
        self.original_name_value.setWordWrap(True)
        original_name_layout.addWidget(original_name_label)
        original_name_layout.addWidget(self.original_name_value, 1)
        
        # 新文件名输入
        new_name_layout = QHBoxLayout()
        new_name_label = QLabel("新文件名:")
        self.new_name_input = QLineEdit(self.file_result.get('original_name', ''))
        new_name_layout.addWidget(new_name_label)
        new_name_layout.addWidget(self.new_name_input, 1)
        
        # 分类选择
        category_layout = QHBoxLayout()
        category_label = QLabel("分类:")
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        
        # 设置当前分类
        current_category = self.file_result.get('category', '')
        if current_category:
            self.category_combo.addItem(current_category)
        
        category_layout.addWidget(category_label)
        category_layout.addWidget(self.category_combo, 1)
        
        # 显示文件路径
        path_layout = QHBoxLayout()
        path_label = QLabel("文件路径:")
        path_value = QLabel(self.file_result.get('path', '') or self.file_result.get('source_path', ''))
        path_value.setWordWrap(True)
        path_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        path_layout.addWidget(path_label)
        path_layout.addWidget(path_value, 1)
        
        # 创建按钮区域
        buttons_layout = QHBoxLayout()
        self.apply_button = QPushButton("应用")
        self.cancel_button = QPushButton("取消")
        
        # 连接按钮信号
        self.apply_button.clicked.connect(self.on_apply)
        self.cancel_button.clicked.connect(self.reject)
        
        # 添加到布局
        buttons_layout.addWidget(self.apply_button)
        buttons_layout.addWidget(self.cancel_button)
        
        # 将所有布局添加到主布局
        main_layout.addLayout(original_name_layout)
        main_layout.addLayout(new_name_layout)
        main_layout.addLayout(category_layout)
        main_layout.addLayout(path_layout)
        main_layout.addLayout(buttons_layout)
    
    def on_apply(self):
        """应用更新"""
        # 获取分类更新
        new_category = self.category_combo.currentText().strip()
        if new_category and new_category != self.file_result.get('category', ''):
            self.updated_properties['category'] = new_category
        
        # 获取文件名更新
        new_name = self.new_name_input.text().strip()
        if new_name and new_name != self.file_result.get('original_name', ''):
            self.updated_properties['new_name'] = new_name
        
        # 接受对话框
        self.accept()
    
    def get_updated_properties(self):
        """获取更新的属性"""
        return self.updated_properties.copy()