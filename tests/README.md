# Tests

- `unit/`：不依赖外部服务的核心逻辑回归测试。
- `smoke/`：需要网络或外部服务的轻量连通性验证。

使用 `KG_SMA_env`，从仓库根目录运行：

```powershell
python -m unittest discover -s tests/unit -v
```

测试生成的临时或 smoke 输出写入 `results/test-results/`。
