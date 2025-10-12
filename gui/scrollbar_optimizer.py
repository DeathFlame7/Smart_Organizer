from PySide6.QtWidgets import QApplication, QScrollBar, QAbstractScrollArea
from PySide6.QtCore import Qt, QObject, QEvent
from PySide6.QtGui import QWheelEvent

# 定义滚动条样式常量
def SCROLLBAR_WIDTH():
    return 8

def SCROLLBAR_HANDLE_MIN_WIDTH():
    return 20

def SCROLLBAR_BORDER_RADIUS():
    return 4

class ScrollBarOptimizer:
    """
    滚动条样式优化器，用于美化滚动条并添加shift+鼠标滚轮左右滑动功能
    """
    
    @staticmethod
    def apply_optimized_scrollbar_style(widget):
        """
        应用优化的滚动条样式到指定组件
        """
        # 使用常量定义滚动条样式表
        scrollbar_style = f"""
        QScrollBar:vertical {{
            width: {SCROLLBAR_WIDTH()}px;
            background: #f0f0f0;
            margin: 0px;
            border-radius: {SCROLLBAR_BORDER_RADIUS()}px;
        }}
        
        QScrollBar::handle:vertical {{
            background: #bbbbbb;
            min-height: 20px;
            border-radius: {SCROLLBAR_BORDER_RADIUS()}px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background: #aaaaaa;
        }}
        
        QScrollBar::handle:vertical:pressed {{
            background: #999999;
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
            width: 0px;
        }}
        
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
        
        QScrollBar:horizontal {{
            height: {SCROLLBAR_WIDTH()}px;
            background: #f0f0f0;
            margin: 0px;
            border-radius: {SCROLLBAR_BORDER_RADIUS()}px;
        }}
        
        QScrollBar::handle:horizontal {{
            background: #bbbbbb;
            min-width: {SCROLLBAR_HANDLE_MIN_WIDTH()}px;
            border-radius: {SCROLLBAR_BORDER_RADIUS()}px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background: #aaaaaa;
        }}
        
        QScrollBar::handle:horizontal:pressed {{
            background: #999999;
        }}
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            height: 0px;
            width: 0px;
        }}
        
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
        }}
        """
        
        # 保留原有样式，追加滚动条样式
        existing_style = widget.styleSheet()
        widget.setStyleSheet(existing_style + scrollbar_style)
        
        # 为组件添加事件过滤器以处理shift+滚轮左右滑动
        widget.installEventFilter(ScrollBarOptimizer.ShiftWheelFilter(widget))
        
        # 如果是带有滚动条的复合组件，也需要为其子组件的滚动条设置样式
        if isinstance(widget, QAbstractScrollArea):
            # 为视图的视口添加事件过滤器
            viewport = widget.viewport()
            if viewport:
                viewport.installEventFilter(ScrollBarOptimizer.ShiftWheelFilter(widget))
            
            # 获取并设置水平和垂直滚动条的样式
            h_scrollbar = widget.horizontalScrollBar()
            v_scrollbar = widget.verticalScrollBar()
            
            if h_scrollbar:
                h_scrollbar.setStyleSheet(h_scrollbar.styleSheet() + scrollbar_style)
            if v_scrollbar:
                v_scrollbar.setStyleSheet(v_scrollbar.styleSheet() + scrollbar_style)
        
    class ShiftWheelFilter(QObject):
        """
        处理shift+鼠标滚轮左右滑动的事件过滤器
        """
        
        def __init__(self, widget):
            super().__init__()
            self.widget = widget
            
        def eventFilter(self, obj, event):
            # 检查是否是鼠标滚轮事件
            if event.type() == QEvent.Wheel:
                wheel_event = QWheelEvent(event)
                
                # 检查是否按住了Shift键
                if wheel_event.modifiers() & Qt.ShiftModifier:
                    # 获取水平滚动条
                    if hasattr(self.widget, 'horizontalScrollBar'):
                        h_scrollbar = self.widget.horizontalScrollBar()
                        if h_scrollbar and h_scrollbar.isVisible():
                            # 计算滚动量
                            delta = wheel_event.angleDelta().y()
                            # 根据滚动方向计算水平滚动步长
                            step = h_scrollbar.singleStep() * (delta // 120)
                            # 执行水平滚动
                            h_scrollbar.setValue(h_scrollbar.value() - step)
                            return True
            
            # 不是需要处理的事件，传递给原事件处理器
            return False

    @staticmethod
    def optimize_all_scrollbars():
        """
        优化应用程序中所有组件的滚动条
        """
        app = QApplication.instance()
        if app:
            # 递归查找所有组件并应用滚动条优化
            def optimize_recursive(widgets):
                for widget in widgets:
                    if isinstance(widget, (QScrollBar, QAbstractScrollArea)):
                        ScrollBarOptimizer.apply_optimized_scrollbar_style(widget)
                    # 递归处理子组件
                    optimize_recursive(widget.findChildren(QAbstractScrollArea))
                
            # 从应用程序顶层窗口开始优化
            optimize_recursive(app.topLevelWidgets())

# 创建一个全局优化器实例
scrollbar_optimizer = ScrollBarOptimizer()