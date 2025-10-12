import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 确保中文字体正常显示
app = QApplication(sys.argv)
font = QFont()
font.setFamily("SimHei")  # 设置为黑体
app.setFont(font)

# 导入并显示主窗口
from gui.main_window import MainWindow
main_window = MainWindow()
main_window.show()

# 运行应用程序
sys.exit(app.exec())