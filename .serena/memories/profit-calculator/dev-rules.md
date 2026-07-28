# 开发流程规范

## 执行顺序
1. 审计现状（对比 CONSENSUS.md 检查完成状态）
2. 补齐遗漏的优化项
3. 更新 CONSENSUS.md 反映最新状态
4. 保存 Serena memory 记录项目状态

## 每次修改后
- 运行 `pytest tests/` 验证
- 更新 CONSENSUS.md 验收标准
- 如有新决策，记录到决策表

## 打包规范
- 完成优化后重新打包：`pyinstaller 收益计算器.spec`
- 确保 `console=False`（窗口模式）
- 测试 exe 单实例功能
