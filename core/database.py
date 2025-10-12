import sqlite3
import os
import logging
from pathlib import Path
from utils.config import load_config

class FileDatabase:
    def __init__(self):
        config = load_config()
        self.db_path = Path(config.get('DEFAULT', 'database_path', fallback='data/files.db'))
        os.makedirs(self.db_path.parent, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        """创建独立连接，确保线程安全"""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """初始化表结构，增加异常捕获"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            # files表
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS files
                           (
                               id INTEGER PRIMARY KEY AUTOINCREMENT,
                               path TEXT UNIQUE,
                               name TEXT,
                               extension TEXT,
                               file_type TEXT,
                               size INTEGER,
                               modified_time REAL,
                               content_hash TEXT,
                               category TEXT,
                               confidence REAL,
                               custom_name TEXT,
                               processed BOOLEAN DEFAULT FALSE
                           )
                           ''')
            # operations表 - 增加category和content字段用于机器学习
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS operations
                           (
                               id INTEGER PRIMARY KEY AUTOINCREMENT,
                               operation_type TEXT,
                               source_path TEXT,
                               target_path TEXT,
                               status TEXT,
                               timestamp REAL,
                               category TEXT,
                               content TEXT,
                               batch_id TEXT
                           )
                           ''')
            
            # 如果是现有数据库，添加缺失的字段
            try:
                cursor.execute("ALTER TABLE operations ADD COLUMN category TEXT")
                cursor.execute("ALTER TABLE operations ADD COLUMN content TEXT")
                cursor.execute("ALTER TABLE operations ADD COLUMN batch_id TEXT")
                conn.commit()
            except sqlite3.OperationalError:
                # 字段已存在，忽略错误
                pass
            
            conn.commit()
            logging.info("数据库表结构初始化完成")
        except Exception as e:
            logging.error("数据库初始化失败: %s", str(e))
            conn.rollback()
        finally:
            conn.close()

    def insert_operation(self, op_type: str, source_path: str, target_path: str, status: str, timestamp: float, category: str = None, content: str = None, batch_id: str = None) -> bool:
        """增加类型注解，确保参数类型正确，并添加category和content字段，以及批次ID"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                           INSERT INTO operations 
                           (operation_type, source_path, target_path, status, timestamp, category, content, batch_id)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                           ''', (op_type, source_path, target_path, status, timestamp, category, content, batch_id))
            conn.commit()
            logging.debug(f"操作日志插入成功：{op_type} {source_path} → {target_path}")
            return True
        except Exception as e:
            logging.error("插入操作日志失败: %s", str(e))
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_operations_since(self, timestamp: float) -> list:
        """获取指定时间戳之后的操作记录，用于机器学习
        
        Args:
            timestamp: 时间戳，只返回此时间之后的记录
        
        Returns:
            操作记录列表
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            # 使用参数化查询防止SQL注入
            cursor.execute('''
                           SELECT * FROM operations 
                           WHERE timestamp > ? AND operation_type = ?
                           ORDER BY timestamp DESC
                           ''', (timestamp, "classify_rename"))
            results = [dict(row) for row in cursor.fetchall()]
            return results
        except Exception as e:
            logging.error("获取操作记录失败: %s", str(e))
            return []
        finally:
            conn.close()

    def update_file_processed(self, file_path: str, is_processed: bool = True) -> bool:
        """增加类型注解"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                           UPDATE files 
                           SET processed = ? 
                           WHERE path = ?
                           ''', (is_processed, file_path))
            conn.commit()
            return True
        except Exception as e:
            logging.error("更新文件处理状态失败: %s", str(e))
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_last_operation(self) -> dict or None:
        """获取最后一次操作记录
        
        Returns:
            最后一次操作记录字典，或None（如果没有记录）
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                           SELECT * FROM operations 
                           ORDER BY timestamp DESC
                           LIMIT 1
                           ''')
            result = cursor.fetchone()
            if result:
                return dict(result)
            return None
        except Exception as e:
            logging.error("获取最后操作记录失败: %s", str(e))
            return None
        finally:
            conn.close()

    def close(self):
        logging.info("数据库连接已全部关闭（每次操作后自动关闭）")
        
    def execute_query(self, query, params=None):
        """执行自定义SQL查询
        
        Args:
            query: SQL查询语句
            params: 查询参数（可选）
        
        Returns:
            查询结果列表，每条记录为字典形式
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            results = [dict(row) for row in cursor.fetchall()]
            return results
        except Exception as e:
            logging.error(f"执行SQL查询失败: {str(e)}")
            return []
        finally:
            conn.close()
    
    def get_last_operation_batch(self, time_window=10.0) -> list: # 增加时间窗口到10秒，适应处理多个文件的情况
        """获取最后一个操作批次的所有记录
        
        Args:
            time_window: 时间窗口（秒），用于确定同一批次的操作
        
        Returns:
            操作记录列表
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            # 先获取最后一次操作的时间戳
            cursor.execute('''
                           SELECT timestamp FROM operations 
                           ORDER BY timestamp DESC
                           LIMIT 1
                           ''')
            last_timestamp_row = cursor.fetchone()
            if not last_timestamp_row:
                return []
            
            last_timestamp = last_timestamp_row[0]
            # 获取在时间窗口内的所有操作记录
            cursor.execute('''
                           SELECT * FROM operations 
                           WHERE timestamp > ? - ?
                           ORDER BY timestamp DESC
                           ''', (last_timestamp, time_window))
            results = [dict(row) for row in cursor.fetchall()]
            return results
        except Exception as e:
            logging.error("获取操作批次失败: %s", str(e))
            return []
        finally:
            conn.close()
        
    def update_operation_status(self, operation_id: int, status: str) -> bool:
        """更新操作记录的状态"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                           UPDATE operations 
                           SET status = ? 
                           WHERE id = ?
                           ''', (status, operation_id))
            conn.commit()
            logging.debug(f"操作状态更新成功：ID={operation_id}, 状态={status}")
            return True
        except Exception as e:
            logging.error("更新操作状态失败: %s", str(e))
            conn.rollback()
            return False
        finally:
            conn.close()
