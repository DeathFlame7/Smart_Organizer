from PySide6.QtWidgets import QWidget, QGridLayout, QRubberBand, QApplication, QLabel
from PySide6.QtCore import Qt, QPoint, QRect, QEvent
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QFont
import logging

class DragManager(QWidget):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        
        # 设置透明背景
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        # 拖动状态
        self.dragging_widget = None
        self.drag_start_pos = None
        self.drag_offset = None
        self.rubber_band = None
        
        # 网格设置
        self.grid_size = 20
        
        # 初始化可拖动的区域
        self.draggable_widgets = []
        self.setup_draggable_widgets()
        
        # 隐藏自己，只在拖动时显示
        self.hide()
    
    def setup_draggable_widgets(self):
        """设置可拖动的窗口部件"""
        # 获取三个主要区域
        if hasattr(self.main_window, 'directory_frame'):
            self.draggable_widgets.append(self.main_window.directory_frame)
        if hasattr(self.main_window, 'preview_frame'):
            self.draggable_widgets.append(self.main_window.preview_frame)
        if hasattr(self.main_window, 'log_frame'):
            self.draggable_widgets.append(self.main_window.log_frame)
        
        # 为每个可拖动部件安装事件过滤器
        for widget in self.draggable_widgets:
            widget.installEventFilter(self)
            # 确保标题栏可拖动
            if hasattr(widget, 'findChild'):
                title_label = widget.findChild(QLabel)
                if title_label:
                    title_label.setCursor(Qt.OpenHandCursor)
    
    def eventFilter(self, source, event):
        """事件过滤器，捕获鼠标事件"""
        # 检查事件源是否是可拖动部件
        if source in self.draggable_widgets:
            # 检查是否点击了标题栏区域
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                # 检查是否点击了标题栏（假设第一个子部件是标题标签）
                if hasattr(source, 'children') and source.children():
                    first_child = source.children()[0]
                    if isinstance(first_child, QLabel):
                        # 确保点击位置在标题栏内
                        title_rect = first_child.geometry()
                        if title_rect.contains(event.pos()):
                            self.start_drag(source, event.pos())
                            return True
        return super().eventFilter(source, event)
    
    def start_drag(self, widget, position):
        """开始拖动操作"""
        self.dragging_widget = widget
        self.drag_start_pos = position
        self.drag_offset = widget.pos()
        
        # 创建橡皮筋框
        self.rubber_band = QRubberBand(QRubberBand.Rectangle, self.main_window)
        self.rubber_band.setGeometry(QRect(widget.pos(), widget.size()))
        self.rubber_band.show()
        
        # 显示自己（网格和虚化效果）
        self.show()
        self.raise_()
        
        # 捕获鼠标
        QApplication.setOverrideCursor(Qt.ClosedHandCursor)
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件，更新拖动位置"""
        if self.dragging_widget and self.rubber_band:
            # 计算新位置
            new_pos = event.globalPosition().toPoint() - self.drag_start_pos + self.drag_offset
            
            # 对齐到网格
            new_pos.setX((new_pos.x() // self.grid_size) * self.grid_size)
            new_pos.setY((new_pos.y() // self.grid_size) * self.grid_size)
            
            # 更新橡皮筋框位置
            self.rubber_band.setGeometry(QRect(new_pos, self.dragging_widget.size()))
            
            # 重绘以更新网格和虚化效果
            self.update()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件，结束拖动操作"""
        if self.dragging_widget and self.rubber_band:
            # 获取最终位置
            final_rect = self.rubber_band.geometry()
            
            # 检查是否在有效区域内（窗口内除标题栏和按钮外）
            main_rect = self.main_window.rect()
            title_bar_height = 40  # 估计的标题栏高度
            valid_rect = QRect(
                main_rect.left() + 10,  # 左右边距
                main_rect.top() + title_bar_height + 10,  # 上边距（标题栏下）
                main_rect.width() - 20,  # 左右边距
                main_rect.height() - title_bar_height - 20  # 上下边距
            )
            
            # 确保部件在有效区域内
            if valid_rect.contains(final_rect.center()):
                # 处理重叠区域
                self.handle_overlaps(final_rect)
                
                # 移动部件到最终位置
                self.dragging_widget.move(final_rect.topLeft())
                
                # 调整布局
                self.adjust_layout()
            
            # 清理
            self.rubber_band.hide()
            self.rubber_band.deleteLater()
            self.rubber_band = None
            self.dragging_widget = None
            
            # 隐藏自己
            self.hide()
            
            # 恢复鼠标
            QApplication.restoreOverrideCursor()
    
    def handle_overlaps(self, new_rect):
        """处理重叠区域，移动被覆盖的部件"""
        overlap_threshold = 0.5  # 超过50%的重叠才移动
        
        for widget in self.draggable_widgets:
            if widget != self.dragging_widget and widget.isVisible():
                widget_rect = widget.geometry()
                # 计算重叠区域
                overlap = new_rect.intersected(widget_rect)
                overlap_area = overlap.width() * overlap.height()
                widget_area = widget_rect.width() * widget_rect.height()
                
                # 如果重叠超过阈值，移动部件
                if overlap_area > widget_area * overlap_threshold:
                    # 计算移动方向（优先水平方向）
                    if new_rect.center().x() < widget_rect.center().x():
                        # 向左移动
                        new_x = new_rect.left() - widget_rect.width() - 10
                    else:
                        # 向右移动
                        new_x = new_rect.right() + 10
                    
                    # 保持垂直位置不变
                    new_y = widget_rect.top()
                    
                    # 确保在有效区域内
                    main_rect = self.main_window.rect()
                    if new_x < 10:
                        new_x = 10
                    if new_x + widget_rect.width() > main_rect.width() - 10:
                        new_x = main_rect.width() - widget_rect.width() - 10
                    
                    # 移动部件
                    widget.move(new_x, new_y)
    
    def adjust_layout(self):
        """调整整体布局"""
        # 这里可以根据需要调整布局结构
        # 例如，更新分割器的大小或位置
        pass
    
    def paintEvent(self, event):
        """绘制半透明网格和虚化效果"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 获取窗口大小
        rect = self.rect()
        
        # 绘制背景虚化效果
        bg_color = QColor(255, 255, 255, 128)  # 半透明白色
        painter.fillRect(rect, bg_color)
        
        # 绘制网格
        grid_color = QColor(0, 0, 0, 30)  # 半透明黑色
        pen = QPen(grid_color, 1, Qt.SolidLine)
        painter.setPen(pen)
        
        # 绘制垂直线
        for x in range(0, rect.width(), self.grid_size):
            painter.drawLine(x, 0, x, rect.height())
        
        # 绘制水平线
        for y in range(0, rect.height(), self.grid_size):
            painter.drawLine(0, y, rect.width(), y)
        
        # 虚化其他部件
        if self.dragging_widget:
            for widget in self.draggable_widgets:
                if widget != self.dragging_widget and widget.isVisible():
                    widget_rect = widget.geometry()
                    # 转换为当前部件的坐标系
                    local_rect = self.mapFromGlobal(widget.mapToGlobal(QPoint(0, 0)))
                    local_rect.setSize(widget.size())
                    
                    # 绘制半透明覆盖层
                    dim_color = QColor(255, 255, 255, 150)  # 更不透明的白色
                    painter.fillRect(QRect(local_rect, widget.size()), dim_color)
    
    def resizeEvent(self, event):
        """调整大小时更新自己的大小"""
        # 跟随主窗口大小
        self.setGeometry(self.main_window.rect())
        super().resizeEvent(event)