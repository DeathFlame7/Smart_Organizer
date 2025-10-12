import sys
from PySide6.QtWidgets import (QTreeView, QFileSystemModel, QWidget, QVBoxLayout, QFrame,
                            QMenu, QInputDialog, QMessageBox)
from PySide6.QtCore import QDir, QFileSystemWatcher, Qt, QUrl, Signal
from PySide6.QtGui import QAction
from pathlib import Path
import logging
import subprocess
import os
import sys
import shutil


class FileTreeView(QWidget):
    directory_changed = Signal(str)  # 目录变化信号
    file_selected = Signal(str)  # 文件选择信号
    
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(200)  # 设置最小高度，确保可见
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(5, 5, 5, 5)

        # 创建文件系统模型
        self.model = QFileSystemModel()
        # 使用跨平台兼容的根路径
        if os.name == 'nt':  # Windows系统
            self.model.setRootPath("D:\\")
        else:  # Linux/macOS系统
            self.model.setRootPath("/")
        # 显示所有文件和文件夹，包括隐藏的
        self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot | QDir.Hidden)
        self.model.setNameFilterDisables(False)  # 不显示被过滤掉的文件

        # 文件系统监视器
        self.watcher = QFileSystemWatcher()
        # 连接监视器信号
        self.watcher.directoryChanged.connect(self._on_directory_changed)
        self.watcher.fileChanged.connect(self._on_file_changed)

        # 创建树视图
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(QDir.currentPath()))
        self.tree.setColumnWidth(0, 400)  # 增大文件名列宽度以显示完整路径
        # 显示所有列（名称、大小、类型、修改日期）
        self.tree.setColumnHidden(1, False)
        self.tree.setColumnHidden(2, False)
        self.tree.setColumnHidden(3, False)
        # 启用排序
        self.tree.setSortingEnabled(True)
        # 设置选择模式
        self.tree.setSelectionMode(QTreeView.SingleSelection)
        self.tree.setSelectionBehavior(QTreeView.SelectRows)
        
        # 启用右键菜单
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        # 禁止直接编辑
        self.tree.setEditTriggers(QTreeView.NoEditTriggers)
        
        # 连接信号
        self.tree.clicked.connect(self.on_item_clicked)
        self.tree.doubleClicked.connect(self.on_item_double_clicked)

        self.layout.addWidget(self.tree)
        self.setLayout(self.layout)

        # 保存当前监视的目录
        self.watched_directories = set()
        # 保存正在编辑的索引
        self.editing_index = None
        # 保存原始名称
        self.original_name = ""
        
        # 添加当前目录到监视列表
        self._add_directory_to_watcher(QDir.currentPath())
        
        # 发出信号通知当前目录已更改
        self.directory_changed.emit(QDir.currentPath())

    def show_context_menu(self, position):
        """显示右键菜单"""
        index = self.tree.indexAt(position)
        if not index.isValid():
            return
        
        # 获取当前选中项的路径
        file_path = self.model.filePath(index)
        is_dir = self.model.isDir(index)
        
        # 创建右键菜单
        menu = QMenu(self)
        
        # 只对文件显示打开文件选项
        if not is_dir:
            open_file_action = QAction("打开文件", self)
            open_file_action.triggered.connect(lambda: self.open_file(file_path))
            menu.addAction(open_file_action)
            menu.addSeparator()
        
        # 添加打开所在位置选项
        open_location_action = QAction("打开所在位置", self)
        open_location_action.triggered.connect(lambda: self.open_file_location(file_path))
        menu.addAction(open_location_action)
        
        menu.addSeparator()
        
        # 添加重命名选项
        rename_action = QAction("重命名", self)
        rename_action.triggered.connect(lambda: self.rename_file(index))
        menu.addAction(rename_action)
        
        # 只有文件夹才能添加新建文件夹选项
        if is_dir:
            menu.addSeparator()
            new_folder_action = QAction("新建文件夹", self)
            new_folder_action.triggered.connect(lambda: self.create_new_folder(index))
            menu.addAction(new_folder_action)
            
        # 添加刷新选项
        menu.addSeparator()
        refresh_action = QAction("刷新", self)
        refresh_action.triggered.connect(self.refresh)
        menu.addAction(refresh_action)
        
        # 显示菜单
        menu.exec_(self.tree.mapToGlobal(position))
        
    def open_file_location(self, file_path):
        """打开文件所在位置"""
        try:
            # 确保路径格式正确处理Windows路径
            file_path = os.path.abspath(file_path)
            
            if os.path.isfile(file_path):
                # 根据操作系统使用不同的命令打开文件位置
                if os.name == 'nt':  # Windows
                    subprocess.Popen(f'explorer /select,"{file_path}"')
                    logging.info(f"已打开文件所在位置并选中文件: {file_path}")
                elif sys.platform.startswith('darwin'):  # macOS
                    subprocess.Popen(['open', '-R', file_path])
                    logging.info(f"已打开文件所在位置并选中文件: {file_path}")
                else:  # Linux
                    subprocess.Popen(['xdg-open', os.path.dirname(file_path)])
                    logging.info(f"已打开文件所在目录: {os.path.dirname(file_path)}")
            else:
                # 根据操作系统使用不同的命令打开文件夹
                if os.name == 'nt':  # Windows
                    subprocess.Popen(f'explorer "{file_path}"')
                    logging.info(f"已打开目录: {file_path}")
                elif sys.platform.startswith('darwin'):  # macOS
                    subprocess.Popen(['open', file_path])
                    logging.info(f"已打开目录: {file_path}")
                else:  # Linux
                    subprocess.Popen(['xdg-open', file_path])
                    logging.info(f"已打开目录: {file_path}")
        except Exception as e:
            logging.error(f"无法打开目录: {e}")
            QMessageBox.critical(self, "错误", f"无法打开目录: {str(e)}")
            
    def open_file(self, file_path):
        """打开文件查看内容"""
        try:
            if os.path.isfile(file_path):
                file_path = os.path.abspath(file_path)
                # 使用系统默认程序打开文件
                if sys.platform.startswith('darwin'):
                    subprocess.Popen(['open', file_path])
                elif os.name == 'nt':
                    os.startfile(file_path)  # Windows特有方法
                elif os.name == 'posix':
                    subprocess.Popen(['xdg-open', file_path])
                logging.info(f"已打开文件: {file_path}")
        except Exception as e:
            logging.error(f"打开文件失败: {e}")
            QMessageBox.critical(self, "错误", f"打开文件失败: {str(e)}")
            
    def _on_directory_changed(self, path):
        """目录变化时刷新"""
        if self.tree.rootIndex().isValid():  
            try:
                current_root_path = self.model.filePath(self.tree.rootIndex())
                # 清除模型缓存并刷新
                self.model.setRootPath("")
                self.model.setRootPath(current_root_path)
                self.tree.setRootIndex(self.model.index(current_root_path))
                
                # 确保刷新显示 - 优化：只使用viewport更新以提高性能
                try:
                    self.tree.viewport().update()
                except Exception as e:
                    logging.error(f"文件树视图刷新失败: {e}")
                
                logging.debug(f"目录 {path} 已更新并刷新视图")
            except Exception as e:
                logging.error(f"刷新目录时出错: {e}")

    def _on_file_changed(self, path):
        """文件变化时刷新"""
        try:
            parent_dir = str(Path(path).parent)
            self._on_directory_changed(parent_dir)
            logging.debug(f"文件 {path} 已更新并刷新视图")
        except Exception as e:
            logging.error(f"刷新文件变化时出错: {e}")
    
    def rename_file(self, index):
        """重命名文件或文件夹"""
        try:
            # 获取当前文件名
            current_name = self.model.fileName(index)
            # 弹出输入对话框
            new_name, ok = QInputDialog.getText(
                self, "重命名",
                f"请输入新名称:",
                text=current_name
            )
            
            if ok and new_name and new_name != current_name:
                # 获取完整路径
                current_path = self.model.filePath(index)
                parent_path = os.path.dirname(current_path)
                new_path = os.path.join(parent_path, new_name)
                
                # 检查文件是否已存在
                if os.path.exists(new_path):
                    QMessageBox.warning(self, "警告", f"文件 '{new_name}' 已存在")
                    return
                
                # 检查路径是否包含非法字符
                invalid_chars = '<>:"/\\|?*'
                if any(char in new_name for char in invalid_chars):
                    QMessageBox.warning(self, "警告", f"文件名包含非法字符: {invalid_chars}")
                    return
                
                # 重命名文件
                shutil.move(current_path, new_path)
                logging.info(f"文件已重命名: {current_name} -> {new_name}")
                # 刷新视图
                self.refresh()
        except PermissionError:
            logging.error(f"重命名失败：没有权限操作 {current_path}")
            QMessageBox.critical(self, "权限错误", f"没有权限重命名 {current_name}")
        except FileNotFoundError:
            logging.error(f"重命名失败：文件不存在 {current_path}")
            QMessageBox.critical(self, "文件不存在", f"文件 {current_name} 不存在")
        except OSError as e:
            if e.errno == 18:  # 跨设备移动
                msg = f"无法跨分区移动文件: {str(e)}"
            else:
                msg = f"系统错误: {str(e)}"
            logging.error(f"重命名失败: {msg}")
            QMessageBox.critical(self, "错误", msg)
        except Exception as e:
            logging.error(f"重命名失败: {e}")
            QMessageBox.critical(self, "错误", f"重命名失败: {str(e)}")
            
    def create_new_folder(self, index):
        """创建新文件夹"""
        try:
            # 获取父目录路径
            parent_path = self.model.filePath(index)
            # 弹出输入对话框
            folder_name, ok = QInputDialog.getText(
                self, "新建文件夹",
                "请输入文件夹名称:",
                text="新建文件夹"
            )
            
            if ok and folder_name:
                # 检查文件夹名称是否包含非法字符
                invalid_chars = '<>:"/\\|?*'
                if any(char in folder_name for char in invalid_chars):
                    QMessageBox.warning(self, "警告", f"文件夹名称包含非法字符: {invalid_chars}")
                    return
                
                # 检查文件夹名称是否为空或仅包含空格
                if not folder_name.strip():
                    QMessageBox.warning(self, "警告", "文件夹名称不能为空或仅包含空格")
                    return
                
                # 创建新文件夹路径
                new_folder_path = os.path.join(parent_path, folder_name)
                
                # 检查文件夹是否已存在
                if os.path.exists(new_folder_path):
                    QMessageBox.warning(self, "警告", f"文件夹 '{folder_name}' 已存在")
                    return
                
                # 创建新文件夹
                os.makedirs(new_folder_path)
                logging.info(f"已创建新文件夹: {new_folder_path}")
                # 刷新视图
                self.refresh()
        except PermissionError:
            logging.error(f"创建文件夹失败：没有权限在 {parent_path} 中创建文件夹")
            QMessageBox.critical(self, "权限错误", f"没有权限在当前目录中创建文件夹")
        except FileNotFoundError:
            logging.error(f"创建文件夹失败：父目录不存在 {parent_path}")
            QMessageBox.critical(self, "目录不存在", f"父目录不存在")
        except Exception as e:
            logging.error(f"创建文件夹失败: {e}")
            QMessageBox.critical(self, "错误", f"创建文件夹失败: {str(e)}")
            
    def refresh(self):
        """手动刷新文件树"""
        if self.tree.rootIndex().isValid():
            current_root_path = self.model.filePath(self.tree.rootIndex())
            # 移除之前的监视
            for dir_path in list(self.watched_directories):
                self.watcher.removePath(dir_path)
            self.watched_directories.clear()

            # 重新设置根路径以刷新
            self.model.setRootPath("")
            self.model.setRootPath(current_root_path)
            self.tree.setRootIndex(self.model.index(current_root_path))

            # 添加当前目录及其子目录到监视列表
            self._add_directory_to_watcher(current_root_path, recursive=True)

            logging.info(f"文件树已刷新，当前目录：{current_root_path}")

    def _add_directory_to_watcher(self, dir_path, recursive=True):
        """添加目录到监视列表，可选递归添加子目录"""
        if dir_path in self.watched_directories:
            return

        try:
            self.watcher.addPath(dir_path)
            self.watched_directories.add(dir_path)
            logging.debug(f"开始监视目录：{dir_path}")

            if recursive:
                # 递归添加子目录
                for entry in Path(dir_path).iterdir():
                    if entry.is_dir() and not entry.name.startswith('.'):
                        self._add_directory_to_watcher(str(entry), recursive=True)
        except Exception as e:
            logging.error(f"添加目录到监视列表失败 {dir_path}: {e}")

    def on_item_clicked(self, index):
        """处理树视图中项被点击的事件"""
        if index.isValid():
            file_path = self.model.filePath(index)
            if not self.model.isDir(index):  # 只处理文件点击
                self.file_selected.emit(file_path)
                logging.debug(f"文件已选择: {file_path}")
                
    def on_item_double_clicked(self, index):
        """处理树视图中项被双击的事件"""
        if index.isValid():
            file_path = self.model.filePath(index)
            if self.model.isDir(index):  # 如果是目录，切换到该目录
                self.tree.setRootIndex(index)
                self.directory_changed.emit(file_path)
                logging.info(f"已切换到目录: {file_path}")
                # 更新监视列表
                self.refresh()
            else:  # 如果是文件，打开文件
                self.open_file(file_path)
    
    def load_directory(self, directory_path):
        """加载指定目录并更新文件树视图"""
        try:
            if os.path.exists(directory_path) and os.path.isdir(directory_path):
                # 确保路径是绝对路径
                directory_path = os.path.abspath(directory_path)
                
                # 重置模型的根路径
                self.model.setRootPath(directory_path)
                
                # 将树视图的根索引设置为指定目录
                index = self.model.index(directory_path)
                if index.isValid():
                    self.tree.setRootIndex(index)
                    self.directory_changed.emit(directory_path)
                    logging.info(f"已加载目录: {directory_path}")
                    
                    # 清空并重新添加监视列表
                    self.watcher.removePaths(self.watched_directories)
                    self.watched_directories.clear()
                    self._add_directory_to_watcher(directory_path)
                    
                    # 刷新视图
                    self.refresh()
                else:
                    logging.error(f"无法获取目录索引: {directory_path}")
            else:
                logging.error(f"无效的目录路径: {directory_path}")
        except Exception as e:
            logging.error(f"加载目录时发生错误: {e}")