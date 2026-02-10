# JDM Holiday Custom Component

这是一个基于 Home Assistant 的自定义组件，用于获取中国节假日信息。

## 功能

- 获取最近的节假日安排。
- 判断今天/明天是否为节假日、休息日或工作日。
- 自动从云端更新节假日数据并缓存到本地数据库。

## 安装

1. 将 `jdm_holiday` 文件夹复制到你的 Home Assistant 配置目录下的 `custom_components` 文件夹中。
2. 重启 Home Assistant。

## 配置

在 `configuration.yaml` 中添加以下内容：

```yaml
jdm_holiday:
```

## 实体

组件加载后，将创建以下实体：

- `sensor.nearest_holiday_info`: 最近的节假日信息（例如：10/01(周二)-10/07 放假 共7天...）。
- `sensor.today_holiday_type`: 今天的日期类型（工作日/休息日/节假日）。
- `sensor.tomorrow_holiday_type`: 明天的日期类型。
- `binary_sensor.is_holiday_today`: 今天是否为节假日/休息日（On = 休息/节假日, Off = 工作日）。
- `binary_sensor.is_holiday_tomorrow`: 明天是否为节假日/休息日。

## 数据来源

- 节假日数据来自 `http://tool.bitefu.net/jiari/` 和 `http://d1.weather.com.cn/calendar_new/`。
- 数据会缓存到组件目录下的 `data.db` (SQLite) 和 `holiday.json`。
