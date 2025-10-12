from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
                              QFormLayout, QLineEdit, QPushButton, QComboBox,
                              QLabel, QCheckBox, QDoubleSpinBox)
from PySide6.QtCore import Qt
import logging


class BatchChangeDialog(QDialog):
    """批量修改提示对话框"""

    def __init__(self, original_category, count, parent=None):
        super().__init__(parent)
        self.setWindowTitle("批量修改提示")
        self.setMinimumWidth(350)

        layout = QVBoxLayout()

        msg = f"检测到有 {count} 个文件与当前文件同属 '{original_category}' 分类。\n"
        msg += "是否将这些文件也修改为新分类？"
        layout.addWidget(QLabel(msg))

        self.remember_checkbox = QCheckBox("记住此选择，不再提示")
        layout.addWidget(self.remember_checkbox)

        btn_layout = QHBoxLayout()
        self.yes_btn = QPushButton("是，批量修改")
        self.no_btn = QPushButton("否，只修改当前文件")
        self.cancel_btn = QPushButton("取消")

        self.yes_btn.clicked.connect(lambda: self.accept_with_choice(True))
        self.no_btn.clicked.connect(lambda: self.accept_with_choice(False))
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.yes_btn)
        btn_layout.addWidget(self.no_btn)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

        self.choice = None

    def accept_with_choice(self, choice):
        self.choice = choice
        self.accept()


class FilterDialog(QDialog):
    def __init__(self, headers, parent=None):
        super().__init__(parent)
        self.headers = headers
        self.filters = {}
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("筛选")
        self.setGeometry(300, 300, 400, 300)
        
        # 创建筛选条件区域
        filter_group = QGroupBox("筛选条件")
        filter_layout = QFormLayout()
        
        # 为每个可筛选的列创建输入框和操作符
        self.filter_inputs = {}
        self.filter_operators = {}
        
        # 只允许对特定列进行筛选（跳过序号列和选择列）
        for col_idx in range(2, len(self.headers)):
            if col_idx >= len(self.headers):
                continue
            
            header = self.headers[col_idx]
            if header in ['文件名', '分类', '可信度', '路径', '类型', '大小', '状态']:
                # 对于数值类型的列（大小、可信度），添加操作符下拉框
                if header in ['大小', '可信度']:
                    # 创建水平布局包含操作符和输入框
                    h_layout = QHBoxLayout()
                    operator_combo = QComboBox()
                    operator_combo.addItems(['包含', '大于', '小于', '等于'])
                    h_layout.addWidget(operator_combo, 1)
                    
                    input_field = QLineEdit()
                    if header == '大小':
                        input_field.setPlaceholderText("输入大小值，如: 100KB, 2MB")
                    elif header == '可信度':
                        input_field.setPlaceholderText("输入可信度值，如: 0.8, 0.95")
                    h_layout.addWidget(input_field, 2)
                    
                    filter_layout.addRow(f"{header}:", h_layout)
                    self.filter_operators[col_idx] = operator_combo
                else:
                    input_field = QLineEdit()
                    filter_layout.addRow(f"{header}:", input_field)
                
                self.filter_inputs[col_idx] = input_field
        
        filter_group.setLayout(filter_layout)
        
        # 创建按钮区域
        button_layout = QHBoxLayout()
        
        apply_btn = QPushButton("应用")
        apply_btn.clicked.connect(self.accept)
        
        clear_btn = QPushButton("清除")
        clear_btn.clicked.connect(self.clear_filters)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(apply_btn)
        button_layout.addWidget(clear_btn)
        button_layout.addWidget(cancel_btn)
        
        # 设置主布局
        main_layout = QVBoxLayout()
        main_layout.addWidget(filter_group)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def get_filters(self):
        """获取用户设置的筛选条件，转换为字段名格式"""
        # 列索引到字段名的映射
        header_to_field = {
            '分类': 'category',
            '可信度': 'confidence_min',
            '类型': 'type',
            '大小': 'size',
            '状态': 'status',
            '原文件名': 'name_contains',
            '路径': 'name_contains'
        }
        
        for col_idx, input_field in self.filter_inputs.items():
            text = input_field.text().strip()
            if text and col_idx < len(self.headers):
                header = self.headers[col_idx]
                field_name = header_to_field.get(header)
                
                if field_name:
                    if field_name == 'confidence_min':
                        # 可信度转换为浮点数
                        try:
                            self.filters[field_name] = float(text)
                        except ValueError:
                            logging.warning(f"无效的可信度值: {text}")
                    elif field_name == 'size':
                        # 处理大小筛选
                        # 简单处理：只考虑最小值，实际应用中可能需要更复杂的大小单位转换
                        try:
                            # 这里简化处理，将大小转换为字节
                            size_value = float(text)
                            self.filters['size_min'] = size_value
                        except ValueError:
                            logging.warning(f"无效的大小值: {text}")
                    else:
                        # 其他字段直接使用文本值
                        self.filters[field_name] = text
        
        return self.filters
    
    def clear_filters(self):
        """清除所有筛选条件"""
        for input_field in self.filter_inputs.values():
            input_field.clear()
        for operator_combo in self.filter_operators.values():
            operator_combo.setCurrentIndex(0)
        self.filters.clear()