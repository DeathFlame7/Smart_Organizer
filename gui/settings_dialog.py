import sys
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QColorDialog, QComboBox, QGroupBox, QGridLayout, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette

from utils.application_config import load_config, set_config_value

class SettingsDialog(QDialog):
    """设置对话框，允许用户修改应用程序配置"""
    
    def __init__(self, parent=None, is_start_screen=False):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumSize(400, 300)
        self.config = load_config()
        self.is_start_screen = is_start_screen  # 标识是否在起始界面打开设置
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """初始化设置对话框界面"""
        main_layout = QVBoxLayout(self)
        
        # 创建UI设置分组
        ui_settings_group = QGroupBox("界面设置")
        ui_settings_layout = QGridLayout()
        ui_settings_group.setLayout(ui_settings_layout)
        
        # 程序背景色设置 - 所有界面都显示
        ui_settings_layout.addWidget(QLabel("程序背景色:"), 0, 0)
        self.background_color_frame = QFrame()
        self.background_color_frame.setFixedSize(30, 30)
        self.background_color_frame.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.background_color_btn = QPushButton("选择颜色")
        self.background_color_btn.clicked.connect(lambda: self.select_color(self.background_color_frame, "ui", "background_color"))
        
        bg_color_layout = QHBoxLayout()
        bg_color_layout.addWidget(self.background_color_frame)
        bg_color_layout.addWidget(self.background_color_btn)
        ui_settings_layout.addLayout(bg_color_layout, 0, 1)
        
        # 如果不是在起始界面，则显示所有设置选项
        if not self.is_start_screen:
            # 成功背景色设置
            ui_settings_layout.addWidget(QLabel("成功项背景色:"), 1, 0)
            self.success_color_frame = QFrame()
            self.success_color_frame.setFixedSize(30, 30)
            self.success_color_frame.setFrameStyle(QFrame.Panel | QFrame.Sunken)
            self.success_color_btn = QPushButton("选择颜色")
            self.success_color_btn.clicked.connect(lambda: self.select_color(self.success_color_frame, "ui", "success_background"))
            
            color_layout = QHBoxLayout()
            color_layout.addWidget(self.success_color_frame)
            color_layout.addWidget(self.success_color_btn)
            ui_settings_layout.addLayout(color_layout, 1, 1)
            
            # 失败背景色设置
            ui_settings_layout.addWidget(QLabel("失败项背景色:"), 2, 0)
            self.failure_color_frame = QFrame()
            self.failure_color_frame.setFixedSize(30, 30)
            self.failure_color_frame.setFrameStyle(QFrame.Panel | QFrame.Sunken)
            self.failure_color_btn = QPushButton("选择颜色")
            self.failure_color_btn.clicked.connect(lambda: self.select_color(self.failure_color_frame, "ui", "failure_background"))
            
            color_layout2 = QHBoxLayout()
            color_layout2.addWidget(self.failure_color_frame)
            color_layout2.addWidget(self.failure_color_btn)
            ui_settings_layout.addLayout(color_layout2, 2, 1)
            
            # 布局配置
            ui_settings_layout.addWidget(QLabel("二级界面布局:"), 3, 0)
            self.layout_combobox = QComboBox()
            self.layout_combobox.addItem("默认布局", "default")
            self.layout_combobox.addItem("紧凑布局", "compact")
            self.layout_combobox.addItem("展开布局", "expanded")
            ui_settings_layout.addWidget(self.layout_combobox, 3, 1)
            
            # 布局方向配置
            ui_settings_layout.addWidget(QLabel("目录与预览布局方向:"), 4, 0)
            self.layout_direction_combobox = QComboBox()
            self.layout_direction_combobox.addItem("左右布局", "horizontal")
            self.layout_direction_combobox.addItem("上下布局", "vertical")
            ui_settings_layout.addWidget(self.layout_direction_combobox, 4, 1)
        
        # 按钮布局
        buttons_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_settings)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(self.save_btn)
        buttons_layout.addWidget(self.cancel_btn)
        
        # 添加到主布局
        main_layout.addWidget(ui_settings_group)
        main_layout.addLayout(buttons_layout)
        
    def load_settings(self):
        """加载当前配置"""
        # 加载程序背景色设置 - 所有界面都需要
        background_color = self.config.get("ui", "background_color", "#f0f0f0")  # 默认浅灰色背景
        self.set_frame_color(self.background_color_frame, background_color)
        
        # 如果不是在起始界面，加载其他设置
        if not self.is_start_screen:
            # 加载其他颜色设置
            success_color = self.config.get("ui", "success_background", "#d4edda")  # 默认浅绿色
            failure_color = self.config.get("ui", "failure_background", "#f8d7da")  # 默认浅红色
            self.set_frame_color(self.success_color_frame, success_color)
            self.set_frame_color(self.failure_color_frame, failure_color)
            
            # 加载布局设置
            layout_type = self.config.get("ui", "layout_type", "default")
            index = self.layout_combobox.findData(layout_type)
            if index >= 0:
                self.layout_combobox.setCurrentIndex(index)
                
            # 加载布局方向设置
            layout_direction = self.config.get("ui", "layout_direction", "horizontal")
            index = self.layout_direction_combobox.findData(layout_direction)
            if index >= 0:
                self.layout_direction_combobox.setCurrentIndex(index)
    
    def set_frame_color(self, frame, color_str):
        """设置框架的背景色"""
        palette = frame.palette()
        palette.setColor(QPalette.Window, QColor(color_str))
        frame.setPalette(palette)
        frame.setAutoFillBackground(True)
    
    def select_color(self, target_frame, section, option):
        """打开颜色选择对话框并应用选择的颜色"""
        # 获取当前颜色
        current_color = target_frame.palette().color(QPalette.Window)
        
        # 打开颜色选择对话框
        color = QColorDialog.getColor(current_color, self, "选择颜色")
        
        if color.isValid():
            # 更新预览
            self.set_frame_color(target_frame, color.name())
            # 暂存配置变更
            set_config_value(section, option, color.name())
    
    def save_settings(self):
        """保存设置"""
        # 保存程序背景色设置 - 所有界面都需要
        background_color = self.background_color_frame.palette().color(QPalette.Window).name()
        set_config_value("ui", "background_color", background_color)
        
        # 如果不是在起始界面，保存其他设置
        if not self.is_start_screen:
            # 保存其他颜色设置
            success_color = self.success_color_frame.palette().color(QPalette.Window).name()
            set_config_value("ui", "success_background", success_color)
            
            failure_color = self.failure_color_frame.palette().color(QPalette.Window).name()
            set_config_value("ui", "failure_background", failure_color)
            
            # 保存布局设置
            layout_type = self.layout_combobox.currentData()
            set_config_value("ui", "layout_type", layout_type)
            
            # 保存布局方向设置
            layout_direction = self.layout_direction_combobox.currentData()
            set_config_value("ui", "layout_direction", layout_direction)
        
        # 发送信号通知配置已更新
        self.accept()
        
        # 在实际应用中，可能还需要发送信号通知主界面更新