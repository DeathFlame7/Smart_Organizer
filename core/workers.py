import threading
import time
import logging
import threading
import shutil  # 导入shutil模块用于跨文件系统复制
from PySide6.QtCore import Signal, QObject, QThread
from pathlib import Path
from utils.application_config import load_config

class WorkerSignals(QObject):
    finished = Signal(list)
    progress = Signal(int)
    error = Signal(str)

class FileScanWorker(QThread):
    """用于异步扫描和分析文件的工作线程"""
    progress_updated = Signal(int)
    scan_completed = Signal(list)
    scan_error = Signal(str)
    file_processed = Signal(dict)  # 每处理完一个文件发出信号
    
    def __init__(self, files, processor, classifier, renamer):
        super().__init__()
        self.files = files
        self.processor = processor
        self.classifier = classifier
        self.renamer = renamer
        self._stop_flag = False
        self._lock = threading.Lock()  # 添加线程锁保护共享资源
    
    def run(self):
        try:
            results = []
            total_files = len(self.files)
            
            for i, file_info in enumerate(self.files):
                # 检查是否停止
                if self._stop_flag:
                    self.scan_error.emit("扫描被取消")
                    return
                
                try:
                    file_path = Path(file_info['path'])
                    content = self.processor.extract_text_content(file_path)
                    category, confidence = self.classifier.predict_with_confidence(content)
                    
                    # 生成新文件名预览
                    new_name = self.renamer.generate_name(
                        content=content,
                        file_type=file_info['mime_type'],
                        original_name=file_info['name'],
                        file_path=file_path
                    )
                    
                    # 使用线程锁保护共享资源results列表
                    with self._lock:
                        # 构建结果字典
                        result = {
                            'original_name': file_info['name'],
                            'new_name': new_name,
                            'category': category,
                            'confidence': confidence,
                            'source_path': str(file_path),
                            'path': str(file_path),  # 为了兼容preview_panel的使用
                            'type': file_info.get('mime_type', 'unknown'),
                            'size': file_info.get('size', 0),
                            'content': content
                        }
                        results.append(result)
                    
                    # 发出文件处理完成的信号
                    self.file_processed.emit(result)
                    
                except PermissionError as e:
                    error_msg = str(e)
                    result = {
                        'original_name': file_info['name'],
                        'new_name': file_info['name'],
                        'category': "分析失败",
                        'confidence': 0.0,
                        'source_path': str(file_info['path']),
                        'path': str(file_info['path']),
                        'type': file_info.get('mime_type', 'unknown'),
                        'size': file_info.get('size', 0),
                        'status': 'failed',
                        'error': f"权限错误: {error_msg}"
                    }
                    with self._lock:
                        results.append(result)
                    self.scan_error.emit(f"文件 {file_info['name']} 权限错误: {error_msg}")
                except FileNotFoundError as e:
                    error_msg = str(e)
                    result = {
                        'original_name': file_info['name'],
                        'new_name': file_info['name'],
                        'category': "分析失败",
                        'confidence': 0.0,
                        'source_path': str(file_info['path']),
                        'path': str(file_info['path']),
                        'type': file_info.get('mime_type', 'unknown'),
                        'size': file_info.get('size', 0),
                        'status': 'failed',
                        'error': f"文件未找到: {error_msg}"
                    }
                    with self._lock:
                        results.append(result)
                    self.scan_error.emit(f"文件 {file_info['name']} 未找到: {error_msg}")
                except Exception as e:
                    error_msg = str(e)
                    result = {
                        'original_name': file_info['name'],
                        'new_name': file_info['name'],
                        'category': "分析失败",
                        'confidence': 0.0,
                        'source_path': str(file_info['path']),
                        'path': str(file_info['path']),
                        'type': file_info.get('mime_type', 'unknown'),
                        'size': file_info.get('size', 0),
                        'status': 'failed',
                        'error': str(e)
                    }
                    with self._lock:
                        results.append(result)
                    self.scan_error.emit(f"处理文件 {file_info['name']} 时出错: {error_msg}")
                
                # 更新进度
                progress = int((i + 1) / total_files * 100)
                self.progress_updated.emit(progress)
            
            # 完成扫描
            self.scan_completed.emit(results)
            
        except Exception as e:
            self.scan_error.emit(f"扫描过程中发生错误: {str(e)}")
            
    def stop(self):
        """停止扫描过程"""
        self._stop_flag = True
        self.wait(1000)  # 等待最多1秒


class FileProcessingWorker(threading.Thread):
    def __init__(self, directory, processor, classifier, renamer, db, signals, operation_batch_id=None, current_results=None):
        super().__init__()
        self.directory = directory
        self.processor = processor
        self.classifier = classifier
        self.renamer = renamer
        self.db = db
        self.signals = signals
        self.config = load_config()
        self.preview_before = self.config.getboolean('DEFAULT', 'preview_before_action', fallback=True)
        self._stop_flag = False  # 添加停止标志
        self._lock = threading.Lock()  # 添加线程锁保护共享资源
        self.operation_batch_id = operation_batch_id  # 批次ID
        self.current_results = current_results  # 用户在界面上修改后的结果

    def run(self):
        try:
            files = self.processor.scan_directory(self.directory)
            if not files:
                self.signals.error.emit(f"目录 {self.directory} 下无可用文件")
                return

            results = []
            total_files = len(files)
            logging.info(f"开始处理目录：{self.directory}，共 {total_files} 个文件")

            # 生成批次ID（如果没有提供）
            if not self.operation_batch_id:
                self.operation_batch_id = str(int(time.time()))
                logging.info(f"生成操作批次ID: {self.operation_batch_id}")

            # 构建文件路径到修改后结果的映射
            file_path_to_result = {}
            if self.current_results:
                for result in self.current_results:
                    if 'path' in result:
                        file_path_to_result[result['path']] = result
                    elif 'source_path' in result:
                        file_path_to_result[result['source_path']] = result

            for i, file_info in enumerate(files):
                # 检查是否停止
                if self._stop_flag:
                    self.signals.error.emit("文件处理被取消")
                    return
                
                file_path = Path(file_info['path'])
                file_path_str = str(file_path)
                
                try:
                    # 优先使用用户在界面上修改后的结果
                    content = None
                    category = None
                    confidence = 0.0
                    new_name = file_info['name']
                    
                    # 检查当前文件是否在用户修改后的结果中
                    if file_path_str in file_path_to_result:
                        # 使用用户修改后的分类信息
                        modified_result = file_path_to_result[file_path_str]
                        category = modified_result.get('category', None)
                        confidence = modified_result.get('confidence', 0.0)
                        
                        # 如果用户修改了新文件名，也使用修改后的文件名
                        if 'new_name' in modified_result:
                            new_name = modified_result['new_name']
                    
                    # 如果没有找到用户修改后的分类信息，则使用分类器预测
                    if not category:
                        content = self.processor.extract_text_content(file_path)
                        category, confidence = self.classifier.predict_with_confidence(content)
                    
                    # 如果没有找到用户修改后的文件名，则生成新文件名
                    if new_name == file_info['name']:
                        if not content:
                            content = self.processor.extract_text_content(file_path)
                        new_name = self.renamer.generate_name(
                            content=content,
                            file_type=file_info['mime_type'],
                            original_name=file_info['name'],
                            file_path=file_path
                        )

                    # 直接在当前目录下创建分类目录，不使用嵌套结构
                    target_dir = self.directory / category
                    target_dir.mkdir(exist_ok=True)
                    target_path = target_dir / new_name

                    if target_path.exists():
                        timestamp = int(time.time())
                        new_name = f"{target_path.stem}_{timestamp}{target_path.suffix}"
                        target_path = target_dir / new_name

                    status = "failed"  # 默认状态为失败
                    error_msg = ""
                    
                    # 尝试使用Path.rename移动文件，如果失败则使用shutil.move进行复制+删除
                    try:
                        file_path.rename(target_path)
                        status = "success"
                    except OSError as e:
                        # 如果是跨文件系统移动失败，则使用shutil.move
                        logging.warning(f"文件重命名失败，尝试跨文件系统移动: {e}")
                        try:
                            shutil.move(str(file_path), str(target_path))
                            status = "success"
                        except Exception as move_error:
                            status = "failed"
                            error_msg = f"跨文件系统移动失败: {str(move_error)}"
                            logging.error(error_msg)

                    # 记录操作到数据库
                    self.db.insert_operation(
                        op_type="classify_rename",
                        source_path=str(file_path),
                        target_path=str(target_path),
                        status=status,
                        timestamp=time.time(),
                        category=category,
                        content=content,
                        batch_id=self.operation_batch_id
                    )
                    
                    # 构建结果 - 统一在这里添加结果，避免重复
                    result_data = {
                        'original_name': file_info['name'],
                        'new_name': new_name,
                        'category': category,
                        'confidence': confidence,
                        'source_path': str(file_path),
                        'target_path': str(target_path),
                        'type': file_info.get('mime_type', 'unknown'),
                        'size': file_info.get('size', 0),
                        'status': status
                    }
                    
                    # 如果失败，添加错误信息
                    if status == "failed":
                        result_data['error'] = error_msg
                    
                    with self._lock:
                        results.append(result_data)
                        
                    if status == "success":
                        logging.info(f"成功处理文件: {file_info['name']} -> {new_name}")
                    else:
                        logging.error(f"文件处理失败 {file_path}: {error_msg}")

                except Exception as e:
                    status = "failed"
                    error_msg = str(e)
                    logging.error(f"文件处理失败 {file_path}: {error_msg}")
                    self.db.insert_operation(
                        op_type="classify_rename",
                        source_path=str(file_path),
                        target_path="",
                        status=status,
                        timestamp=time.time(),
                        category="处理失败",
                        content="",
                        batch_id=self.operation_batch_id
                    )
                    with self._lock:
                        results.append({
                            'original_name': file_info['name'],
                            'new_name': file_info['name'],
                            'category': "处理失败",
                            'confidence': 0.0,
                            'source_path': str(file_path),
                            'target_path': "",
                            'type': file_info.get('mime_type', 'unknown'),
                            'size': file_info.get('size', 0),
                            'status': status,
                            'error': error_msg
                        })

                progress = int((i + 1) / total_files * 100)
                self.signals.progress.emit(progress)

            self.signals.finished.emit(results)

        except Exception as e:
            self.signals.error.emit(f"整体处理失败: {str(e)}")

    def stop(self):
        """停止文件处理过程"""
        self._stop_flag = True
        self.join(timeout=1.0)  # 等待最多1秒