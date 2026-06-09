# 答案相关性评估数据集 (EvalScope格式)

## 数据集说明

本目录包含多个适配EvalScope框架的答案相关性评估数据集。

### 数据集列表

1. **squad_sample_evalscope.jsonl** (10条)
   - SQuAD风格的阅读理解数据集
   - 包含问题、答案和上下文
   - 适用于测试答案与上下文的相关性

2. **nq_sample_evalscope.jsonl** (10条)
   - Natural Questions风格的开放域问答数据集
   - 包含问题和简短答案
   - 适用于测试答案准确性

3. **rag_eval_sample_evalscope.jsonl** (10条)
   - RAG系统评估数据集
   - 包含查询、生成答案和检索上下文
   - 专门用于评估RAG系统的答案相关性

4. **multilingual_sample_evalscope.jsonl** (10条)
   - 多语言问答数据集
   - 包含英语、中文、法语、德语、西班牙语、日语
   - 适用于测试多语言模型的答案相关性

### EvalScope格式说明

每个数据集采用JSONL格式，每行一个JSON对象：

```json
{
    "query": "用户问题",
    "response": "参考答案/标准答案",
    "contexts": ["相关上下文（可选）"]
}
```

### 使用方法

1. 使用配置文件进行评测：
```bash
swift eval --eval_url http://your-api-endpoint/v1     --eval_dataset no     --eval_is_chat_model true     --model_type your-model     --custom_eval_config evalscope_config.json
```

2. 单独使用某个数据集：
```python
from evalscope.run import run_task

task_cfg = {
    "eval_backend": "VLMEvalKit",
    "eval_config": {
        "model": [...],
        "data": ["squad_answer_relevance"],
        "work_dir": "outputs"
    }
}
run_task(task_cfg=task_cfg)
```

### 扩展数据集

如需更多数据，可以从以下来源下载完整数据集：
- SQuAD: https://rajpurkar.github.io/SQuAD-explorer/
- Natural Questions: https://ai.google.com/research/NaturalQuestions
- MS MARCO: https://microsoft.github.io/msmarco/
- TriviaQA: http://nlp.cs.washington.edu/triviaqa/

下载后使用 `convert_to_evalscope.py` 脚本转换为EvalScope格式。

## 评估指标

对于答案相关性评估，建议使用以下指标：
- **ROUGE**: 评估生成答案与参考答案的文本重叠度
- **BLEU**: 评估生成答案的准确性
- **语义相似度**: 使用嵌入模型计算答案的语义相关性
