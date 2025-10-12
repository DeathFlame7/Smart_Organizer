import os
import logging
import random
import time
from pathlib import Path
import joblib  # 使用更安全的joblib替代pickle

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
import jieba

from core.database import FileDatabase

# 导入配置管理模块
from utils.config import load_config, get_config_value


class FileClassifier:
    def __init__(self):
        self.model = MultinomialNB()
        self.vectorizer = TfidfVectorizer(tokenizer=self._chinese_tokenizer, max_features=5000)
        self.is_trained = False
        # 扩展样本数据，添加图片相关样本
        self.sample_data = self._load_sample_data()
        self.classes_ = None  # 存储训练后的类别列表
        
        # 新增：用于存储从历史分类中学习的数据
        self.learning_data = []
        self.db = None
        
        # 改进模型路径管理，使用配置获取路径
        config = load_config()
        data_dir = get_config_value(config, 'data_path', 'data')
        # 确保data_dir不为None
        if data_dir is None:
            data_dir = 'data'
        self.model_path = Path(data_dir) / 'classifier_model.pkl'
        self.vectorizer_path = Path(data_dir) / 'classifier_vectorizer.pkl'
        
        # 初始化数据目录
        self._init_data_directory()
        
        # 改进模型加载的错误处理
        try:
            self._load_saved_model()
        except Exception as e:
            logging.warning(f"加载已保存模型失败，将使用默认配置: {str(e)}")
        
        # 连接数据库以获取历史数据
        try:
            self.db = FileDatabase()
            self._load_history_data()
        except Exception as e:
            logging.warning(f"无法加载历史数据: {e}")
            # 如果没有历史数据，至少使用基础样本进行训练
            if not self.is_trained:
                self.train()

    def _chinese_tokenizer(self, text):
        return list(jieba.cut(text))

    def _load_sample_data(self):
        """加载基础训练样本"""
        samples = [
            # 合同类
            ("这是一个合同文件 包含条款和签名 甲乙双方协议", "合同"),
            ("合同协议 法律条款 签署日期 违约责任", "合同"),
            ("服务协议 条款与条件 权利义务 有效期限", "合同"),
            ("租赁合同 租金支付 房屋使用 押金条款", "合同"),
            ("劳动合同 工作内容 薪资待遇 保密协议", "合同"),
            ("销售合同 商品名称 数量 价格 交货日期", "合同"),
            
            # 会议纪要类
            ("会议纪要 讨论内容 决议事项 参会人员", "会议纪要"),
            ("项目会议记录 时间地点 讨论要点 后续行动", "会议纪要"),
            ("部门例会记录 工作总结 工作计划 问题讨论", "会议纪要"),
            ("高层会议备忘录 战略决策 资源分配 时间节点", "会议纪要"),
            
            # 项目计划类
            ("项目计划 时间安排 任务分配 里程碑", "项目计划"),
            ("工作计划 目标设定 责任分工 进度跟踪", "项目计划"),
            ("开发计划 需求分析 设计阶段 开发阶段 测试阶段", "项目计划"),
            ("实施计划 资源配置 风险评估 应急方案", "项目计划"),
            
            # 财务报表类
            ("财务报表 收入支出 数据统计 利润表", "财务报表"),
            ("资产负债表 资产 负债 所有者权益", "财务报表"),
            ("现金流量表 经营活动 投资活动 筹资活动", "财务报表"),
            ("成本核算 直接成本 间接成本 费用分摊", "财务报表"),
            ("预算报表 收入预算 支出预算 利润预算", "财务报表"),
            
            # 产品说明类
            ("产品说明书 功能介绍 使用方法 注意事项", "产品说明"),
            ("产品规格书 技术参数 性能指标 适用范围", "产品说明"),
            ("产品手册 安装指南 操作步骤 维护保养", "产品说明"),
            ("产品目录 型号规格 功能特点 价格信息", "产品说明"),
            
            # 用户手册类
            ("用户手册 操作指南 安装步骤 故障排除", "用户手册"),
            ("使用说明书 功能介绍 配置方法 常见问题", "用户手册"),
            ("操作手册 安全须知 维护指南 联系客服", "用户手册"),
            ("指导手册 使用教程 技巧分享 最佳实践", "用户手册"),
            
            # 技术文档类
            ("技术文档 开发指南 API说明 系统架构", "技术文档"),
            ("设计文档 需求分析 系统设计 数据库设计", "技术文档"),
            ("技术白皮书 技术原理 实现方案 优势分析", "技术文档"),
            ("API文档 接口定义 参数说明 返回值 错误码", "技术文档"),
            ("系统文档 部署指南 配置说明 升级步骤", "技术文档"),
            
            # 培训资料类
            ("培训资料 学习内容 课程安排 考核标准", "培训资料"),
            ("培训课件 PPT讲义 练习作业 参考资料", "培训资料"),
            ("教程文档 入门指南 进阶技巧 实例演示", "培训资料"),
            ("学习笔记 重点总结 知识点梳理 复习资料", "培训资料"),
            
            # 研究报告类
            ("研究报告 数据分析 结论建议 参考文献", "研究报告"),
            ("市场分析 行业趋势 竞争格局 用户需求", "研究报告"),
            ("调查报告 调查方法 数据统计 结果分析", "研究报告"),
            ("可行性研究 技术可行性 经济可行性 风险评估", "研究报告"),
            
            # 新闻文章类
            ("新闻文章 当前事件 社会动态 时事评论", "新闻文章"),
            ("资讯报道 最新动态 行业信息 政策解读", "新闻文章"),
            ("评论文章 观点分析 深度解读 建议看法", "新闻文章"),
            ("专题报道 背景介绍 事件经过 影响分析", "新闻文章"),
            
            # 文学作品类
            ("小说文学 故事情节 人物描写 环境渲染", "小说文学"),
            ("诗歌散文 文学作品 情感表达 意境描绘", "诗歌散文"),
            ("散文随笔 生活感悟 思想表达 情感流露", "诗歌散文"),
            ("短篇小说 情节紧凑 人物鲜明 主题突出", "小说文学"),
            
            # 个人文档类
            ("简历介绍 工作经历 教育背景 技能特长", "个人简历"),
            ("求职信 申请职位 个人优势 求职意向", "求职信"),
            ("个人总结 工作回顾 成绩反思 未来计划", "个人简历"),
            ("备忘录 待办事项 重要信息 提醒事项", "个人简历"),
            
            # 图片类
            ("图片文件 格式: JPEG 尺寸: 1920x1080像素", "图片"),
            ("图片文件 格式: PNG 尺寸: 800x600像素 包含透明通道", "图片"),
            ("照片 格式: WEBP 尺寸: 1024x768像素 包含EXIF元数据", "图片"),
            ("截图 格式: PNG 尺寸: 1280x720像素", "图片"),
            ("图像文件 格式: GIF 动画图片", "图片"),
            ("图像文件 格式: BMP 位图 无压缩", "图片"),
            ("照片文件 风景照 人物照 纪念照", "图片"),
            ("设计图片 PSD文件 AI文件 矢量图", "图片")
        ]
        return samples

    def train(self):
        """训练分类器，结合基础样本数据和学习数据"""
        # 合并基础样本数据和学习数据
        all_data = self.sample_data.copy()
        if self.learning_data:
            all_data.extend(self.learning_data)
            
        if not all_data:
            logging.warning("没有可用的训练数据")
            return False
            
        try:
            texts, labels = zip(*all_data)
            X = self.vectorizer.fit_transform(texts)
            self.model.fit(X, labels)
            self.is_trained = True
            self.classes_ = self.model.classes_
            
            # 记录训练信息
            base_count = len(self.sample_data)
            learning_count = len(self.learning_data)
            logging.info("文件分类器训练完成，共训练 %d 个样本（基础样本: %d, 学习样本: %d），支持类别：%s",
                         len(all_data), base_count, learning_count, str(self.classes_))
            
            return True
        except Exception as e:
            logging.error("分类器训练失败: %s", str(e))
            return False

    def predict_with_confidence(self, text_content):
        if not self.is_trained:
            if not self.train():
                return '未分类', 0.0

        # 优化：优先根据内容特征判断图片类型
        if any(keyword in text_content for keyword in
               ['图片', '照片', '截图', '图像', '像素', '格式: JPEG', '格式: PNG']):
            return '图片', 0.95  # 高可信度

        if not text_content or len(text_content.strip()) < 10:
            return '其他', 0.5

        try:
            clean_text = self._extract_keywords(text_content)
            X = self.vectorizer.transform([clean_text])
            probs = self.model.predict_proba(X)[0]
            max_prob_idx = probs.argmax()
            category = self.classes_[max_prob_idx]
            confidence = round(probs[max_prob_idx], 2)
            return category, confidence
        except Exception as e:
            logging.error("分类预测失败: %s", str(e))
            return '未分类', 0.0

    def predict(self, text_content):
        category, _ = self.predict_with_confidence(text_content)
        return category

    def _init_data_directory(self):
        """初始化数据目录"""
        # 使用配置中的数据路径
        config = load_config()
        data_dir = get_config_value(config, 'data_path', 'data')
        # 确保data_dir不为None
        if data_dir is None:
            data_dir = 'data'
        data_dir_path = Path(data_dir)
        
        if not data_dir_path.exists():
            try:
                data_dir_path.mkdir(parents=True)
                logging.info(f"创建数据目录: {data_dir_path}")
            except Exception as e:
                logging.error(f"创建数据目录失败: {e}")
    
    def _load_saved_model(self):
        """加载已保存的模型（使用joblib替代pickle以提高安全性）"""
        try:
            if self.model_path.exists() and self.vectorizer_path.exists():
                # 使用joblib加载模型，更加安全高效
                self.model = joblib.load(self.model_path)
                self.vectorizer = joblib.load(self.vectorizer_path)
                
                # 添加类型验证，确保加载的是预期对象
                from sklearn.naive_bayes import MultinomialNB
                from sklearn.feature_extraction.text import TfidfVectorizer
                
                if not isinstance(self.model, MultinomialNB) or not isinstance(self.vectorizer, TfidfVectorizer):
                    raise TypeError("加载的模型或向量器类型不正确")
                
                self.is_trained = True
                self.classes_ = self.model.classes_
                logging.info(f"加载已保存的模型成功")
        except Exception as e:
            logging.warning(f"加载已保存的模型失败: {e}")
    
    def _load_history_data(self):
        """从数据库加载历史分类数据"""
        if not self.db:
            return
        
        try:
            # 获取最近30天的成功分类记录
            days_ago = int(time.time()) - (30 * 24 * 60 * 60)
            history = self.db.get_operations_since(days_ago)
            
            for op in history:
                if op['status'] == 'success' and op['category'] and op['content']:
                    # 只添加有内容和有效分类的记录
                    self.learning_data.append((op['content'], op['category']))
                    
            logging.info(f"加载历史分类数据: {len(self.learning_data)} 条记录")
        except Exception as e:
            logging.error(f"加载历史数据失败: {e}")
    
    def save_model(self):
        """保存训练好的模型（使用joblib替代pickle以提高安全性）"""
        if not self.is_trained:
            logging.warning("模型尚未训练，无法保存")
            return False
        
        try:
            # 使用joblib保存模型，更加安全高效
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.vectorizer, self.vectorizer_path)
            logging.info(f"模型保存成功: {self.model_path}")
            return True
        except Exception as e:
            logging.error(f"模型保存失败: {e}")
            return False
    
    def learn_from_manual_classification(self, content, category):
        """从用户手动分类中学习"""
        try:
            # 确保内容不为空
            if not content or not category:
                logging.warning("跳过无效的手动分类学习数据：内容或类别为空")
                return
                
            # 避免重复添加相同的样本
            duplicate = False
            for existing_content, existing_category in self.learning_data:
                if existing_content == content and existing_category == category:
                    duplicate = True
                    break
                    
            if duplicate:
                logging.debug(f"跳过重复的手动分类学习样本: 类别 '{category}'")
                return
                
            self.learning_data.append((content, category))
            logging.info(f"从手动分类中学习: 类别 '{category}'，内容长度: {len(content)} 字符")
            logging.debug(f"当前学习数据总数: {len(self.learning_data)}")
            
            # 重新训练模型
            if self.train():
                # 保存更新后的模型
                if self.save_model():
                    logging.info(f"模型已成功更新并保存，包含新的手动分类数据")
                else:
                    logging.warning("模型训练成功，但保存失败")
            else:
                logging.error("模型重新训练失败")
        except Exception as e:
            logging.error(f"从手动分类中学习时出错: {str(e)}")

    def _extract_keywords(self, text):
        """提取关键词"""
        # 扩展关键词映射，添加图片相关关键词
        keywords_map = {
            '合同': ['合同', '协议', '条款', '签署', '法律', '约定', '义务', '权利'],
            '财务': ['财务', '报表', '收入', '支出', '金额', '统计', '数据', '账目'],
            '项目': ['项目', '计划', '任务', '时间', '安排', '进度', '里程碑'],
            '技术': ['技术', '开发', 'API', '代码', '功能', '系统', '设计', '架构'],
            '报告': ['报告', '研究', '分析', '结论', '数据', '结果', '调查'],
            '说明': ['说明', '手册', '指南', '使用', '操作', '安装', '功能', '介绍'],
            '新闻': ['新闻', '事件', '社会', '当前', '报道', '动态', '今天'],
            '文学': ['小说', '诗歌', '散文', '故事', '人物', '情节', '描写', '情感'],
            '图片': ['图片', '照片', '截图', '图像', '像素', 'JPEG', 'PNG', 'WEBP', 'GIF']
        }

        text_lower = text.lower()
        for _, keywords in keywords_map.items():
            if any(keyword in text_lower for keyword in keywords):
                return text[:20]
        return text[:20]
