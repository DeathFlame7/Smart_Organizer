from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox, QToolTip, QMessageBox
from PySide6.QtCore import Qt, Signal, QEvent, QTimer
from pathlib import Path
import logging

from gui.preview_components.preview_panel_core import PreviewPanel as PreviewPanelCore
from core.undo_manager import create_undo_manager

class PreviewPanel(QWidget):
    """预览面板，用于显示和操作文件分类结果"""
    
    # 定义信号
    file_updated = Signal(list, dict)
    process_single_file = Signal(dict)
    process_selected_files = Signal(list)
    results_updated = Signal(list)

    def __init__(self, parent=None, file_processor=None, file_classifier=None):
        super().__init__(parent)
        
        # 保存参数
        self.parent_window = parent
        self.file_processor = file_processor
        self.file_classifier = file_classifier
        
        # 创建核心组件，并传递所需参数
        self.core = PreviewPanelCore(parent=self, file_processor=file_processor, file_classifier=file_classifier)
        
        # 连接信号
        self.core.file_updated.connect(self.file_updated)
        self.core.process_single_file.connect(self.process_single_file)
        self.core.process_selected_files.connect(self.process_selected_files)
        self.core.results_updated.connect(self.results_updated)
        
        # 初始化撤销管理器
        self.undo_manager = None
        
        # 初始化UI
        self.init_ui()
        
        # 为表格安装事件过滤器，用于显示路径提示
        self.table.viewport().installEventFilter(self)
        
        # 延迟初始化撤销管理器，确保所有组件都已创建
        self.set_undo_manager()
    
    def set_undo_manager(self):
        """设置撤销管理器"""
        # 获取数据库连接（通过父窗口或核心组件）
        db = None
        if hasattr(self.parent_window, 'db'):
            db = self.parent_window.db
        elif hasattr(self.core, 'main_window') and hasattr(self.core.main_window, 'db'):
            db = self.core.main_window.db
        
        # 初始化撤销管理器
        self.undo_manager = create_undo_manager(self.file_processor, db)

    def init_ui(self):
        """初始化UI布局"""
        layout = QVBoxLayout(self)

        # 筛选工具栏
        filter_layout = QHBoxLayout()
        self.filter_btn = QPushButton("筛选")
        self.filter_btn.clicked.connect(self.core.filter_operations.show_filter_dialog)

        self.clear_filter_btn = QPushButton("清除筛选")
        # 添加日志以确认信号连接
        logging.info(f"连接clear_filter_btn.clicked信号到: {self.core.filter_operations.clear_filters}")
        logging.info(f"FilterOperations实例ID: {id(self.core.filter_operations)}")
        logging.info(f"preview_panel属性ID: {id(self.core.filter_operations.preview_panel)}")
        self.clear_filter_btn.clicked.connect(self.core.filter_operations.clear_filters)
        self.clear_filter_btn.setEnabled(False)
        
        # 添加撤销按钮
        self.undo_btn = QPushButton("撤销操作")
        self.undo_btn.clicked.connect(self.undo_operations)
        
        self.undo_selected_btn = QPushButton("撤销选中")
        self.undo_selected_btn.clicked.connect(self.undo_selected_operations)

        # 添加全选复选框到工具栏
        self.select_all_checkbox = QCheckBox("全选")
        self.select_all_checkbox.stateChanged.connect(self.on_select_all_checkbox_changed)

        filter_layout.addWidget(self.select_all_checkbox)
        filter_layout.addStretch()
        filter_layout.addWidget(self.undo_btn)
        filter_layout.addWidget(self.undo_selected_btn)
        filter_layout.addWidget(self.filter_btn)
        filter_layout.addWidget(self.clear_filter_btn) 

        layout.addLayout(filter_layout)
        layout.addWidget(self.core.table)  # 添加核心组件的表格

        self.setLayout(layout)

        # 从核心组件获取对表格的引用
        self.table = self.core.table
        
        # 关键修复：只在需要时连接cellChanged信号
        self._table_signals_connected = False
        self.connect_table_signals()
        
        # 关键修改：确保核心组件中的表格操作组件能够更新全选框状态
        if hasattr(self.core, 'table_operations'):
            # 为表格操作组件添加对全选框的引用
            self.core.table_operations.select_all_checkbox = self.select_all_checkbox
    
    def connect_table_signals(self):
        """连接表格信号"""
        if not self._table_signals_connected:
            self.table.cellChanged.connect(self.on_table_cell_changed)
            self._table_signals_connected = True
            
    def disconnect_table_signals(self):
        """断开表格信号"""
        if self._table_signals_connected:
            try:
                self.table.cellChanged.disconnect(self.on_table_cell_changed)
            except:
                pass
            self._table_signals_connected = False

    def on_select_all_checkbox_changed(self, state):
        """全选复选框状态变化处理"""
        logging.debug(f"全选框状态变化: {state}")
        
        # 阻塞信号避免递归调用
        was_blocked = self.select_all_checkbox.signalsBlocked()
        self.select_all_checkbox.blockSignals(True)
        
        try:
            # 确保state是Qt.CheckState枚举值
            if isinstance(state, int):
                state_enum = Qt.CheckState(state)
                logging.debug(f"将整数状态转换为枚举: {state_enum}")
            else:
                state_enum = state
                logging.debug(f"使用原始状态枚举: {state_enum}")
            
            # 执行相应的全选/取消全选操作
            if state_enum == Qt.Checked or state_enum == Qt.PartiallyChecked:
                logging.debug(f"状态 {state_enum}，执行全选操作")
                self.select_all_files()
                # 强制更新全选框状态为选中
                self.select_all_checkbox.setCheckState(Qt.Checked)
            elif state_enum == Qt.Unchecked:
                logging.debug("全选框变为未选中状态，执行取消全选操作")
                self.deselect_all_files()
                # 强制更新全选框状态为未选中
                self.select_all_checkbox.setCheckState(Qt.Unchecked)
            
            # 确保表格视图完全更新
            if hasattr(self, 'table'):
                try:
                    # 关键修改：使用多种刷新方式
                    self.table.viewport().update()
                    QTimer.singleShot(50, self.table.repaint)  # 延迟重绘
                except Exception as e:
                    logging.error(f"预览面板表格刷新失败: {e}")
            
        except Exception as e:
            logging.error(f"全选框操作失败: {e}")
        finally:
            # 恢复信号 - 确保恢复到原来的状态
            self.select_all_checkbox.blockSignals(was_blocked)
            
    def force_update_all_checkboxes(self, state):
        """强制更新表格中所有复选框的显示状态"""
        try:
            # 根据全选框的状态决定表格中复选框的状态
            if state == Qt.Checked:
                # 全选框被选中，所有表格复选框应该被选中
                check_state = Qt.Checked
            elif state == Qt.Unchecked:
                # 全选框被取消选中，所有表格复选框应该被取消选中
                check_state = Qt.Unchecked
            elif state == Qt.PartiallyChecked:
                # 部分选中状态，应该变为全选
                check_state = Qt.Checked
            else:
                check_state = Qt.Unchecked
            
            # 直接操作表格中的所有复选框
            count = 0
            for row in range(self.table.rowCount()):
                checkbox_item = self.table.item(row, 0)
                if checkbox_item:
                    # 直接设置复选框状态
                    checkbox_item.setCheckState(check_state)
                    count += 1
            
            # 强制刷新表格视图
            try:
                self.table.viewport().update()
            except Exception as e:
                logging.error(f"预览面板表格刷新失败: {e}")
            
            logging.debug(f"强制更新了 {self.table.rowCount()} 个复选框的状态")
            
        except Exception as e:
            logging.error(f"强制更新复选框失败: {e}")

    def eventFilter(self, source, event):
        """事件过滤器，用于处理鼠标悬停事件，显示完整路径提示"""
        if source == self.table.viewport() and event.type() == QEvent.ToolTip:
            # 获取鼠标位置
            pos = event.pos()
            # 获取单元格索引
            index = self.table.indexAt(pos)
            # 检查是否是路径列（假设第5列是路径列）
            if index.isValid() and index.column() == 5:
                # 获取文件路径信息（从原始结果中获取完整路径）
                if hasattr(self.core, 'original_results') and index.row() < len(self.core.original_results):
                    full_path = self.core.original_results[index.row()].get('path', '')
                    if full_path:
                        # 显示工具提示
                        QToolTip.showText(event.globalPos(), full_path, self.table)
                        return True
        # 其他情况继续处理
        return super().eventFilter(source, event)

    # 以下方法全部转发到核心组件
    def select_all_files(self):
        """全选所有文件"""
        if hasattr(self.core, 'table_operations'):
            self.core.table_operations.select_all_files()
        else:
            # 备用方案
            self.core.select_all_files()

    def deselect_all_files(self):
        """取消全选所有文件"""
        if hasattr(self.core, 'table_operations'):
            self.core.table_operations.deselect_all_files()
        else:
            # 备用方案
            self.core.deselect_all_files()

    def process_selected(self):
        """处理选中的文件"""
        self.core.process_selected()

    def process_file(self, row):
        """处理单个文件"""
        self.core.process_file(row)

    def show_header_menu(self, position):
        """显示表头右键菜单"""
        self.core.show_header_menu(position)

    def show_cell_menu(self, position):
        """显示单元格右键菜单"""
        self.core.show_cell_menu(position)

    def sort_by_column(self, column, ascending):
        """按指定列排序"""
        self.core.sort_by_column(column, ascending)

    def cancel_sort(self):
        """取消排序"""
        self.core.cancel_sort()

    def on_header_double_clicked(self, logical_index):
        """双击表头编辑列名"""
        self.core.on_header_double_clicked(logical_index)

    def reset_all_headers(self):
        """重置所有列名为原始名称"""
        self.core.reset_all_headers()

    def on_cell_double_clicked(self, row, column):
        """单元格双击事件"""
        self.core.on_cell_double_clicked(row, column)

    def on_cell_clicked(self, row, column):
        """单元格单击事件"""
        self.core.on_cell_clicked(row, column)

    def toggle_file_selection(self, row):
        """切换文件选择状态"""
        self.core.toggle_file_selection(row)

    def update_checkbox_display(self):
        """更新复选框显示状态"""
        self.core.update_checkbox_display()

    def edit_category(self, category, row=None, file_path=None):
        """编辑文件分类"""
        self.core.edit_category(category, row, file_path)

    def _simplify_path(self, path):
        """简化文件路径显示"""
        if not hasattr(self, 'core') or not hasattr(self.core, '_simplify_path'):
            logging.warning("core组件或_simplify_path方法不存在，返回原始路径")
            return path
        simplified_path = self.core._simplify_path(path)
        return simplified_path

    def show_classification_results(self, results):
        """显示分类结果"""
        self.core.show_classification_results(results)
        
    def show_process_results(self, results):
        """显示处理结果"""
        self.core.show_process_results(results)
        
    def show_filter_dialog(self):
        """显示筛选对话框"""
        self.core.show_filter_dialog()
        
    def apply_filters(self, filters):
        """应用筛选条件"""
        self.core.apply_filters(filters)
        
    def clear_filters(self):
        """清除筛选条件"""
        self.core.clear_filters()
        
    def clear(self):
        """清空预览面板中的所有数据和状态"""
        self.core.clear()
        
    def show_preview(self, results):
        """显示扫描结果预览"""
        # 断开信号避免重复触发
        self.disconnect_table_signals()
        
        try:
            # 确保filtered_results正确设置为results
            self.core.filtered_results = results.copy()
            logging.debug(f"设置filtered_results，包含{len(results)}个文件")
            
            # 阻塞表格信号
            self.table.blockSignals(True)
            
            # 调用核心显示方法
            self.core.show_preview(results)
            
        except Exception as e:
            logging.error(f"显示预览失败: {e}")
        finally:
            # 恢复信号
            self.table.blockSignals(False)
            # 重新连接信号
            self.connect_table_signals()
            
            # 强制刷新
            self.table.viewport().update()
        
    def debug_table_content(self):
        """调试表格内容"""
        try:
            if hasattr(self, 'table'):
                logging.debug(f"表格最终状态 - 行数: {self.table.rowCount()}")
                # 检查前3行的内容
                for row in range(min(3, self.table.rowCount())):
                    row_info = []
                    for col in range(min(9, self.table.columnCount())):
                        item = self.table.item(row, col)
                        if item:
                            row_info.append(f"列{col}: '{item.text()}'")
                        else:
                            row_info.append(f"列{col}: 无项目")
                    logging.debug(f"行{row}: {', '.join(row_info)}")
        except Exception as e:
            logging.error(f"调试表格内容失败: {e}")
        
    def edit_row_properties(self, row):
        """编辑单行属性"""
        self.core.edit_row_properties(row)
        
    def update_select_all_checkbox_state(self):
        """更新全选复选框状态，基于当前选中文件数量"""
        if not hasattr(self, 'select_all_checkbox') or not self.select_all_checkbox:
            return
        
        # 确保有有效的数据
        if not hasattr(self.core, 'table_operations') or not hasattr(self.core.table_operations, 'selected_files'):
            return
        
        total_files = len(self.core.filtered_results) if hasattr(self.core, 'filtered_results') and self.core.filtered_results else 0
        selected_count = len(self.core.table_operations.selected_files)
        
        logging.debug(f"更新全选框状态: 总文件数={total_files}, 选中数={selected_count}")
        
        # 阻塞信号避免递归调用
        self.select_all_checkbox.blockSignals(True)
        
        try:
            if total_files == 0:
                # 没有文件时，全选框不可用或未选中
                self.select_all_checkbox.setCheckState(Qt.Unchecked)
                self.select_all_checkbox.setEnabled(False)
            elif selected_count == total_files:
                # 所有文件都选中
                self.select_all_checkbox.setCheckState(Qt.Checked)
                self.select_all_checkbox.setEnabled(True)
            elif selected_count == 0:
                # 没有文件选中
                self.select_all_checkbox.setCheckState(Qt.Unchecked)
                self.select_all_checkbox.setEnabled(True)
            else:
                # 部分文件选中
                self.select_all_checkbox.setCheckState(Qt.PartiallyChecked)
                self.select_all_checkbox.setEnabled(True)
        finally:
            # 确保恢复信号
            self.select_all_checkbox.blockSignals(False)
        
    def on_table_cell_changed(self, row, column):
        """处理表格单元格变化，特别是复选框列的变化"""
        if column == 0:  # 选择列
            checkbox_item = self.table.item(row, 0)
            if checkbox_item:
                state = checkbox_item.checkState()
                logging.debug(f"表格复选框变化: 行 {row}, 状态 {state}")
                
                # 更新全选复选框状态
                self.update_select_all_checkbox_state()
        
    def update_file_status(self, file_path, new_status):
        """更新单个文件的状态"""
        for result in self.core.current_results:
            if result.get('path') == file_path or result.get('source_path') == file_path:
                result['status'] = new_status
                break
        
        # 刷新显示
        self.core.data_display.show_process_results(self.core.current_results)
        
        # 强制刷新表格以确保状态样式正确显示
        self.core.data_display._full_refresh()
    
    def update_all_results_status(self, status_updates=None, file_info_updates=None):
        """统一更新所有结果集的状态和信息，确保表格正确显示文件状态和颜色
        
        Args:
            status_updates: 状态更新字典 {文件路径: 新状态}
            file_info_updates: 文件信息更新字典 {文件路径: {字段: 新值}}
        """
        logging.debug(f"update_all_results_status: 入参 - status_updates类型={type(status_updates)}, file_info_updates类型={type(file_info_updates)}")
        
        # 确保参数有默认值且为正确类型
        if status_updates is None:
            status_updates = {}
            logging.debug("update_all_results_status: status_updates为None，已初始化为空字典")
        elif not isinstance(status_updates, dict):
            logging.warning("status_updates不是字典类型，已转换为空字典")
            status_updates = {}
        
        if file_info_updates is None:
            file_info_updates = {}
            logging.debug("update_all_results_status: file_info_updates为None，已初始化为空字典")
        elif not isinstance(file_info_updates, dict):
            logging.warning("file_info_updates不是字典类型，已转换为空字典")
            file_info_updates = {}
        
        # 记录开始更新
        logging.debug(f"开始更新结果状态: status_updates={len(status_updates)}个, file_info_updates={len(file_info_updates)}个")
        
        # 断开表格信号避免重复触发
        self.disconnect_table_signals()
        
        # 阻塞表格信号
        self.table.blockSignals(True)
        
        try:
            # 获取当前显示的文件路径列表
            current_file_paths = set()
            for result in self.core.current_results:
                if isinstance(result, dict):
                    file_key = result.get('path') or result.get('source_path')
                    if file_key:
                        current_file_paths.add(file_key)
            
            # 更新current_results、original_results和filtered_results
            for result_list_name in ['current_results', 'original_results', 'filtered_results']:
                logging.debug(f"更新结果列表: {result_list_name}")
                if hasattr(self.core, result_list_name):
                    result_list = getattr(self.core, result_list_name)
                    if not isinstance(result_list, list):
                        logging.warning(f"{result_list_name}不是列表类型: {type(result_list)}")
                        continue
                    
                    for i, result in enumerate(result_list):
                        # 确保result是字典
                        if not isinstance(result, dict):
                            result_list[i] = {}
                            result = result_list[i]
                            logging.warning(f"{result_list_name}[{i}]不是字典类型，已初始化为空字典")
                        
                        file_key = result.get('path') or result.get('source_path')
                        if not file_key:
                            continue
                        
                        # 更新状态
                        if file_key in status_updates:
                            old_status = result.get('status', 'unknown')
                            result['status'] = status_updates[file_key]
                            logging.debug(f"更新状态: {file_key} - 从 {old_status} 到 {status_updates[file_key]}")
                            
                        # 更新文件信息
                        if file_key in file_info_updates:
                            info_update = file_info_updates[file_key]
                            if isinstance(info_update, dict):
                                # 只更新有效的字段
                                valid_keys = {'path', 'source_path', 'target_path', 'new_name', 'original_name', 
                                            'status', 'category', 'type', 'size', 'confidence', 'message'}
                                for key, value in info_update.items():
                                    if key in valid_keys:
                                        # 确保值是基本数据类型
                                        if not isinstance(value, (str, int, float, bool, type(None))):
                                            result[key] = str(value)
                                        else:
                                            result[key] = value
            
            # 获取需要更新的行索引
            rows_to_update = []
            for row, result in enumerate(self.core.current_results):
                if isinstance(result, dict):
                    file_key = result.get('path') or result.get('source_path')
                    if file_key and (file_key in status_updates or file_key in file_info_updates):
                        rows_to_update.append(row)
                        logging.debug(f"添加行{row}到更新列表: {file_key}")
            
            logging.debug(f"需要更新的行数: {len(rows_to_update)}")
            
            # 只更新需要变更的行，避免不必要的重绘
            if hasattr(self.core.data_display, '_set_row_data'):
                logging.debug(f"开始更新行数据，共{len(rows_to_update)}行")
                for row in rows_to_update:
                    if 0 <= row < len(self.core.current_results):
                        result = self.core.current_results[row]
                        if isinstance(result, dict):
                            file_key = result.get('path') or result.get('source_path') or 'unknown'
                            file_name = Path(file_key).name if file_key != 'unknown' else 'unknown'
                            logging.debug(f"更新行{row}数据: {file_name}, 状态={result.get('status', 'unknown')}")
                            self.core.data_display._set_row_data(row, result)
            
            # 执行一次完整的表格刷新，确保颜色和样式正确显示
            if hasattr(self.core.data_display, '_full_refresh'):
                logging.debug("执行完整表格刷新")
                self.core.data_display._full_refresh()
            
        except Exception as e:
            logging.error(f"更新结果状态时出错: {e}", exc_info=True)
        finally:
            # 恢复表格信号
            self.table.blockSignals(False)
            # 重新连接信号
            self.connect_table_signals()
            
            # 强制刷新表格视图
            self.table.viewport().update()
            self.table.repaint()
            
            logging.debug("结果状态更新完成")
    
    def batch_update_status(self, status_dict):
        """批量更新文件状态"""
        self.update_all_results_status(status_dict)
    
    def undo_operations(self):
        """撤销所有已处理文件的操作 - 使用统一的撤销管理器"""
        try:
            # 确保撤销管理器已初始化
            if not self.undo_manager:
                self.set_undo_manager()
                if not self.undo_manager:
                    QMessageBox.warning(self.parent(), "错误", "撤销管理器初始化失败")
                    return
            
            # 获取所有成功处理的文件
            processed_files = []
            for result in self.core.current_results:
                if result.get('status') == 'success' and result.get('target_path'):
                    processed_files.append(result)
            
            if not processed_files:
                logging.warning("没有可撤销的操作")
                QMessageBox.information(self.parent(), "提示", "没有可撤销的操作")
                return
            
            # 准备批量撤销操作列表
            operations_to_undo = []
            for file_info in processed_files:
                source_path = file_info.get('source_path')
                target_path = file_info.get('target_path')
                if source_path and target_path:
                    operations_to_undo.append({'source_path': source_path, 'target_path': target_path})
            
            # 使用统一的撤销管理器执行批量撤销
            undo_results = self.undo_manager.undo_operations_batch(operations_to_undo)
            
            # 准备状态更新字典和文件信息更新字典
            status_updates = {}
            file_info_updates = {}
            for i, file_info in enumerate(processed_files):
                if i < len(undo_results):
                    source_path = file_info.get('source_path')
                    status_updates[source_path] = undo_results[i].get('status', 'undone')
                    
                    # 构建文件信息更新字典，确保包含所有必要字段
                    if undo_results[i].get('status') == 'undone':
                        # 撤销后，文件路径应该恢复为原始路径
                        file_name = file_info.get('original_name')
                        # 确保文件名为有效字符串
                        if not file_name or file_name == '未知文件名':
                            from pathlib import Path
                            file_name = Path(source_path).name
                        
                        file_info_updates[source_path] = {
                            'path': source_path,
                            'source_path': source_path,
                            'target_path': '',  # 清空目标路径
                            'new_name': file_name,
                            'original_name': file_name,
                            'message': undo_results[i].get('message', '')
                        }
            
            # 更新所有结果的状态和信息
            self.update_all_results_status(status_updates, file_info_updates)
            
            # 使用撤销管理器获取撤销结果统计
            summary = self.undo_manager.get_undo_summary(undo_results)
            
            logging.info(f"撤销操作完成: 成功 {summary['success_count']} 个, 失败 {summary['failed_count']} 个")
            
            # 显示结果消息
            if summary['success_count'] > 0:
                QMessageBox.information(self.parent(), "撤销完成", f"成功撤销 {summary['success_count']} 个文件操作\n失败 {summary['failed_count']} 个文件")
            
        except Exception as e:
            logging.error(f"撤销操作失败: {e}")
            QMessageBox.critical(self.parent(), "撤销失败", f"撤销操作失败：{str(e)}")
    
    def get_selected_files(self):
        """获取当前选中的文件列表"""
        selected_files = []
        if hasattr(self.core, 'table_operations') and hasattr(self.core.table_operations, 'selected_files'):
            # 从table_operations获取选中文件
            for file_key in self.core.table_operations.selected_files:
                # 在current_results中查找对应的文件
                for result in self.core.current_results:
                    result_key = result.get('path') or result.get('source_path')
                    if result_key == file_key:
                        selected_files.append(result)
                        break
        return selected_files

    def force_table_refresh(self):
        """强制刷新表格显示"""
        try:
            if hasattr(self, 'table'):
                # 多种刷新方式组合使用
                self.table.viewport().update()
                self.table.repaint()
                
                # 重置滚动条位置
                self.table.verticalScrollBar().setValue(0)
                self.table.horizontalScrollBar().setValue(0)
                
                # 调用核心组件的完整刷新逻辑
                if hasattr(self.core, '_force_complete_refresh'):
                    self.core._force_complete_refresh()
                
                logging.debug("预览面板表格强制刷新完成")
        except Exception as e:
            logging.error(f"预览面板表格刷新失败: {e}")
    
    def undo_selected_operations(self):
        """撤销选中文件的操作 - 使用统一的撤销管理器"""
        try:
            # 确保撤销管理器已初始化
            if not self.undo_manager:
                self.set_undo_manager()
                if not self.undo_manager:
                    QMessageBox.warning(self.parent(), "错误", "撤销管理器初始化失败")
                    return
            
            # 获取选中的文件
            selected_files = self.get_selected_files()
            
            if not selected_files:
                logging.warning("没有选中的文件")
                QMessageBox.information(self.parent(), "提示", "请先选择要撤销操作的文件")
                return
            
            # 过滤出可撤销的文件
            operations_to_undo = []
            for file_info in selected_files:
                if file_info.get('status') == 'success' and file_info.get('target_path'):
                    operations_to_undo.append({
                        'source_path': file_info.get('source_path'),
                        'target_path': file_info.get('target_path')
                    })
            
            if not operations_to_undo:
                logging.warning("选中的文件中没有可撤销的操作")
                QMessageBox.information(self.parent(), "提示", "选中的文件中没有可撤销的操作")
                return
            
            # 使用统一的撤销管理器执行批量撤销
            undo_results = self.undo_manager.undo_operations_batch(operations_to_undo)
            
            # 准备状态更新字典和文件信息更新字典
            status_updates = {}
            file_info_updates = {}
            for i, file_info in enumerate(selected_files):
                if i < len(undo_results):
                    source_path = file_info.get('source_path')
                    status_updates[source_path] = undo_results[i].get('status', 'undone')
                    
                    # 构建文件信息更新字典，包括撤销后的路径和名称等
                    if undo_results[i].get('status') == 'undone':
                        # 撤销后，文件路径应该恢复为原始路径
                        file_name = file_info.get('original_name')
                        # 确保文件名为有效字符串
                        if not file_name or file_name == '未知文件名':
                            from pathlib import Path
                            file_name = Path(source_path).name
                        
                        file_info_updates[source_path] = {
                            'path': source_path,
                            'source_path': source_path,
                            'target_path': '',  # 清空目标路径
                            'new_name': file_name,
                            'original_name': file_name,
                            'message': undo_results[i].get('message', '')
                        }
            
            # 更新所有结果的状态和信息
            self.update_all_results_status(status_updates, file_info_updates)
            
            # 使用撤销管理器获取撤销结果统计
            summary = self.undo_manager.get_undo_summary(undo_results)
            
            # 收集所有错误信息，以便向用户显示
            error_messages = []
            for result in undo_results:
                if result.get('status') == 'failed':
                    error_msg = result.get('error_message', '未知错误')
                    source_path = result.get('source_path', '未知路径')
                    target_path = result.get('target_path', '未知目标')
                    error_messages.append(f"文件: {os.path.basename(source_path) or source_path}\n错误: {error_msg}")
            
            logging.info(f"撤销选中文件操作完成: 成功 {summary['success_count']} 个, 失败 {summary['failed_count']} 个")
            
            # 显示结果消息
            if summary['success_count'] > 0:
                if summary['failed_count'] > 0:
                    # 如果有成功也有失败，显示更详细的消息
                    success_msg = f"成功撤销 {summary['success_count']} 个选中文件操作\n"
                    failure_msg = f"失败 {summary['failed_count']} 个文件\n\n错误详情：\n" + "\n\n".join(error_messages[:3])
                    if len(error_messages) > 3:
                        failure_msg += f"\n\n... 还有 {len(error_messages) - 3} 个错误未显示"
                    QMessageBox.information(self.parent(), "撤销结果", success_msg + failure_msg)
                else:
                    QMessageBox.information(self.parent(), "撤销完成", f"成功撤销 {summary['success_count']} 个选中文件操作")
            elif summary['failed_count'] > 0:
                # 如果全部失败，显示错误详情
                error_msg = f"所有 {summary['failed_count']} 个文件的撤销操作失败\n\n错误详情：\n" + "\n\n".join(error_messages[:5])
                if len(error_messages) > 5:
                    error_msg += f"\n\n... 还有 {len(error_messages) - 5} 个错误未显示"
                QMessageBox.critical(self.parent(), "撤销失败", error_msg)
            
        except Exception as e:
            logging.error(f"撤销选中文件操作失败: {e}")
            QMessageBox.critical(self.parent(), "撤销失败", f"撤销操作失败：{str(e)}")