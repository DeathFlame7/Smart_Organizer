from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QFont

class ResultPopup(QWidget):
    """文件处理结果提示弹窗"""
    def __init__(self, parent, success_count, failed_count):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.SubWindow  # 确保弹窗不会获得焦点，不阻塞交互
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)  # 显示时不激活窗口
        
        # 设置弹窗内容
        layout = QVBoxLayout(self)
        
        # 计算总文件数
        total = success_count + failed_count
        
        # 标题
        title = QLabel("文件处理完成")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #333;")
        
        # 内容
        if total == 1:
            # 单个文件处理结果
            if success_count == 1:
                content_text = "文件处理成功"
            else:
                content_text = "文件处理失败"
        else:
            # 多个文件处理结果
            content_text = f"文件处理成功 -> 处理成功{success_count}个文件/处理失败{failed_count}个文件"
        
        content = QLabel(content_text)
        content_font = QFont()
        content_font.setPointSize(12)
        content.setFont(content_font)
        content.setAlignment(Qt.AlignCenter)
        content.setStyleSheet("color: #333;")
        
        layout.addWidget(title)
        layout.addWidget(content)
        
        # 设置弹窗样式
        self.setStyleSheet(f"""
            background-color: rgba(230, 230, 230, 0.8);
            border-radius: 8px;
            padding: 20px 30px;
        """)
        
        # 调整大小
        self.adjustSize()
        
        # 设置透明度动画
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        # 初始透明度为0
        self.opacity_effect.setOpacity(0)
        
        # 淡入动画
        self.fade_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in.setDuration(300)
        self.fade_in.setStartValue(0)
        self.fade_in.setEndValue(1)
        self.fade_in.setEasingCurve(QEasingCurve.InOutQuad)
        
        # 淡出动画
        self.fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out.setDuration(500)
        self.fade_out.setStartValue(1)
        self.fade_out.setEndValue(0)
        self.fade_out.setEasingCurve(QEasingCurve.InOutQuad)
        
        # 居中显示
        self.center_in_parent()
        
        # 显示并开始动画
        self.show()
        self.fade_in.start()
        
        # 设置自动消失定时器
        self.timer = QTimer(self)
        self.timer.singleShot(2000, self.start_fade_out)  # 2秒后开始淡出
    
    def center_in_parent(self):
        """在父窗口中居中显示"""
        if self.parent():
            parent_rect = self.parent().geometry()
            x = parent_rect.center().x() - self.width() // 2
            y = parent_rect.center().y() - self.height() // 2
            self.move(x, y)
    
    def start_fade_out(self):
        """开始淡出动画并在结束后关闭"""
        self.fade_out.finished.connect(self.close)
        self.fade_out.start()
    
    def resizeEvent(self, event):
        """窗口大小变化时重新居中"""
        self.center_in_parent()
        super().resizeEvent(event)