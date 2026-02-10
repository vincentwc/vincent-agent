#!/usr/bin/env python3
"""
自动分析 Python (FastAPI) 项目结构，生成架构描述
"""

import ast
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set


class PythonProjectAnalyzer:
    """Python/FastAPI 项目分析器"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.modules: Set[str] = set()
        self.services: List[Dict] = []
        self.controllers: List[Dict] = []
        self.repositories: List[Dict] = []
        self.entities: List[Dict] = []
        self.configs: List[Dict] = []
        self.dependencies: List[Dict] = []

    def scan(self):
        """扫描项目"""
        print(f"🔍 扫描项目: {self.project_root.name}")
        print(f"   路径: {self.project_root}\n")

        # 排除的目录
        exclude_dirs = {
            ".git",
            "__pycache__",
            ".venv",
            "venv",
            "env",
            ".idea",
            ".vscode",
            "node_modules",
            "static",
            "tests",
        }

        # 递归扫描所有 Python 文件
        python_files = []
        for root, dirs, files in os.walk(self.project_root):
            # 修改 dirs 以便原地修改遍历列表，排除不需要的目录
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for file in files:
                if file.endswith(".py"):
                    python_files.append(Path(root) / file)

        print(f"📁 找到 {len(python_files)} 个 Python 文件\n")

        for py_file in python_files:
            try:
                self._analyze_file(py_file)
            except Exception as e:
                print(f"❌ 处理文件失败: {py_file} - {e}")
                continue

        # 分析依赖关系
        self._analyze_dependencies()

        return self._generate_report()

    def _analyze_file(self, py_file: Path):
        """分析单个 Python 文件"""
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content)
        except Exception:
            return

        rel_path = py_file.relative_to(self.project_root)
        module_name = str(rel_path).replace("/", ".").replace(".py", "")
        self.modules.add(module_name)

        # 基于路径和内容进行分类
        path_str = str(rel_path)

        # 1. 控制器/路由 (api/routes)
        if "api/routes" in path_str or "server.py" in path_str:
            endpoints = self._extract_endpoints(content)
            if endpoints or "APIRouter" in content or "FastAPI" in content:
                self.controllers.append(
                    {
                        "name": module_name,
                        "file": str(rel_path),
                        "endpoints": endpoints,
                        "classes": self._extract_classes(tree),
                    }
                )
                return

        # 2. 业务服务 (services/)
        if "services" in path_str:
            self.services.append(
                {
                    "name": module_name,
                    "file": str(rel_path),
                    "methods": self._extract_functions(tree),
                    "classes": self._extract_classes(tree),
                }
            )
            return

        # 3. 数据仓储/基础设施 (rag/)
        if "rag" in path_str and ("db.py" in path_str or "vector_store.py" in path_str):
            self.repositories.append(
                {
                    "name": module_name,
                    "file": str(rel_path),
                    "methods": self._extract_functions(tree),
                    "classes": self._extract_classes(tree),
                }
            )
            return

        # 4. 实体/模型 (schemas/ or models.py)
        if "schemas" in path_str or "model" in path_str or "models.py" in path_str:
            self.entities.append(
                {
                    "name": module_name,
                    "file": str(rel_path),
                    "classes": self._extract_classes(tree),
                }
            )
            return

        # 5. 配置 (config/ or core/)
        if "config" in path_str or "core" in path_str:
            self.configs.append({"name": module_name, "file": str(rel_path)})
            return

    def _extract_classes(self, tree: ast.AST) -> List[str]:
        """提取类名"""
        return [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

    def _extract_functions(self, tree: ast.AST) -> List[str]:
        """提取函数/方法名 (排除私有方法)"""
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if not node.name.startswith("_"):
                    functions.append(node.name)
        return functions[:5]  # 限制数量

    def _extract_endpoints(self, content: str) -> List[Dict]:
        """提取 FastAPI 端点"""
        endpoints = []
        # 匹配 @router.get("/path"), @app.post("/path") 等
        pattern = (
            r'@(?:router|app)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
        )

        for match in re.finditer(pattern, content):
            endpoints.append({"method": match.group(1).upper(), "path": match.group(2)})

        return endpoints[:5]  # 限制数量

    def _analyze_dependencies(self):
        """分析组件间依赖关系"""
        # 构建模块到类型的映射
        module_type_map = {}
        for s in self.services:
            module_type_map[s["name"]] = "service"
        for r in self.repositories:
            module_type_map[r["name"]] = "repository"
        for c in self.controllers:
            module_type_map[c["name"]] = "controller"

        all_components = self.services + self.controllers + self.repositories

        for component in all_components:
            file_path = self.project_root / component["file"]
            if not file_path.exists():
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except:
                continue

            # 检查 import 语句和用法
            # 简单检查：如果 component B 的名字出现在 component A 的文件中，且 B 不是 A，则认为有依赖

            # 1. 检查 Service 引用
            for target in self.services:
                if target["name"] != component["name"]:
                    # 检查 import
                    # from services.xxx import yyy
                    # import services.xxx
                    if (
                        target["name"] in content
                        or target["name"].split(".")[-1] in content
                    ):
                        # 避免自我引用误判
                        if target["file"] not in component["file"]:
                            self.dependencies.append(
                                {
                                    "from": component["name"],
                                    "to": target["name"],
                                    "type": "service_call",
                                }
                            )

            # 2. 检查 Repository 引用
            for target in self.repositories:
                if (
                    target["name"] in content
                    or target["name"].split(".")[-1] in content
                ):
                    self.dependencies.append(
                        {
                            "from": component["name"],
                            "to": target["name"],
                            "type": "data_access",
                        }
                    )

        # 去重
        unique_deps = []
        seen = set()
        for dep in self.dependencies:
            key = f"{dep['from']}->{dep['to']}"
            if key not in seen:
                seen.add(key)
                unique_deps.append(dep)
        self.dependencies = unique_deps

    def _generate_report(self) -> Dict:
        """生成分析报告"""
        return {
            "project_name": self.project_root.name,
            "total_files": len(self.services)
            + len(self.controllers)
            + len(self.repositories)
            + len(self.entities),
            "summary": {
                "services": len(self.services),
                "controllers": len(self.controllers),
                "repositories": len(self.repositories),
                "entities": len(self.entities),
                "configs": len(self.configs),
            },
            "services": self.services,
            "controllers": self.controllers,
            "repositories": self.repositories,
            "entities": self.entities,
            "dependencies": self.dependencies,
        }

    def generate_architecture_description(self) -> str:
        """生成用于绘图的自然语言描述"""
        report = self._generate_report()

        desc = f"""
项目名称: {report["project_name"]}

## 系统架构分析 (Python/FastAPI)

这是一个基于 FastAPI 的 Python 项目，包含以下层次结构：

### 1. 接口层 (API Layer)
{self._format_controllers()}

### 2. 业务服务层 (Service Layer)
{self._format_services()}

### 3. 数据基础设施层 (Infrastructure Layer)
{self._format_repositories()}

### 4. 数据模型 (Data Models)
{self._format_entities()}

### 5. 组件依赖关系
{self._format_dependencies()}

## 绘图要求

请生成一张专业的系统架构图，要求：

1. **分层布局**：
   - 顶部：API 路由/接口层（橙色）
   - 中部：业务服务层（蓝色）
   - 底部：基础设施/数据层（绿色）
   - 最底部：外部系统/数据库（深灰色）

2. **组件样式**：
   - Router/Controller: 矩形，橙色边框
   - Service: 矩形，蓝色填充
   - Repository/DB Manager: 矩形，浅绿色填充
   - Schema/Model: 圆角矩形，灰色填充

3. **连接线**：
   - 服务调用：实线箭头
   - 数据读写：虚线箭头
   - 标注调用方向

4. **文字标注**：
   - 显示模块名或类名
   - 关键 API 路径可作为子标签

5. **整体风格**：
   - 简洁、现代
   - 使用 C4 模型或类似的分层架构风格
"""
        return desc.strip()

    def _format_controllers(self) -> str:
        if not self.controllers:
            return "暂无接口层组件"

        lines = []
        for ctrl in self.controllers:
            name = ctrl["name"].split(".")[-1]
            endpoints = (
                ", ".join([f"{e['method']} {e['path']}" for e in ctrl["endpoints"]])
                if ctrl.get("endpoints")
                else "无显式路由"
            )
            lines.append(f"- {name} ({ctrl['file']}): {endpoints}")
        return "\n".join(lines)

    def _format_services(self) -> str:
        if not self.services:
            return "暂无业务服务组件"

        lines = []
        for svc in self.services:
            name = svc["name"].split(".")[-1]
            methods = ", ".join(svc["methods"]) if svc.get("methods") else ""
            classes = ", ".join(svc["classes"]) if svc.get("classes") else ""
            info = classes if classes else methods
            lines.append(f"- {name}: {info}")
        return "\n".join(lines)

    def _format_repositories(self) -> str:
        if not self.repositories:
            return "暂无数据基础设施组件"

        lines = []
        for repo in self.repositories:
            name = repo["name"].split(".")[-1]
            classes = ", ".join(repo["classes"]) if repo.get("classes") else ""
            lines.append(f"- {name}: {classes}")
        return "\n".join(lines)

    def _format_entities(self) -> str:
        if not self.entities:
            return "暂无实体模型"

        lines = []
        for entity in self.entities:
            name = entity["name"].split(".")[-1]
            classes = ", ".join(entity["classes"]) if entity.get("classes") else ""
            if classes:
                lines.append(f"- {name}: {classes}")
        return "\n".join(lines[:10])  # 限制显示数量

    def _format_dependencies(self) -> str:
        if not self.dependencies:
            return "暂无显著依赖关系"

        lines = []
        for dep in self.dependencies[:20]:
            src = dep["from"].split(".")[-1]
            dst = dep["to"].split(".")[-1]
            arrow = "→" if dep["type"] == "service_call" else "⤳"
            lines.append(f"- {src} {arrow} {dst}")
        return "\n".join(lines)


def main():
    """主函数"""
    analyzer = PythonProjectAnalyzer()
    report = analyzer.scan()

    # 确保输出目录存在
    output_dir = Path(".trae-tools/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存绘图描述
    desc_file = output_dir / "architecture_description.txt"
    description = analyzer.generate_architecture_description()
    with open(desc_file, "w", encoding="utf-8") as f:
        f.write(description)

    print("\n" + "=" * 60)
    print("✅ 项目分析完成！")
    print("=" * 60)
    print(f"\n📊 统计信息:")
    print(f"   - 接口层模块: {report['summary']['controllers']}")
    print(f"   - 业务层模块: {report['summary']['services']}")
    print(f"   - 基础设施层模块: {report['summary']['repositories']}")
    print(f"   - 数据模型: {report['summary']['entities']}")

    print(f"\n📁 输出文件:")
    print(f"   - 绘图描述: {desc_file}")

    return description


if __name__ == "__main__":
    main()
