# 多轮对话能力评测数据集

## 评测维度

| 维度 | 英文名 | 说明 |
|------|--------|------|
| 对话相关性 | Turn Relevancy | 多轮回答是否始终围绕用户意图 |
| 对话完整性 | Conversation Completeness | 整个对话是否完成用户目标 |
| 知识保持 | Knowledge Retention | 是否在后续轮次中保持前文知识一致 |
| 角色保持 | Role Adherence | 是否持续遵守设定身份、角色和风格 |

## 数据集统计

- **总样本数**: 60 条
- **每维度样本数**: 15 条
- **格式**: JSONL

## 数据格式

每条样本包含以下字段：

```json
{
  "dimension": "turn_relevancy",
  "description": "笔记本电脑购买咨询",
  "query": "评测指令和对话历史...",
  "response": "当前轮次的用户输入",
  "reference": "期望的模型行为",
  "conversation": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "check_turn": 3,
  "expected": "回答应围绕笔记本电脑续航..."
}
```

### 字段说明

- `dimension`: 评测维度（turn_relevancy / conversation_completeness / knowledge_retention / role_adherence）
- `description`: 样本场景描述
- `query`: 完整的评测指令（兼容 deepeval 格式）
- `response`: 当前检查轮次的用户输入
- `reference`: 期望的模型行为描述
- `conversation`: 多轮对话历史（包含 user / assistant / system 角色）
- `check_turn`: 需要检查的轮次（1-based）
- `expected`: 对该轮次模型回答的期望

## 生成数据集

```bash
python scripts/deepeval/dataset/19_multi_turn_datasets/generate_multi_turn_dataset.py
```

## 运行评测

```bash
# 在远程服务器上运行
cd /data/chenweihang/Intern_CMW
python scripts/deepeval/multi_turn_eval.py
```

## 评测流程

1. 加载数据集，按维度分组
2. 对每个样本，构建对话历史并调用被测模型生成回答
3. 使用裁判模型（LLM-as-Judge）对生成的回答进行评分
4. 输出每个维度的评分汇总和详细结果

## 输出结果

结果保存在 `results/deepeval/{模型名}/multi_turn/` 目录下：

```
multi_turn/
├── turn_relevancy/
│   ├── config.json
│   ├── summary.json
│   ├── detailed_results.json
│   └── history.json
├── conversation_completeness/
│   ├── config.json
│   ├── summary.json
│   ├── detailed_results.json
│   └── history.json
├── knowledge_retention/
│   ├── config.json
│   ├── summary.json
│   ├── detailed_results.json
│   └── history.json
├── role_adherence/
│   ├── config.json
│   ├── summary.json
│   ├── detailed_results.json
│   └── history.json
└── multi_turn_overall_summary.json
```

## 样本场景覆盖

### 对话相关性 (15条)
- 笔记本电脑购买咨询
- 北京旅游行程规划
- 睡眠问题咨询
- 编程语言选择
- AI书籍推荐
- 健身计划制定
- 租房咨询
- 英语学习建议
- 宠物养护
- 摄影入门
- 面试准备
- 菜谱咨询
- 手机选购
- 理财规划
- 旅行准备

### 对话完整性 (15条)
- 红烧肉做法
- 电脑开机慢
- 信用卡申请
- 天气查询替代
- 辞职信写作
- 简历修改
- 论文写作
- 装修预算
- 签证办理
- 育儿建议
- 汽车保养
- 考研规划
- 社保转移
- 瑜伽入门
- 税务申报

### 知识保持 (15条)
- 记住用户姓名
- 记住居住地点
- 记住饮食偏好
- 记住技术栈
- 记住宠物信息
- 记住工作信息
- 记住学习进度
- 记住健康信息
- 记住旅行计划
- 记住家庭情况
- 记住项目细节
- 记住预算限制
- 记住时间约束
- 记住设备信息
- 记住过敏史

### 角色保持 (15条)
- 中医师角色
- 幽默导游角色
- 理财顾问角色
- 心理咨询师角色
- 小学老师角色
- 法律顾问角色
- 健身教练角色
- 历史学家角色
- 科幻作家角色
- 老中医角色
- 侦探角色
- 诗人角色
- 厨师角色
- 程序员角色
- 环保主义者角色
