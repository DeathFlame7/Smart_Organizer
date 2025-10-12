from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QMessageBox
from pathlib import Path
import time
import logging
import shutil

from core.workers import WorkerSignals, FileProcessingWorker
from core.undo_manager import create_undo_manager

class FileProcessorManager:
    """文件处理管理类"""
    def __init__(self, main_window):
        self.main_window = main_window
        # 初始化撤销管理器
        self.undo_manager = create_undo_manager(main_window.processor, main_window.db)
    
    def process_files(self):
        """处理文件并更新状态"""
        try:
            # 正确获取当前结果
            current_results = getattr(self.main_window.preview_panel.core, 'current_results', [])
            
            if not self.main_window.selected_dir or not current_results:
                QMessageBox.warning(self.main_window, "警告", "请先选择文件夹并完成扫描")
                return
            
            # 获取选中的文件 - 通过preview_panel.core.table_operations.selected_files
            selected_files = getattr(self.main_window.preview_panel.core.table_operations, 'selected_files', {})
            
            # 处理选中的文件，添加防御性编程逻辑
            if self._has_selected_files(selected_files):
                filtered_results = self._get_filtered_results(current_results, selected_files)
                if filtered_results:
                    self.main_window.process_selected_files(filtered_results)
                return
            
            # 若没有选中文件，询问是否处理所有文件
            msg_box = QMessageBox()
            msg_box.setWindowTitle("确认处理")
            msg_box.setText(f"未选择文件，是否处理所有 {len(current_results)} 个文件？")
            msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            msg_box.setDefaultButton(QMessageBox.Cancel)
            
            if msg_box.exec() != QMessageBox.Ok:
                return
            
            # 处理所有文件
            self._log_status("开始批量处理所有文件")
            
            # 创建信号对象并连接槽函数
            signals = WorkerSignals()
            signals.progress.connect(self.main_window.update_progress)
            signals.finished.connect(self.main_window.on_processing_finished)
            signals.error.connect(self.main_window.on_processing_error)
            
            # 生成操作批次ID
            operation_batch_id = str(int(time.time()))
            self._log_status(f"生成操作批次ID: {operation_batch_id}")
            
            # 创建工作线程，传递current_results以使用用户修改后的分类信息
            worker = FileProcessingWorker(
                directory=self.main_window.selected_dir,
                processor=self.main_window.processor,
                classifier=self.main_window.classifier,
                renamer=self.main_window.renamer,
                db=self.main_window.db,
                signals=signals,
                operation_batch_id=operation_batch_id,
                current_results=current_results  # 传递用户修改后的结果
            )
            
            # 启动线程
            worker.start()
            
            # 禁用按钮，防止重复点击
            self._disable_process_buttons()
            
        except Exception as e:
            self._handle_exception("处理文件过程中发生错误", e)
            # 启用按钮
            self._enable_process_buttons()
    
    def _has_selected_files(self, selected_files):
        """检查是否有选中的文件"""
        if isinstance(selected_files, (dict, set, list)):
            return bool(selected_files)
        elif isinstance(selected_files, int):
            # 如果是整数，也认为有选中项
            return True
        return False
    
    def _get_filtered_results(self, current_results, selected_files):
        """根据选中的文件获取过滤后的结果"""
        filtered_results = []
        
        if isinstance(selected_files, dict):
            # 处理字典类型的选中文件
            for res in current_results:
                file_key = self._get_file_identifier(res)
                if file_key in selected_files and selected_files[file_key]:
                    filtered_results.append(res)
        elif isinstance(selected_files, (set, list)):
            # 处理集合或列表类型的选中文件
            filtered_results = [res for res in current_results if self._get_file_identifier(res) in selected_files]
        elif isinstance(selected_files, int):
            # 处理整数类型的选中文件（可能是行号）
            if 0 <= selected_files < len(current_results):
                filtered_results = [current_results[selected_files]]
        else:
            # 未知类型
            logging.warning(f"未知的selected_files类型: {type(selected_files)}")
        
        return filtered_results
    
    def _get_file_identifier(self, result):
        """获取文件的唯一标识符"""
        # 尝试使用path或source_path作为唯一标识符
        return result.get('path') or result.get('source_path') or str(result.get('id', ''))
        
    def update_progress(self, value):
        """更新处理进度"""
        self.main_window.status_text.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 处理进度：{value}%")
        # 使用正确的QTextCursor常量
        self.main_window.status_text.moveCursor(QTextCursor.End)
    
    def on_processing_finished(self, results):
        """处理完成后的回调"""
        # 处理完成后更新界面
        self.main_window.current_results = results
        
        # 更新核心数据和强制刷新表格
        self._update_and_refresh_table(results)
        
        # 刷新文件树
        self.main_window.file_tree.refresh()
        
        # 启用相关按钮
        self.main_window.undo_btn.setEnabled(True)
        self._enable_process_buttons()
        
        # 显示完成消息
        success_count = sum(1 for result in results if result['status'] == 'success')
        failed_count = sum(1 for result in results if result['status'] == 'failed')
        
        self._log_status("文件处理完成")
        self._log_status(f"成功: {success_count} 个文件, 失败: {failed_count} 个文件")
        
        QMessageBox.information(self.main_window, "处理完成", f"文件处理完成！\n成功: {success_count} 个文件\n失败: {failed_count} 个文件")
    
    def on_processing_error(self, error_msg):
        """处理过程中出错的回调"""
        self._log_status(f"处理错误: {error_msg}")
        QMessageBox.critical(self.main_window, "处理错误", f"处理过程中发生错误：{error_msg}")
        
        # 启用按钮
        self._enable_process_buttons()
    
    def process_single_file(self, file_info):
        """处理单个文件"""
        file_path = Path(file_info['path'])
        
        msg_box = QMessageBox()
        msg_box.setWindowTitle("确认处理单个文件")
        msg_box.setText(f"将对以下文件执行操作：\n{file_path.name}")
        msg_box.setInformativeText(
            f"1. 移动到 '{file_info['category']}' 目录\n" \
            f"2. 智能重命名文件\n" \
            "\n操作不可撤销，是否继续？"
        )
        msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg_box.setDefaultButton(QMessageBox.Cancel)
        
        if msg_box.exec() != QMessageBox.Ok:
            return
        
        self._log_status(f"开始处理单个文件: {file_path.name}")
        
        try:
            # 使用内部方法处理单个文件
            result = self._process_single_file(file_info)
            
            # 显示处理结果
            if result['status'] == 'success':
                QMessageBox.information(
                    self.main_window, 
                    "处理完成",
                    f"文件处理成功！\n源文件：{file_path.name}\n目标文件：{result['target_path']}"
                )
                # 在文件管理器中选中处理后的文件
                self.main_window.select_file_in_explorer(result['target_path'])
            else:
                QMessageBox.critical(
                    self.main_window, 
                    "处理失败",
                    f"文件处理失败：\n{result['error']}"
                )
            
            # 更新预览面板，不重新扫描以保持处理状态
            updated_results = [res for res in self.main_window.current_results if res.get('path') != str(file_path)]
            updated_results.append(result)
            self.main_window.current_results = updated_results
            
            # 更新核心数据和强制刷新表格
            self._update_and_refresh_table(updated_results)
            
            # 刷新文件树显示
            self.main_window.file_tree.refresh()
            
        except Exception as e:
            error_msg = str(e)
            self._log_status(f"文件处理失败 {file_path.name}: {error_msg}")
            QMessageBox.critical(
                self.main_window, 
                "处理失败",
                f"文件处理异常：\n{error_msg}"
            )
    
    def _process_single_file(self, file_info, operation_batch_id=None):
        """内部方法：处理单个文件的实际逻辑"""
        file_path = Path(file_info['path'])
        
        try:
            # 获取文件信息
            file_info_dict = self.main_window.processor.get_file_info(file_path)
            
            # 提取文件内容
            content = self.main_window.processor.extract_text_content(file_path)
            
            # 使用已确定的分类或重新分类
            category = file_info['category'] if 'category' in file_info else \
                       self.main_window.classifier.predict_with_confidence(content)[0]
            
            # 生成新文件名 - 优先使用用户自定义的文件名
            new_name = self._get_new_file_name(file_info, file_info_dict, content, file_path)
            
            # 确定目标路径 - 确保整理后的目录与所选文件夹同级
            target_dir = self.main_window.selected_dir / category
            target_dir.mkdir(exist_ok=True)
            target_path = target_dir / new_name
            
            # 检查文件是否已存在并处理
            target_path = self._handle_file_conflict(target_path)
            
            # 使用shutil.move代替os.rename，支持跨文件系统移动
            shutil.move(str(file_path), str(target_path))
            
            # 记录操作
            self.main_window.db.insert_operation(
                op_type="classify_rename",
                source_path=str(file_path),
                target_path=str(target_path),
                status="success",
                timestamp=time.time(),
                category=category,
                content=content,
                batch_id=operation_batch_id  # 添加批次ID
            )
            
            self._log_status(f"文件处理成功：{file_path.name} → {target_path}")
            
            return self._create_success_result(file_path, new_name, category, file_info, file_info_dict, target_path)
            
        except Exception as e:
            error_msg = str(e)
            self._log_status(f"文件处理失败 {file_path.name}: {error_msg}")
            
            # 记录失败操作
            self.main_window.db.insert_operation(
                op_type="classify_rename",
                source_path=str(file_path),
                target_path="",
                status="failed",
                timestamp=time.time(),
                category="处理失败",
                content="",
                batch_id=operation_batch_id  # 添加批次ID
            )
            
            return self._create_failure_result(file_path, error_msg, file_info_dict)
    
    def _get_new_file_name(self, file_info, file_info_dict, content, file_path):
        """获取新的文件名，优先使用用户自定义的文件名"""
        if 'new_name' in file_info and file_info['new_name'] and file_info['new_name'].strip():
            return file_info['new_name'].strip()
        else:
            file_type = file_info_dict.get('mime_type', 'unknown') if file_info_dict else 'unknown'
            original_name = file_info_dict.get('name', file_path.name) if file_info_dict else file_path.name
            return self.main_window.renamer.generate_name(
                content=content,
                file_type=file_type,
                original_name=original_name,
                file_path=file_path
            )
    
    def _handle_file_conflict(self, target_path):
        """处理文件冲突，添加时间戳后缀"""
        if target_path.exists():
            timestamp = int(time.time())
            new_name = f"{target_path.stem}_{timestamp}{target_path.suffix}"
            target_path = target_path.parent / new_name
        return target_path
    
    def _create_success_result(self, file_path, new_name, category, file_info, file_info_dict, target_path):
        """创建处理成功的结果字典"""
        return {
            'original_name': file_path.name,
            'new_name': new_name,
            'category': category,
            'confidence': file_info.get('confidence', 0.0),
            'source_path': str(file_path),
            'target_path': str(target_path),
            'type': file_info_dict.get('mime_type', 'unknown') if file_info_dict else 'unknown',
            'size': file_info_dict.get('size', 0) if file_info_dict else 0,
            'status': 'success'
        }
    
    def _create_failure_result(self, file_path, error_msg, file_info_dict=None):
        """创建处理失败的结果字典"""
        return {
            'original_name': file_path.name,
            'new_name': file_path.name,
            'category': "处理失败",
            'confidence': 0.0,
            'source_path': str(file_path),
            'target_path': "",
            'type': file_info_dict.get('mime_type', 'unknown') if file_info_dict else 'unknown',
            'size': file_info_dict.get('size', 0) if file_info_dict else 0,
            'status': 'failed',
            'error': error_msg
        }
    
    def process_selected_files(self, selected_files):
        """处理用户在预览面板中选择的多个文件"""
        if not selected_files:
            QMessageBox.warning(self.main_window, "警告", "请先选择要处理的文件")
            return
        
        self._log_status(f"开始处理 {len(selected_files)} 个选定文件")
        
        # 生成操作批次ID
        operation_batch_id = str(int(time.time()))
        self._log_status(f"生成操作批次ID: {operation_batch_id}")
        
        # 禁用按钮
        self._disable_process_buttons()
        
        # 处理每个选定的文件
        processed_results = []
        processed_file_paths = []
        
        # 获取原始结果列表
        original_results = getattr(self.main_window.preview_panel.core, 'current_results', [])
        
        # 处理每个文件并更新状态
        for item in selected_files:
            file_info, file_path = self._get_file_info_from_item(item)
            if not file_info or not file_path:
                continue
            
            try:
                # 处理文件逻辑，传递批次ID
                result = self._process_single_file(file_info, operation_batch_id)
                
                # 确保状态正确传递
                if 'status' not in result:
                    result['status'] = 'success'  # 默认成功
                
                processed_results.append(result)
                processed_file_paths.append(file_path)
                
            except Exception as e:
                logging.error(f"处理文件失败 {file_info.get('original_name', '未知文件')}: {e}")
                result = self._create_failure_result(file_path, str(e), file_info)
                processed_results.append(result)
                processed_file_paths.append(file_path)
            
        # 更新原始结果列表中已处理的文件
        updated_results = self._update_processed_results(original_results, processed_results, processed_file_paths)
        
        # 更新核心数据和强制刷新表格
        self._update_and_refresh_table(updated_results)
        
        # 刷新文件树
        self.main_window.file_tree.refresh()
        
        # 启用按钮
        self.main_window.undo_btn.setEnabled(True)
        self._enable_process_buttons()
        
        # 统计成功和失败的文件数量
        success_count = sum(1 for result in processed_results if result['status'] == 'success')
        failed_count = sum(1 for result in processed_results if result['status'] == 'failed')
        
        # 显示处理摘要 - 使用中心渐变提示
        self.show_center_message(f"文件处理完成！\n成功: {success_count} 个文件\n失败: {failed_count} 个文件", success_count, failed_count)
        
    def _get_file_info_from_item(self, item):
        """从选中项中获取文件信息和路径"""
        if isinstance(item, dict):
            # 正常情况：item是完整的文件信息字典
            file_info = item
            file_path = Path(file_info.get('path', ''))
        elif isinstance(item, (str, Path)):
            # 如果item是文件路径字符串或Path对象
            file_path = Path(item)
            # 尝试从current_results中查找对应的文件信息
            file_info = next((res for res in self.main_window.preview_panel.core.current_results 
                            if res.get('path') == str(file_path)), None)
            if not file_info:
                logging.warning(f"无法找到文件路径对应的文件信息: {file_path}")
                return None, None
        else:
            # 如果item是整数（可能是行号）或其他未知类型
            logging.warning(f"跳过未知类型的选中项: {type(item)}, 值: {item}")
            return None, None
        
        return file_info, file_path
    
    def _update_processed_results(self, original_results, processed_results, processed_file_paths):
        """更新原始结果列表中已处理的文件"""
        updated_results = []
        
        for result in original_results:
            result_path = None
            # 检查'path'键是否存在，如果不存在则尝试使用'source_path'
            if 'path' in result:
                result_path = Path(result['path'])
            elif 'source_path' in result:
                result_path = Path(result['source_path'])
            
            if result_path:
                # 检查这个文件是否已经被处理
                processed_index = -1
                for i, processed_path in enumerate(processed_file_paths):
                    if result_path == processed_path:
                        processed_index = i
                        break
                
                if processed_index != -1:
                    # 如果已处理，使用处理后的结果
                    updated_results.append(processed_results[processed_index])
                    continue
            else:
                # 如果两个键都不存在，记录警告
                logging.warning(f"结果缺少path和source_path字段: {result}")
            
            # 如果未处理，保留原始结果
            updated_results.append(result)
        
        return updated_results
    
    def _update_and_refresh_table(self, results):
        """更新表格数据并强制刷新显示"""
        # 更新核心数据
        core = getattr(self.main_window.preview_panel, 'core', None)
        if core:
            if hasattr(core, 'filtered_results'):
                core.filtered_results = results
            if hasattr(core, 'current_results'):
                core.current_results = results
            if hasattr(core, 'original_results'):
                core.original_results = results
        
        # 获取数据显示组件
        data_display = getattr(core, 'data_display', None)
        if data_display:
            # 强制刷新表格数据显示
            if hasattr(data_display, 'force_table_refresh'):
                data_display.force_table_refresh()
            
            # 对每个文件执行单独的行数据更新，确保完整显示
            for row, result in enumerate(results):
                if hasattr(data_display, '_set_row_data'):
                    data_display._set_row_data(row, result)
            
            # 最后执行一次全面刷新
            if hasattr(data_display, '_full_refresh'):
                data_display._full_refresh()
        
        # 强制表格视图更新
        table = getattr(self.main_window.preview_panel, 'table', None)
        if table:
            table.viewport().update()
            table.repaint()
    
    def show_center_message(self, message, success_count, failed_count):
        """使用ResultPopup显示处理结果消息"""
        try:
            from gui.window_components.result_popup import ResultPopup
            ResultPopup(self.main_window, success_count, failed_count)
        except ImportError as e:
            logging.error(f"导入ResultPopup失败: {e}")
            # 如果无法导入ResultPopup，使用QMessageBox代替
            QMessageBox.information(self.main_window, "处理完成", message)
    
    def undo_last_operation(self):
        """撤销所有已处理文件的操作 - 使用表格区域的撤销按钮实现逻辑"""
        try:
            # 检查预览面板是否存在
            if not hasattr(self.main_window, 'preview_panel'):
                QMessageBox.warning(self.main_window, "错误", "预览面板初始化失败")
                return
            
            # 确保撤销管理器已初始化
            if not hasattr(self.main_window.preview_panel, 'undo_manager') or not self.main_window.preview_panel.undo_manager:
                # 调用表格区域的撤销管理器设置方法
                if hasattr(self.main_window.preview_panel, 'set_undo_manager'):
                    self.main_window.preview_panel.set_undo_manager()
                if not hasattr(self.main_window.preview_panel, 'undo_manager') or not self.main_window.preview_panel.undo_manager:
                    QMessageBox.warning(self.main_window, "错误", "撤销管理器初始化失败")
                    return
            
            # 获取所有成功处理的文件（从当前结果列表中获取）
            processed_files = []
            core = getattr(self.main_window.preview_panel, 'core', None)
            if core and hasattr(core, 'current_results'):
                for result in core.current_results:
                    if isinstance(result, dict) and result.get('status') == 'success' and result.get('target_path'):
                        processed_files.append(result)
            
            if not processed_files:
                logging.warning("没有可撤销的操作")
                QMessageBox.information(self.main_window, "提示", "没有可撤销的操作")
                return
            
            # 准备批量撤销操作列表
            operations_to_undo = []
            for file_info in processed_files:
                source_path = file_info.get('source_path')
                target_path = file_info.get('target_path')
                if source_path and target_path:
                    operations_to_undo.append({'source_path': source_path, 'target_path': target_path})
            
            # 使用统一的撤销管理器执行批量撤销
            undo_results = self.main_window.preview_panel.undo_manager.undo_operations_batch(operations_to_undo)
            
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
            if hasattr(self.main_window.preview_panel, 'update_all_results_status'):
                self.main_window.preview_panel.update_all_results_status(status_updates, file_info_updates)
            
            # 使用撤销管理器获取撤销结果统计
            summary = self.main_window.preview_panel.undo_manager.get_undo_summary(undo_results)
            
            logging.info(f"撤销操作完成: 成功 {summary['success_count']} 个, 失败 {summary['failed_count']} 个")
            
            # 记录状态信息
            self._log_status(f"撤销操作完成: 成功 {summary['success_count']} 个, 失败 {summary['failed_count']} 个")
            
            # 重新扫描文件树
            self.main_window.file_tree.refresh()
            
            # 显示结果消息
            if summary['success_count'] > 0:
                QMessageBox.information(self.main_window, "撤销完成", 
                                       f"成功撤销 {summary['success_count']} 个文件操作\n失败 {summary['failed_count']} 个文件")
                
        except Exception as e:
            logging.error(f"撤销操作失败: {e}")
            self._log_status(f"撤销操作失败: {str(e)}")
            QMessageBox.critical(self.main_window, "撤销失败", f"撤销操作失败：{str(e)}")
    
    def _confirm_undo_operation(self, operations):
        """确认撤销操作"""
        msg_box = QMessageBox()
        msg_box.setWindowTitle("确认撤销")
        
        # 检查是否有批次ID
        has_batch_id = operations[0].get('batch_id') is not None
        
        if len(operations) == 1:
            op = operations[0]
            if has_batch_id:
                msg_box.setText(f"是否撤销上一次操作？\n类型：{op['operation_type']}\n文件：{Path(op['source_path']).name}\n时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(op['timestamp']))}\n批次ID：{op['batch_id']}")
            else:
                msg_box.setText(f"是否撤销上一次操作？\n类型：{op['operation_type']}\n文件：{Path(op['source_path']).name}\n时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(op['timestamp']))}")
        else:
            if has_batch_id:
                msg_box.setText(f"是否撤销上一次操作批次？\n共包含 {len(operations)} 个文件操作\n批次ID：{operations[0]['batch_id']}\n时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(operations[0]['timestamp']))}")
            else:
                msg_box.setText(f"是否撤销上一次操作批次？\n共包含 {len(operations)} 个文件操作\n时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(operations[0]['timestamp']))}")
        
        msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg_box.setDefaultButton(QMessageBox.Cancel)
        
        return msg_box.exec() == QMessageBox.Ok
    
    def _prepare_operations_to_undo(self, operations):
        """准备要撤销的操作列表"""
        operations_to_undo = []
        
        for i, op in enumerate(operations):
            # 先检查op是否为字典类型，再调用get方法
            if isinstance(op, dict):
                if op.get('operation_type') == "classify_rename" and op.get('status') == "success":
                    source_path = op.get('source_path')
                    target_path = op.get('target_path')
                    
                    if source_path and target_path:
                        operations_to_undo.append({
                            'source_path': source_path,
                            'target_path': target_path
                        })
                    else:
                        logging.warning(f"撤销操作[{i}]缺少源路径或目标路径")
                else:
                    # 确保op是字典类型才调用get方法
                    if isinstance(op, dict):
                        logging.warning(f"操作[{i}]不满足撤销条件: 类型={op.get('operation_type')}, 状态={op.get('status')}")
                    else:
                        logging.warning(f"操作[{i}]不满足撤销条件: 非字典类型={type(op)}")
            else:
                continue
        
        return operations_to_undo
    
    def _prepare_status_updates(self, operations, undo_results):
        """准备状态更新字典 - 增强健壮性"""
        status_updates = {}
        file_paths = []
        
        # 确保operations是列表
        if not isinstance(operations, list):
            operations = []
            logging.warning("_prepare_status_updates: operations不是列表类型，已转换为空列表")
            
        # 确保undo_results是列表
        if not isinstance(undo_results, list):
            undo_results = [undo_results] if undo_results is not None else []
            logging.warning("_prepare_status_updates: undo_results不是列表类型，已尝试转换")
        
        for i, op in enumerate(operations):
            # 确保op是字典类型并且包含source_path键
            if isinstance(op, dict) and 'source_path' in op:
                try:
                    # 获取源路径
                    source_path = op['source_path']
                    
                    # 检查索引是否在范围内
                    if i < len(undo_results):
                        # 确保undo_results[i]是字典类型
                        if isinstance(undo_results[i], dict):
                            status_value = undo_results[i].get('status', 'undone')
                            status_updates[source_path] = status_value
                            file_paths.append(source_path)
                        else:
                            # 如果undo_result不是字典，默认设为'undone'
                            status_updates[source_path] = 'undone'
                            file_paths.append(source_path)
                            logging.warning(f"_prepare_status_updates: undo_results[{i}]不是字典类型: {type(undo_results[i])}")
                    else:
                        # 没有对应的撤销结果，默认设为'undone'
                        status_updates[source_path] = 'undone'
                        file_paths.append(source_path)
                except (TypeError, ValueError) as e:
                    logging.warning(f"_prepare_status_updates: 处理操作{i}失败: {e}")
            elif not isinstance(op, dict):
                logging.warning(f"_prepare_status_updates: operations[{i}]不是字典类型: {type(op)}")
            else:
                logging.warning(f"_prepare_status_updates: operations[{i}]缺少source_path键")
        
        return status_updates, file_paths
    
    def _update_results_status(self, status_updates, operations, undo_results=None):
        """更新结果的状态和文件信息
        
        Args:
            status_updates: 状态更新字典 {文件路径: 新状态}
            operations: 操作列表
            undo_results: 撤销结果列表，用于获取详细的撤销信息
        """
        
        # 确保status_updates是字典
        if not isinstance(status_updates, dict):
            status_updates = {}
            logging.warning("status_updates不是字典类型，已转换为空字典")
        
        # 确保operations是列表
        if not isinstance(operations, list):
            operations = []
            logging.warning("operations不是列表类型，已转换为空列表")
        
        # 确保undo_results有默认值且是列表类型
        if undo_results is None:
            undo_results = []
        elif not isinstance(undo_results, list):
            undo_results = [undo_results]  # 尝试转换为列表
            logging.warning("undo_results不是列表类型，已转换为包含单个元素的列表")
        
        if hasattr(self.main_window.preview_panel, 'update_all_results_status'):
            # 创建文件信息更新字典，为每个文件构建完整、安全的更新信息
            file_info_updates = {}
            
            # 构建文件路径到撤销结果的映射 - 增强健壮性
            undo_result_map = {}
            for result in undo_results:
                # 确保result是字典类型并且包含source_path键
                if isinstance(result, dict) and 'source_path' in result:
                    try:
                        undo_result_map[result['source_path']] = result
                    except (TypeError, ValueError) as e:
                        logging.warning(f"添加撤销结果到映射失败: {e}")
                elif not isinstance(result, dict):
                    logging.warning(f"撤销结果不是字典类型: {type(result)}")
            
            for op in operations:
                source_path = op.get('source_path')
                if not source_path:
                    continue
                
                # 从原始结果中找到对应文件的完整信息
                original_result = None
                for result in self.main_window.current_results:
                    if result.get('path') == source_path or result.get('source_path') == source_path:
                        original_result = result
                        break
                
                # 获取对应的撤销结果
                undo_result = undo_result_map.get(source_path, {})
                
                # 构建完整、安全的文件信息更新字典
                file_info = {
                    'path': source_path,  # 撤销后恢复到原始路径
                    'source_path': source_path,
                    'target_path': '',  # 清空目标路径
                    'status': status_updates.get(source_path, 'undone'),
                    'message': undo_result.get('message', '')
                }
                
                # 如果有原始结果，从中提取额外信息
                if original_result and isinstance(original_result, dict):
                    file_info.update({
                        'new_name': original_result.get('original_name', ''),
                        'original_name': original_result.get('original_name', ''),
                        'category': original_result.get('category', ''),
                        'type': original_result.get('type', ''),
                        'size': original_result.get('size', 0),
                        'confidence': original_result.get('confidence', 0.0)
                    })
                
                # 确保所有值都是基本数据类型（字符串、数字、布尔值）
                for key, value in list(file_info.items()):
                    if not isinstance(value, (str, int, float, bool, type(None))):
                        file_info[key] = str(value)
                
                file_info_updates[source_path] = file_info
            
            # 调用update_all_results_status同时更新状态和文件信息
            self.main_window.preview_panel.update_all_results_status(status_updates, file_info_updates)
        else:
            # 备用方案：直接更新当前结果中的文件状态
            for result in self.main_window.current_results:
                if not isinstance(result, dict):
                    continue
                
                source_path = result.get('source_path') or result.get('path')
                if source_path in status_updates:
                    result['status'] = status_updates[source_path]
    
    def _force_refresh_table(self):
        """强制刷新表格显示"""
        # 获取核心组件和数据显示组件
        core = getattr(self.main_window.preview_panel, 'core', None)
        data_display = getattr(core, 'data_display', None)
        
        if data_display:
            if hasattr(data_display, '_full_refresh'):
                data_display._full_refresh()
        
        # 强制表格视图更新
        table = getattr(self.main_window.preview_panel, 'table', None)
        if table:
            table.viewport().update()
            table.repaint()
    
    def _log_undo_results(self, summary, undo_results, operations_to_undo):
        """记录撤销结果到日志"""
        self._log_status(f"撤销操作完成: 成功 {summary['success_count']} 个, 失败 {summary['failed_count']} 个")
        
        # 记录每个文件的撤销详情
        for i, result in enumerate(undo_results):
            if i < len(operations_to_undo):
                op = operations_to_undo[i]
                if result['status'] == 'undone':
                    self._log_status(f"撤销成功: {Path(op['target_path']).name} → {Path(op['source_path']).name}")
                else:
                    error_msg = result.get('error_message', '撤销失败')
                    self._log_status(f"撤销失败: {Path(op['target_path']).name} → {Path(op['source_path']).name}, 原因: {error_msg}")
    
    def _log_status(self, message):
        """记录状态信息到日志"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        self.main_window.status_text.append(f"[{timestamp}] {message}")
        self.main_window.status_text.moveCursor(QTextCursor.End)
    
    def _handle_exception(self, title, exception):
        """处理异常"""
        error_msg = str(exception)
        logging.error(f"{title}: {error_msg}")
        self._log_status(f"{title}: {error_msg}")
        QMessageBox.critical(self.main_window, "错误", f"{title}：{error_msg}")
    
    def _disable_process_buttons(self):
        """禁用处理相关的按钮"""
        self.main_window.process_btn.setEnabled(False)
        self.main_window.reselect_btn.setEnabled(False)
        self.main_window.reset_btn.setEnabled(False)
    
    def _enable_process_buttons(self):
        """启用处理相关的按钮"""
        self.main_window.process_btn.setEnabled(True)
        self.main_window.reselect_btn.setEnabled(True)
        self.main_window.reset_btn.setEnabled(True)