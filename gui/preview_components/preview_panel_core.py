from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QApplication
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import QHeaderView, QTableWidget, QApplication, QWidget, QVBoxLayout
import logging
import os
from pathlib import Path

from gui.preview_components.table_operations import TableOperations
from gui.preview_components.data_display import DataDisplay
from gui.preview_components.filter_operations import FilterOperations
from gui.preview_components.category_operations import CategoryOperations

class PreviewPanel(QWidget):
    """预览面板的核心组件，负责整合其他功能组件并处理用户交互事件"""
    # 定义信号
    file_updated = Signal(list, dict)
    process_single_file = Signal(dict)
    process_selected_files = Signal(list)
    results_updated = Signal(list)

    def __init__(self, parent=None, file_processor=None, file_classifier=None, config_manager=None):
        super().__init__(parent)
        self.file_processor = file_processor
        self.file_classifier = file_classifier
        self.config_manager = config_manager
        
        # 存储数据
        self.original_results = []
        self.current_results = []
        self.filtered_results = []
        self.selected_files = set()
        self.custom_categories = {}
        self.filters = {}
        
        # 跟踪信号连接状态
        self._signals_blocked = False
        
        # 存储原始列宽设置，用于优化刷新
        self.original_column_widths = []
        
        # 初始化UI和各组件
        self.init_ui()
        self.init_components()
    
    def init_ui(self):
        """初始化预览面板UI，创建布局和工具栏"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        
        # 创建表格
        self.table = QTableWidget(0, 9)  # 9列
        self.table.setHorizontalHeaderLabels(["选择", "原文件名", "新文件名", "分类", "可信度", "路径", "类型", "大小", "状态"])
        
        # 设置表格属性
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)  # 默认不可编辑
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)  # 启用排序
        self.table.horizontalHeader().setSectionsMovable(True)  # 表头可移动
        self.table.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        
        # 设置表格水平滚动条策略
        self.table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        
        # 安装事件过滤器
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        self.table.cellClicked.connect(self.on_cell_clicked)
        self.table.horizontalHeader().sectionDoubleClicked.connect(self.on_header_double_clicked)
        self.table.horizontalHeader().customContextMenuRequested.connect(self.show_header_menu)
        self.table.customContextMenuRequested.connect(self.show_cell_menu)
        
        # 添加表格到布局
        main_layout.addWidget(self.table)
        
        # 保存原始列宽
        self.save_original_column_widths()
    
    def save_original_column_widths(self):
        """保存表格的原始列宽设置"""
        for i in range(self.table.columnCount()):
            self.original_column_widths.append(self.table.columnWidth(i))
    
    def init_components(self):
        """初始化各个功能组件"""
        # 表格操作组件
        self.table_operations = TableOperations(self)
        
        # 数据显示组件
        self.data_display = DataDisplay(self)
        
        # 筛选操作组件
        self.filter_operations = FilterOperations(self)
        
        # 分类操作组件
        self.category_operations = CategoryOperations(self)
        
    def block_signals(self, block):
        """统一管理信号阻塞状态"""
        if block != self._signals_blocked:
            self._signals_blocked = block
            self.table.blockSignals(block)
    
    def select_all_files(self):
        """选择所有文件"""
        self.table_operations.select_all_files()
        
    def deselect_all_files(self):
        """取消选择所有文件"""
        self.table_operations.deselect_all_files()
        
    def update_select_all_checkbox_state(self, total_files, selected_count):
        """更新全选复选框状态"""
        # 此方法在PreviewPanel类中实现，由table_operations调用
        pass
    
    def on_cell_double_clicked(self, row, column):
        """处理单元格双击事件"""
        if row < len(self.current_results):
            result = self.current_results[row]
            
            # 双击原文件名打开文件
            if column == 1:  # 原文件名列
                file_path = result.get('path') or result.get('source_path')
                if file_path and Path(file_path).exists():
                    # 使用Python内置的方法打开文件
                    import os
                    os.startfile(file_path)
            
            # 双击新文件名编辑名称
            elif column == 2:  # 新文件名列
                self.edit_new_filename(row)
            
            # 双击分类列编辑分类
            elif column == 3:  # 分类列
                # 获取该行的文件标识符
                file_key = result.get('path') or result.get('source_path') or str(result.get('id', ''))
                self.category_operations.edit_category([file_key])
            
            # 双击可信度编辑数值
            elif column == 4:  # 可信度列
                self.edit_confidence(row)
            
            # 双击路径列打开文件夹或修改路径
            elif column == 5:  # 路径列
                self.handle_path_double_click(row)
            
            # 双击状态列修改状态
            elif column == 8:  # 状态列
                self.edit_status(row)
                
    def edit_new_filename(self, row):
        """编辑新文件名"""
        if row < len(self.current_results):
            result = self.current_results[row]
            current_name = result.get('new_name', result.get('new_filename', result.get('original_name', '未知文件名')))
            
            from PySide6.QtWidgets import QInputDialog
            new_name, ok = QInputDialog.getText(self, "编辑新文件名", "请输入新的文件名:", text=current_name)
            
            if ok and new_name:
                # 保存当前排序状态
                was_sorting_enabled = self.table.isSortingEnabled()
                
                try:
                    # 临时禁用排序以防止行位置变化
                    if was_sorting_enabled:
                        self.table.setSortingEnabled(False)
                    
                    # 获取文件唯一标识符
                    file_key = result.get('path') or result.get('source_path') or str(result.get('id', ''))
                    
                    # 更新当前结果数据
                    result['new_name'] = new_name
                    
                    # 更新原始结果中的数据，确保处理时使用最新文件名
                    if hasattr(self, 'original_results'):
                        for original_result in self.original_results:
                            original_key = original_result.get('path') or original_result.get('source_path') or str(original_result.get('id', ''))
                            if original_key == file_key:
                                original_result['new_name'] = new_name
                                break
                    
                    # 确保custom_categories中存储文件名修改
                    if not hasattr(self, 'custom_categories'):
                        self.custom_categories = {}
                    self.custom_categories[f"{file_key}_name"] = new_name
                    
                    # 更新表格显示
                    self.data_display._set_row_data(row, result)
                    
                    # 发出文件更新信号
                    self.file_updated.emit([row], result)
                finally:
                    # 恢复排序状态
                    if was_sorting_enabled:
                        self.table.setSortingEnabled(True)
                        # 强制表格更新而不重新排序
                        QApplication.processEvents()
    
    def edit_confidence(self, row):
        """编辑可信度数值"""
        if row < len(self.current_results):
            result = self.current_results[row]
            current_confidence = result.get('confidence', 0.0)
            
            from PySide6.QtWidgets import QInputDialog
            new_confidence, ok = QInputDialog.getDouble(self, "编辑可信度", "请输入可信度 (0-1):", 
                                                       value=current_confidence, minValue=0.0, maxValue=1.0, decimals=2)
            
            if ok:
                # 更新结果数据
                result['confidence'] = new_confidence
                
                # 更新表格显示
                self.data_display._set_row_data(row, result)
                
                # 发出文件更新信号
                self.file_updated.emit([row], result)
    
    def handle_path_double_click(self, row):
        """处理路径列的双击事件"""
        if row < len(self.current_results):
            result = self.current_results[row]
            file_path = result.get('path') or result.get('source_path')
            
            if file_path and Path(file_path).exists():
                # 选择操作：打开文件夹或修改目标路径
                from PySide6.QtWidgets import QMessageBox
                response = QMessageBox.question(self, "选择操作", 
                                              "请选择操作:\n1. 打开文件所在文件夹\n2. 修改目标路径", 
                                              QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
                
                if response == QMessageBox.Yes:
                    # 打开文件所在文件夹
                    import os
                    directory = os.path.dirname(file_path)
                    os.startfile(directory)
                elif response == QMessageBox.No:
                    # 修改目标路径
                    self.edit_target_path(row)
    
    def edit_target_path(self, row):
        """修改文件整理后的目标路径"""
        if row < len(self.current_results):
            result = self.current_results[row]
            current_target = result.get('target_path', '')
            
            from PySide6.QtWidgets import QFileDialog
            # 获取原文件所在目录作为默认路径
            default_dir = os.path.dirname(result.get('path') or result.get('source_path', '')) if current_target else ''
            
            # 打开文件夹选择对话框
            target_dir = QFileDialog.getExistingDirectory(self, "选择目标文件夹", default_dir)
            
            if target_dir:
                # 构建完整的目标路径
                file_name = result.get('new_name', result.get('new_filename', result.get('original_name', '未知文件名')))
                new_target_path = os.path.join(target_dir, file_name)
                
                # 更新结果数据
                result['target_path'] = new_target_path
                
                # 更新表格显示
                self.data_display._set_row_data(row, result)
                
                # 发出文件更新信号
                self.file_updated.emit([row], result)
    
    def edit_status(self, row):
        """编辑文件状态"""
        if row < len(self.current_results):
            result = self.current_results[row]
            current_status = result.get('status', 'default')
            
            from PySide6.QtWidgets import QComboBox, QDialog, QVBoxLayout, QPushButton, QLabel, QHBoxLayout
            
            # 创建状态编辑对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("编辑文件状态")
            layout = QVBoxLayout(dialog)
            
            layout.addWidget(QLabel("请选择文件状态:"))
            
            # 创建状态下拉框
            status_combo = QComboBox()
            status_combo.addItems(["待处理", "成功", "失败", "已撤销"])
            
            # 设置当前状态
            status_text_map = {'default': '待处理', 'success': '成功', 'failed': '失败', 'undone': '已撤销'}
            current_status_text = status_text_map.get(current_status, '待处理')
            status_combo.setCurrentText(current_status_text)
            
            layout.addWidget(status_combo)
            
            # 创建按钮布局
            button_layout = QHBoxLayout()
            ok_button = QPushButton("确定")
            cancel_button = QPushButton("取消")
            
            ok_button.clicked.connect(dialog.accept)
            cancel_button.clicked.connect(dialog.reject)
            
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)
            
            # 显示对话框
            if dialog.exec():  # 如果用户点击了确定
                # 获取选择的状态
                selected_status_text = status_combo.currentText()
                
                # 映射回内部状态值
                reverse_status_map = {'待处理': 'default', '成功': 'success', '失败': 'failed', '已撤销': 'undone'}
                new_status = reverse_status_map.get(selected_status_text, 'default')
                
                # 更新结果数据
                result['status'] = new_status
                
                # 更新表格显示
                self.data_display._set_row_data(row, result)
                
                # 发出文件更新信号
                self.file_updated.emit([row], result)
    
    def on_cell_clicked(self, row, column):
        """处理单元格单击事件"""
        if column == 0 and row < self.table.rowCount():
            # 点击选择列
            self.toggle_file_selection(row)
    
    def toggle_file_selection(self, row):
        """切换文件选择状态"""
        # 使用正确的方法名toggle_row_selection
        self.table_operations.toggle_row_selection(row)
    
    def show_cell_menu(self, position):
        """显示单元格右键菜单"""
        # 由于TableOperations没有show_cell_menu方法，这里实现简单的右键菜单
        try:
            index = self.table.indexAt(position)
            if index.isValid():
                # 可以在这里实现简单的右键菜单功能
                pass
        except Exception as e:
            logging.error(f"显示单元格右键菜单失败: {e}")
    
    def show_header_menu(self, position):
        """显示表头右键菜单"""
        # 由于TableOperations没有show_header_menu方法，这里实现简单的右键菜单
        try:
            # 可以在这里实现简单的表头右键菜单功能
            pass
        except Exception as e:
            logging.error(f"显示表头右键菜单失败: {e}")
    
    def on_header_double_clicked(self, logical_index):
        """表头双击事件处理"""
        # 由于TableOperations没有on_header_double_clicked方法，这里实现双击表头的功能
        try:
            # 可以在这里实现双击表头的功能，例如自动调整列宽
            self.table.horizontalHeader().setSectionResizeMode(logical_index, QHeaderView.Interactive)
            self.table.resizeColumnToContents(logical_index)
        except Exception as e:
            logging.error(f"处理表头双击事件失败: {e}")
    
    def process_selected(self):
        """处理选中的文件"""
        # 使用正确的方法名get_selected_results
        selected_files = self.table_operations.get_selected_results()
        if selected_files:
            self.process_selected_files.emit(selected_files)
    
    def process_file(self, row):
        """处理单个文件"""
        if row < len(self.current_results):
            file_info = self.current_results[row]
            self.process_single_file.emit(file_info)
    
    def _simplify_path(self, path):
        """简化文件路径显示"""
        import os
        parts = path.split(os.sep)
        if len(parts) > 3:
            return os.path.join('...', parts[-3], parts[-2], parts[-1])
        return path
    
    def show_classification_results(self, results):
        """显示分类结果"""
        self.block_signals(True)
        try:
            self.original_results = results
            self.current_results = results.copy()
            self.filtered_results = results.copy()
            self.data_display.show_classification_results(results)
        finally:
            self.block_signals(False)
            # 强制刷新以确保表格完全显示
            self._force_complete_refresh()
    
    def show_process_results(self, results):
        """显示处理结果"""
        self.block_signals(True)
        try:
            # 保存原始结果和当前结果
            self.original_results = results
            self.current_results = results.copy()
            self.filtered_results = results.copy()
            
            # 调用data_display的show_process_results方法
            self.data_display.show_process_results(results)
            
            # 发出结果更新信号
            self.results_updated.emit(results)
        finally:
            self.block_signals(False)
            # 强制刷新以确保表格完全显示
            self._force_complete_refresh()
    
    def show_preview(self, results):
        """显示扫描结果预览"""
        self.block_signals(True)
        try:
            # 确保所有结果都有status字段
            for result in results:
                if 'status' not in result:
                    result['status'] = '待处理'
                # 确保所有结果都有original_name字段
                if 'original_name' not in result:
                    result['original_name'] = Path(result.get('path', '')).name or '未知文件'
            
            # 保存结果
            self.original_results = results
            self.current_results = results.copy()
            self.filtered_results = results.copy()
            
            # 调用data_display的show_process_results方法
            self.data_display.show_process_results(results)
            
            # 发出结果更新信号
            self.results_updated.emit(results)
        finally:
            self.block_signals(False)
            # 强制刷新以确保表格完全显示
            self._force_complete_refresh()
    
    def _force_complete_refresh(self):
        """强制完全刷新UI，确保表格完全显示"""
        try:
            # 先处理所有未处理的事件
            QApplication.processEvents()
            
            # 强制刷新数据显示
            self.data_display.force_table_refresh()
            
            # 再次处理事件，确保刷新生效
            QApplication.processEvents()
            
            # 使用QTimer添加一个短暂的延迟，让UI有时间响应
            QTimer.singleShot(50, self._finalize_refresh)
        except Exception as e:
            logging.error(f"强制刷新失败: {e}")
    
    def _finalize_refresh(self):
        """刷新的最终步骤，再次确保表格显示完整"""
        try:
            # 强制重绘表格
            self.table.viewport().update()
            self.table.repaint()
            
            # 处理事件队列
            QApplication.processEvents()
            
            # 再次刷新数据显示
            self.data_display.force_table_refresh()
        except Exception as e:
            logging.error(f"最终刷新步骤失败: {e}")
    
    def clear(self):
        """清空预览面板"""
        self.block_signals(True)
        try:
            # 清空所有数据存储
            self.original_results = []
            self.current_results = []
            self.filtered_results = []
            self.selected_files.clear()
            self.custom_categories.clear()
            self.filters.clear()
            
            # 设置表格行数为0
            self.table.setRowCount(0)
            
            # 清除表格的所有选择状态
            self.table.clearSelection()
            
            # 重置表头菜单中的选项
            self.table.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
            
            # 清除分类操作中的批量选择记忆
            if hasattr(self.category_operations, 'remember_batch_choice'):
                self.category_operations.remember_batch_choice = None
        finally:
            self.block_signals(False)
    
    def sort_by_column(self, column, ascending):
        """按指定列排序"""
        self.table.sortByColumn(column, Qt.AscendingOrder if ascending else Qt.DescendingOrder)
    
    def cancel_sort(self):
        """取消排序"""
        # 先禁用排序再启用，以取消当前排序
        self.table.setSortingEnabled(False)
        self.table.setSortingEnabled(True)
    
    def reset_all_headers(self):
        """重置所有列名为原始名称"""
        self.table.setHorizontalHeaderLabels(["选择", "原文件名", "新文件名", "分类", "可信度", "路径", "类型", "大小", "状态"])
    
    def edit_category(self, category, row=None, file_path=None):
        """编辑文件分类"""
        if row is not None:
            self.category_operations.edit_category(row)
    
    def show_filter_dialog(self):
        """显示筛选对话框"""
        self.filter_operations.show_filter_dialog()
    
    def apply_filters(self, filters):
        """应用筛选条件"""
        self.filter_operations.apply_filters(filters)
    
    def clear_filters(self):
        """清除筛选条件"""
        self.filter_operations.clear_filters()
    
    def edit_row_properties(self, row):
        """编辑单行属性"""
        self.category_operations.edit_row_properties(row)
    
    def update_file_status(self, file_path, new_status):
        """更新单个文件的状态"""
        for result in self.current_results:
            if result.get('path') == file_path or result.get('source_path') == file_path:
                result['status'] = new_status
                break
        
        # 刷新显示
        self.data_display.show_process_results(self.current_results)
    
    def update_all_results_status(self, status_updates, file_info_updates=None):
        """统一更新所有结果集的状态和文件信息"""
        # 确保参数类型安全
        if not isinstance(status_updates, dict):
            status_updates = {}
            logging.warning("update_all_results_status: status_updates不是字典类型，已转换为空字典")
            
        if file_info_updates is None:
            file_info_updates = {}
        elif not isinstance(file_info_updates, dict):
            file_info_updates = {}
            logging.warning("update_all_results_status: file_info_updates不是字典类型，已转换为空字典")
            
        # 存储需要更新的行索引
        updated_rows = set()
        
        # 阻塞信号以避免不必要的刷新
        self.block_signals(True)
        try:
            # 更新所有结果集合
            for results_list in [self.original_results, self.current_results, self.filtered_results]:
                for result in results_list:
                    if not isinstance(result, dict):
                        continue
                        
                    # 获取文件唯一标识符
                    file_key = result.get('path') or result.get('source_path')
                    
                    # 更新状态
                    if file_key in status_updates:
                        result['status'] = status_updates[file_key]
                        
                    # 更新文件信息
                    if file_key in file_info_updates:
                        file_info = file_info_updates[file_key]
                        # 只更新有效字段，避免覆盖重要数据
                        valid_fields = ['path', 'source_path', 'target_path', 'new_name', 'original_name', 
                                      'category', 'type', 'size', 'confidence', 'message']
                        
                        for field in valid_fields:
                            if field in file_info:
                                # 确保值是基本数据类型
                                value = file_info[field]
                                if isinstance(value, (str, int, float, bool, type(None))):
                                    result[field] = value
                                else:
                                    try:
                                        result[field] = str(value)
                                        logging.debug(f"文件信息中的{field}转换为字符串类型")
                                    except:
                                        pass
            
            # 找出在current_results中更新的行索引
            for idx, result in enumerate(self.current_results):
                file_key = result.get('path') or result.get('source_path')
                if file_key in status_updates or file_key in file_info_updates:
                    updated_rows.add(idx)
            
            # 对更新的行进行单独刷新，提高性能
            for row_idx in updated_rows:
                if 0 <= row_idx < len(self.current_results):
                    self.data_display._set_row_data(row_idx, self.current_results[row_idx])
                    
            # 最后执行一次全面刷新以确保表格显示正确
            self.data_display._full_refresh()
            
        finally:
            # 恢复信号
            self.block_signals(False)
            
            # 强制刷新以确保表格完全显示
            self._force_complete_refresh()