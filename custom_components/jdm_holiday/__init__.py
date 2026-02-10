"""JDM Holiday 组件初始化文件。

该文件负责组件的初始化过程，包括加载核心引擎（Holiday Engine）
以及注册相应的传感器平台（Sensor 和 Binary Sensor）。
"""

import logging
import voluptuous as vol

from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .holiday_engine import Holiday

# 获取当前模块的日志记录器
_LOGGER = logging.getLogger(__name__)

# 定义配置架构（Configuration Schema）
# 目前该组件配置为空字典，即不需要在 configuration.yaml 中配置额外参数
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema({})
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """设置 JDM Holiday 组件。
    
    该函数在 Home Assistant 启动时被调用。它负责：
    1. 初始化共享数据存储区域。
    2. 在执行器（Executor）中初始化 Holiday 引擎（涉及文件IO）。
    3. 加载传感器平台。
    
    Args:
        hass: Home Assistant 核心实例。
        config: 用户配置内容。
        
    Returns:
        bool: 如果初始化成功返回 True，否则返回 False。
    """
    # 确保 hass.data 中有我们的 DOMAIN 键，用于存储组件全局数据
    hass.data.setdefault(DOMAIN, {})

    _LOGGER.info("正在初始化 JDM Holiday 组件...")

    # 初始化 Holiday 引擎
    # 我们使用 async_add_executor_job 将同步的 Holiday 类初始化过程放入线程池中执行
    # 这是因为 Holiday.__init__ 涉及文件读取（sqlite, json）和可能的网络请求（如果本地无数据）
    # 避免阻塞 Home Assistant 的主事件循环
    try:
        holiday_engine = await hass.async_add_executor_job(Holiday)
        # 将初始化的引擎实例存储在 hass.data 中，以便其他平台（sensor, binary_sensor）调用
        hass.data[DOMAIN]["engine"] = holiday_engine
    except Exception as e:
        _LOGGER.error("Holiday 引擎初始化失败: %s", e)
        return False

    # 注册传感器（sensor）和二元传感器（binary_sensor）平台
    # 这里使用 discovery.async_load_platform 动态加载平台
    # 这意味着只要 configuration.yaml 中有 `jdm_holiday:`，这些平台就会自动加载
    # 而不需要用户显式配置 `sensor: - platform: jdm_holiday`
    
    # 加载 sensor 平台 (提供详细信息的传感器)
    hass.async_create_task(
        hass.helpers.discovery.async_load_platform(hass, "sensor", DOMAIN, {}, config)
    )
    # 加载 binary_sensor 平台 (提供 是/否 状态的传感器)
    hass.async_create_task(
        hass.helpers.discovery.async_load_platform(hass, "binary_sensor", DOMAIN, {}, config)
    )

    return True
