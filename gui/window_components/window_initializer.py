from PySide6.QtWidgets import (QVBoxLayout, QWidget, QFrame, QStackedWidget,
                               QSplitter, QHBoxLayout, QPushButton, QLabel, QTextEdit,
                               QSizePolicy, QFileDialog)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QLinearGradient, QPalette, QColor

from gui.components import WindowControls, GradientBackground
from gui.file_tree import FileTreeView
from gui.preview_panel import PreviewPanel
from gui.drag_manager import DragManager
from utils.config import get_config_value

class WindowInitializer:
    """窗口初始化辅助类"""
    def __init__(self, main_window):
        self.main_window = main_window
    
    def setup_ui(self):
        # 创建界面容器
        self.main_window.main_widget = QWidget()
        self.main_window.main_layout = QVBoxLayout(self.main_window.main_widget)
        self.main_window.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建窗口控制栏（区域1）
        self.create_window_controls()
        
        # 将标题栏添加到主布局
        self.main_window.main_layout.addWidget(self.main_window.title_bar)
        
        # 创建界面切换容器
        self.main_window.stacked_widget = QStackedWidget()
        
        # 创建起始界面
        self.create_start_screen()
        
        # 创建主操作界面
        self.create_main_screen()
        
        # 添加界面到堆栈
        self.main_window.stacked_widget.addWidget(self.main_window.start_screen)
        self.main_window.stacked_widget.addWidget(self.main_window.main_screen)
        
        # 添加堆栈到主布局
        self.main_window.main_layout.addWidget(self.main_window.stacked_widget)
        
        # 设置中心部件
        self.main_window.setCentralWidget(self.main_window.main_widget)
        
        # 默认显示起始界面
        self.main_window.stacked_widget.setCurrentWidget(self.main_window.start_screen)
    
    def create_window_controls(self):
        # 创建自定义窗口标题栏
        self.main_window.title_bar = WindowControls(self.main_window)
        
        # 连接按钮信号
        self.main_window.title_bar.minimize_btn.clicked.connect(self.main_window.showMinimized)
        self.main_window.title_bar.maximize_btn.clicked.connect(self.main_window.toggle_maximize)
        self.main_window.title_bar.close_btn.clicked.connect(self.main_window.close)
        self.main_window.title_bar.back_btn.clicked.connect(self.main_window.show_start_screen)
        
        # 允许拖动窗口
        self.main_window.title_bar.mousePressEvent = self.main_window.mousePressEvent
        self.main_window.title_bar.mouseMoveEvent = self.main_window.mouseMoveEvent
        self.main_window.title_bar.mouseReleaseEvent = self.main_window.mouseReleaseEvent
        
        # 初始时清空标题文本（在起始界面不显示标题）
        self.main_window.title_bar.title_label.setText("")
    
    def create_start_screen(self):
        # 创建起始界面容器
        self.main_window.start_screen = QWidget()
        start_layout = QVBoxLayout(self.main_window.start_screen)
        
        # 设置渐变背景
        gradient_bg = GradientBackground()
        gradient_bg.set_gradient(self.main_window.start_screen)
        
        # 标题
        title_label = QLabel("智能文件管理助手")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #333;")
        
        # 选择文件夹按钮
        self.main_window.select_folder_start_btn = QPushButton("请选择文件夹")
        self.main_window.select_folder_start_btn.clicked.connect(self.main_window.select_folder_and_show_main)
        self.main_window.select_folder_start_btn.setStyleSheet("""
            QPushButton {
                padding: 15px 40px;
                font-size: 16px;
                background-color: white;
                color: #333;
                border-radius: 30px;
                border: none;
                border-style: outset;
            border-width: 2px;
            border-color: rgba(0, 0, 0, 0.1);
            }
            QPushButton:hover {
                background-color: #f5f5f5;
                border-style: outset;
            border-width: 2px;
            border-color: rgba(0, 0, 0, 0.15);
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """)
        
        # 设置按钮
        self.main_window.settings_btn = QPushButton("设置")
        self.main_window.settings_btn.clicked.connect(self.main_window.show_settings)
        self.main_window.settings_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                font-size: 14px;
                background-color: transparent;
                color: #555;
                border-radius: 20px;
                border: 1px solid #ccc;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.3);
            }
        """)
        
        # 布局调整
        vertical_spacer1 = QWidget()
        vertical_spacer1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        vertical_spacer2 = QWidget()
        vertical_spacer2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        vertical_spacer3 = QWidget()
        vertical_spacer3.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 设置按钮布局
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.main_window.settings_btn, alignment=Qt.AlignLeft | Qt.AlignBottom)
        bottom_layout.addStretch()
        
        # 添加到布局
        start_layout.addWidget(vertical_spacer1)
        start_layout.addWidget(title_label)
        start_layout.addWidget(vertical_spacer2)
        start_layout.addWidget(self.main_window.select_folder_start_btn, alignment=Qt.AlignCenter)
        start_layout.addWidget(vertical_spacer3)
        start_layout.addLayout(bottom_layout)
    
    def create_main_screen(self):
        # 创建主操作界面容器
        self.main_window.main_screen = QWidget()
        main_layout = QVBoxLayout(self.main_window.main_screen)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 顶部按钮布局
        top_buttons_layout = QHBoxLayout()
        
        # 操作按钮组
        self.main_window.reselect_btn = QPushButton("重新选择文件夹")
        self.main_window.reselect_btn.clicked.connect(self.main_window.select_folder)
        self.main_window.reselect_btn.setStyleSheet(self.main_window.get_button_style())
        
        self.main_window.reset_btn = QPushButton("重置预览")
        self.main_window.reset_btn.clicked.connect(self.main_window.refresh_all)
        self.main_window.reset_btn.setStyleSheet(self.main_window.get_button_style())
        
        self.main_window.undo_btn = QPushButton("撤销上一次处理")
        self.main_window.undo_btn.clicked.connect(self.main_window.undo_last_operation)
        self.main_window.undo_btn.setStyleSheet(self.main_window.get_button_style())
        self.main_window.undo_btn.setEnabled(False)
        
        self.main_window.process_btn = QPushButton("执行处理")
        self.main_window.process_btn.clicked.connect(self.main_window.process_files)
        self.main_window.process_btn.setStyleSheet(self.main_window.get_process_button_style())
        self.main_window.process_btn.setEnabled(False)
        
        # 设置按钮
        self.main_window.settings_btn = QPushButton("设置")
        self.main_window.settings_btn.clicked.connect(self.main_window.show_settings)
        self.main_window.settings_btn.setStyleSheet(self.main_window.get_button_style())
        
        # 清空日志按钮
        self.main_window.clear_log_btn = QPushButton("清空日志")
        self.main_window.clear_log_btn.clicked.connect(self.main_window.clear_log)
        self.main_window.clear_log_btn.setStyleSheet(self.main_window.get_button_style())
        
        # 添加按钮到顶部布局
        top_buttons_layout.addWidget(self.main_window.reselect_btn)
        top_buttons_layout.addWidget(self.main_window.reset_btn)
        top_buttons_layout.addWidget(self.main_window.undo_btn)
        top_buttons_layout.addWidget(self.main_window.process_btn)
        top_buttons_layout.addWidget(self.main_window.clear_log_btn)
        top_buttons_layout.addWidget(self.main_window.settings_btn)
        
        # 创建主水平分割器，用于左右布局
        self.main_window.main_splitter = QSplitter(Qt.Horizontal)
        self.main_window.main_splitter.setStyleSheet("QSplitter::handle { background-color: #ddd; width: 5px; }")
        self.main_window.main_splitter.setContentsMargins(0, 0, 0, 0)
        
        # 左侧容器 - 包含区域5和区域3
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # 区域5：目录（文件树）
        self.main_window.directory_frame = QFrame()
        self.main_window.directory_frame.setStyleSheet("QFrame { background-color: white; border-radius: 8px; border-style: outset; border-width: 1px; border-color: rgba(0, 0, 0, 0.05); }")
        directory_layout = QVBoxLayout(self.main_window.directory_frame)
        directory_layout.setContentsMargins(10, 10, 10, 10)
        
        directory_label = QLabel("目录")
        directory_label.setStyleSheet("font-weight: bold; color: #333; margin-bottom: 5px;")
        
        # 创建文件树视图
        self.main_window.file_tree = FileTreeView()
        directory_layout.addWidget(directory_label)
        directory_layout.addWidget(self.main_window.file_tree)
        
        # 连接文件树信号
        self.main_window.file_tree.file_selected.connect(self.main_window.on_file_selected)
        
        # 区域3：分类预览/处理结果
        self.main_window.preview_frame = QFrame()
        self.main_window.preview_frame.setStyleSheet("QFrame { background-color: white; border-radius: 8px; border-style: outset; border-width: 1px; border-color: rgba(0, 0, 0, 0.05); }")
        preview_layout = QVBoxLayout(self.main_window.preview_frame)
        preview_layout.setContentsMargins(10, 10, 10, 10)
        
        preview_label = QLabel("分类预览/处理结果")
        preview_label.setStyleSheet("font-weight: bold; color: #333; margin-bottom: 5px;")
        
        # 初始化增强版PreviewPanel，并传递必要的参数
        self.main_window.preview_panel = PreviewPanel(
            parent=self.main_window.preview_frame,
            file_processor=self.main_window.processor,
            file_classifier=self.main_window.classifier
        )
        self.main_window.preview_panel.file_updated.connect(self.main_window.on_preview_updated)
        self.main_window.preview_panel.process_single_file.connect(self.main_window.process_single_file)
        self.main_window.preview_panel.process_selected_files.connect(self.main_window.process_selected_files)
        
        preview_layout.addWidget(preview_label)
        preview_layout.addWidget(self.main_window.preview_panel)
        
        # 添加区域5和区域3到左侧容器
        left_layout.addWidget(self.main_window.directory_frame)
        left_layout.addWidget(self.main_window.preview_frame)
        left_layout.setStretch(0, 1)  # 区域5占1份
        left_layout.setStretch(1, 2)  # 区域3占2份
        
        # 右侧容器 - 包含区域4
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 区域4：操作日志
        self.main_window.log_frame = QFrame()
        self.main_window.log_frame.setStyleSheet("QFrame { background-color: white; border-radius: 8px; border-style: outset; border-width: 1px; border-color: rgba(0, 0, 0, 0.05); }")
        log_layout = QVBoxLayout(self.main_window.log_frame)
        log_layout.setContentsMargins(10, 10, 10, 10)
        
        log_label = QLabel("操作日志")
        log_label.setStyleSheet("font-weight: bold; color: #333; margin-bottom: 5px;")
        
        # 创建日志文本框
        self.main_window.status_text = QTextEdit()
        self.main_window.status_text.setReadOnly(True)
        self.main_window.status_text.setStyleSheet("QTextEdit { background-color: #f9f9f9; border: 1px solid #ddd; border-radius: 4px; padding: 5px; }")
        
        log_layout.addWidget(log_label)
        log_layout.addWidget(self.main_window.status_text)
        
        # 添加区域4到右侧容器
        right_layout.addWidget(self.main_window.log_frame)
        
        # 添加左侧和右侧容器到主水平分割器
        self.main_window.main_splitter.addWidget(left_container)
        self.main_window.main_splitter.addWidget(right_container)
        # 设置初始大小比例
        self.main_window.main_splitter.setSizes([600, 400])
        self.main_window.main_splitter.setHandleWidth(5)
        
        # 添加所有布局到主布局
        main_layout.addLayout(top_buttons_layout)
        main_layout.addWidget(self.main_window.main_splitter)
        
        # 应用滚动条优化到关键组件
        from gui.scrollbar_optimizer import scrollbar_optimizer
        scrollbar_optimizer.apply_optimized_scrollbar_style(self.main_window.preview_panel)
        scrollbar_optimizer.apply_optimized_scrollbar_style(self.main_window.file_tree)
        scrollbar_optimizer.apply_optimized_scrollbar_style(self.main_window.status_text)
        
        # 初始化拖放管理器，允许拖动三个主要区域
        self.main_window.drag_manager = DragManager(self.main_window)