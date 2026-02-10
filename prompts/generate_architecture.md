## 指令

请为我的 Python FastAPI 项目生成系统架构图。

## 项目信息

[请先运行 `python3 script/analyze_project.py`，然后将生成的 `.trae-tools/output/architecture_description.txt` 内容粘贴到此处]

## 要求

1. **分层架构**：
   - 接口层（API/Routes）- 橙色 (#FFE6CC)
   - 业务层（Service）- 蓝色 (#DAE8FC)
   - 基础设施层（Infrastructure/Repository）- 绿色 (#D5E8D4)
   - 数据模型（Schemas/Models）- 灰色 (#F5F5F5)

2. **组件标注**：
   - 显示模块名或类名
   - 标注关键 API 路径或方法
   - 用箭头标明依赖关系（实线：调用，虚线：数据流）

3. **输出格式**：
   - 保存为 docs/architecture.drawio
   - 确保布局清晰，避免线条交叉

## 工具

请使用 drawio MCP 工具完成绘图。
