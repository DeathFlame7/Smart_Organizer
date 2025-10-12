# 智理 - 智能文件管理助手

![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![PySide6](https://img.shields.io/badge/GUI-PySide6-orange.svg)
![Machine Learning](https://img.shields.io/badge/Machine%20Learning-scikit--learn-green.svg)

## 项目简介

**智理**是一款基于Python的智能文件管理助手，能够自动扫描、分类、重命名和整理用户指定目录下的文件。该工具通过文本内容分析和机器学习模型实现智能分类，大大提高了文件管理的效率和准确性，让文件系统井然有序。

## 主要功能

- **智能文件分类**：基于机器学习算法自动识别文件类型（支持14种基础文件类型）
- **自动文件重命名**：根据文件内容和类型生成有意义的新文件名
- **批量文件处理**：支持一次性处理多个文件，提高工作效率
- **操作历史记录**：详细记录所有文件操作，支持撤销功能
- **用户友好界面**：基于PySide6的现代图形界面，操作简单直观
- **多条件筛选**：支持按类型、大小、修改时间等条件筛选文件
- **文件预览**：提供文件内容预览和分类结果预览
- **支持多种文件格式**：支持PDF、DOCX、TXT、图片等多种常见文件格式

## 技术架构

项目采用模块化设计，各模块之间职责明确，便于维护和扩展。整体架构分为核心处理层、数据持久层和用户界面层三大部分。

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│    用户界面层       │     │    核心处理层       │     │    数据持久层       │
│  (GUI Components)   │◄───►│  (Core Processing)  │◄───►│  (Data Storage)     │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
        │                         │                         │
        │                         ▼                         │
        │                   ┌─────────────────────┐         │
        │                   │   文件处理结果      │         │
        │                   │ (Processing Results)│         │
        │                   └─────────────────────┘         │
        └───────────────────────────┬───────────────────────┘
                                     ▼
                             ┌─────────────────────┐
                             │     文件系统        │
                             │   (File System)     │
                             └─────────────────────┘
```

## 目录结构

```
├── core/             # 核心处理模块
│   ├── database.py   # 数据库操作模块
│   ├── file_processor.py # 文件处理模块
│   ├── classifier.py # 文件分类模块
│   ├── renamer.py    # 文件重命名模块
│   └── workers.py    # 异步工作线程
├── gui/              # 用户界面模块
│   ├── main_window.py # 主窗口
│   ├── preview_panel.py # 预览面板
│   ├── file_tree.py  # 文件树视图
│   ├── components/   # UI组件
│   ├── drag_manager/ # 拖拽管理
│   └── window_components/ # 窗口组件
├── utils/            # 工具函数
│   ├── config.py     # 配置管理
│   └── logger.py     # 日志管理
├── data/             # 数据存储目录
├── main.py           # 程序入口
├── start_app.py      # 应用启动脚本
├── requirements.txt  # 依赖项列表
└── config.ini        # 配置文件
```

## 核心功能模块

### 1. 文件处理模块 (FileProcessor)
- 获取文件元数据（大小、类型、路径等）
- 扫描目录并筛选支持的文件类型
- 提取文档内容（支持PDF、DOCX、TXT等格式）

```python
# 关键方法
def scan_directory(directory, recursive=True):
    # 扫描目录并返回文件列表
    

def get_file_info(file_path):
    # 获取文件基本信息
```

### 2. 文件分类模块 (FileClassifier)
基于机器学习的文本分类算法，自动识别文件类型：
- 使用jieba进行中文分词
- 使用TfidfVectorizer将文本转换为特征向量
- 使用MultinomialNB模型进行分类预测
- 支持从用户手动分类中学习，不断优化分类准确性

支持的文件类别包括：合同、会议纪要、项目计划、财务报表、产品说明、用户手册、技术文档、图片等14种类型。

```python
# 关键方法
def predict_with_confidence(content):
    # 预测内容分类并返回可信度
    

def learn_from_manual_classification(content, correct_category):
    # 从手动分类中学习
```

### 3. 文件重命名模块 (FileRenamer)
根据文件类型和内容生成新的、有意义的名称：
- 针对不同类型文件采用不同命名策略
- 文档文件：基于内容关键词生成名称
- 图片文件：基于图片特性和时间生成名称
- 合同文件：识别合同特性生成标准名称
- 财务文件：识别时间周期生成名称

```python
# 关键方法
def generate_name(content, file_type, original_name, file_path=None):
    # 生成新文件名
```

### 4. 数据库模块 (FileDatabase)
负责文件操作历史的记录与查询，为撤销功能提供数据支持：
- 记录文件操作信息（源路径、目标路径、操作类型、时间戳等）
- 查询操作历史
- 更新操作状态

```python
# 关键方法
def insert_operation(op_type, source_path, target_path, status, timestamp, category=None, content=None, batch_id=None):
    # 插入操作记录
    

def get_last_operation():
    # 获取最后一次操作记录
```

### 5. 图形界面模块 (GUI)
基于PySide6的现代用户界面，提供直观的操作体验：
- 主窗口：整体布局和各组件的协调
- 文件树视图：文件系统的层次化浏览
- 预览面板：文件分类结果的预览和交互
- 结果弹窗：显示文件处理结果
- 设置管理器：管理应用程序配置

```python
# 主窗口关键方法
def scan_and_preview():
    # 扫描文件并显示分类预览
    

def process_files():
    # 处理选定的文件
    

def undo_last_operation():
    # 撤销最后一次操作
```

## 工作流程

### 文件处理流程
1. 用户选择要扫描的目录
2. 程序扫描目录并分析每个文件的内容和元数据
3. 使用机器学习模型预测文件类型
4. 为每个文件生成建议的新名称
5. 显示分类预览，用户可以调整分类和文件名
6. 用户确认后，执行文件移动和重命名操作
7. 记录操作历史到数据库

### 撤销操作流程
1. 用户点击"撤销"按钮
2. 系统查询最后一次操作记录
3. 根据操作记录执行撤销逻辑（将文件移回原位置）
4. 更新操作状态
5. 重新扫描并显示更新后的文件列表

## 安装指南

### 前置要求
- Python 3.11或更高版本
- pip包管理器

### 安装步骤
1. 克隆项目仓库
   ```bash
   git clone https://github.com/Chen2871/Smart_Organizer.git
   cd Smart_Organizer
   ```

2. 安装依赖包
   ```bash
   pip install -r requirements.txt
   ```

3. 运行应用程序
   ```bash
   python start_app.py  # 或
   python main.py
   ```

## 使用说明

### 基本操作
1. 启动应用程序后，点击"选择文件夹"按钮选择要整理的目录，开始扫描文件
2. 扫描完成后，查看文件分类结果预览
3. 可以手动调整文件分类和建议的新名称
4. 选择要处理的文件，点击"处理"按钮执行文件整理操作
5. 操作完成后，可以查看处理结果

### 高级功能
- **筛选文件**：使用筛选功能按类型、大小等条件筛选文件
- **批量处理**：选择多个文件进行批量分类和重命名
- **撤销操作**：如果对处理结果不满意，可以使用撤销功能恢复到之前的状态

## 技术栈

- **编程语言**：Python 3.11
- **GUI框架**：PySide6
- **机器学习**：scikit-learn, jieba
- **文件处理**：pdfplumber, python-docx, Pillow
- **数据存储**：SQLite
- **其他工具**：python-magic, chardet, hashlib

## 许可证

MIT License

## 更新日志

### 最新版本
- 增加了图片文件支持
- 优化了文件分类算法
- 改进了用户界面体验
- 增强了程序稳定性

---

智理 - 让文件管理更智能、更高效！