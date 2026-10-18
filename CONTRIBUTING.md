# 贡献指南

## 本地开发

```bash
conda create -n pyy python=3.11 -y
conda activate pyy
pip install -r requirements-dev.txt
python run.py
```

跑测试与静态检查：

```bash
pytest -q
ruff check app scripts tests --select E,F,W --ignore E501
```

## 新增一个院校源

1. 在 `app/crawler/sources.py` 的 `SOURCES` 里加一条：

```python
_s("某某大学", ["https://yjs.example.edu.cn/zsgz/sszs.htm"], "省份"),
```

2. 如果该站有反爬或 JS 渲染，加 `render=True`；需要特殊请求头时加 `headers={...}`。
3. 用 `python scripts/monitor_once.py --school 某某大学 --dry-run` 验证解析结果。
4. 若解析为 0 条，把该页 HTML 片段补进 `tests/test_parser.py` 作为回归用例。

## 调整精度规则

- 词表在 `app/crawler/classifier.py` 顶部，`STRONG / MEDIUM / NEGATIVE` 三张表。
- 任何阈值改动都要在 `tests/test_classifier.py` 里补一条用例，说明为什么。
- 不要用「命中就入库」的写法，低置信条目一律走 `review` 状态。

## 提交规范

```
feat(crawler): 支持 <li title> 形式的列表项
fix(parser): 日期从锚点父节点提取
docs: 补充 Docker 部署说明
test: 覆盖 SimHash 近似判重
```

提交前请确保 `pytest -q` 全绿。
