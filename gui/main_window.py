import os
import time
import subprocess  # 用于Windows文件管理器选中文件
import sys
from pathlib import Path
import logging
from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QWidget, QFileDialog,
                               QPushButton, QTextEdit, QLabel, QMessageBox,
                               QProgressDialog, QHBoxLayout, QFrame,
                               QSizePolicy, QStackedWidget, QSplitter, QApplication)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QRect, QThread, QDateTime

from PySide6.QtGui import QFont, QColor, QLinearGradient, QPalette, QTextCursor

from core.database import FileDatabase
from core.file_processor import FileProcessor
from core.classifier import FileClassifier
from core.renamer import FileRenamer
from core.workers import WorkerSignals, FileProcessingWorker, FileScanWorker
from gui.file_tree import FileTreeView
from gui.preview_panel import PreviewPanel
from gui.components import WindowControls, GradientBackground
from utils.config import load_config, get_config_value

# 导入拆分出去的模块
from gui.window_components.result_popup import ResultPopup
from gui.window_components.window_initializer import WindowInitializer
from gui.window_components.file_processor_manager import FileProcessorManager
from gui.window_components.settings_manager import SettingsManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 设置无边框窗口
        self.setWindowFlags(Qt.FramelessWindowHint)
        # 设置窗口标题和大小
        self.setWindowTitle("智理 - 智能文件管理助手")
        self.setGeometry(100, 100, 1000, 750)
        
        # 初始化核心组件
        self.db = FileDatabase()
        self.processor = FileProcessor()
        self.classifier = FileClassifier()
        self.renamer = FileRenamer()
        self.selected_dir = None
        self.current_results = []
        
        # 初始化管理器
        self.window_initializer = WindowInitializer(self)
        self.file_processor_manager = FileProcessorManager(self)
        self.settings_manager = SettingsManager(self)
        
        # 异步处理相关属性
        self.scan_thread = None
        self.scan_progress = None
        
        # 创建界面容器
        self.setup_ui()
        
        # 确保核心组件已初始化
        assert hasattr(self, 'preview_panel'), "preview_panel 未初始化"
        assert hasattr(self, 'file_tree'), "file_tree 未初始化"
        
        # 拖动窗口相关属性
        self.dragging = False
        self.drag_position = None
        self.is_maximized = False
        
        # 窗口调整大小相关属性
        self.resizing = False
        self.resize_direction = None  # 'left', 'right', 'top', 'bottom', 'topleft', 'topright', 'bottomleft', 'bottomright'
        self.edge_width = 15  # 边缘检测宽度，增加到15像素以提高用户体验
        
        # 性能优化相关属性
        self.last_paint_time = 0
        self.paint_interval = 50  # 50ms内只重绘一次，减少高频操作导致的UI卡顿
        
        # 窗口最小尺寸限制
        self.setMinimumSize(800, 600)
    
    def toggle_maximize(self):
        """切换窗口最大化状态"""
        if self.is_maximized:
            self.showNormal()
            self.is_maximized = False
        else:
            self.showMaximized()
            self.is_maximized = True
    
    def get_process_button_style(self):
        """获取处理按钮的样式表"""
        return """
            QPushButton {
                padding: 10px 20px;
                font-size: 14px;
                background-color: #4CAF50;
                color: white;
                border-radius: 20px;
                border: none;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """
    
    def setup_ui(self):
        # 使用WindowInitializer来设置UI
        self.window_initializer.setup_ui()
    
    def select_folder_and_show_main(self):
        directory = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if directory:
            self.selected_dir = Path(directory)
            self.scan_and_preview()
            self.stacked_widget.setCurrentWidget(self.main_screen)
            # 显示返回按钮
            self.title_bar.back_btn.show()
            # 显示标题文本
            self.title_bar.title_label.setText("智能文件管理助手")
    
    def select_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if directory:
            self.selected_dir = Path(directory)
            self.scan_and_preview()
    
    def show_start_screen(self):
        # 重置状态
        self.selected_dir = None
        self.current_results = []
        self.undo_btn.setEnabled(False)
        self.process_btn.setEnabled(False)
        # 切换到起始界面
        self.stacked_widget.setCurrentWidget(self.start_screen)
        # 隐藏返回按钮
        self.title_bar.back_btn.hide()
        # 清空标题文本
        self.title_bar.title_label.setText("")
    
    def update_progress(self, value):
        """更新异步处理的进度条"""
        if self.scan_progress and self.scan_progress.isVisible():
            self.scan_progress.setValue(value)
            
    def on_scan_error(self, error_msg):
        """处理异步扫描过程中的错误"""
        self.status_text.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 扫描错误: {error_msg}")
        
    def on_processing_error(self, error_msg):
        """处理异步处理过程中的错误"""
        self.status_text.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 异步处理错误: {error_msg}")
        QMessageBox.critical(self, "处理错误", error_msg)
        # 清理线程和进度条
        self._cleanup_scan_resources()
        self.process_btn.setEnabled(True)
        
    def process_selected_files(self, selected_files):
        """处理用户在预览面板中选择的多个文件"""
        if hasattr(self, 'file_processor_manager'):
            self.file_processor_manager.process_selected_files(selected_files)
            
    def on_preview_updated(self, updated_results, update_info):
        """处理预览面板更新信号"""
        # 确保接收到的参数格式正确
        if isinstance(updated_results, list) and isinstance(update_info, dict):
            self.current_results = updated_results
            # 更新文件树
            if hasattr(self, 'file_tree') and self.selected_dir:
                self.file_tree.load_directory(self.selected_dir)
        else:
            logging.warning(f"预览更新信号参数类型不正确: results={type(updated_results)}, info={type(update_info)}")
        
    def on_file_processed(self, result):
        """处理单个文件分析完成的信号"""
        # 可以在这里添加实时更新UI的逻辑
        # 例如显示已处理文件的数量
        pass
        
    def on_processing_finished(self, results):
        """异步处理完成后的回调"""
        # 保存当前结果
        self.current_results = results
        
        # 显示预览
        self.preview_panel.show_preview(results)
        
        # 加载文件树
        self.file_tree.load_directory(self.selected_dir)
        
        # 清理线程和进度条
        self._cleanup_scan_resources()
        
        # 启用处理按钮
        self.process_btn.setEnabled(True)
        self.status_text.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 文件分析完成")
        
    def _cleanup_scan_resources(self):
        """清理异步扫描的资源"""
        # 移除进度条
        if self.scan_progress:
            self.statusBar().removeWidget(self.scan_progress)
            self.scan_progress = None
        
        # 停止并清理线程，添加超时控制
        if self.scan_thread and self.scan_thread.isRunning():
            # 发送中断请求
            if hasattr(self.scan_thread, 'requestInterruption'):
                self.scan_thread.requestInterruption()
            
            # 请求线程退出
            self.scan_thread.quit()
            
            # 等待线程结束，最多等待1秒
            if not self.scan_thread.wait(1000):
                # 如果超时，记录警告日志
                logging.warning("扫描线程清理超时，可能已强制终止")
        
        # 无论如何都将线程引用设为None
        self.scan_thread = None
        
    def scan_and_preview(self):
        if not self.selected_dir or not self.selected_dir.exists():
            QMessageBox.warning(self, "警告", "请选择有效的文件夹路径")
            return
        
        try:
            # 清空预览面板和日志
            self.preview_panel.clear()
            self.status_text.clear()
        
            # 扫描目录
            self.status_text.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 正在扫描目录：{self.selected_dir}")
            files = self.processor.scan_directory(self.selected_dir)
        
            if not files:
                self.status_text.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 未找到支持的文件")
                QMessageBox.information(self, "提示", "未找到支持的文件")
                return
        
            self.status_text.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 发现 {len(files)} 个支持的文件")
        
            # 禁用处理按钮以防止重复操作
            self.process_btn.setEnabled(False)
        
            # 为了避免UI线程阻塞，我们根据文件数量选择不同的处理策略
            if len(files) <= 50:  # 少量文件时使用同步处理以获得更好的响应性
                # 显示进度对话框
                progress = QProgressDialog("正在分析文件...", "取消", 0, len(files), self)
                progress.setWindowTitle("文件分析")
                progress.setWindowModality(Qt.WindowModal)
                progress.setValue(0)
        
                # 分析文件并显示预览
                results = []
                for i, file_info in enumerate(files):
                    if progress.wasCanceled():
                        self.status_text.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 操作已取消")
                        self.process_btn.setEnabled(True)
                        return
        
                    try:
                        file_path = Path(file_info['path'])
                        content = self.processor.extract_text_content(file_path)
                        category, confidence = self.classifier.predict_with_confidence(content)
        
                        # 生成新文件名预览
                        new_name = self.renamer.generate_name(
                            content=content,
                            file_type=file_info['mime_type'],
                            original_name=file_info['name'],
                            file_path=file_path
                        )
        
                        # 构建结果字典
                        result = {
                            'original_name': file_info['name'],
                            'new_name': new_name,
                            'category': category,
                            'confidence': confidence,
                            'source_path': str(file_path),
                            'path': str(file_path),  # 为了兼容preview_panel的使用
                            'type': file_info.get('mime_type', 'unknown'),
                            'size': file_info.get('size', 0),
                            'content': content
                        }
                        results.append(result)
        
                    except PermissionError as e:
                        error_msg = str(e)
                        self.status_text.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 分析文件失败(权限不足) {file_info['name']}: {error_msg}")
                    except FileNotFoundError as e:
                        error_msg = str(e)
                        self.status_text.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 分析文件失败(文件未找到) {file_info['name']}: {error_msg}")
                    except Exception as e:
                        error_msg = str(e)
                        self.status_text.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 分析文件失败 {file_info['name']}: {error_msg}")
                          
                        # 添加失败的文件信息到结果
                        results.append({
                            'original_name': file_info['name'],
                            'new_name': file_info['name'],
                            'category': "分析失败",
                            'confidence': 0.0,
                            'source_path': str(file_info['path']),
                            'path': str(file_info['path']),
                            'type': file_info.get('mime_type', 'unknown'),
                            'size': file_info.get('size', 0),
                            'status': 'failed',
                            'error': error_msg
                        })
        
                    # 更新进度
                    progress.setValue(i + 1)
                    # 处理UI事件，确保界面响应
                    QApplication.processEvents()
        
                # 保存当前结果
                self.current_results = results
        
                # 显示预览
                self.preview_panel.show_preview(results)
        
                # 加载文件树
                self.file_tree.load_directory(self.selected_dir)
        
                # 启用处理按钮
                self.process_btn.setEnabled(True)
                self.status_text.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 文件分析完成")
            else:  # 大量文件时使用异步处理，避免UI阻塞
                self.status_text.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 发现大量文件，启动异步分析...")
        
                # 创建进度条
                self.scan_progress = QProgressBar()
                self.scan_progress.setRange(0, 100)
                self.statusBar().addWidget(self.scan_progress)
        
                # 创建信号和工作线程
                signals = WorkerSignals()
                signals.progress.connect(self.update_progress)
                signals.finished.connect(self.on_processing_finished)
                signals.error.connect(self.on_scan_error)
        
                self.scan_thread = QThread()
                self.scan_worker = FileScanWorker(
                    files=files,
                    processor=self.processor,
                    classifier=self.classifier,
                    renamer=self.renamer
                )
                self.scan_worker.moveToThread(self.scan_thread)
        
                # 连接信号和槽
                self.scan_thread.started.connect(self.scan_worker.run)
                self.scan_worker.progress_updated.connect(self.update_progress)
                self.scan_worker.scan_completed.connect(self.on_processing_finished)
                self.scan_worker.scan_error.connect(self.on_scan_error)
                self.scan_worker.file_processed.connect(self.on_file_processed)
        
                # 启动线程
                self.scan_thread.start()
        
        except PermissionError as e:
            self.status_text.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 权限错误：{str(e)}")
            QMessageBox.critical(self, "权限错误", f"没有足够的权限访问文件或目录：{str(e)}")
            # 确保按钮被重新启用
            self.process_btn.setEnabled(True)
        except FileNotFoundError as e:
            self.status_text.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 文件未找到：{str(e)}")
            QMessageBox.critical(self, "文件未找到", f"找不到指定的文件或目录：{str(e)}")
            # 确保按钮被重新启用
            self.process_btn.setEnabled(True)
        except OSError as e:
            self.status_text.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 操作系统错误：{str(e)}")
            QMessageBox.critical(self, "操作系统错误", f"操作文件系统时发生错误：{str(e)}")
            # 确保按钮被重新启用
            self.process_btn.setEnabled(True)
        except Exception as e:
            self.status_text.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 扫描过程发生未知错误：{str(e)}")
            QMessageBox.critical(self, "未知错误", f"扫描过程发生未知错误：{str(e)}")
            # 确保按钮被重新启用
            self.process_btn.setEnabled(True)
    
    def process_files(self):
        # 延迟初始化file_processor_manager，确保所有组件都已创建
        if not hasattr(self, 'file_processor_manager'):
            from gui.window_components.file_processor_manager import FileProcessorManager
            self.file_processor_manager = FileProcessorManager(self)
        self.file_processor_manager.process_files()
    
    def update_progress(self, value):
        if hasattr(self, 'file_processor_manager'):
            self.file_processor_manager.update_progress(value)
    
    def on_processing_finished(self, results):
        if hasattr(self, 'file_processor_manager'):
            self.file_processor_manager.on_processing_finished(results)
    
    def on_processing_error(self, error_msg):
        if hasattr(self, 'file_processor_manager'):
            self.file_processor_manager.on_processing_error(error_msg)
    
    def clear_log(self):
        """清空操作日志"""
        self.status_text.clear()
        
    def refresh_all(self):
        # 重新扫描并预览
        if self.selected_dir:
            self.scan_and_preview()
    
    def on_file_selected(self, file_path):
        # 当文件树中选择文件时，更新预览面板
        if hasattr(self.preview_panel, 'select_file'):
            self.preview_panel.select_file(file_path)
    
    def on_preview_updated(self, updated_results):
        # 当预览面板中的内容更新时，更新当前结果
        self.current_results = updated_results
    
    def show_settings(self):
        """显示设置对话框"""
        if not hasattr(self, 'settings_manager'):
            from gui.window_components.settings_manager import SettingsManager
            self.settings_manager = SettingsManager(self)
        self.settings_manager.show_settings()
        # 不再强制刷新预览面板，保持表格状态不变
    
    def update_ui_from_config(self):
        """根据配置更新界面"""
        if not hasattr(self, 'settings_manager'):
            from gui.window_components.settings_manager import SettingsManager
            self.settings_manager = SettingsManager(self)
        self.settings_manager.update_ui_from_config()
    
    def process_single_file(self, file_info):
        """处理单个文件"""
        self.file_processor_manager.process_single_file(file_info)
    
    def _process_single_file(self, file_info):
        """内部方法：处理单个文件的实际逻辑"""
        return self.file_processor_manager._process_single_file(file_info)
    
    def get_button_style(self):
        """获取按钮的样式表"""
        return """
            QPushButton {
                padding: 10px 20px;
                font-size: 14px;
                background-color: white;
                color: #333;
                border-radius: 20px;
                border: none;
                border-style: outset;
                border-width: 2px;
                border-color: rgba(0, 0, 0, 0.1);
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """
    
    def process_selected_files(self, selected_files):
        """处理用户在预览面板中选择的多个文件"""
        if not hasattr(self, 'file_processor_manager'):
            from gui.window_components.file_processor_manager import FileProcessorManager
            self.file_processor_manager = FileProcessorManager(self)
        self.file_processor_manager.process_selected_files(selected_files)
    
    def show_center_message(self, message, success_count, failed_count):
        """使用ResultPopup显示处理结果消息"""
        ResultPopup(self, success_count, failed_count)
        
    def select_file_in_explorer(self, file_path):
        """在文件资源管理器中选中并显示文件"""
        try:
            file_path = os.path.abspath(file_path)
            if os.name == 'nt':  # Windows
                subprocess.Popen(f'explorer /select,"{file_path}"')
            elif sys.platform.startswith('darwin'):  # macOS
                subprocess.Popen(['open', '-R', file_path])
            else:  # Linux
                subprocess.Popen(['xdg-open', os.path.dirname(file_path)])
        except Exception as e:
            self.status_text.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 无法定位文件: {str(e)}")
    
    def undo_last_operation(self):
        """撤销上一次操作"""
        self.file_processor_manager.undo_last_operation()
    
    def closeEvent(self, event):
        self.processor.close()
        self.db.close()
        self.status_text.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 程序已关闭")
        event.accept()
        
    def get_resize_direction(self, pos):
        """根据鼠标位置确定调整大小的方向"""
        # 确保我们使用的是有效的QPoint对象
        if not isinstance(pos, QPoint):
            return None
            
        x, y = pos.x(), pos.y()
        width, height = self.width(), self.height()
        
        # 检查是否在窗口边缘
        on_left = x <= self.edge_width
        on_right = x >= width - self.edge_width
        on_top = y <= self.edge_width
        on_bottom = y >= height - self.edge_width
        
        # 确定调整方向
        if on_left and on_top:
            return 'topleft'
        elif on_right and on_top:
            return 'topright'
        elif on_left and on_bottom:
            return 'bottomleft'
        elif on_right and on_bottom:
            return 'bottomright'
        elif on_left:
            return 'left'
        elif on_right:
            return 'right'
        elif on_top:
            return 'top'
        elif on_bottom:
            return 'bottom'
        else:
            return None
    
    def update_cursor_shape(self, pos):
        """根据鼠标位置更新光标形状，提供更直观的视觉反馈"""
        if self.is_maximized:
            self.setCursor(Qt.ArrowCursor)
            return
        
        # 确保pos是相对于窗口的位置
        if isinstance(pos, QPoint):
            local_pos = pos
        else:
            # 对于QMouseEvent，转换为本地坐标
            local_pos = self.mapFromGlobal(pos)
            
        direction = self.get_resize_direction(local_pos)
        
        # 如果正在拖动中，则显示闭合手型光标
        if self.dragging:
            self.setCursor(Qt.ClosedHandCursor)
        elif direction:
            # 仅当鼠标位于边界线处时显示对应的调整光标
            if direction == 'left' or direction == 'right':
                self.setCursor(Qt.SizeHorCursor)  # 水平调整光标
            elif direction == 'top' or direction == 'bottom':
                self.setCursor(Qt.SizeVerCursor)  # 垂直调整光标
            elif direction == 'topleft' or direction == 'bottomright':
                self.setCursor(Qt.SizeFDiagCursor)  # 对角线调整光标
            elif direction == 'topright' or direction == 'bottomleft':
                self.setCursor(Qt.SizeBDiagCursor)  # 反向对角线调整光标
        else:
            # 鼠标不在边界线处时立即回归箭头光标
            self.setCursor(Qt.ArrowCursor)
    
    def mousePressEvent(self, event):
        """鼠标按下事件，开始拖动窗口或调整窗口大小"""
        # 如果窗口已最大化，则不允许调整大小
        if self.is_maximized:
            event.ignore()
            return
        
        # 检查是否在窗口边缘，开始调整大小
        pos = event.position().toPoint()
        direction = self.get_resize_direction(pos)
        
        if event.button() == Qt.LeftButton:
            if direction:
                # 仅当鼠标位于边界线处且按住左键时才开始调整大小
                self.resizing = True
                self.resize_direction = direction
                # 保存当前的全局位置，用于后续计算
                self.drag_start_pos = event.globalPosition().toPoint()
                # 保存当前窗口的位置和大小
                self.window_start_rect = self.frameGeometry()
                event.accept()
            else:
                # 检查是否在标题栏区域内，开始拖动窗口
                # 简化标题栏检测逻辑，确保拖动功能正常
                # 假设标题栏是窗口顶部的一个区域
                if hasattr(self, 'title_bar') and self.title_bar.geometry().contains(pos):
                    self.dragging = True
                    self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                    # 拖动时显示闭合手型光标
                    self.setCursor(Qt.ClosedHandCursor)
                    event.accept()
                elif pos.y() <= self.edge_width * 2:  # 备用方案：标题栏区域稍大于边缘检测宽度
                    self.dragging = True
                    self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                    # 拖动时显示闭合手型光标
                    self.setCursor(Qt.ClosedHandCursor)
                    event.accept()
                
    def is_resizable_edge(self, pos):
        """检查鼠标位置是否在可调整大小的边缘区域"""
        return self.get_resize_direction(pos) is not None
        
    def mouseMoveEvent(self, event):
        """鼠标移动事件，拖动窗口或调整窗口大小（优化版）"""
        # 确保事件被正确接受
        event.accept()
        
        # 拖动窗口 - 确保标题栏拖动功能正常
        if self.dragging and event.buttons() == Qt.LeftButton and not self.is_maximized:
            # 拖动时显示闭合手型光标
            self.setCursor(Qt.ClosedHandCursor)
            self.move(event.globalPosition().toPoint() - self.drag_position)
            
        # 调整窗口大小 - 仅在按住左键且处于调整状态时进行调整
        elif self.resizing and event.buttons() == Qt.LeftButton and not self.is_maximized:
            # 正在调整大小时保持对应的光标形状
            pos = event.position().toPoint()
            direction = self.resize_direction
            if direction == 'left' or direction == 'right':
                self.setCursor(Qt.SizeHorCursor)
            elif direction == 'top' or direction == 'bottom':
                self.setCursor(Qt.SizeVerCursor)
            elif direction == 'topleft' or direction == 'bottomright':
                self.setCursor(Qt.SizeFDiagCursor)
            elif direction == 'topright' or direction == 'bottomleft':
                self.setCursor(Qt.SizeBDiagCursor)
            
            # 使用节流机制减少重绘频率，提高性能
            current_time = QDateTime.currentDateTime().toMSecsSinceEpoch()
            if current_time - self.last_paint_time > self.paint_interval:
                # 应用性能优化到UI刷新
                if hasattr(self, 'preview_panel') and hasattr(self.preview_panel, 'table') and self.preview_panel.table:
                    self.preview_panel.table.viewport().update()
                if hasattr(self, 'file_tree') and self.file_tree and hasattr(self.file_tree, 'tree'):
                    self.file_tree.tree.viewport().update()
                # 记录最后重绘时间
                self.last_paint_time = current_time
                
                # 仅在调整大小时执行窗口大小计算和调整
                if hasattr(self, 'drag_start_pos') and hasattr(self, 'resize_direction') and hasattr(self, 'window_start_rect'):
                    # 获取当前鼠标的全局位置
                    global_pos = event.globalPosition().toPoint()
                    # 计算鼠标移动的距离
                    delta_x = global_pos.x() - self.drag_start_pos.x()
                    delta_y = global_pos.y() - self.drag_start_pos.y()
                    
                    # 保存窗口起始位置和大小
                    start_x = self.window_start_rect.x()
                    start_y = self.window_start_rect.y()
                    start_width = self.window_start_rect.width()
                    start_height = self.window_start_rect.height()
                    
                    # 计算新的窗口位置和大小
                    new_x = start_x
                    new_y = start_y
                    new_width = start_width
                    new_height = start_height
                    
                    # 根据调整方向计算新的窗口位置和大小
                    if self.resize_direction == 'right':
                        new_width = max(self.minimumWidth(), start_width + delta_x)
                    elif self.resize_direction == 'bottom':
                        new_height = max(self.minimumHeight(), start_height + delta_y)
                    elif self.resize_direction == 'left':
                        new_width = max(self.minimumWidth(), start_width - delta_x)
                        new_x = start_x + delta_x
                    elif self.resize_direction == 'top':
                        new_height = max(self.minimumHeight(), start_height - delta_y)
                        new_y = start_y + delta_y
                    elif self.resize_direction == 'topright':
                        new_width = max(self.minimumWidth(), start_width + delta_x)
                        new_height = max(self.minimumHeight(), start_height - delta_y)
                        new_y = start_y + delta_y
                    elif self.resize_direction == 'bottomright':
                        new_width = max(self.minimumWidth(), start_width + delta_x)
                        new_height = max(self.minimumHeight(), start_height + delta_y)
                    elif self.resize_direction == 'bottomleft':
                        new_width = max(self.minimumWidth(), start_width - delta_x)
                        new_height = max(self.minimumHeight(), start_height + delta_y)
                        new_x = start_x + delta_x
                    elif self.resize_direction == 'topleft':
                        new_width = max(self.minimumWidth(), start_width - delta_x)
                        new_height = max(self.minimumHeight(), start_height - delta_y)
                        new_x = start_x + delta_x
                        new_y = start_y + delta_y
                    
                    # 确保窗口不会移出屏幕可视区域
                    screen = self.screen().availableGeometry()
                    new_x = max(screen.x(), min(new_x, screen.right() - new_width))
                    new_y = max(screen.y(), min(new_y, screen.bottom() - new_height))
                    
                    # 设置新的窗口位置和大小
                    self.setGeometry(new_x, new_y, new_width, new_height)
        
        # 非拖动或调整状态时，实时更新光标形状
        else:
            self.update_cursor_shape(event.position().toPoint())
            
    def mouseReleaseEvent(self, event):
        """鼠标释放事件，结束拖动窗口或调整窗口大小"""
        # 释放鼠标后立即结束调整大小状态，下一次拖动需要重新按住边界线
        self.dragging = False
        self.resizing = False
        self.resize_direction = None
        
        # 释放鼠标后立即恢复默认光标
        self.setCursor(Qt.ArrowCursor)
        
        # 清除临时变量，确保每次拖动都是独立的操作
        if hasattr(self, 'drag_start_pos'):
            delattr(self, 'drag_start_pos')
        if hasattr(self, 'window_start_rect'):
            delattr(self, 'window_start_rect')
        event.accept()
        
    def leaveEvent(self, event):
        """鼠标离开窗口事件，恢复默认光标"""
        self.setCursor(Qt.ArrowCursor)
        event.accept()
        
    def enterEvent(self, event):
        """鼠标进入窗口事件，更新光标形状"""
        self.update_cursor_shape(event.position().toPoint())
        event.accept()

if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    
    # 初始化配置和日志
    config = load_config()
    log_level = config.get('DEFAULT', 'log_level', fallback='INFO')
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())