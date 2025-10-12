import logging
from pathlib import Path
from typing import Dict, List, Any


class UndoManager:
    """撤销操作管理类 - 统一处理各类撤销操作"""
    def __init__(self, file_processor, db=None):
        self.file_processor = file_processor
        self.db = db
        
    def undo_file_operation(self, source_path: str, target_path: str) -> Dict[str, Any]:
        """执行单个文件操作的撤销"""
        try:
            # 调用底层的撤销文件操作方法
            return self.file_processor.undo_file_operation(source_path, target_path)
        except Exception as e:
            logging.error(f"撤销文件操作失败 {source_path} -> {target_path}: {e}")
            return {
                'status': 'failed',
                'error_message': str(e),
                'source_path': source_path,
                'target_path': target_path
            }
    
    def undo_operations_batch(self, operations: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """批量撤销多个文件操作"""
        logging.debug(f"开始批量撤销操作: operations类型={type(operations)}, 操作数量={len(operations) if isinstance(operations, list) else '无效'}")
        
        results = []
        
        for i, op in enumerate(operations):
            logging.debug(f"处理第{i+1}个撤销操作: type={type(op)}")
            source_path = op.get('source_path')
            target_path = op.get('target_path')
            
            if source_path and target_path:
                logging.debug(f"执行撤销操作: source_path={source_path}, target_path={target_path}")
                result = self.undo_file_operation(source_path, target_path)
                results.append(result)
                logging.debug(f"撤销操作结果: {result}")
                
                # 如果有数据库连接且撤销成功，更新数据库记录
                if self.db and result['status'] == 'undone':
                    self._update_db_operation(source_path)
            else:
                logging.warning(f"第{i+1}个撤销操作缺少源路径或目标路径: source_path={source_path}, target_path={target_path}")
                results.append({
                    'status': 'failed',
                    'error_message': '缺少源路径或目标路径',
                    'source_path': source_path,
                    'target_path': target_path
                })
        
        logging.debug(f"批量撤销操作完成: 总结果数={len(results)}")
        return results
    
    def _update_db_operation(self, source_path: str):
        """更新数据库中的操作记录状态"""
        try:
            # 尝试获取get_operations_by_source_path方法
            if hasattr(self.db, 'get_operations_by_source_path'):
                operations = self.db.get_operations_by_source_path(source_path)
                for op in operations:
                    if op['status'] == 'success':
                        self.db.update_operation_status(op['id'], 'undone')
                        break
            # 如果没有get_operations_by_source_path方法，尝试获取最后一次操作
            elif hasattr(self.db, 'get_last_operation'):
                # 注意：这种方式可能不准确，因为get_last_operation返回的是全局最后一次操作
                last_op = self.db.get_last_operation()
                if last_op and last_op.get('source_path') == source_path and last_op.get('status') == 'success':
                    self.db.update_operation_status(last_op['id'], 'undone')
        except Exception as e:
            logging.error(f"更新数据库操作记录失败: {e}")
    
    def get_undo_summary(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
        """获取撤销结果的统计摘要"""
        success_count = sum(1 for r in results if r.get('status') == 'undone')
        failed_count = sum(1 for r in results if r.get('status') == 'failed')
        
        return {
            'success_count': success_count,
            'failed_count': failed_count
        }


# 工厂方法，用于创建UndoManager实例
def create_undo_manager(file_processor, db=None):
    """创建撤销管理器实例"""
    return UndoManager(file_processor, db)
