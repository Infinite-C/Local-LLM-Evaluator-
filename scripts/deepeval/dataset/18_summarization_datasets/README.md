# 摘要质量评估数据集 (EvalScope格式)

## 数据集说明

本数据集包含50条摘要质量评估数据，适配EvalScope框架的General-QA格式。

### 数据分布

| 类别 | 条数 | 说明 |
|------|------|------|
| 科技类 | 10条 | AI、区块链、5G、量子计算等 |
| 商业经济类 | 10条 | 电子商务、供应链管理、数字营销等 |
| 医疗健康类 | 10条 | 远程医疗、精准医疗、心理健康等 |
| 教育类 | 10条 | 在线教育、个性化学习、STEM教育等 |
| 环境气候类 | 10条 | 气候变化、可再生能源、循环经济等 |
| **总计** | **50条** | |

### EvalScope格式

```json
{
    "query": "原始长文本（需要摘要的文章）",
    "response": "参考摘要（人工撰写的黄金标准）"
}
```

### 评测指标

- **ROUGE-1**: 一元词重叠度
- **ROUGE-2**: 二元词重叠度
- **ROUGE-L**: 最长公共子序列
- **BLEU**: 双语评估替补

## 使用方法

### 1. 使用配置文件评测

```bash
swift eval --eval_url http://your-api-endpoint/v1 \
    --eval_dataset no \
    --eval_is_chat_model true \
    --model_type your-model \
    --custom_eval_config custom_eval_config.json
```

### 2. 在eval_task.yaml中使用

```yaml
# 17. 摘要质量评估
  - name: my_summarization_eval
    display_name: 摘要质量评估 (ROUGE/BLEU)
    dimension: summarization
    dataset: general_qa
    metric: Rouge
    dataset_args:
      local_path: summarization_datasets
      subset_list: ['my_summary_set']
    limit: 50
    enabled: true
    need_judge_model: false
```

### 3. Python代码使用

```python
from evalscope.run import run_task

task_cfg = {
    "eval_backend": "VLMEvalKit",
    "eval_config": {
        "model": [...],
        "data": ["my_summary_set"],
        "work_dir": "outputs"
    }
}
run_task(task_cfg=task_cfg)
```

## 文件列表

- `my_summary_set.jsonl` - 摘要数据集（50条）
- `custom_eval_config.json` - EvalScope配置文件
- `README.md` - 本文件

## 扩展数据集

如需更多数据，可以从以下公开摘要数据集获取：
- **LCSTS**: 中文短文本摘要数据集
- **NLPCC2017**: 中文新闻摘要数据集
- **CNN/DailyMail**: 英文新闻摘要数据集
- **XSum**: 英文极端摘要数据集
- **Gigaword**: 英文标题生成数据集

使用 `convert_summarization_datasets.py` 脚本转换为EvalScope格式。
