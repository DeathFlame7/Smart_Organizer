from PySide6.QtWidgets import QTableWidgetItem, QCheckBox
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
import logging
from pathlib import Path

class TableOperations:
    """表格操作管理类 - 负责表格的选择和基本操作功能"""
    
    def __init__(self, preview_panel):
        self.preview_panel = preview_panel
        self.selected_files = {}
        self.signals_connected = False
    
    def connect_table_signals(self):
        """连接表格信号"""
        if not self.signals_connected and hasattr(self.preview_panel, 'table'):
            try:
                # 连接单元格点击信号
                self.preview_panel.table.cellClicked.connect(self.on_cell_clicked)
                # 连接单元格双击信号
                self.preview_panel.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
                # 连接选择范围变化信号
                self.preview_panel.table.itemSelectionChanged.connect(self.on_selection_changed)
                # 连接单元格内容变化信号
                self.preview_panel.table.itemChanged.connect(self.on_item_changed)
                
                self.signals_connected = True
                
            except Exception as e:
                logging.error(f"连接表格信号失败: {e}")
    
    def disconnect_table_signals(self):
        """断开表格信号"""
        if self.signals_connected and hasattr(self.preview_panel, 'table'):
            try:
                # 断开所有连接的信号
                self.preview_panel.table.cellClicked.disconnect(self.on_cell_clicked)
                self.preview_panel.table.cellDoubleClicked.disconnect(self.on_cell_double_clicked)
                self.preview_panel.table.itemSelectionChanged.disconnect(self.on_selection_changed)
                self.preview_panel.table.itemChanged.disconnect(self.on_item_changed)
                
                self.signals_connected = False
                
            except Exception as e:
                logging.error(f"断开表格信号失败: {e}")
    
    def on_cell_clicked(self, row, column):
        """处理单元格点击事件"""
        try:
            # 如果点击的是选择列（索引为0）
            if column == 0:
                # 获取单元格项目
                item = self.preview_panel.table.item(row, column)
                if item:
                    # 更新选中状态
                    is_checked = item.checkState() == Qt.Checked
                    
                    # 获取文件标识符
                    file_key = self.get_file_identifier(self.preview_panel.current_results[row])
                    
                    # 更新选中文件字典
                    if is_checked:
                        self.selected_files[file_key] = True
                    else:
                        self.selected_files.pop(file_key, None)
                    
                    # 更新全选复选框状态
                    self.update_select_all_checkbox()
            
        except Exception as e:
            logging.error(f"处理单元格点击事件失败: {e}")
    
    def on_cell_double_clicked(self, row, column):
        """处理单元格双击事件"""
        try:
            # 双击任何单元格都编辑该行属性
            if hasattr(self.preview_panel, 'category_operations'):
                self.preview_panel.category_operations.edit_row_properties(row)
            
        except Exception as e:
            logging.error(f"处理单元格双击事件失败: {e}")
    
    def on_selection_changed(self):
        """处理选择范围变化事件"""
        try:
            # 如果当前结果为空，直接返回
            if not self.preview_panel.current_results:
                return
            
            # 获取所有选中的行
            selected_rows = set()
            for item in self.preview_panel.table.selectedItems():
                selected_rows.add(item.row())
            
            # 更新选中文件状态
            for row in selected_rows:
                if 0 <= row < len(self.preview_panel.current_results):
                    file_key = self.get_file_identifier(self.preview_panel.current_results[row])
                    self.selected_files[file_key] = True
                    
                    # 更新复选框状态
                    checkbox_item = self.preview_panel.table.item(row, 0)
                    if checkbox_item and checkbox_item.checkState() != Qt.Checked:
                        checkbox_item.setCheckState(Qt.Checked)
            
            # 更新全选复选框状态
            self.update_select_all_checkbox()
            
        except Exception as e:
            logging.error(f"处理选择范围变化事件失败: {e}")
    
    def on_item_changed(self, item):
        """处理单元格内容变化事件"""
        try:
            # 只处理选择列的变化
            if item.column() == 0:
                row = item.row()
                
                # 确保行索引有效
                if 0 <= row < len(self.preview_panel.current_results):
                    # 获取文件标识符
                    file_key = self.get_file_identifier(self.preview_panel.current_results[row])
                    
                    # 更新选中文件字典
                    if item.checkState() == Qt.Checked:
                        self.selected_files[file_key] = True
                    else:
                        self.selected_files.pop(file_key, None)
                    
                    # 更新全选复选框状态
                    self.update_select_all_checkbox()
            
        except Exception as e:
            logging.error(f"处理单元格内容变化事件失败: {e}")
    
    def select_all_files(self):
        """全选所有文件"""
        try:
            # 重置选中文件字典
            self.selected_files.clear()
            
            # 更新表格中的所有复选框
            for row in range(len(self.preview_panel.current_results)):
                # 获取文件标识符
                file_key = self.get_file_identifier(self.preview_panel.current_results[row])
                
                # 添加到选中文件字典
                self.selected_files[file_key] = True
                
                # 更新复选框状态
                checkbox_item = self.preview_panel.table.item(row, 0)
                if checkbox_item:
                    checkbox_item.setCheckState(Qt.Checked)
            
            # 更新全选复选框状态
            self.update_select_all_checkbox()
            
        except Exception as e:
            logging.error(f"全选文件失败: {e}")
    
    def deselect_all_files(self):
        """取消选择所有文件"""
        try:
            # 清空选中文件字典
            self.selected_files.clear()
            
            # 更新表格中的所有复选框
            for row in range(len(self.preview_panel.current_results)):
                checkbox_item = self.preview_panel.table.item(row, 0)
                if checkbox_item:
                    checkbox_item.setCheckState(Qt.Unchecked)
            
            # 更新全选复选框状态
            self.update_select_all_checkbox()
            
        except Exception as e:
            logging.error(f"取消选择文件失败: {e}")
    
    def update_select_all_checkbox(self):
        """更新全选复选框状态"""
        try:
            # 检查是否存在全选复选框
            if hasattr(self.preview_panel, 'select_all_checkbox') and self.preview_panel.select_all_checkbox:
                # 检查当前结果数量
                result_count = len(self.preview_panel.current_results)
                
                if result_count == 0:
                    # 如果没有结果，设置为未选中状态
                    self.preview_panel.select_all_checkbox.setCheckState(Qt.Unchecked)
                elif len(self.selected_files) == result_count:
                    # 如果所有文件都被选中，设置为选中状态
                    self.preview_panel.select_all_checkbox.setCheckState(Qt.Checked)
                else:
                    # 否则设置为部分选中状态
                    self.preview_panel.select_all_checkbox.setCheckState(Qt.PartiallyChecked)
            
        except Exception as e:
            logging.error(f"更新全选复选框状态失败: {e}")
    
    def get_file_identifier(self, result):
        """获取文件的唯一标识符"""
        # 尝试使用path或source_path作为唯一标识符
        return result.get('path') or result.get('source_path') or str(result.get('id', ''))
    
    def get_selected_results(self):
        """获取选中的文件结果"""
        selected_results = []
        
        for result in self.preview_panel.current_results:
            file_key = self.get_file_identifier(result)
            if file_key in self.selected_files:
                selected_results.append(result)
                
        return selected_results
    
    def select_row(self, row):
        """选择指定行"""
        try:
            # 确保行索引有效
            if 0 <= row < len(self.preview_panel.current_results):
                # 获取文件标识符
                file_key = self.get_file_identifier(self.preview_panel.current_results[row])
                
                # 添加到选中文件字典
                self.selected_files[file_key] = True
                
                # 更新复选框状态
                checkbox_item = self.preview_panel.table.item(row, 0)
                if checkbox_item:
                    checkbox_item.setCheckState(Qt.Checked)
                
                # 更新全选复选框状态
                self.update_select_all_checkbox()
            
        except Exception as e:
            logging.error(f"选择行失败: {e}")
    
    def deselect_row(self, row):
        """取消选择指定行"""
        try:
            # 确保行索引有效
            if 0 <= row < len(self.preview_panel.current_results):
                # 获取文件标识符
                file_key = self.get_file_identifier(self.preview_panel.current_results[row])
                
                # 从选中文件字典中移除
                self.selected_files.pop(file_key, None)
                
                # 更新复选框状态
                checkbox_item = self.preview_panel.table.item(row, 0)
                if checkbox_item:
                    checkbox_item.setCheckState(Qt.Unchecked)
                
                # 更新全选复选框状态
                self.update_select_all_checkbox()
            
        except Exception as e:
            logging.error(f"取消选择行失败: {e}")
    
    def toggle_row_selection(self, row):
        """切换指定行的选择状态"""
        try:
            # 确保行索引有效
            if 0 <= row < len(self.preview_panel.current_results):
                # 获取文件标识符
                file_key = self.get_file_identifier(self.preview_panel.current_results[row])
                
                # 切换选择状态
                if file_key in self.selected_files:
                    self.deselect_row(row)
                else:
                    self.select_row(row)
            
        except Exception as e:
            logging.error(f"切换行选择状态失败: {e}")
    
    def get_selected_count(self):
        """获取选中文件的数量"""
        return len(self.selected_files)
    
    def clear_selection(self):
        """清除所有选择"""
        try:
            # 清空选中文件字典
            self.selected_files.clear()
            
            # 清除表格中的所有选择
            if hasattr(self.preview_panel, 'table'):
                self.preview_panel.table.clearSelection()
            
            # 更新全选复选框状态
            self.update_select_all_checkbox()
            
        except Exception as e:
            logging.error(f"清除选择失败: {e}")
    
    def is_file_selected(self, file_key):
        """检查指定文件是否被选中"""
        return file_key in self.selected_files