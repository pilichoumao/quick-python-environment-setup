# Quick Python Environment Setup 需求文档 v4

## 1. 项目名称

Quick Python Environment Setup

## 2. 项目定位

Quick Python Environment Setup 是一个面向 Python 初学者和开源项目使用者的环境配置 Skill / Agent Tool。

它的目标不是简单执行：

```bash
pip install -r requirements.txt
```

而是帮助用户从一个 GitHub/GitLab 仓库链接 或 本地项目路径 出发，自动完成：

- 项目识别
- 环境管理方式选择
- Python 版本解析
- 虚拟环境创建
- GPU / CUDA / CPU / MPS 判断
- PyTorch 安装策略选择
- 依赖安装
- 版本冲突诊断
- 国内镜像源加速
- 基础环境验收
- 运行入口识别
- 权重 / 数据集 / 配置文件缺失提示
- 最终报告生成

一句话定位：

> Quick Python Environment Setup 是一个面向新手的、跨平台的、支持主流编码 Agent 调用的 Python 开源项目环境配置助手。

## 3. 核心目标

### 3.1 用户目标

用户只需要提供：

- 一个 GitHub/GitLab 链接

或者：

- 一个本地项目路径

Skill 就能帮助用户分析这个项目应该如何配置环境，并尽可能安全、稳定地完成环境安装。

### 3.2 Agent 目标

该项目不仅要能被人手动运行，还要能被主流编码 Agent 调用，包括：

- OpenAI Codex
- Claude Code
- Qoder
- GitHub Copilot coding agent
- Cursor / Windsurf / Cline 等其他 Agent

因此，项目应采用：

```text
核心 CLI + Python 库 + Agent 适配层
```

而不是只写成某一个平台专用的 Skill。

## 4. 设计原则

### 4.1 Agent-neutral

核心逻辑必须与具体 Agent 解耦。

也就是说，核心能力不要依赖 Codex、Claude Code、Qoder 的专有接口。

推荐架构：

```text
Core Python Package
        ↓
CLI Interface
        ↓
Agent Adapter Layer
        ↓
Codex / Claude Code / Qoder / Copilot / Other Agents
```

核心能力通过 CLI 暴露，例如：

```bash
python -m quick_env_setup --source <git_url_or_local_path>
```

任何 Agent 只要能读文件、运行终端命令，就可以调用这个工具。

### 4.2 默认推荐 Conda，但提供 venv 选项

默认推荐 Conda。

原因：

1. Conda 更适合机器学习和深度学习项目
2. Conda 更容易管理 Python 版本
3. Conda 环境隔离更清晰
4. 新手更容易理解“一个项目一个环境”

但也提供 venv 作为轻量选项：

1. Conda，推荐，适合机器学习、深度学习、科研项目
2. venv，轻量，适合普通 Python 项目、Web 项目、脚本项目

默认：

```text
Conda
```

### 4.3 默认新建环境

默认策略：

```text
为每个项目创建一个新的独立环境。
```

不推荐默认复用已有环境。

原因：

1. 复用旧环境容易造成依赖污染
2. 新手很难判断依赖冲突来源
3. 新建环境更容易删除、重建和排错

如果用户明确要求复用已有环境，应提示风险。

### 4.4 默认安全等级 Level 2

安全等级分为：

- Level 1：只分析项目，不安装依赖，不运行项目代码
- Level 2：创建环境并安装依赖，但不运行项目代码
- Level 3：安装依赖并运行 demo / quickstart 命令

默认：

```text
Level 2
```

也就是说：

- 可以 clone 项目
- 可以创建虚拟环境
- 可以安装依赖
- 可以做基础 import 验证
- 不默认运行项目代码

运行 demo、训练脚本、推理脚本、Web 服务前必须用户确认。

## 5. Agent 兼容性设计

这是本版本新增的关键部分。

### 5.1 为什么要做 Agent 兼容

现在用户可能会用不同的 Agent 来实现或调用该工具，例如：

- Codex
- Claude Code
- Qoder
- GitHub Copilot
- Cursor
- Windsurf
- Cline
- Devin
- Jules

这些 Agent 的项目指令格式不同。

例如：

- Codex：`AGENTS.md` / `SKILL.md`
- Claude Code：`SKILL.md` / slash commands
- Qoder：`.qoder/rules`
- GitHub Copilot：repository custom instructions / `AGENTS.md`

因此，项目不能只提供一种格式，而应提供一个通用适配目录。

### 5.2 推荐目录结构

```text
quick-python-environment-setup/
├── README.md
├── AGENTS.md
├── pyproject.toml
├── quick_env_setup/
│   ├── __init__.py
│   ├── cli.py
│   ├── source_resolver.py
│   ├── git_handler.py
│   ├── system_detector.py
│   ├── project_type_detector.py
│   ├── env_manager.py
│   ├── conda_manager.py
│   ├── venv_manager.py
│   ├── project_scanner.py
│   ├── dependency_file_parser.py
│   ├── python_version_resolver.py
│   ├── device_detector.py
│   ├── pytorch_resolver.py
│   ├── mirror_manager.py
│   ├── dependency_installer.py
│   ├── conflict_analyzer.py
│   ├── asset_detector.py
│   ├── run_command_discoverer.py
│   ├── validator.py
│   ├── safety_policy.py
│   ├── report_generator.py
│   ├── interactive_prompt.py
│   ├── logger.py
│   └── utils.py
├── skills/
│   ├── codex/
│   │   └── SKILL.md
│   ├── claude-code/
│   │   └── SKILL.md
│   ├── copilot/
│   │   └── instructions.md
│   └── generic/
│       └── SKILL.md
├── .qoder/
│   └── rules/
│       └── quick-python-environment-setup.md
├── examples/
│   ├── codex_prompt.md
│   ├── claude_code_prompt.md
│   ├── qoder_prompt.md
│   └── generic_agent_prompt.md
├── tests/
│   ├── test_source_resolver.py
│   ├── test_project_type_detector.py
│   ├── test_python_version_resolver.py
│   ├── test_pytorch_resolver.py
│   ├── test_conflict_analyzer.py
│   └── test_asset_detector.py
└── docs/
    ├── agent_compatibility.md
    ├── safety_policy.md
    ├── troubleshooting.md
    └── mirror_configuration.md
```

### 5.3 通用 AGENTS.md

项目根目录需要提供 `AGENTS.md`，用于告诉所有支持该格式的编码 Agent：

- 这个项目是什么
- 如何运行
- 如何测试
- 哪些操作不能自动执行
- 如何处理安全问题
- 如何修改代码

`AGENTS.md` 示例内容：

````markdown
# AGENTS.md

## Project Overview

This project implements Quick Python Environment Setup, an agent-friendly CLI tool for configuring Python environments for open-source projects.

The tool accepts either:

- a GitHub/GitLab repository URL
- a local project path

It analyzes the project, detects Python version requirements, creates an isolated environment, installs dependencies, handles PyTorch CPU/CUDA/MPS strategies, diagnoses dependency conflicts, and generates a final setup report.

## Main Commands

Run dry-run analysis:

```bash
python -m quick_env_setup --source <path_or_url> --dry-run
```

Run setup in default Level 2 mode:

```bash
python -m quick_env_setup --source <path_or_url>
```

Run with Conda:

```bash
python -m quick_env_setup --source <path_or_url> --env-manager conda
```

Run with venv:

```bash
python -m quick_env_setup --source <path_or_url> --env-manager venv
```

## Safety Rules

Agents must not automatically:

- delete existing environments
- delete project directories
- execute sudo commands
- run training scripts
- run demo scripts
- run unknown project code
- download large model weights without confirmation

Demo execution requires explicit user confirmation.

## Testing

Run unit tests:

```bash
pytest
```

## Coding Guidelines

- Prefer standard library where possible.
- Use `subprocess.run` with argument lists, not `shell=True`.
- Keep platform-specific logic isolated.
- All installation commands must be logged.
- All failures must produce user-friendly explanations.
````

Codex 和 GitHub Copilot 都已经有围绕 `AGENTS.md` 的项目指令支持；Codex 文档明确说明会读取 `AGENTS.md`，GitHub 也说明 Copilot coding agent 支持仓库自定义指令和 `AGENTS.md`。

### 5.4 Codex 适配

Codex 适配应提供：

```text
skills/codex/SKILL.md
```

Codex 的 Skill 应该只负责说明：

- 何时调用该 Skill
- 如何调用 CLI
- 不要越权执行哪些操作
- 如何输出报告

Codex Skill 示例：

````markdown
# Quick Python Environment Setup

Use this skill when the user wants to configure a Python environment for an open-source project.

The user may provide:

- GitHub URL
- GitLab URL
- local project path

## Workflow

1. Run dry-run first.
2. Present the detected setup plan.
3. Ask for confirmation on key decisions.
4. Run setup in Level 2 mode by default.
5. Do not run project demo code unless the user explicitly confirms.

## Commands

Dry run:

```bash
python -m quick_env_setup --source <path_or_url> --dry-run
```

Default setup:

```bash
python -m quick_env_setup --source <path_or_url> --level 2
```

## Safety

Never automatically run:

- `python train.py`
- `python demo.py`
- `python app.py`
- sudo commands
- environment deletion
````

Codex 的 Agent Skills 通过 `SKILL.md` 暴露能力，且 Codex 会在需要使用技能时加载完整 Skill 指令。

### 5.5 Claude Code 适配

Claude Code 适配应提供：

```text
skills/claude-code/SKILL.md
```

Claude Code Skill 示例：

````markdown
# Quick Python Environment Setup

This skill helps configure Python environments for open-source projects.

## When to use

Use this skill when the user asks to:

- set up a Python project
- run a GitHub Python repository
- configure Conda / venv
- fix Python dependency installation issues
- install PyTorch with CPU/CUDA/MPS

## Default behavior

- Use Level 2 safety mode.
- Do not run project code by default.
- Ask before running demo commands.
- Ask before deleting environments.
- Ask before using sudo.

## Recommended command

```bash
python -m quick_env_setup --source <path_or_url> --dry-run
```

Then show the plan to the user.
````

Claude Code 文档中有 Skills 和 slash commands 的说明，slash commands 可以用于控制 Claude Code 会话，Skills 则可以扩展 Claude Code 的能力。

### 5.6 Qoder 适配

Qoder 适配应提供：

```text
.qoder/rules/quick-python-environment-setup.md
```

示例：

````markdown
# Quick Python Environment Setup Rule

When working on this repository, treat it as an agent-friendly Python environment setup tool.

## Expected behavior

- Preserve cross-platform compatibility.
- Keep Codex, Claude Code, Qoder, Copilot compatibility files updated.
- Do not hard-code one agent platform.
- Keep CLI as the source of truth.
- All agent adapters should call the same CLI.

## Safety

Do not implement automatic execution of project demo code unless gated by explicit confirmation.

## Test command

```bash
pytest
```
````

Qoder 文档说明项目规则存放在 `.qoder/rules` 目录下，用于让 Qoder 适应项目约定；Qoder Agent Mode 也支持项目搜索、文件编辑、终端和工具调用，因此适合通过规则 + CLI 的方式集成。

### 5.7 GitHub Copilot 适配

GitHub Copilot 适配应提供：

```text
skills/copilot/instructions.md
```

也可以依赖根目录的：

```text
AGENTS.md
```

Copilot instructions 示例：

````markdown
# GitHub Copilot Instructions

This repository implements an agent-friendly Python environment setup CLI.

When modifying this project:

- Keep CLI behavior stable.
- Do not introduce unsafe automatic execution.
- Do not run demo project code in tests.
- Maintain cross-platform support.
- Update AGENTS.md and skill adapters when changing CLI behavior.

Main test command:

```bash
pytest
```
````

GitHub 官方文档说明可以添加 repository custom instructions 来帮助 Copilot 理解项目如何构建、测试和验证；GitHub changelog 也说明 Copilot coding agent 支持 `AGENTS.md`。

## 6. 输入来源设计

用户输入可能是：

```text
GitHub 链接
GitLab 链接
其他 Git 仓库链接
本地项目路径
```

CLI 统一入口：

```bash
python -m quick_env_setup --source <git_url_or_local_path>
```

### 6.1 远程仓库链接

支持：

```text
https://github.com/xxx/yyy
https://gitlab.com/xxx/yyy
git@github.com:xxx/yyy.git
git@gitlab.com:xxx/yyy.git
```

如果是远程仓库，流程为：

1. 检查 git 是否可用
2. 询问 clone 目录
3. clone 项目
4. 如果目录已存在，询问用户如何处理
5. 进入项目目录
6. 继续环境配置

不能静默删除已有目录。

### 6.2 本地项目路径

如果用户输入：

```text
/home/user/projects/demo
```

或：

```text
E:\projects\demo
```

流程为：

1. 检查路径是否存在
2. 检查是否为目录
3. 扫描 Python 项目特征
4. 如果不是明显 Python 项目，提示用户确认是否继续

## 7. 项目类型识别

Skill 需要先判断项目类型。

支持类型：

1. Deep Learning / Machine Learning 项目
2. 普通 Python 包
3. Web 项目
4. Jupyter Notebook 项目
5. CLI 命令行工具项目
6. 数据分析 / 脚本项目
7. 不确定类型

### 7.1 深度学习 / 机器学习项目

关键词：

```text
torch
tensorflow
jax
keras
transformers
diffusers
accelerate
mmcv
mmdet
detectron2
deepspeed
flash-attn
yolo
train.py
infer.py
inference.py
checkpoint
weights
```

策略：

- 推荐 Conda
- 检测 GPU / CUDA / MPS
- 重点处理 PyTorch / CUDA 版本
- 检查权重文件和数据集

### 7.2 Web 项目

关键词：

```text
flask
fastapi
django
uvicorn
streamlit
gradio
app.py
server.py
manage.py
```

策略：

- Conda 或 venv 均可
- 重点识别启动命令
- 检查 `.env` 配置文件
- 检查端口和 API key

### 7.3 Notebook 项目

关键词：

```text
.ipynb
notebooks/
jupyter
```

策略：

- 安装 jupyter / ipykernel
- 提示用户注册 kernel

示例：

```bash
python -m ipykernel install --user --name env_name --display-name "Python (env_name)"
```

### 7.4 普通 Python 包

关键词：

```text
pyproject.toml
setup.py
setup.cfg
src/
```

策略：

- `pip install -e .`
- 运行 import 验证

## 8. 环境管理方式

### 8.1 Conda 模式

默认推荐 Conda。

流程：

1. 检查 conda 是否存在
2. 如果没有 Conda，提示安装 Miniconda
3. 解析 Python 版本
4. 询问环境名称
5. 创建 Conda 环境
6. 安装依赖
7. 验证环境

示例：

```bash
conda create -n my_project python=3.10 -y
```

安装命令建议：

```bash
conda run -n my_project pip install -r requirements.txt
```

### 8.2 venv 模式

venv 适合：

- 普通 Python 工具项目
- Web 项目
- 脚本项目
- 不涉及 CUDA / PyTorch 复杂依赖的项目

macOS/Linux：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Windows：

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

如果检测到深度学习项目，应提示：

> 检测到该项目可能是深度学习项目，推荐使用 Conda。

## 9. Python 版本识别

从以下文件解析 Python 版本：

- `environment.yml`
- `conda.yml`
- `pyproject.toml`
- `setup.py`
- `setup.cfg`
- `README.md`

优先级：

1. `environment.yml` / `conda.yml`
2. `pyproject.toml`
3. `setup.py` / `setup.cfg`
4. `README.md`
5. 默认推荐

默认推荐：

```text
Python 3.10
```

原因：

- Python 3.10 对多数普通项目和机器学习项目兼容性较好。
- 不建议默认使用过新的 Python 版本，因为旧项目可能不兼容。

## 10. GPU / CUDA / CPU / MPS 策略

### 10.1 总体策略

- 无 NVIDIA GPU → 不检查 CUDA，默认 CPU 方案
- 有 NVIDIA GPU → 检查 `nvidia-smi` 和驱动支持的 CUDA 版本
- Apple Silicon Mac → 不走 CUDA，检查 MPS
- AMD GPU → 第一版默认 CPU，后续可扩展 ROCm

### 10.2 无 GPU

如果没有检测到 NVIDIA GPU：

```text
未检测到 NVIDIA GPU。
如果项目需要 PyTorch，将默认安装 CPU 版本 PyTorch。
```

安装示例：

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

如果项目不需要 PyTorch：

```text
未检测到项目需要 PyTorch，因此不会额外安装 PyTorch。
```

### 10.3 NVIDIA GPU

如果 `nvidia-smi` 可用，提取：

- GPU 名称
- Driver Version
- CUDA Version

提示：

```text
检测到 NVIDIA GPU：RTX 4060 Ti
驱动支持的 CUDA 版本：12.4
```

然后根据 PyTorch 官方安装命令选择 CUDA 构建。PyTorch 官方页面提供不同 CUDA/CPU 版本的安装命令，Skill 应优先以官方命令为准。

示例：

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 10.4 Apple Silicon Mac

如果检测到 Apple Silicon：

- 不安装 CUDA 版 PyTorch。
- 可以安装普通 PyTorch，并验证 MPS 是否可用。

验证：

```bash
python -c "import torch; print(torch.backends.mps.is_available())"
```

### 10.5 AMD GPU

第一版不自动适配 ROCm。

提示：

```text
检测到非 NVIDIA GPU。
第一版暂不自动配置 ROCm，默认使用 CPU 版本。
后续可扩展 AMD ROCm 支持。
```

## 11. PyTorch 安装策略

不能简单依赖 `requirements.txt` 中的 `torch`。

如果 `requirements.txt` 中包含：

- `torch`
- `torchvision`
- `torchaudio`

提示：

```text
检测到 requirements.txt 中包含 PyTorch 相关依赖。
为了避免安装错误的 CPU/CUDA 版本，建议单独安装适配当前设备的 PyTorch，然后跳过 requirements.txt 中的 torch 相关项。
是否采用该策略？
默认：是
```

处理方式：

1. 生成 `requirements_without_torch.txt`
2. 先安装适配设备的 PyTorch
3. 再安装剩余依赖

## 12. 国内镜像源策略

### 12.1 是否启用镜像

交互示例：

```text
是否使用国内镜像源加速 pip / conda 下载？
1. 不使用，默认
2. 使用清华源
3. 使用 USTC 源
4. 使用阿里云源
```

### 12.2 pip 镜像

清华 TUNA PyPI 帮助页提供了 pip 镜像使用方式，并说明 simple 路径不能少；USTC 也提供 PyPI 镜像帮助。

可配置：

```bash
pip install -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple some-package
pip install -i https://mirrors.ustc.edu.cn/pypi/simple some-package
```

注意：

- 普通 Python 包可以用国内 PyPI 镜像。
- PyTorch CUDA wheel 优先使用 PyTorch 官方 `index-url`。

### 12.3 conda 镜像

可选：

- 清华 TUNA Anaconda 镜像
- USTC Anaconda 镜像

Skill 应允许用户选择是否配置镜像，但不要强制覆盖用户已有 conda 配置。

## 13. 依赖安装顺序

推荐顺序：

1. 判断输入来源
2. clone 或进入本地项目
3. 识别操作系统和项目类型
4. 选择环境管理方式：Conda / venv
5. 解析 Python 版本
6. 询问环境名称
7. 创建新环境
8. 升级 pip / setuptools / wheel
9. 判断是否需要 PyTorch
10. 根据设备安装 CPU / CUDA / MPS 方案的 PyTorch
11. 安装其他依赖
12. 处理依赖冲突
13. 基础环境验证
14. 扫描 quickstart / demo / 权重 / 数据集需求
15. 输出最终报告

## 14. 版本冲突处理

版本冲突处理是重点能力。

### 14.1 需要识别的错误

- `No matching distribution found`
- `ResolutionImpossible`
- `ModuleNotFoundError`
- `ImportError`
- `cannot import name`
- `metadata-generation-failed`
- `Failed building wheel`
- `Microsoft Visual C++ 14.0 or greater is required`
- `CUDA_HOME is not set`
- `torch.cuda.is_available() is False`
- `libGL.so.1: cannot open shared object file`
- `protobuf version conflict`
- `numpy version conflict`
- `pydantic v1/v2 conflict`

### 14.2 错误分类

1. Python 版本不兼容
2. 包版本冲突
3. 缺少系统编译工具
4. 缺少系统动态库
5. PyTorch / CUDA 不匹配
6. 网络下载失败
7. 权重 / 数据集 / 配置文件缺失
8. 项目代码自身问题

### 14.3 处理策略

不要盲目强制升级所有包。

应当：

1. 保存完整日志
2. 提取核心错误
3. 判断错误类型
4. 输出用户能理解的解释
5. 给出下一步建议
6. 如有必要，建议重建 Python 版本更合适的新环境

示例：

```text
检测到依赖版本冲突：

package A 需要 numpy<1.24
package B 需要 numpy>=1.26

建议：
1. 查看项目 README 是否指定 Python/依赖版本；
2. 尝试使用项目推荐的 requirements.txt；
3. 如项目较旧，可尝试 Python 3.8 或 3.10；
4. 不建议直接强行升级所有包。
```

## 15. 权重 / 数据集 / 配置文件识别

环境安装成功后，还要检查运行准备。

扫描关键词：

```text
checkpoint
checkpoints
pretrained
pre-trained
weights
model zoo
download weights
dataset
datasets
data path
config
.env
API_KEY
Hugging Face
Google Drive
Baidu Netdisk
OneDrive
```

如果发现缺失：

```text
环境依赖已经安装，但项目运行可能还需要额外文件：

1. 模型权重：weights/best.pt
2. 数据目录：data/
3. 配置文件：config.yaml

请根据 README 下载或配置后再运行。
```

如果 README 中有下载链接，应提取并列出。

## 16. 环境验收设计

### 16.1 基础环境验收，默认自动执行

低风险命令可以自动执行：

```bash
python --version
pip --version
python -c "import torch; print(torch.__version__)"
python -c "import torch; print(torch.cuda.is_available())"
python -c "import numpy"
python -c "import cv2"
```

这些属于 Level 2。

### 16.2 项目运行验收，必须用户确认

扫描：

```text
README.md
examples/
demo/
scripts/
main.py
app.py
demo.py
train.py
test.py
infer.py
inference.py
predict.py
run.py
```

提取命令：

```bash
python demo.py
python main.py --config configs/demo.yaml
streamlit run app.py
uvicorn app:app
```

默认不运行，只告诉用户：

```text
检测到以下可能的运行命令：

1. python demo.py
2. python main.py --config configs/demo.yaml

默认不自动运行项目代码。
你可以手动执行，或者选择让我运行其中一个命令进行测试。
```

## 17. 安全策略

Skill 和所有 Agent 适配层都必须遵守：

1. 不默认运行项目代码
2. 不默认删除环境或目录
3. 不默认执行 sudo
4. 不默认下载大模型权重
5. 不默认启动长时间训练任务
6. 不默认暴露用户路径、密钥或 token
7. 所有高风险操作必须用户确认

实现时尽量使用：

```python
subprocess.run(["conda", "create", "-n", env_name, f"python={python_version}", "-y"])
```

避免：

```python
subprocess.run(f"conda create -n {env_name} python={python_version} -y", shell=True)
```

## 18. CLI 参数设计

统一 CLI：

```bash
python -m quick_env_setup --source <git_url_or_local_path>
```

可选参数：

```text
--env-manager conda|venv
--env-name <name>
--python <version>
--clone-dir <path>
--cpu-only
--use-china-mirror
--mirror tuna|ustc|aliyun
--dry-run
--yes
--level 1|2|3
--run-demo
--timeout 60
--recreate
--verbose
```

说明：

| 参数 | 说明 |
| --- | --- |
| `--source` | Git 链接或本地项目路径 |
| `--env-manager` | 环境管理方式，默认 conda |
| `--env-name` | 指定环境名 |
| `--python` | 指定 Python 版本 |
| `--clone-dir` | 指定 clone 目录 |
| `--cpu-only` | 强制 CPU 方案 |
| `--use-china-mirror` | 启用国内镜像 |
| `--mirror` | 选择镜像源 |
| `--dry-run` | 只生成计划，不执行 |
| `--yes` | 自动接受低风险推荐选项 |
| `--level` | 安全等级，默认 2 |
| `--run-demo` | 允许运行 demo |
| `--timeout` | demo 超时时间 |
| `--recreate` | 允许删除并重建环境 |
| `--verbose` | 输出详细日志 |

## 19. 日志与报告

创建：

```text
.env_setup_logs/
```

包含：

```text
setup.log
detected_config.json
install_plan.json
error_summary.txt
run_candidates.txt
missing_assets.txt
final_report.txt
agent_trace_summary.txt
```

### 19.1 detected_config.json 示例

```json
{
  "source_type": "git_url",
  "source": "https://github.com/xxx/project",
  "local_project_path": "/home/user/projects/project",
  "os": "Linux",
  "arch": "x86_64",
  "project_type": "deep_learning",
  "env_manager": "conda",
  "env_name": "project_env",
  "python_version": "3.10",
  "has_nvidia_gpu": false,
  "device_strategy": "cpu",
  "needs_pytorch": true,
  "pytorch_install_type": "cpu",
  "use_china_mirror": true,
  "mirror": "tuna",
  "safety_level": 2,
  "validation_status": "passed"
}
```

## 20. 最终报告示例

```text
环境配置完成。

项目来源：
https://github.com/xxx/project

本地路径：
/home/user/projects/project

项目类型：
Deep Learning / Machine Learning

环境管理方式：
Conda

环境名称：
project_env

Python 版本：
3.10

设备策略：
未检测到 NVIDIA GPU，已使用 CPU 版本 PyTorch

PyTorch：
2.x CPU

基础验收：
通过

运行准备检查：
检测到项目可能需要额外模型权重：
weights/best.pt

README 中检测到可能的下载说明：
请查看 Pretrained Models / Model Zoo 部分。

可能的运行命令：
1. python demo.py
2. python inference.py --config configs/demo.yaml

默认未运行项目代码。
你可以手动执行：

conda activate project_env
python demo.py
```

## 21. MVP 范围

第一版 MVP 必须实现：

1. 支持 GitHub/GitLab 链接和本地路径
2. 支持 Conda，venv 作为可选基础能力
3. 默认推荐 Conda
4. 默认新建环境
5. 支持 Windows/macOS/Linux
6. 支持项目类型识别
7. 支持 Python 版本识别
8. 支持无 GPU / NVIDIA GPU / Apple Silicon 的分支策略
9. 无 GPU 时默认 CPU 版 PyTorch
10. 支持 `requirements.txt` / `environment.yml` / `pyproject.toml`
11. 支持 PyTorch 特殊安装策略
12. 支持国内镜像源选项
13. 支持常见版本冲突识别和解释
14. 支持基础环境验证
15. 支持 README / demo / quickstart 命令提取
16. 支持权重 / 数据集 / 配置文件缺失提示
17. 默认 Level 2，不运行项目代码
18. 运行 demo 前必须用户确认
19. 保存日志和最终报告
20. 提供 `AGENTS.md`
21. 提供 Codex `SKILL.md`
22. 提供 Claude Code `SKILL.md`
23. 提供 Qoder rules
24. 提供 GitHub Copilot instructions
25. 保证核心 CLI 与 Agent 适配层解耦

暂不做：

1. 一键复现脚本
2. Dockerfile 自动生成
3. 完整 Poetry / Pipenv 支持
4. AMD ROCm 自动配置
5. 自动下载模型权重和数据集
6. 自动修复所有依赖冲突
7. GUI 图形界面

## 22. 推荐实现模块

```text
quick_env_setup/
├── cli.py
├── source_resolver.py
├── git_handler.py
├── system_detector.py
├── project_type_detector.py
├── env_manager.py
├── conda_manager.py
├── venv_manager.py
├── project_scanner.py
├── dependency_file_parser.py
├── python_version_resolver.py
├── device_detector.py
├── pytorch_resolver.py
├── mirror_manager.py
├── dependency_installer.py
├── conflict_analyzer.py
├── asset_detector.py
├── run_command_discoverer.py
├── validator.py
├── safety_policy.py
├── report_generator.py
├── agent_adapter.py
├── interactive_prompt.py
├── logger.py
└── utils.py
```

## 23. 推荐执行流程伪代码

```python
def main(args):
    source_info = resolve_source(args.source)

    if source_info.type == "git_url":
        check_git_available()
        clone_dir = ask_clone_dir_or_default(args.clone_dir)
        project_path = clone_repository(source_info.url, clone_dir)
    else:
        project_path = validate_local_path(source_info.path)

    system_info = detect_system_info()

    project_info = scan_project(project_path)
    project_type = detect_project_type(project_info)

    env_manager = choose_env_manager(
        user_choice=args.env_manager,
        project_type=project_type,
        default="conda"
    )

    python_version = resolve_python_version(project_info)
    python_version = ask_or_confirm_python_version(python_version)

    env_name = ask_env_name(generate_recommended_env_name(project_path))
    env_name = handle_existing_env(env_name, env_manager)

    device_info = detect_device(system_info)

    pytorch_strategy = resolve_pytorch_strategy(
        project_info=project_info,
        project_type=project_type,
        device_info=device_info,
        cpu_only=args.cpu_only
    )

    mirror_config = configure_mirror_if_needed(
        use_china_mirror=args.use_china_mirror,
        mirror=args.mirror
    )

    install_plan = build_install_plan(
        project_path=project_path,
        env_manager=env_manager,
        env_name=env_name,
        python_version=python_version,
        project_info=project_info,
        project_type=project_type,
        device_info=device_info,
        pytorch_strategy=pytorch_strategy,
        mirror_config=mirror_config,
        safety_level=args.level
    )

    if args.dry_run:
        print_install_plan(install_plan)
        save_install_plan(install_plan)
        return

    enforce_safety_policy(install_plan)

    install_result = execute_install_plan(install_plan)

    if not install_result.success:
        conflict_report = analyze_install_error(install_result.logs)
        print_conflict_report(conflict_report)
        save_logs()
        return

    validation_result = validate_environment(
        env_manager=env_manager,
        env_name=env_name,
        pytorch_strategy=pytorch_strategy
    )

    run_candidates = discover_run_commands(project_path)

    missing_assets = detect_missing_assets(
        project_path=project_path,
        run_candidates=run_candidates
    )

    if args.level == 3 or args.run_demo:
        confirm_run_demo()
        demo_result = run_demo_with_timeout(
            command=select_demo_command(run_candidates),
            timeout=args.timeout
        )
    else:
        demo_result = None

    generate_final_report(
        source_info=source_info,
        project_path=project_path,
        project_type=project_type,
        env_manager=env_manager,
        env_name=env_name,
        python_version=python_version,
        device_info=device_info,
        pytorch_strategy=pytorch_strategy,
        validation_result=validation_result,
        run_candidates=run_candidates,
        missing_assets=missing_assets,
        demo_result=demo_result
    )
```

## 24. 给 Codex 的规划任务

你可以直接把下面这段发给 Codex：

```text
请根据 Quick Python Environment Setup v4 需求文档，帮我规划并实现这个项目。

要求：

1. 先不要直接写全部代码。
2. 先阅读需求文档，给出整体技术方案。
3. 给出推荐项目结构。
4. 给出 MVP 开发阶段划分。
5. 给出每个模块的职责。
6. 给出 CLI 参数设计。
7. 给出安全策略设计。
8. 给出 Agent 兼容设计，包括：
   - AGENTS.md
   - Codex SKILL.md
   - Claude Code SKILL.md
   - Qoder rules
   - GitHub Copilot instructions
9. 核心逻辑必须与具体 Agent 解耦。
10. 默认安全等级为 Level 2：安装依赖，但不运行项目代码。
11. 运行 demo、删除环境、执行 sudo 都必须用户确认。
12. 支持 GitHub/GitLab 链接和本地路径。
13. 默认推荐 Conda，但提供 venv 选项。
14. 支持项目类型识别。
15. 支持无 GPU / NVIDIA GPU / Apple Silicon 的设备分支。
16. 无 GPU 时安装 CPU 版 PyTorch。
17. 有 NVIDIA GPU 时再检测 CUDA。
18. 支持 PyTorch 特殊安装策略。
19. 支持国内镜像源选项。
20. 支持依赖版本冲突诊断。
21. 支持权重 / 数据集 / 配置文件缺失提示。
22. 输出完整日志和最终报告。

请先输出项目规划，不要一次性生成所有代码。
```

## 25. 最终总结

这个项目现在应该被定义成：

> 一个跨平台、跨 Agent、面向新手的 Python 开源项目环境配置工具。

它的关键不是“自动安装依赖”，而是这几个能力：

1. 能理解项目来源：Git 链接或本地路径
2. 能理解项目类型：深度学习 / Web / Notebook / 普通包
3. 能选择合适环境：Conda 或 venv
4. 能判断设备：CPU / NVIDIA CUDA / Apple MPS
5. 能处理 PyTorch：避免装错 CPU 或 CUDA 版本
6. 能诊断依赖冲突：而不是只输出报错
7. 能识别运行准备：权重、数据集、配置文件
8. 能保护用户安全：默认不运行项目代码
9. 能适配主流 Agent：Codex、Claude Code、Qoder、Copilot
10. 能通过 CLI 作为统一入口，避免绑定单一平台

这版已经可以作为一个比较完整的 Codex 规划输入了。
