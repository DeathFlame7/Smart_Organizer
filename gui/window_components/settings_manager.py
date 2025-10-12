from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QColorDialog, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from utils.config import get_config_value, save_config_value, load_config
import logging

class SettingsManager:
    """设置管理类"""
    def __init__(self, main_window):
        self.main_window = main_window
    
    def show_settings(self):
        """显示设置对话框"""
        # 创建设置对话框
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle("设置")
        dialog.resize(400, 300)
        dialog.setStyleSheet("background-color: #2c2c2c; color: #ffffff;")
        
        # 创建主布局
        main_layout = QVBoxLayout(dialog)
        
        # 布局方向设置
        layout_dir_group = QWidget()
        layout_dir_layout = QHBoxLayout(layout_dir_group)
        layout_dir_label = QLabel("界面布局方向:")
        layout_dir_label.setStyleSheet("color: #ffffff;")
        
        self.layout_dir_combo = QComboBox()
        self.layout_dir_combo.addItems(["水平布局", "垂直布局"])
        
        # 获取当前布局方向配置
        config = load_config()
        current_layout = get_config_value(config, "ui", "layout_direction", "horizontal")
        index = 0 if current_layout == "horizontal" else 1
        self.layout_dir_combo.setCurrentIndex(index)
        
        # 设置下拉框样式
        self.layout_dir_combo.setStyleSheet(
            "background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555;"
        )
        
        layout_dir_layout.addWidget(layout_dir_label)
        layout_dir_layout.addWidget(self.layout_dir_combo)
        
        # 背景颜色设置
        bg_color_group = QWidget()
        bg_color_layout = QHBoxLayout(bg_color_group)
        bg_color_label = QLabel("界面背景颜色:")
        bg_color_label.setStyleSheet("color: #ffffff;")
        
        self.bg_color_btn = QPushButton("选择颜色")
        self.bg_color_btn.setStyleSheet(
            "background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555;"
        )
        
        # 获取当前背景色配置
        config = load_config()
        current_bg_color = get_config_value(config, "ui", "background_color", "#1e1e1e")
        self.current_color = QColor(current_bg_color)
        self.update_color_button_style()
        
        self.bg_color_btn.clicked.connect(self.select_background_color)
        
        bg_color_layout.addWidget(bg_color_label)
        bg_color_layout.addWidget(self.bg_color_btn)
        
        # 按钮布局
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        ok_btn = QPushButton("确定")
        ok_btn.setStyleSheet(
            "background-color: #4caf50; color: white; border: none; padding: 8px 16px;"
        )
        ok_btn.clicked.connect(lambda: self.apply_settings(dialog))
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet(
            "background-color: #3c3c3c; color: white; border: 1px solid #555555; padding: 8px 16px;"
        )
        cancel_btn.clicked.connect(dialog.reject)
        
        buttons_layout.addWidget(ok_btn)
        buttons_layout.addWidget(cancel_btn)
        
        # 添加到主布局
        main_layout.addWidget(layout_dir_group)
        main_layout.addWidget(bg_color_group)
        main_layout.addStretch()
        main_layout.addLayout(buttons_layout)
        
        # 显示对话框
        dialog.exec()
    
    def select_background_color(self):
        """选择背景颜色"""
        color = QColorDialog.getColor(self.current_color, self.main_window, "选择界面背景颜色")
        if color.isValid():
            self.current_color = color
            self.update_color_button_style()
    
    def update_color_button_style(self):
        """更新颜色按钮样式"""
        color_name = self.current_color.name()
        self.bg_color_btn.setStyleSheet(
            f"background-color: {color_name}; color: white; border: 1px solid #555555;"
        )
    
    def apply_settings(self, dialog):
        """应用设置并关闭对话框"""
        # 保存布局方向设置
        layout_dir = "horizontal" if self.layout_dir_combo.currentIndex() == 0 else "vertical"
        save_config_value("ui", "layout_direction", layout_dir)
        
        # 保存背景颜色设置
        save_config_value("ui", "background_color", self.current_color.name())
        
        # 应用UI更新
        self.update_ui_from_config()
        
        # 关闭对话框
        dialog.accept()
    
    def update_ui_from_config(self):
        """从配置文件更新UI设置"""
        # 获取背景颜色配置
        config = load_config()
        background_color = get_config_value(config, "ui", "background_color", "#1e1e1e")
        # 验证颜色有效性
        if not QColor.isValidColor(background_color):
            logging.warning(f"无效的背景颜色配置: {background_color}，使用默认值")
            background_color = "#1e1e1e"
        self.main_window.setStyleSheet(f"background-color: {background_color};")
        
        # 获取布局方向配置
        config = load_config()
        layout_direction = get_config_value(config, "ui", "layout_direction", "horizontal")
        
        # 设置主分割器方向
        if hasattr(self.main_window, 'main_splitter'):
            if layout_direction == "horizontal":
                self.main_window.main_splitter.setOrientation(Qt.Horizontal)
            else:
                self.main_window.main_splitter.setOrientation(Qt.Vertical)
        
        # 重新设置渐变背景
        if hasattr(self.main_window, 'set_gradient_background'):
            self.main_window.set_gradient_background()
            
        # 更新窗口标题栏颜色
        if hasattr(self.main_window, 'title_bar') and hasattr(self.main_window.title_bar, 'setStyleSheet'):
            self.main_window.title_bar.setStyleSheet(
                f'''background-color: {background_color};
color: white;
border-bottom: 1px solid #555;''')
        
        # 更新状态文本区域背景
        if hasattr(self.main_window, 'status_text') and hasattr(self.main_window.status_text, 'setStyleSheet'):
            self.main_window.status_text.setStyleSheet(
                f'''background-color: {self.get_darker_color(background_color, 0.9)};
color: #cccccc;
border: 1px solid #555;
font-family: Microsoft YaHei, SimHei, sans-serif;
font-size: 12px;''')
        
        # 更新按钮样式
        self.update_button_styles()
    
    def get_darker_color(self, color_str, factor=0.8):
        """获取更暗的颜色"""
        color = QColor(color_str)
        h, s, v, a = color.getHsvF()
        # 降低亮度值
        new_v = max(0, v * factor)
        new_color = QColor.fromHsvF(h, s, new_v, a)
        return new_color.name()
    
    def update_button_styles(self):
        """更新所有按钮的样式"""
        if hasattr(self.main_window, 'process_btn') and self.main_window.process_btn:
            self.main_window.process_btn.setStyleSheet(self.main_window.get_process_button_style())
            
        if hasattr(self.main_window, 'reselect_btn') and self.main_window.reselect_btn:
            self.main_window.reselect_btn.setStyleSheet(self.main_window.get_button_style())
            
        if hasattr(self.main_window, 'reset_btn') and self.main_window.reset_btn:
            self.main_window.reset_btn.setStyleSheet(self.main_window.get_button_style())
            
        if hasattr(self.main_window, 'undo_btn') and self.main_window.undo_btn:
            self.main_window.undo_btn.setStyleSheet(self.main_window.get_button_style())
            
        if hasattr(self.main_window, 'settings_btn') and self.main_window.settings_btn:
            self.main_window.settings_btn.setStyleSheet(self.main_window.get_button_style())