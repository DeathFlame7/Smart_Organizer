from PySide6.QtWidgets import QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QLinearGradient, QPalette, QColor

class WindowControls(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: transparent;")
        self.title_layout = QHBoxLayout(self)
        self.title_layout.setContentsMargins(0, 0, 0, 0)
        self.title_layout.setSpacing(0)
        
        # 返回按钮 - 移到最左侧
        self.back_btn = QPushButton("返回")
        self.back_btn.setFixedSize(60, 30)
        self.back_btn.setStyleSheet("""QPushButton {
            background-color: rgba(200, 200, 200, 50);
            color: #333;
            border-radius: 8px;
            font-family: Arial;
            font-size: 12px;
            margin-left: 10px;
        }
        QPushButton:hover {
            background-color: rgba(200, 200, 200, 150);
        }""")
        self.back_btn.hide()  # 默认隐藏
        
        # 窗口标题 - 位于中间
        self.title_label = QLabel("智能文件管理助手")
        self.title_label.setStyleSheet("color: #333; font-weight: bold;")
        self.title_label.setAlignment(Qt.AlignCenter)
        
        # 窗口控制按钮容器
        self.controls_layout = QHBoxLayout()
        self.controls_layout.setContentsMargins(0, 0, 10, 0)
        
        # 最小化按钮
        self.minimize_btn = QPushButton("-")
        self.minimize_btn.setFixedSize(30, 30)
        self.minimize_btn.setStyleSheet("""QPushButton {
            background-color: transparent;
            color: #333;
            border-radius: 0px;
            font-family: Arial;
            font-size: 16px;
        }
        QPushButton:hover {
            background-color: rgba(200, 200, 200, 100);
        }""")
        
        # 最大化按钮
        self.maximize_btn = QPushButton("□")
        self.maximize_btn.setFixedSize(30, 30)
        self.maximize_btn.setStyleSheet("""QPushButton {
            background-color: transparent;
            color: #333;
            border-radius: 0px;
            font-family: Arial;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: rgba(200, 200, 200, 100);
        }""")
        
        # 关闭按钮
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setStyleSheet("""QPushButton {
            background-color: transparent;
            color: #333;
            border-radius: 0px;
            font-family: Arial;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: rgba(255, 0, 0, 100);
            color: white;
        }""")
        
        # 添加按钮到布局
        self.controls_layout.addWidget(self.minimize_btn)
        self.controls_layout.addWidget(self.maximize_btn)
        self.controls_layout.addWidget(self.close_btn)
        
        # 添加到标题栏布局 - 返回按钮在最左侧，标题在中间，控制按钮在右侧
        self.title_layout.addWidget(self.back_btn)
        self.title_layout.addWidget(self.title_label, 1)  # 1表示拉伸权重
        self.title_layout.addLayout(self.controls_layout)

class GradientBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def set_gradient(self, widget):
        """为指定控件设置渐变背景"""
        gradient = QLinearGradient(0, 0, widget.width(), widget.height())
        gradient.setColorAt(0.0, QColor(240, 240, 240))
        gradient.setColorAt(1.0, QColor(220, 220, 220))
        
        palette = QPalette()
        palette.setBrush(QPalette.Window, gradient)
        widget.setPalette(palette)
        widget.setAutoFillBackground(True)

class ActionButton(QPushButton):
    """可复用的操作按钮样式"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                padding: 15px 40px;
                font-size: 16px;
                background-color: white;
                color: #333;
                border-radius: 30px;
                border: none;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
            }
            QPushButton:hover {
                background-color: #f5f5f5;
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """)

class SettingButton(QPushButton):
    """可复用的设置按钮样式"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
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