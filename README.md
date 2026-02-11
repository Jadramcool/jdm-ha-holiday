# JDM Holiday - Home Assistant 中国节假日集成

这是一个专为 Home Assistant 设计的自定义组件，用于获取中国法定节假日、农历、节气以及管理自定义纪念日。

## ✨ 主要功能

- **法定节假日查询**：自动获取并缓存国务院发布的节假日安排（春节、国庆等）。
- **精准状态判断**：提供传感器实体，精准判断“今天/明天”是工作日、休息日还是节假日（支持调休识别）。
- **综合节日信息**：包含公历节日、农历节日（如中秋、端午）及二十四节气。
- **自定义纪念日**：支持配置公历或农历的生日、纪念日，并显示倒计时。
- **离线支持**：数据缓存于本地 SQLite 数据库，断网情况下仍可查询已缓存数据。

## 🚀 安装方法

### 方式一：使用 HACS 安装（推荐）

如果您的 Home Assistant 已安装 HACS (Home Assistant Community Store)：

1.  打开 HACS -> **集成 (Integrations)**。
2.  点击右上角的三个点图标 -> **自定义存储库 (Custom repositories)**。
3.  在 "存储库 (Repository)" 栏输入本项目的 GitHub 地址。
4.  在 "类别 (Category)" 栏选择 **Integration**。
5.  点击 **添加 (Add)**。
6.  在 HACS 列表中找到 **JDM Holiday** 并点击下载。
7.  下载完成后，**重启 Home Assistant**。

### 方式二：手动安装

1.  下载本项目源代码。
2.  找到项目中的 `custom_components/jdm_holiday` 文件夹。
3.  将该文件夹完整的复制到您 Home Assistant 配置目录下的 `custom_components` 文件夹中。
    - 路径应为：`/config/custom_components/jdm_holiday`
4.  **重启 Home Assistant**。

## ⚙️ 配置说明

安装完成后，需要在 `configuration.yaml` 文件中添加配置才能启用组件。

```yaml
# configuration.yaml

jdm_holiday:
  anniversaries:
    # --- 公历配置 ---
    "01-01": "元旦" # 每年公历 1月1日
    "10-01": "国庆节" # 每年公历 10月1日
    "2026-05-20": "结婚纪念日" # 仅 2026年5月20日 (一次性)

    # --- 农历配置 (前缀 n) ---
    "n01-01": "春节" # 每年农历 正月初一
    "n08-15": "中秋节" # 每年农历 八月十五
    "n05-05": "端午节" # 每年农历 五月初五
    "n1990-01-01": "生日" # 仅 1990年农历正月初一 (通常用于计算虚岁或特定纪念，但在本组件中主要用于每年循环匹配)
```

**注意**：修改配置后需要重启 Home Assistant 才能生效。

## 📊 实体说明

组件启动后，会创建以下实体：

### 1. 主传感器 (`sensor.jdm_holiday`)

这是一个包含丰富属性的传感器，状态通常为 `正常`。所有详细数据都存储在其 **属性 (Attributes)** 中，方便在 Lovelace 卡片或自动化中使用。

- `today`: 今日详情（含农历、宜忌、状态）。
- `tomorrow`: 明日详情。
- `nearest_holiday`: 最近的一个法定节假日（如“春节”）。
- `nearest_festival`: 最近的一个综合节日（含纪念日）。
- `nearest_jieqi`: 最近的一个节气。
- `anniversaries_future`: 未来纪念日列表（带倒计时）。

### 2. 二元传感器 (Binary Sensors)

用于自动化触发（On = 是，Off = 否）。

- `binary_sensor.is_holiday_today`: **今天是否放假**（包含周末和法定节假日）。
- `binary_sensor.is_holiday_tomorrow`: **明天是否放假**。

---

**数据来源说明**：本组件使用的节假日数据来源于第三方 API 及本地算法计算，并定期自动更新。

