from pathlib import Path
import re
import logging
from datetime import datetime
import hashlib
from pathlib import Path


class FileRenamer:
    @staticmethod
    def generate_name(content: str, file_type: str, original_name: str, file_path: Path = None) -> str:
        if not content or content in ["[空文件]", "[提取失败]"]:
            return FileRenamer._default_rename(original_name, file_type, file_path)

        try:
            # 新增：优先处理图片文件
            if 'image' in file_type or any(keyword in content for keyword in ['图片', '照片', '截图', '像素']):
                return FileRenamer._generate_image_name(content, original_name, file_path)
            # 原有文档类型处理
            elif file_type in ['application/pdf',
                               'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain',
                               'text/markdown']:
                return FileRenamer._generate_document_name(content, original_name)
            elif any(keyword in content for keyword in ['合同', '协议', '条款']):
                return FileRenamer._generate_contract_name(content, original_name)
            elif any(keyword in content for keyword in ['财务', '报表', '收入', '支出']):
                return FileRenamer._generate_financial_name(content, original_name)
            else:
                return FileRenamer._default_rename(original_name, file_type, file_path)
        except Exception as e:
            logging.error(f"生成文件名失败: {e}")
            return original_name

    @staticmethod
    def _generate_document_name(content: str, original_name: str) -> str:
        sample_text = content[:500].replace('\n', ' ').replace('\r', ' ')
        words = [w for w in sample_text.split() if len(w) > 1 and not w.isdigit()]
        keywords = []
        for word in words[:20]:
            if len(word) > 2 and not any(char.isdigit() for char in word):
                keywords.append(word)
        prefix = '_'.join(keywords[:3]) if keywords else 'document'
        ext = Path(original_name).suffix
        date_str = datetime.now().strftime('%Y%m%d')
        return f"{prefix}_{date_str}{ext}"

    # 增强：更智能的图片命名
    @staticmethod
    def _generate_image_name(content: str, original_name: str, file_path: Path) -> str:
        ext = Path(original_name).suffix
        # 提取图片特征
        is_screenshot = '截图' in content
        is_photo = '照片' in content or 'EXIF' in content

        # 确定前缀
        if is_screenshot:
            prefix = 'screenshot'
        elif is_photo:
            prefix = 'photo'
        else:
            prefix = 'image'

        # 获取尺寸信息
        size_match = re.search(r'(\d+)x(\d+)像素', content)
        size_str = f"{size_match.group(1)}x{size_match.group(2)}" if size_match else ""

        # 确定日期
        if file_path:
            try:
                # 使用文件修改时间
                modified_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                date_str = modified_time.strftime('%Y%m%d_%H%M')
            except:
                date_str = datetime.now().strftime('%Y%m%d_%H%M')
        else:
            date_str = datetime.now().strftime('%Y%m%d_%H%M')

        # 组合文件名
        if size_str:
            return f"{prefix}_{size_str}_{date_str}{ext}"
        else:
            return f"{prefix}_{date_str}{ext}"

    @staticmethod
    def _generate_contract_name(content: str, original_name: str) -> str:
        sample_text = content[:300]
        prefix = 'contract' if ('甲方' in sample_text and '乙方' in sample_text) else 'agreement'
        ext = Path(original_name).suffix
        date_str = datetime.now().strftime('%Y%m%d')
        return f"{prefix}_{date_str}{ext}"

    @staticmethod
    def _generate_financial_name(content: str, original_name: str) -> str:
        ext = Path(original_name).suffix
        period_match = re.search(r'(\d{4}年\d{1,2}月|\d{4}-\d{1,2})', content)
        period = period_match.group(1) if period_match else datetime.now().strftime('%Y%m%d')
        return f"finance_{period}{ext}"

    @staticmethod
    def _default_rename(original_name: str, file_type: str, file_path: Path) -> str:
        ext = Path(original_name).suffix
        if file_path:
            modified_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            date_str = modified_time.strftime('%Y%m%d_%H%M')
            if file_path.parent.name == "其他":
                return f"file_{date_str}{ext}"
            return f"file_{date_str}{ext}"
        else:
            return f"renamed_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"

    @staticmethod
    def generate_preview_name(original_name: str, suggested_category: str) -> str:
        ext = Path(original_name).suffix
        timestamp = datetime.now().strftime('%Y%m%d')
        return f"[{suggested_category}]_{original_name}_{timestamp}{ext}"
