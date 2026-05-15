from __future__ import annotations

from pathlib import Path

from quick_env_setup.asset_detector import detect_missing_assets
from quick_env_setup.project_scanner import scan_project


def test_detect_missing_assets_finds_weights_data_and_env_hints(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "README.md").write_text(
        "\n".join(
            [
                "# Demo",
                "Download model weights from https://example.com/model.pt before running.",
                "Place data/train.csv under the data directory.",
                "Create a .env file with API_TOKEN=demo before starting.",
            ]
        ),
        encoding="utf-8",
    )
    (project_root / "infer.py").write_text(
        "\n".join(
            [
                'MODEL_PATH = "weights/model.pt"',
                'DATA_PATH = "data/train.csv"',
                'CONFIG_PATH = "configs/infer.yaml"',
                'ENV_FILE = ".env"',
            ]
        ),
        encoding="utf-8",
    )

    findings = detect_missing_assets(scan_project(project_root))

    assert [finding.category for finding in findings] == [
        "config",
        "data",
        "env",
        "weights",
    ]
    assert findings[0].asset_path == "configs/infer.yaml"
    assert findings[1].asset_path == "data/train.csv"
    assert findings[2].asset_path == ".env"
    assert findings[3].asset_path == "weights/model.pt"
    assert findings[1].download_hints == ["Place data/train.csv under the data directory."]
    assert findings[2].download_hints == ["Create a .env file with API_TOKEN=demo before starting."]
    assert findings[3].download_hints == [
        "Download model weights from https://example.com/model.pt before running."
    ]


def test_detect_missing_assets_ignores_present_files(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    (project_root / "weights").mkdir(parents=True)
    (project_root / "configs").mkdir(parents=True)
    (project_root / "README.md").write_text(
        "Download model weights from https://example.com/model.pt before running.\n",
        encoding="utf-8",
    )
    (project_root / "serve.py").write_text(
        "\n".join(
            [
                'MODEL_PATH = "weights/model.pt"',
                'CONFIG_PATH = "configs/serve.yaml"',
            ]
        ),
        encoding="utf-8",
    )
    (project_root / "weights" / "model.pt").write_text("", encoding="utf-8")
    (project_root / "configs" / "serve.yaml").write_text("demo: true\n", encoding="utf-8")

    findings = detect_missing_assets(scan_project(project_root))

    assert findings == []


def test_detect_missing_assets_includes_root_level_files(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "README.md").write_text(
        "Download model.pt from https://example.com/model.pt before running.\n",
        encoding="utf-8",
    )
    (project_root / "predict.py").write_text(
        "\n".join(
            [
                'MODEL_PATH = "model.pt"',
                'CONFIG_PATH = "config.yaml"',
                'DATA_PATH = "data.csv"',
            ]
        ),
        encoding="utf-8",
    )

    findings = detect_missing_assets(scan_project(project_root))

    assert [(finding.category, finding.asset_path) for finding in findings] == [
        ("config", "config.yaml"),
        ("data", "data.csv"),
        ("weights", "model.pt"),
    ]


def test_detect_missing_assets_ignores_readme_and_notebook_noise(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    (project_root / "notebooks").mkdir(parents=True)
    (project_root / "README.md").write_text(
        "\n".join(
            [
                "# Demo",
                "Example config.yaml and data.csv files are described below.",
                "Download assets from https://example.com/assets.zip if needed.",
            ]
        ),
        encoding="utf-8",
    )
    (project_root / "notebooks" / "analysis.ipynb").write_text(
        '{"cells":[{"source":["load model.pt and config.yaml for an example"]}],"metadata":{}}',
        encoding="utf-8",
    )
    (project_root / "runner.py").write_text("print('no asset references here')\n", encoding="utf-8")

    findings = detect_missing_assets(scan_project(project_root))

    assert findings == []


def test_detect_missing_assets_ignores_absolute_host_paths(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "infer.py").write_text(
        'MODEL_PATH = "/models/model.pt"\nCONFIG_PATH = "/configs/demo.yaml"\n',
        encoding="utf-8",
    )

    findings = detect_missing_assets(scan_project(project_root))

    assert findings == []


def test_detect_missing_assets_ignores_windows_absolute_host_paths(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "infer.py").write_text(
        'MODEL_PATH = "C:\\\\models\\\\model.pt"\nCONFIG_PATH = "D:\\\\configs\\\\demo.yaml"\n',
        encoding="utf-8",
    )

    findings = detect_missing_assets(scan_project(project_root))

    assert findings == []


def test_detect_missing_assets_respects_referencing_file_relative_paths(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    module_dir = project_root / "tools"
    module_dir.mkdir(parents=True)
    (module_dir / "config.yaml").write_text("demo: true\n", encoding="utf-8")
    (module_dir / "serve.py").write_text('CONFIG_PATH = "config.yaml"\n', encoding="utf-8")

    findings = detect_missing_assets(scan_project(project_root))

    assert findings == []
