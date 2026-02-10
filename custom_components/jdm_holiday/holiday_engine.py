#!/usr/local/bin/python3
# coding=utf-8
"""
Holiday 模块

核心逻辑：
1. 从服务端（API）获取节假日数据。
2. 将数据存入本地 JSON 文件进行缓存。
3. 提供查询接口，判断特定日期是否为节假日，或获取最近的节假日安排。
"""

import datetime
import json
import logging
import os
import sqlite3
import time
from datetime import datetime as datetime_class
from datetime import timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter

_LOGGER = logging.getLogger(__name__)

# 使用当前文件所在目录作为数据存储目录
DATA_DIR = os.path.dirname(os.path.realpath(__file__))
# JSON 缓存文件路径
HOLIDAY_DATA_FILE = os.path.join(DATA_DIR, "holiday.json")
# SQLite 数据库路径
HOLIDAY_DB_FILE = os.path.join(DATA_DIR, "data.db")
# API 地址
API_URL = "http://tool.bitefu.net/jiari/"


class HolidayDB:
    """简化的 SQLite 存储封装，用于数据备份。"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_table()

    def _get_conn(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_table(self):
        """初始化全量数据表"""
        try:
            with self._get_conn() as conn:
                # 1. 创建元数据表
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS meta_info (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                """
                )

                # 2. 创建详细数据表 (字段一一对应)
                # day: 20260201
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS holiday_detail (
                        day TEXT PRIMARY KEY,
                        status INTEGER,
                        type INTEGER,
                        typename TEXT,
                        unixtime INTEGER,
                        yearname TEXT,
                        nonglicn TEXT,
                        nongli TEXT,
                        shengxiao TEXT,
                        jieqi TEXT,
                        weekcn TEXT,
                        week1 TEXT,
                        week2 TEXT,
                        week3 TEXT,
                        daynum INTEGER,
                        weeknum INTEGER,
                        avoid TEXT,
                        suit TEXT
                    )
                """
                )
                conn.commit()
        except Exception as e:
            _LOGGER.error("初始化数据库失败: %s", e)

    def save_full(self, data_list: List[Dict[str, Any]], update_time: str):
        """保存全量数据列表到数据库"""
        try:
            with self._get_conn() as conn:
                # 1. 保存更新时间
                conn.execute(
                    "REPLACE INTO meta_info (key, value) VALUES (?, ?)",
                    ("update_time", update_time),
                )

                # 2. 保存详细数据
                for item in data_list:
                    conn.execute(
                        """
                        REPLACE INTO holiday_detail (
                            day, status, type, typename, unixtime, yearname, 
                            nonglicn, nongli, shengxiao, jieqi, weekcn, 
                            week1, week2, week3, daynum, weeknum, avoid, suit
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            item.get("day"),
                            item.get("status"),
                            item.get("type"),
                            item.get("typename"),
                            item.get("unixtime"),
                            item.get("yearname"),
                            item.get("nonglicn"),
                            item.get("nongli"),
                            item.get("shengxiao"),
                            item.get("jieqi"),
                            item.get("weekcn"),
                            item.get("week1"),
                            item.get("week2"),
                            item.get("week3"),
                            item.get("daynum"),
                            item.get("weeknum"),
                            item.get("avoid"),
                            item.get("suit"),
                        ),
                    )
                conn.commit()
        except Exception as e:
            _LOGGER.error("备份数据到数据库失败: %s", e)

    def load(self) -> Dict[str, Any]:
        """从数据库加载数据（重构为内存使用的格式）"""
        data = {}
        try:
            if not os.path.exists(self.db_path):
                return data

            with self._get_conn() as conn:
                conn.row_factory = sqlite3.Row  # 允许通过列名访问

                # 1. 加载更新时间
                cursor = conn.execute(
                    "SELECT value FROM meta_info WHERE key='update_time'"
                )
                row = cursor.fetchone()
                if row:
                    data["update_time"] = row[0]

                # 2. 加载节假日数据，重构为 {year: {mmdd: full_item_dict}} 格式
                cursor = conn.execute("SELECT * FROM holiday_detail")
                for row in cursor:
                    item = dict(row)  # 转换为字典
                    day_str = item.get("day")
                    if not day_str or len(day_str) != 8:
                        continue

                    year = day_str[:4]
                    date_short = day_str[4:]  # MMDD

                    if year not in data:
                        data[year] = {}

                    # 存储完整数据对象
                    data[year][date_short] = item

        except Exception as e:
            _LOGGER.error("从数据库加载数据失败: %s", e)
        return data


class Holiday:
    """节假日核心逻辑类。

    提供公共方法：
    - is_holiday(date): 判断某天是否为节日。
    - is_holiday_today(): 判断今天是否为节假日。
    - nearest_holiday_info(): 获取最近的节假日安排信息。
    """

    # 状态码映射
    STATUS_MAP = {0: "工作日", 1: "休息日", 2: "节假日"}

    def __init__(self):
        """初始化 Holiday 类。"""
        self._holiday_json: Dict[str, Any] = {}
        self.db = HolidayDB(HOLIDAY_DB_FILE)  # 初始化数据库备份

        self.session = requests.Session()
        # 设置重试策略和 Headers
        adapter = HTTPAdapter(max_retries=3)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )

        # 初始化时尝试从本地磁盘加载缓存的节假日数据
        self.get_holidays_from_disk()

    @classmethod
    def day(cls, n: int) -> datetime.datetime:
        """获取相对于今天的第 n 天的日期对象。

        Args:
            n: 天数偏移量。1 表示明天，-1 表示昨天。

        Returns:
            datetime: 计算后的日期对象（UTC+8）。
        """
        # 使用 timezone-aware 对象获取 UTC 时间，然后转换为北京时间
        utc_now = datetime_class.now(timezone.utc)
        return utc_now + timedelta(hours=8) + timedelta(hours=n * 24)

    @classmethod
    def today(cls) -> datetime.datetime:
        """获取今天的日期对象。"""
        return Holiday.day(0)

    @classmethod
    def tomorrow(cls) -> datetime.datetime:
        """获取明天的日期对象。"""
        return Holiday.day(1)

    def _collect_holiday_candidates(
        self, today: datetime.datetime
    ) -> List[datetime.datetime]:
        """收集所有符合条件的节假日候选日期。

        Args:
            today: 今天的日期对象

        Returns:
            List[datetime]: 排序后的节假日日期列表
        """
        current_year = str(today.year)
        next_year = str(today.year + 1)
        target_years = [y for y in self._holiday_json if y in (current_year, next_year)]
        candidates = []

        # 将 timezone-aware 的 today 转换为 naive datetime 以便比较
        if today.tzinfo is not None:
            today_naive = today.replace(tzinfo=None)
        else:
            today_naive = today

        for y in target_years:
            dates = self._holiday_json[y]
            if not isinstance(dates, dict):
                continue
            for m_d, item in dates.items():
                if self._is_holiday_item(item):
                    date = self._parse_holiday_date(item, y, m_d)
                    if date and (date - today_naive).days >= 0:
                        candidates.append(date)

        candidates.sort()
        return candidates

    def _is_holiday_item(self, item: Any) -> bool:
        """判断是否为法定节假日。

        Args:
            item: 节假日数据项

        Returns:
            bool: 是否为法定节假日
        """
        type_val = 0
        if isinstance(item, dict):
            type_val = int(item.get("type", 0))
        else:
            type_val = int(item)
        return type_val == 2

    def _parse_holiday_date(
        self, item: Any, year: str, month_day: str
    ) -> Optional[datetime.datetime]:
        """解析节假日日期。

        Args:
            item: 节假日数据项
            year: 年份字符串
            month_day: 月日字符串 (MMDD)

        Returns:
            Optional[datetime]: 解析后的日期对象，失败返回 None
        """
        try:
            if isinstance(item, dict) and "day" in item:
                d_str = item["day"]
                return datetime_class.strptime(d_str, "%Y%m%d")
            d_str = "{}-{}-{}".format(year, month_day[0:2], month_day[2:])
            return datetime_class.strptime(d_str, "%Y-%m-%d")
        except ValueError:
            return None

    def nearest_holiday_info(self, min_days: int = 0, max_days: int = 60) -> str:
        """计算并获取最近一次节假日的详细安排。

        Args:
            min_days: 最小查找天数范围。
            max_days: 最大查找天数范围。

        Returns:
            str: 格式化后的节假日信息文本。
        """
        today = Holiday.today()
        if not self._holiday_json:
            self.get_holidays_from_server()

        candidates = self._collect_holiday_candidates(today)

        # 将 timezone-aware 的 today 转换为 naive datetime 以便比较
        if today.tzinfo is not None:
            today_naive = today.replace(tzinfo=None)
        else:
            today_naive = today

        for date in candidates:
            days_diff = (date - today_naive).days
            if not (min_days <= days_diff <= max_days):
                continue

            start, end = self._find_holiday_range(date)
            before_workdays = self._find_surrounding_workdays(start, look_back=True)
            after_workdays = self._find_surrounding_workdays(end, look_back=False)

            return self._format_holiday_info(
                today_naive, start, end, before_workdays, after_workdays
            )

        return "无最近节假日信息"

    def get_nearest_holiday(
        self, min_days: int = 0, max_days: int = 60
    ) -> Optional[Dict[str, Any]]:
        """获取最近一次节假日的详细信息对象。

        Args:
            min_days: 最小查找天数范围。
            max_days: 最大查找天数范围。

        Returns:
            Optional[Dict]: 包含节假日详细信息的字典，无结果时返回 None。
        """
        today = Holiday.today()
        if not self._holiday_json:
            self.get_holidays_from_server()

        candidates = self._collect_holiday_candidates(today)

        # 将 timezone-aware 的 today 转换为 naive datetime 以便比较
        if today.tzinfo is not None:
            today_naive = today.replace(tzinfo=None)
        else:
            today_naive = today

        for date in candidates:
            days_diff = (date - today_naive).days
            if not (min_days <= days_diff <= max_days):
                continue

            # 查找节假日的完整信息
            year = str(date.year)
            month_day = date.strftime("%m%d")
            if year in self._holiday_json and month_day in self._holiday_json[year]:
                holiday_item = self._holiday_json[year][month_day]
                return {
                    "date": date,
                    "name": holiday_item.get("typename", "未知节假日"),
                    "days_diff": days_diff,
                    "full_info": holiday_item,
                }

        return None

    def _find_holiday_range(
        self, date: datetime.datetime
    ) -> Tuple[datetime.datetime, datetime.datetime]:
        """查找连续假期的开始和结束日期。"""
        start = date
        end = date
        # 向前查找
        while self.is_holiday_status(start - timedelta(days=1)) != 0:
            start -= timedelta(days=1)
        # 向后查找
        while self.is_holiday_status(end + timedelta(days=1)) != 0:
            end += timedelta(days=1)
        return start, end

    def _find_surrounding_workdays(
        self, date: datetime.datetime, look_back: bool = True
    ) -> List[Dict[str, Any]]:
        """查找节假日周边连续的工作日（调休）。"""
        workdays = []
        current = date - timedelta(days=1) if look_back else date + timedelta(days=1)
        step = -1 if look_back else 1

        while self.is_holiday_status(current) == 0:
            # 判断是否为调休（即本该是周末但变成了工作日）
            is_weekend = current.weekday() in (5, 6)
            # 记录工作日信息
            workdays.append({"date": current, "invert": is_weekend})
            current += timedelta(days=step)

        if look_back:
            workdays.reverse()
        return workdays

    def _format_holiday_info(
        self,
        today: datetime.datetime,
        start: datetime.datetime,
        end: datetime.datetime,
        before_workdays: List[Dict],
        after_workdays: List[Dict],
    ) -> str:
        """格式化节假日信息字符串。"""

        def format_workdays(workdays):
            res = ""
            for item in workdays:
                d = item["date"]
                res += " {}/{}".format(d.month, d.day)
                if item["invert"]:
                    res += "(串休日，周{})".format(d.weekday() + 1)
            return res

        before_str = format_workdays(before_workdays)
        after_str = format_workdays(after_workdays)

        # 计算各种天数
        total_days = (end - start).days + 1

        # 修正逻辑：直接用工作日列表长度来表示连续工作天数
        days_worked_before = len(before_workdays)
        days_worked_after = len(after_workdays)

        info = (
            "{}(周{})-{} 放假 共{}天\n据上一次休息{}天 {} \n据下一次休息{}天 {}".format(
                start.strftime("%m/%d"),
                start.weekday() + 1,
                end.strftime("%m/%d"),
                total_days,
                days_worked_before,
                before_str,
                days_worked_after,
                after_str,
            )
        )
        return info

    def get_holidays_from_disk(self) -> None:
        """从本地加载节假日数据。

        优先从 SQLite 数据库加载，如果数据库为空，再尝试从 JSON 文件加载。
        """
        loaded = False

        # 1. 优先尝试从数据库加载
        try:
            db_data = self.db.load()
            if db_data:
                self._holiday_json = db_data
                loaded = True
                _LOGGER.debug("从 SQLite 数据库加载数据成功")
        except Exception as e:
            _LOGGER.error("从 SQLite 数据库加载数据失败: %s", e)

        # 2. 如果数据库没有数据，尝试从 JSON 文件加载
        if not loaded:
            try:
                if os.path.exists(HOLIDAY_DATA_FILE):
                    with open(HOLIDAY_DATA_FILE, "r", encoding="utf-8") as f:
                        self._holiday_json = json.load(f)
                        loaded = True
                        _LOGGER.info("从 JSON 文件加载数据成功")
            except Exception as e:
                _LOGGER.error("加载本地 JSON 数据失败: %s", e)
                self._holiday_json = {}

    def get_holidays_from_server(self, days: int = 15) -> None:
        """从服务器获取节假日数据。

        Args:
            days: 缓存有效期天数。
        """
        os.makedirs(os.path.dirname(HOLIDAY_DATA_FILE), exist_ok=True)

        # 检查是否需要更新
        last_update_str = self._holiday_json.get("update_time", "2020-01-01")
        try:
            last_update = datetime_class.strptime(last_update_str, "%Y-%m-%d")
        except ValueError:
            last_update = datetime_class(2020, 1, 1)

        today = Holiday.today()
        # 将 timezone-aware 的 today 转换为 naive datetime 以便比较
        if today.tzinfo is not None:
            today_naive = today.replace(tzinfo=None)
        else:
            today_naive = today
        interval = (today_naive - last_update).days

        # 检查是否包含当前年份的数据，如果没有数据，即使时间没过期也应该更新
        current_year_str = str(today.year)
        has_data = (
            current_year_str in self._holiday_json
            and self._holiday_json[current_year_str]
        )

        _LOGGER.debug(
            "距上次更新 %s 天, 阈值 %s 天, 是否有当前年份数据: %s",
            interval,
            days,
            has_data,
        )

        if interval <= days and days != 0 and has_data:
            _LOGGER.debug("无需更新")
            return

        # 执行更新
        _LOGGER.info("开始更新节假日数据(强制刷新)...")
        new_data = self._holiday_json.copy()
        update_time_str = today.strftime("%Y-%m-%d")
        new_data["update_time"] = update_time_str

        # 用于收集全量数据以便存入数据库
        full_data_items: List[Dict[str, Any]] = []

        # 获取当前月及未来 5 个月的数据
        for i in range(6):
            # 计算年月
            y, m = self._get_year_month(today, i)

            y_str = str(y)
            if y_str not in new_data:
                new_data[y_str] = {}

            # 获取数据，并填充 simple dict 和 full list
            self._fetch_month_data(y, m, new_data[y_str], full_data_items)
            time.sleep(0.5)  # 礼貌延时，避免触发API频率限制

        # 保存数据
        try:
            # 1. 保存到 JSON (仅包含简略信息，保持兼容)
            with open(HOLIDAY_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(new_data, f, ensure_ascii=False, indent=2)

            # 2. 备份到 SQLite (包含全量信息)
            self.db.save_full(full_data_items, update_time_str)

            self._holiday_json = new_data
            _LOGGER.info("节假日数据更新完成 (JSON + SQLite)")
        except Exception as e:
            _LOGGER.error("保存数据失败: %s", e)

    def _get_year_month(
        self, start_date: datetime.datetime, offset_month: int
    ) -> Tuple[int, int]:
        """计算偏移后的年月"""
        m = start_date.month + offset_month
        y = start_date.year
        while m > 12:
            m -= 12
            y += 1
        return y, m

    def _fetch_month_data(
        self,
        year: int,
        month: int,
        year_dict: Dict[str, Any],
        full_data_list: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """获取指定月份数据并填充到字典中。

        Args:
            year: 年份
            month: 月份
            year_dict: 用于内存使用的字典 {day: full_item_dict}
            full_data_list: 用于数据库存储的全量数据列表
        """
        d = "{}{:0>2d}".format(year, month)
        params = {"d": d, "info": 1}

        try:
            resp = self.session.get(API_URL, params=params, timeout=10)
            if resp.status_code != 200:
                _LOGGER.warning("API请求失败: %s", resp.status_code)
                return

            data = resp.json()
            if d not in data:
                return

            for day_key, item in data[d].items():
                try:
                    if not isinstance(item, dict):
                        continue

                    # 1. 基础校验逻辑
                    t = int(item.get("type", 0))
                    w = item.get("week", item.get("week2", 0))
                    try:
                        w = int(w)
                    except (ValueError, TypeError):
                        w = 0

                    # 确保 item 中包含 day 字段 (数据库和内存都可能需要)
                    if "day" not in item:
                        item["day"] = "{}{:0>2d}{:0>2d}".format(
                            year, month, int(day_key)
                        )

                    # 只要是 休息日(1)、节假日(2) 或 调休上班日(周末且type=0)
                    if t in (1, 2) or (t == 0 and w in (6, 7)):
                        # 修改：存储完整对象，保持 JSON 和 数据库 一致
                        year_dict[day_key] = item

                    # 2. 收集全量数据 (数据库用)
                    if full_data_list is not None:
                        full_data_list.append(item)

                except Exception as e:
                    _LOGGER.debug("解析日期 %s 失败: %s", day_key, e)

        except Exception as e:
            _LOGGER.error("获取 %s 数据失败: %s", d, e)

    def get_day_detail(self, date: datetime.datetime) -> Dict[str, Any]:
        """获取某天的完整详细信息（农历、宜忌等）。"""
        if not self._holiday_json:
            self.get_holidays_from_server()

        y_str = str(date.year)
        m_d_key = "{:0>2d}{:0>2d}".format(date.month, date.day)

        if y_str in self._holiday_json:
            if (
                isinstance(self._holiday_json[y_str], dict)
                and m_d_key in self._holiday_json[y_str]
            ):
                item = self._holiday_json[y_str][m_d_key]
                if isinstance(item, dict):
                    return item
        return {}

    def is_holiday_status(self, date: datetime.datetime) -> int:
        """获取某天的状态码。

        Returns:
            int: 0=工作日, 1=休息日/周末, 2=节假日
        """
        # 懒加载
        if not self._holiday_json:
            self.get_holidays_from_server()

        y_str = str(date.year)
        m_d_key = "{:0>2d}{:0>2d}".format(date.month, date.day)

        # 优先查表
        if y_str in self._holiday_json:
            if (
                isinstance(self._holiday_json[y_str], dict)
                and m_d_key in self._holiday_json[y_str]
            ):
                item = self._holiday_json[y_str][m_d_key]
                # 兼容处理：如果是字典，取type字段；如果是数字，直接返回
                if isinstance(item, dict):
                    return int(item.get("type", 0))
                return int(item)

        # 查不到则默认按星期判断
        if date.weekday() >= 5:  # 5=Sat, 6=Sun
            return 1
        return 0

    def is_holiday(self, date: datetime.datetime) -> str:
        """获取某天的状态描述文本。"""
        status = self.is_holiday_status(date)
        return self.STATUS_MAP.get(status, "未知")

    def is_holiday_today(self) -> str:
        """判断今天是否是节假日/休息日。"""
        return self.is_holiday(Holiday.today())

    def is_holiday_tomorrow(self) -> str:
        """判断明天是否是节假日/休息日。"""
        return self.is_holiday(Holiday.tomorrow())


if __name__ == "__main__":
    # 本地测试代码
    logging.basicConfig(level=logging.DEBUG)
    h = Holiday()

    # 强制更新数据（传入 days=0）
    # print("正在强制拉取最新数据...")
    # h.get_holidays_from_server(days=15)
    print(h.get_day_detail(datetime.datetime.now()))
    print("今天是否节假日:", h.is_holiday_today())
    print("明天是否节假日:", h.is_holiday_tomorrow())
    print("最近节假日信息:", h.nearest_holiday_info())
    print("最近节假日信息:", h.get_nearest_holiday())
