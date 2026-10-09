from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field, field_validator

SCHEMA_VERSION = "wm-v1.1"

TASK_TAGS = [
    "静态场景重建",
    "动态场景 / 4D 重建",
    "表面 / 网格重建",
    "新视角合成",
    "视角外推",
    "三维物体 / 资产生成",
    "场景生成",
    "场景编辑 / 资产插入",
    "深度估计",
    "相机位姿估计",
    "定位与建图",
    "语义场景理解",
    "语义 / 实例分割",
    "语义占据预测",
    "三维 / 点云补全",
    "仿真与闭环评测",
    "场景 / 驾驶情景 / 数据生成",
    "未来帧 / 视频预测",
    "世界状态预测",
    "运动 / 轨迹预测",
    "行为条件生成",
    "交互式场景生成",
    "规划与决策",
    "多模态理解",
    "动作预测 / 控制",
]

DOMAIN_TAGS = [
    "自动驾驶 / 城市道路",
    "通用室外场景",
    "室内场景",
    "物体级场景",
    "通用 / 多领域",
    "机器人 / 具身环境",
    "游戏 / 仿真环境",
    "通用视频 / 互联网数据",
]

# Method 统一包含“场景表示 + 建模范式 + 核心技术”。
# 不再单独维护 Representation 维度，避免分类体系膨胀。
METHOD_TAGS = [
    "3DGS",
    "NeRF / 神经辐射场",
    "网格 / 显式表面",
    "点云",
    "体素 / 占据表示",
    "显式表示",
    "隐式表示",
    "Latent / Token 表示",
    "多视图几何 / SfM / MVS",
    "几何 / 光度优化",
    "SLAM / BA",
    "前馈式 / 泛化式重建",
    "Diffusion / 视频扩散",
    "生成式先验",
    "深度先验",
    "多模态 / 多传感器融合",
    "实例级建模",
    "时序建模",
    "自监督学习",
    "Transformer",
    "JEPA / 表征预测",
    "World Model / Latent Dynamics",
    "VLM / VLA",
    "Autoregressive Modeling",
    "Model-Based RL",
    "Tokenized World Representation",
]

TYPE_TAGS = [
    "研究论文",
    "综述 / 系统综述",
    "技术报告",
    "数据集 / 基准",
    "开源代码 / 项目",
    "书籍 / 章节",
    "学位论文",
]

ROLE_TAGS = [
    "基础 / 奠基工作",
    "方法论文",
    "基准 / 数据集工作",
]


class PaperAnalysis(BaseModel):
    title: str = ""
    short_name: str = ""
    year: str = ""
    authors: str = ""
    venue: str = ""
    arxiv_or_doi: str = ""

    research_problem: str
    core_idea: str
    pipeline: str
    key_innovations: List[str] = Field(default_factory=list)
    main_results: str = ""
    limitations: str = ""
    questions: List[str] = Field(default_factory=list)
    inspiration: str = ""

    # 四维主分类：Task / Domain / Method / Type
    task: List[str] = Field(default_factory=list)
    domain: List[str] = Field(default_factory=list)
    method: List[str] = Field(default_factory=list)
    type: str = "研究论文"

    # 辅助分类，不属于四维主分类
    role: str = "方法论文"

    suggested_new_tags: List[str] = Field(default_factory=list)

    @field_validator("task")
    @classmethod
    def check_task(cls, v):
        return [x for x in v if x in TASK_TAGS]

    @field_validator("domain")
    @classmethod
    def check_domain(cls, v):
        return [x for x in v if x in DOMAIN_TAGS]

    @field_validator("method")
    @classmethod
    def check_method(cls, v):
        return [x for x in v if x in METHOD_TAGS]

    @field_validator("type")
    @classmethod
    def check_type(cls, v):
        return v if v in TYPE_TAGS else "研究论文"

    @field_validator("role")
    @classmethod
    def check_role(cls, v):
        return v if v in ROLE_TAGS else "方法论文"


# 飞书字段名 -> PaperAnalysis 字段
# 多选字段直接写 list；长文本字段写字符串。
FEISHU_FIELD_MAP = {
    "标题": "title",
    "简称": "short_name",
    "年份": "year",
    "作者": "authors",
    "会议 / 期刊": "venue",
    "DOI / arXiv": "arxiv_or_doi",
    "研究问题": "research_problem",
    "核心思想": "core_idea",
    "技术路线": "pipeline",
    "关键创新": "key_innovations",
    "主要结果 / 结论": "main_results",
    "不足之处": "limitations",
    "待解决疑点": "questions",
    "感悟启发": "inspiration",
    "Task": "task",
    "Domain": "domain",
    "Method": "method",
    "Type": "type",
    "Role": "role",
}
