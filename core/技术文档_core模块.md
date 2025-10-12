# 智能文件管理助手 - Core模块技术文档

## 1. 模块概述

Core模块是智能文件管理助手的核心功能模块，负责实现文件处理、分类、重命名以及数据存储等基础功能。该模块为上层UI提供了所有必要的业务逻辑支持，实现了文件智能管理的核心算法和数据处理流程。

## 2. 目录结构

```
.venv/core/
├── classifier.py      # 文件分类器实现
├── database.py        # 数据库操作实现
├── file_processor.py  # 文件处理功能实现
├── renamer.py         # 文件重命名功能实现
└── workers.py         # 工作线程管理实现
```

## 3. 核心功能模块

### 3.1 文件分类器 (FileClassifier)

文件分类器负责根据文件内容自动识别文件类型和类别，使用机器学习算法进行智能分类。

#### 3.1.1 主要功能
- 基于朴素贝叶斯算法和TF-IDF向量izer实现文本分类
- 支持中文文本分词（使用jieba库）
- 包含预定义的多种文件类别（合同、会议纪要、项目计划等）
- 支持从历史分类数据中学习和优化
- 支持手动分类结果的学习和模型更新
- 支持模型的保存和加载

#### 3.1.2 类结构
```python
class FileClassifier:
    def __init__(self):
        # 初始化分类器、向量izer和训练数据
        self.model = MultinomialNB()
        self.vectorizer = TfidfVectorizer(tokenizer=self._chinese_tokenizer, max_features=5000)
        self.is_trained = False
        self.sample_data = self._load_sample_data()
        # ...其他初始化代码
```

#### 3.1.3 核心方法
- `train()`: 训练分类器，结合基础样本数据和学习数据
- `predict_with_confidence(text_content)`: 预测文件类别并返回可信度
- `predict(text_content)`: 仅预测文件类别
- `learn_from_manual_classification(content, category)`: 从用户手动分类中学习
- `_extract_keywords(text)`: 提取关键词用于分类
- `save_model()`: 保存训练好的模型
- `_load_saved_model()`: 加载已保存的模型

### 3.2 数据库操作 (FileDatabase)

数据库操作模块负责管理应用程序的数据存储，使用SQLite数据库保存文件信息和操作记录。

#### 3.2.1 主要功能
- 初始化数据库表结构
- 记录文件操作历史
- 存储和检索文件分类信息
- 支持事务处理和错误恢复
- 提供线程安全的数据库连接

#### 3.2.2 类结构
```python
class FileDatabase:
    def __init__(self):
        config = load_config()
        self.db_path = Path(config.get('DEFAULT', 'database_path', fallback='data/files.db'))
        os.makedirs(self.db_path.parent, exist_ok=True)
        self._init_db()
```

#### 3.2.3 核心方法
- `_get_connection()`: 创建独立连接，确保线程安全
- `_init_db()`: 初始化表结构，增加异常捕获
- `insert_operation(op_type, source_path, target_path, status, timestamp, category, content)`: 插入操作记录
- `get_operations_since(timestamp)`: 获取指定时间戳之后的操作记录，用于机器学习
- `update_file_processed(file_path, is_processed)`: 更新文件处理状态
- `get_last_operation()`: 获取最后一次操作记录
- `update_operation_status(operation_id, status)`: 更新操作记录的状态

### 3.3 文件处理器 (FileProcessor)

文件处理器负责文件信息获取、目录扫描和内容提取等功能，支持多种文件格式的处理。

#### 3.3.1 主要功能
- 获取文件基本信息（路径、名称、大小、修改时间等）
- 扫描目录下的所有支持的文件
- 提取文件内容（支持PDF、DOCX、TXT、图片等格式）
- 获取图片文件的额外信息（尺寸、格式、元数据等）
- 支持多线程处理

#### 3.3.2 类结构
```python
class FileProcessor:
    def __init__(self):
        self.mime = magic.Magic(mime=True)
        self.config = load_config()
        self.thread_count = int(self.config.get('DEFAULT', 'scan_threads', fallback=4))
        self.executor = ThreadPoolExecutor(max_workers=self.thread_count)
        self.task_queue = queue.Queue()
        self.supported_extensions = {'.pdf', '.docx', '.txt', '.md', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
```

#### 3.3.3 核心方法
- `get_file_info(file_path)`: 获取文件信息，扩展支持图片文件
- `scan_directory(directory, recursive)`: 扫描目录，确保包含所有支持的文件类型
- `extract_text_content(file_path)`: 提取文件内容，为图片文件生成描述性内容
- `extract_text_content_async(file_path)`: 异步提取文件内容
- `_extract_image_info(file_path)`: 提取图片信息作为文本内容
- `_read_txt(file_path)`: 读取文本文件内容
- `_extract_pdf_text(file_path)`: 提取PDF文件文本
- `_extract_docx_text(file_path)`: 提取DOCX文件文本
- `process_file(file_path, category, new_name)`: 处理单个文件并返回处理结果

### 3.4 文件重命名器 (FileRenamer)

文件重命名器负责根据文件内容、类型等信息生成有意义的新文件名。

#### 3.4.1 主要功能
- 根据文件内容和类型生成适当的文件名
- 支持图片文件的智能命名
- 支持不同类型文档的专门命名规则
- 生成带时间戳的文件名以避免冲突

#### 3.4.2 类结构
```python
class FileRenamer:
    @staticmethod
    def generate_name(content, file_type, original_name, file_path=None):
        # 根据文件内容和类型生成合适的文件名
        # ...
```

#### 3.4.3 核心方法
- `generate_name(content, file_type, original_name, file_path)`: 生成文件名
- `_generate_document_name(content, original_name)`: 生成文档文件名
- `_generate_image_name(content, original_name, file_path)`: 生成图片文件名
- `_generate_contract_name(content, original_name)`: 生成合同文件名
- `_generate_financial_name(content, original_name)`: 生成财务文件名
- `_default_rename(original_name, file_type, file_path)`: 默认重命名规则
- `generate_preview_name(original_name, suggested_category)`: 生成预览文件名

### 3.5 工作线程管理 (FileProcessingWorker)

工作线程管理负责后台处理文件，避免阻塞UI线程，并提供进度反馈和结果通知。

#### 3.5.1 主要功能
- 在后台线程中处理文件
- 提供处理进度反馈
- 通知处理完成或错误
- 支持取消正在进行的处理

#### 3.5.2 类结构
```python
class WorkerSignals(QObject):
    finished = Signal(list)
    progress = Signal(int)
    error = Signal(str)

class FileProcessingWorker(threading.Thread):
    def __init__(self, directory, processor, classifier, renamer, db, signals):
        super().__init__()
        self.directory = directory
        self.processor = processor
        self.classifier = classifier
        self.renamer = renamer
        self.db = db
        self.signals = signals
        # ...
```

#### 3.5.3 核心方法
- `run()`: 线程运行方法，处理目录中的所有文件

## 4. 模块间交互

Core模块的各个组件之间存在密切的交互关系：

1. **FileProcessingWorker** 作为协调者，整合了其他所有组件的功能：
   - 使用 **FileProcessor** 扫描目录和提取文件内容
   - 使用 **FileClassifier** 对文件进行分类
   - 使用 **FileRenamer** 生成新文件名
   - 使用 **FileDatabase** 记录操作历史

2. **FileClassifier** 和 **FileDatabase** 之间存在数据交换：
   - **FileClassifier** 从 **FileDatabase** 加载历史分类数据进行学习
   - **FileClassifier** 将学习到的新分类规则保存到模型文件

3. **FileProcessor** 为其他组件提供基础数据支持：
   - 为 **FileClassifier** 提供文件内容用于分类
   - 为 **FileRenamer** 提供文件信息用于命名

## 5. 数据流向

1. **扫描阶段**：
   - FileProcessor 扫描指定目录，获取文件基本信息
   - 将文件信息传递给 FileClassifier 进行分类
   - 将分类结果传递给 FileRenamer 生成新文件名
   - 将所有信息整合为处理结果返回给UI

2. **处理阶段**：
   - FileProcessingWorker 接收UI传递的处理指令
   - 调用相应组件对文件进行实际处理（分类、重命名、移动）
   - 将处理结果保存到数据库
   - 向UI提供处理进度和最终结果

## 6. 异常处理

Core模块实现了全面的异常处理机制，确保在各种异常情况下系统能够稳定运行：

1. **数据库操作**：所有数据库操作都包含完整的try-except块，并在失败时回滚事务
2. **文件处理**：处理文件时捕获所有可能的异常，并记录详细的错误信息
3. **模型加载**：在加载预训练模型失败时，自动回退到使用基础样本重新训练
4. **配置管理**：处理配置文件不存在或损坏的情况

## 7. 扩展性设计

Core模块设计具有良好的扩展性，可以方便地添加新功能：

1. **分类器扩展**：可以轻松添加新的文件类别和训练样本
2. **文件格式支持**：可以扩展FileProcessor以支持更多的文件格式
3. **重命名规则**：可以添加新的专门针对特定文件类型的命名规则
4. **数据库表结构**：设计允许灵活添加新的字段和表

## 8. 性能优化

Core模块实现了多项性能优化措施：

1. **多线程处理**：使用ThreadPoolExecutor进行并行文件处理
2. **缓存机制**：对文件内容和分类结果进行适当的缓存
3. **批量操作**：对数据库操作进行批量处理，减少IO开销
4. **资源管理**：确保文件句柄和数据库连接等资源正确关闭

以上是Core模块的详细技术文档，该模块作为智能文件管理助手的核心，为整个应用程序提供了基础功能支持。