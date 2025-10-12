from pathlib import Path
import magic
import logging
import hashlib
import chardet
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
from typing import Dict, List, Tuple
from utils.config import load_config
import pdfplumber
from docx import Document
from PIL import Image  # 新增：用于处理图片文件
import io


class FileProcessor:
    def __init__(self):
        self.mime = magic.Magic(mime=True)
        self.config = load_config()
        self.thread_count = int(self.config.get('DEFAULT', 'scan_threads', fallback=4))
        self.executor = ThreadPoolExecutor(max_workers=self.thread_count)
        self.task_queue = queue.Queue()
        # 扩展支持的文件类型，添加图片格式
        self.supported_extensions = {
            '.pdf', '.docx', '.txt', '.md',  # 原有文档类型
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'  # 新增图片类型
        }
        # 图片MIME类型映射
        self.image_mime_types = {
            'image/jpeg': ['.jpg', '.jpeg'],
            'image/png': ['.png'],
            'image/gif': ['.gif'],
            'image/bmp': ['.bmp'],
            'image/webp': ['.webp']
        }

    def get_file_info(self, file_path: Path) -> Dict[str, any]:
        """获取文件信息，扩展支持图片文件"""
        try:
            if file_path.suffix.lower() not in self.supported_extensions:
                logging.debug(f"跳过不支持的文件格式：{file_path}")
                return None

            stat = file_path.stat()
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5(f.read(8192)).hexdigest()

            file_info = {
                'path': str(file_path),
                'name': file_path.name,
                'extension': file_path.suffix.lower(),
                'size': stat.st_size,
                'modified_time': stat.st_mtime,
                'content_hash': file_hash,
                'mime_type': self.mime.from_file(str(file_path))
            }

            # 新增：获取图片文件的额外信息
            if file_info['extension'] in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                try:
                    with Image.open(file_path) as img:
                        file_info['image_width'], file_info['image_height'] = img.size
                        file_info['image_mode'] = img.mode
                        file_info['image_format'] = img.format
                except Exception as e:
                    logging.warning(f"获取图片信息失败 {file_path}: {e}")

            return file_info
        except Exception as e:
            logging.error(f"获取文件信息失败 {file_path}: {e}")
            return None

    def scan_directory(self, directory: Path, recursive: bool = True) -> List[Dict[str, any]]:
        """扫描目录，确保包含所有支持的文件类型"""
        files = []
        if not directory.is_dir():
            logging.warning(f"目录不存在或不是文件夹: {directory}")
            return files

        try:
            dir_iter = directory.rglob('*') if recursive else directory.glob('*')
            for item in dir_iter:
                try:
                    if item.is_file():
                        # 检查文件是否为支持的类型
                        if item.suffix.lower() in self.supported_extensions:
                            file_info = self.get_file_info(item)
                            if file_info:
                                files.append(file_info)
                        else:
                            # 可选：记录不支持的文件类型，便于后续扩展
                            logging.debug(f"不支持的文件类型: {item}")
                except PermissionError:
                    logging.warning(f"权限不足，无法访问文件: {item}")
                except Exception as e:
                    logging.warning(f"访问文件时出错: {item}, 错误: {e}")
        except PermissionError:
            logging.error(f"权限不足，无法扫描目录: {directory}")
        except Exception as e:
            logging.error(f"扫描目录时出错: {directory}, 错误: {e}")

        logging.info(f"扫描完成：{directory} 下共发现 {len(files)} 个支持的文件（含子目录：{recursive}）")
        return files

    def extract_text_content(self, file_path: Path) -> str:
        """提取文件内容，为图片文件生成描述性内容"""
        _, content = self.extract_text_content_async(file_path)
        return content.strip() if content.strip() else "[空文件]"

    def extract_text_content_async(self, file_path: Path) -> Tuple[Path, str]:
        try:
            extension = file_path.suffix.lower()
            content = ""

            # 文档类型处理（原有逻辑）
            if extension == '.pdf':
                content = self._extract_pdf_text(file_path)
            elif extension == '.docx':
                content = self._extract_docx_text(file_path)
            elif extension in ('.txt', '.md'):
                content = self._read_txt(file_path)
            # 新增：图片类型处理
            elif extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                content = self._extract_image_info(file_path)
            else:
                logging.debug(f"不支持提取 {extension} 格式的文本内容")

            return (file_path, content.strip())
        except Exception as e:
            logging.error(f"提取文件内容失败 {file_path}: {e}")
            return (file_path, "[提取失败]")

    # 新增：提取图片信息作为文本内容
    def _extract_image_info(self, file_path: Path) -> str:
        try:
            with Image.open(file_path) as img:
                info = [
                    f"图片文件",
                    f"格式: {img.format}",
                    f"尺寸: {img.size[0]}x{img.size[1]}像素",
                    f"模式: {img.mode}"
                ]
                # 尝试获取图片元数据
                if hasattr(img, '_getexif'):
                    exif = img._getexif()
                    if exif:
                        info.append("包含EXIF元数据")
                return "; ".join(info)
        except Exception as e:
            logging.error(f"提取图片信息失败 {file_path}: {e}")
            return "图片文件"

    # 以下为原有方法，保持不变
    def _read_txt(self, file_path: Path) -> str:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            detect_result = chardet.detect(raw_data)
            encoding = detect_result['encoding'] or 'utf-8'
            if encoding.lower() not in ['utf-8', 'gbk', 'gb2312']:
                encoding = 'utf-8'
            try:
                return raw_data.decode(encoding, errors='ignore')
            except UnicodeDecodeError:
                return raw_data.decode('gbk', errors='ignore')

    def _extract_pdf_text(self, file_path: Path) -> str:
        try:
            with pdfplumber.open(file_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        text += page_text + "\n"
                return text.strip()
        except Exception as e:
            logging.error(f"PDF文本提取失败 {file_path}: {e}")
            return ""

    def _extract_docx_text(self, file_path: Path) -> str:
        try:
            doc = Document(file_path)
            paragraphs = [para.text.strip() for para in doc.paragraphs if para.text.strip()]
            return "\n".join(paragraphs)
        except Exception as e:
            logging.error(f"DOCX文本提取失败 {file_path}: {e}")
            return ""

    def close(self):
        self.executor.shutdown(wait=True)
        logging.info("文件处理器线程池已关闭")

    def process_file(self, file_path: str, category: str, new_name: str) -> Dict[str, any]:
        """处理单个文件并返回处理结果"""
        try:
            path = Path(file_path)
            
            # 获取文件基本信息
            file_info = {
                'path': file_path,
                'source_path': file_path,
                'original_name': path.name,
                'category': category,
                'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                'type': 'unknown',
                'confidence': 1.0  # 默认可信度
            }
            
            # 提取文件内容（如果需要）
            content = self.extract_text_content(path)
            file_info['content'] = content
            
            # 确定目标路径和文件名
            target_path = str(path)
            if new_name and new_name != path.name:
                # 创建新的目标路径
                target_dir = path.parent
                new_file_path = target_dir / new_name
                target_path = str(new_file_path)
            
            # 设置处理状态为成功
            result = {
                'status': 'success',
                'source_path': file_path,
                'target_path': target_path,
                'new_name': new_name if new_name else path.name,
                'category': category
            }
            
            # 合并原始文件信息
            result.update(file_info)
            
            logging.info(f"处理文件成功: {file_path} -> {target_path}")
            return result
        except Exception as e:
            logging.error(f"处理文件失败 {file_path}: {e}")
            return {
                'status': 'failed',
                'source_path': file_path,
                'error_message': str(e),
                'category': category,
                'original_name': Path(file_path).name if os.path.exists(file_path) else os.path.basename(file_path)
            }
    
    def undo_file_operation(self, source_path: str, target_path: str) -> Dict[str, any]:
        """撤销文件操作，增强健壮性处理路径不匹配情况"""
        try:
            source = Path(source_path)
            target = Path(target_path)
            
            # 记录尝试撤销的文件路径
            logging.info(f"尝试撤销操作: 源路径={source_path}, 目标路径={target_path}")
            
            # 检查目标文件是否存在
            if target.exists():
                try:
                    # 确保源目录存在
                    source.parent.mkdir(parents=True, exist_ok=True)
                    
                    # 如果源文件已存在，先备份
                    if source.exists():
                        backup_path = source.with_suffix(source.suffix + '.backup')
                        source.rename(backup_path)
                        logging.info(f"备份原文件: {source} -> {backup_path}")
                    
                    # 移动文件回原位置
                    target.rename(source)
                    
                    return {
                        'status': 'undone',
                        'source_path': str(source),
                        'target_path': str(target),
                        'original_name': source.name,
                        'category': '已撤销'
                    }
                except PermissionError as e:
                    logging.error(f"权限错误，无法撤销文件操作: {e}")
                    return {
                        'status': 'failed',
                        'error_message': f'权限错误，可能文件被其他程序占用: {str(e)}',
                        'source_path': str(source),
                        'target_path': str(target)
                    }
                except OSError as e:
                    logging.error(f"系统错误，无法撤销文件操作: {e}")
                    return {
                        'status': 'failed',
                        'error_message': f'系统错误，可能文件路径无效或被锁定: {str(e)}',
                        'source_path': str(source),
                        'target_path': str(target)
                    }
            else:
                # 增强：检查源文件是否存在（如果存在，可能文件已经回到了源位置）
                if source.exists():
                    logging.info(f"源文件已存在，可能已经撤销：{source}")
                    return {
                        'status': 'undone',
                        'source_path': str(source),
                        'target_path': str(target),
                        'original_name': source.name,
                        'category': '已撤销',
                        'message': '源文件已存在，可能已经撤销'
                    }
                
                # 增强：检查目标目录是否存在
                if not target.parent.exists():
                    logging.error(f"目标目录不存在：{target.parent}")
                    return {
                        'status': 'failed',
                        'error_message': f'目标目录不存在，无法撤销：{target.parent}',
                        'source_path': str(source),
                        'target_path': str(target)
                    }
                
                # 增强：尝试查找类似名称的文件
                similar_files = []
                try:
                    target_name_no_ext = target.stem
                    target_ext = target.suffix
                    similar_files = [f for f in target.parent.iterdir() 
                                    if f.is_file() and f.stem.startswith(target_name_no_ext) and f.suffix == target_ext]
                except Exception as e:
                    logging.warning(f"尝试查找类似文件时出错: {e}")
                
                if similar_files:
                    found_file = similar_files[0]  # 选择第一个匹配的文件
                    try:
                        logging.info(f"找到类似的文件：{found_file}，尝试使用它进行撤销")
                        
                        # 确保源目录存在
                        source.parent.mkdir(parents=True, exist_ok=True)
                        
                        # 移动找到的文件到源位置
                        found_file.rename(source)
                        
                        return {
                            'status': 'undone',
                            'source_path': str(source),
                            'target_path': str(target),
                            'original_name': source.name,
                            'category': '已撤销',
                            'message': f'使用类似文件 {found_file.name} 完成撤销'
                        }
                    except Exception as e:
                        logging.error(f"使用类似文件撤销失败: {e}")
                        return {
                            'status': 'failed',
                            'error_message': f'使用类似文件撤销失败: {str(e)}',
                            'source_path': str(source),
                            'target_path': str(target)
                        }
                
                # 所有尝试都失败
                return {
                    'status': 'failed',
                    'error_message': f'目标文件不存在，无法撤销：{target_path}',
                    'source_path': str(source),
                    'target_path': str(target)
                }
        except Exception as e:
            logging.error(f"撤销操作失败 {source_path} -> {target_path}: {e}")
            return {
                'status': 'failed',
                'error_message': str(e),
                'source_path': source_path,
                'target_path': target_path
            }
