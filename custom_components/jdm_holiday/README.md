# JDM Holiday Custom Component

这是一个功能强大的 Home Assistant 自定义组件，用于获取中国节假日信息、农历、节气以及自定义纪念日管理。

## 核心功能

1.  **法定节假日查询**：获取最近的法定节假日安排（如春节、国庆节等）。
2.  **综合节日查询**：获取最近的任何节日，包括公历节日（如情人节）、农历节日（如重阳节）和自定义纪念日。
3.  **日期类型判断**：精准判断今天/明天是工作日、休息日还是节假日。
4.  **自定义纪念日**：支持公历、农历的多种配置方式（每年一次、一次性），并支持倒计时。
5.  **本地缓存**：自动从云端更新数据并缓存到本地 SQLite 数据库，无网也能查询已缓存数据。

## 安装

1.  将 `jdm_holiday` 文件夹复制到你的 Home Assistant 配置目录下的 `custom_components` 文件夹中。
2.  重启 Home Assistant。

## 配置

在 `configuration.yaml` 中添加以下配置。你可以通过 `anniversaries` 字段定义自己的纪念日。

```yaml
jdm_holiday:
  anniversaries:
    # 公历每年 (MM-DD)
    "01-01": "元旦"
    "10-01": "国庆节"
    
    # 公历一次性 (YYYY-MM-DD)
    "2026-05-20": "特定的日子"
    
    # 农历每年 (nMM-DD) - 前缀 n 表示农历
    "n01-01": "春节"
    "n08-15": "中秋节"
    "n05-05": "端午节"
    
    # 农历一次性 (nYYYY-MM-DD)
    "n2026-01-01": "2026农历新年"
```

## 实体说明

组件加载后，将创建一个主传感器实体 `sensor.jdm_holiday`，其属性包含了所有详细信息。

### 主传感器: `sensor.jdm_holiday`

状态值：`正常`

#### 属性列表 (Attributes)

| 属性名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `today` | Object | 今天的详细信息，包含 `status` (工作日/休息日/节假日), `detail` (农历/宜忌/节日), `anniversaries` (今日纪念日) |
| `tomorrow` | Object | 明天的详细信息，结构同上 |
| `nearest_info` | String | 最近法定节假日的文本描述（例如：10/01-10/07 放假 共7天...） |
| `nearest_holiday` | Object | **最近法定节假日**对象，包含日期、名称、天数差等（仅包含放假的节日） |
| `nearest_festival` | Object | **最近综合节日**对象，包含法定节日、公历/农历节日、自定义纪念日（谁最近显示谁） |
| `anniversaries_future` | List | 未来纪念日列表（含倒计时天数），按时间排序 |

### 二进制传感器 (Binary Sensors)

- `binary_sensor.is_holiday_today`: 今天是否为节假日/休息日（On = 休息/节假日, Off = 工作日）。
- `binary_sensor.is_holiday_tomorrow`: 明天是否为节假日/休息日。
- `binary_sensor.is_workday_today`: 今天是否为工作日（On = 工作日, Off = 休息/节假日）。

## 开发者文档 (Holiday Engine)

核心逻辑位于 `holiday_engine.py` 的 `Holiday` 类中。

### 主要方法

#### 1. `get_nearest_statutory_holiday(min_days=0, max_days=60)`
获取最近的 **法定节假日**（国家规定的放假节日）。
- **返回**: `Dict` 或 `None`
- **包含**: `date` (日期对象), `name` (节日名称), `days_diff` (天数差), `full_info` (完整信息)

#### 2. `get_nearest_festival(min_days=0, max_days=60)`
获取最近的 **综合节日**。优先级顺序：自定义纪念日 > 法定节假日 > 公历/农历节日。
- **返回**: `Dict` 或 `None`
- **用途**: 适用于“下一个是什么节”的场景，不一定放假。

#### 3. `is_holiday(date)`
判断指定日期是工作日、休息日还是节假日。
- **返回**: 字符串 ("工作日", "休息日", "节假日")

#### 4. `get_day_detail(date)`
获取指定日期的详细信息，包括农历、黄历（宜忌）、节日列表等。
- **返回**: `Dict`
- **字段**: `solar_festival`, `lunar_festival`, `festival`, `nongli`, `jieqi`, `suit`, `avoid` 等。

#### 5. `get_future_anniversaries(date)`
获取从指定日期开始的未来自定义纪念日列表。
- **支持**: 自动计算农历日期的公历对应日，并支持跨年计算。

## 数据来源

- 节假日数据来自第三方 API 及本地计算。
- 数据存储在 `data.db` (SQLite) 中，支持离线访问。
