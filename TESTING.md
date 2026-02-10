# 本地测试指南

本项目包含一个 Home Assistant 自定义组件。为了在不启动 Home Assistant 的情况下测试核心逻辑，你可以使用以下方法。

## 1. 环境准备

确保你已经安装了 Python 3。

```bash
python --version
```

## 2. 运行核心逻辑测试

我们提供了一个测试脚本 `tests/test_local.py`，可以直接运行它来验证节假日获取逻辑是否正常。

在项目根目录下运行：

```bash
python tests/test_local.py
```

或者直接运行引擎模块：

```bash
python custom_components/jdm_holiday/holiday_engine.py
```

## 3. 在 Home Assistant 中测试

如果你本地安装了 Home Assistant，可以通过以下步骤进行集成测试：

1.  找到你的 Home Assistant 配置目录（通常在 `%APPDATA%\.homeassistant` 或 `config` 目录）。
2.  将本项目中的 `custom_components/jdm_holiday` 文件夹完整复制到 Home Assistant 配置目录下的 `custom_components/` 中。
3.  修改 Home Assistant 的 `configuration.yaml`，添加：
    ```yaml
    jdm_holiday:
    ```
4.  重启 Home Assistant。
5.  在“开发者工具” -> “状态”中查找 `sensor.nearest_holiday_info` 或 `sensor.today_holiday_type` 等实体。

## 常见问题

- **数据获取失败**：检查网络连接，部分 API 可能需要特定的网络环境。
- **依赖缺失**：核心逻辑主要依赖 `requests`，Home Assistant 环境通常已包含。如果本地运行报错，请安装：`pip install requests`。
