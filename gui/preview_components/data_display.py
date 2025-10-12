from PySide6.QtWidgets import QTableWidgetItem, QApplication
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtCore import Qt
import logging
import copy
from pathlib import Path

class DataDisplay:
    """表格数据显示管理类 - 负责表格数据的显示和刷新"""
    
    def __init__(self, preview_panel):
        self.preview_panel = preview_panel
        self.table = preview_panel.table
        self._init_colors()
        
        # 确保必要的属性存在
        if not hasattr(self.preview_panel, 'selected_files'):
            self.preview_panel.selected_files = set()
    
    def _init_colors(self):
        """初始化状态颜色配置，确保颜色显示正确"""
        self.color_map = {
            'success': QColor(198, 239, 206),  # 浅绿色（已处理）
            'failed': QColor(255, 209, 209),   # 浅红色（失败）
            'undone': QColor(252, 247, 189),   # 浅黄色（已撤销）
            'pending': QColor(229, 238, 252),  # 浅蓝色（待处理）
            'default': QColor(255, 255, 255)   # 白色（默认）
        }
        
        self.status_text_map = {
            'success': "已处理",
            'failed': "失败",
            'undone': "已撤销",
            'pending': "待处理",
            'default': "待处理"
        }
    
    def _format_size(self, size):
        """格式化文件大小显示"""
        try:
            size_value = float(size) if isinstance(size, (str, int)) else size
            if size_value >= 1024 * 1024:
                return f"{size_value / (1024 * 1024):.2f} MB"
            elif size_value >= 1024:
                return f"{size_value / 1024:.2f} KB"
            else:
                return f"{size_value} bytes"
        except (ValueError, TypeError):
            return "未知大小"
    
    def _ensure_result_integrity(self, result):
        """确保结果字典包含所有必要字段，增强数据安全性"""
        if not isinstance(result, dict):
            result = {}
        
        # 确保必要字段存在且类型正确
        if 'status' not in result:
            result['status'] = 'default'
        else:
            # 确保status是字符串
            result['status'] = str(result['status']) if result['status'] is not None else 'default'
        
        # 原文件名处理
        if 'original_name' not in result or not result['original_name']:
            path = result.get('path') or result.get('source_path', '')
            if path:
                try:
                    result['original_name'] = Path(path).name
                except (TypeError, ValueError):
                    result['original_name'] = '未知文件名'
            else:
                result['original_name'] = '未知文件名'
        
        # 确保其他必要字段存在
        result.setdefault('category', '未分类')
        result.setdefault('confidence', 0.0)
        result.setdefault('type', 'unknown')
        result.setdefault('size', 0)
        
        return result
    
    def _get_display_path(self, result):
        """获取用于显示的文件路径，确保路径正确显示"""
        try:
            status = result.get('status', 'default')
            
            # 优先显示实际路径
            if status == 'success':
                path = result.get('target_path', '')
                # 撤销操作后，路径应该显示为原始路径
                if path and hasattr(self.preview_panel, 'core') and hasattr(self.preview_panel.core, 'undo_manager'):
                    # 检查是否有撤销记录
                    pass
            else:
                path = result.get('source_path', result.get('path', ''))
            
            # 使用预览面板的路径简化方法
            if path and hasattr(self.preview_panel, '_simplify_path'):
                try:
                    return self.preview_panel._simplify_path(path)
                except Exception as e:
                    logging.debug(f"简化路径失败: {e}")
            
            return path or '未知路径'
        except Exception as e:
            logging.error(f"获取显示路径失败: {e}")
            return '未知路径'
    
    def _set_row_data(self, row, result):
        """设置单行数据，确保所有列的内容和样式正确"""
        try:
            # 确保结果字典完整性
            result = self._ensure_result_integrity(result)
            
            # 检查行索引是否有效
            if row < 0 or row >= self.table.rowCount():
                return
            
            # 保存当前行的复选框状态
            current_check_state = Qt.Unchecked
            if 0 <= row < self.table.rowCount():
                checkbox_item = self.table.item(row, 0)
                if checkbox_item:
                    current_check_state = checkbox_item.checkState()
            
            # 设置复选框
            checkbox_item = QTableWidgetItem()
            checkbox_item.setTextAlignment(Qt.AlignCenter)
            checkbox_item.setFlags(checkbox_item.flags() & ~Qt.ItemIsEditable)
            checkbox_item.setCheckState(current_check_state)
            self.table.setItem(row, 0, checkbox_item)
            
            # 设置各列数据 - 确保创建全新的QTableWidgetItem实例
            # 原文件名
            original_name = result.get('original_name', '未知文件名')
            item1 = QTableWidgetItem(str(original_name))
            self.table.setItem(row, 1, item1)
            
            # 新文件名
            new_name = result.get('new_name', result.get('new_filename', original_name))
            item2 = QTableWidgetItem(str(new_name))
            self.table.setItem(row, 2, item2)
            
            # 分类
            category = result.get('category', '未分类')
            item3 = QTableWidgetItem(str(category))
            self.table.setItem(row, 3, item3)
            
            # 可信度
            confidence = result.get('confidence', 0.0)
            try:
                confidence_value = float(confidence) if confidence is not None else 0.0
                item4 = QTableWidgetItem(f"{confidence_value:.2f}")
                # 根据可信度设置字体颜色
                if confidence_value >= 0.8:
                    item4.setForeground(QBrush(QColor(0, 128, 0)))
                elif confidence_value >= 0.5:
                    item4.setForeground(QBrush(QColor(128, 128, 0)))
                else:
                    item4.setForeground(QBrush(QColor(128, 0, 0)))
            except (ValueError, TypeError):
                item4 = QTableWidgetItem("0.00")
            self.table.setItem(row, 4, item4)
            
            # 路径
            display_path = self._get_display_path(result)
            item5 = QTableWidgetItem(str(display_path))
            # 设置路径列的提示
            item5.setToolTip(str(display_path))
            self.table.setItem(row, 5, item5)
            
            # 类型
            file_type = result.get('type', 'unknown')
            item6 = QTableWidgetItem(str(file_type))
            self.table.setItem(row, 6, item6)
            
            # 大小
            file_size = result.get('size', 0)
            item7 = QTableWidgetItem(self._format_size(file_size))
            self.table.setItem(row, 7, item7)
            
            # 设置状态列
            status = result.get('status', 'default')
            status_text = self.status_text_map.get(status, self.status_text_map['default'])
            
            item8 = QTableWidgetItem(status_text)
            # 根据状态设置字体颜色
            if status == 'success':
                item8.setForeground(QBrush(QColor(0, 128, 0)))
            elif status == 'failed':
                item8.setForeground(QBrush(QColor(128, 0, 0)))
            elif status == 'undone':
                item8.setForeground(QBrush(QColor(128, 128, 0)))
            
            self.table.setItem(row, 8, item8)
            
            # 设置整行背景色
            bg_color = self.color_map.get(status, self.color_map['default'])
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(QBrush(bg_color))
            
            # 设置行高
            self.table.setRowHeight(row, 25)
            
        except Exception as e:
            logging.error(f"设置行数据失败 (行 {row}): {e}")
    
    def _full_refresh(self):
        """全面刷新表格，确保所有内容正确显示"""
        try:
            # 禁用排序避免干扰
            was_sorting_enabled = self.table.isSortingEnabled()
            if was_sorting_enabled:
                self.table.setSortingEnabled(False)
            
            # 自动调整列宽（只调整必要的列）
            self.table.resizeColumnToContents(0)  # 选择列
            self.table.resizeColumnToContents(1)  # 原文件名
            self.table.resizeColumnToContents(2)  # 新文件名
            self.table.resizeColumnToContents(3)  # 分类
            self.table.resizeColumnToContents(4)  # 可信度
            self.table.resizeColumnToContents(6)  # 类型
            self.table.resizeColumnToContents(7)  # 大小
            self.table.resizeColumnToContents(8)  # 状态
            
            # 设置路径列的宽度为固定值
            self.table.setColumnWidth(5, 300)  # 路径列
            
            # 强制刷新视图的多个层次
            self.table.viewport().update()
            self.table.repaint()
            
            # 强制模型布局更新
            model = self.table.model()
            if model:
                try:
                    model.layoutChanged.emit()
                except RuntimeError:
                    # 可能模型已被销毁
                    pass
            
            # 强制处理所有待处理的UI事件
            QApplication.processEvents()
            
            # 恢复排序状态
            if was_sorting_enabled:
                self.table.setSortingEnabled(True)
                
        except Exception as e:
            logging.error(f"全面刷新表格失败: {e}")
    
    def _update_select_all_checkbox(self):
        """更新全选复选框状态"""
        try:
            if hasattr(self.preview_panel, 'table_operations') and hasattr(self.preview_panel.table_operations, 'update_select_all_checkbox'):
                self.preview_panel.table_operations.update_select_all_checkbox()
        except Exception as e:
            logging.error(f"更新全选复选框状态失败: {e}")
    
    def _display_results(self, results, clear_original=False):
        """核心显示方法，统一处理各种结果的显示逻辑"""
        try:
            # 验证结果参数
            if not isinstance(results, list):
                results = []
                logging.warning("结果不是列表类型，已转换为空列表")
            
            # 阻塞信号避免不必要的更新
            self.table.blockSignals(True)
            
            # 保存结果引用（使用深拷贝避免引用问题）
            # 避免循环导入
            if hasattr(self.preview_panel, 'current_results'):
                self.preview_panel.current_results = copy.deepcopy(results)
            if hasattr(self.preview_panel, 'filtered_results'):
                self.preview_panel.filtered_results = copy.deepcopy(results)
            
            # 处理core中的结果引用
            if hasattr(self.preview_panel, 'core'):
                if hasattr(self.preview_panel.core, 'current_results'):
                    self.preview_panel.core.current_results = copy.deepcopy(results)
                if hasattr(self.preview_panel.core, 'filtered_results'):
                    self.preview_panel.core.filtered_results = copy.deepcopy(results)
                if clear_original and hasattr(self.preview_panel.core, 'original_results'):
                    self.preview_panel.core.original_results = copy.deepcopy(results)
            elif clear_original and hasattr(self.preview_panel, 'original_results'):
                self.preview_panel.original_results = copy.deepcopy(results)
            
            # 保存当前排序状态
            was_sorting_enabled = self.table.isSortingEnabled()
            
            # 禁用排序以提高性能
            self.table.setSortingEnabled(False)
            
            # 清空表格内容并设置新行数
            self.table.clearContents()
            self.table.setRowCount(len(results))
            
            # 清除选中状态
            self.preview_panel.selected_files.clear()
            if hasattr(self.preview_panel, 'table_operations') and hasattr(self.preview_panel.table_operations, 'selected_files'):
                self.preview_panel.table_operations.selected_files.clear()
            
            # 填充数据
            for row, result in enumerate(results):
                self._set_row_data(row, result)
            
            # 执行全面刷新以解决不完全显示问题
            self._full_refresh()
            
            # 更新全选复选框状态
            self._update_select_all_checkbox()
            
        except Exception as e:
            logging.error(f"显示结果失败: {e}")
        finally:
            # 确保信号恢复
            self.table.blockSignals(False)
    
    # 公开的方法接口
    def show_classification_results(self, results):
        """显示分类结果"""
        self._display_results(results, clear_original=True)
    
    def show_process_results(self, results):
        """显示处理结果"""
        # 清除自定义分类记录
        if hasattr(self.preview_panel, 'custom_categories'):
            self.preview_panel.custom_categories.clear()
        
        self._display_results(results)
    
    def show_preview(self, results):
        """显示扫描结果预览"""
        self._display_results(results)
    
    def force_table_refresh(self):
        """强制刷新表格显示"""
        try:
            # 执行全面刷新
            self._full_refresh()
            
        except Exception as e:
            logging.error(f"强制刷新表格失败: {e}")