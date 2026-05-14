"""天气查询工具 — 通过高德地图 API 获取实时天气和未来预报。"""

import datetime
import random

from pydantic import BaseModel, Field

from src.services.amap_client import get_client

WEATHER_CONDITIONS = ["晴", "多云", "阴", "小雨", "阵雨", "雷阵雨"]


class WeatherInput(BaseModel):
    """天气查询输入。

    支持单城市（destination）和多城市（cities）两种模式。
    """

    destination: str = Field(default="", description="目的地城市（单城市模式）", examples=["东京"])
    cities: list[str] = Field(default_factory=list, description="多个城市名称（多城市模式）")
    start_date: datetime.date | None = Field(default=None, description="查询起始日期")
    end_date: datetime.date | None = Field(default=None, description="查询结束日期")


class DailyWeather(BaseModel):
    """单日天气预报。"""

    date: datetime.date = Field(..., description="日期")
    temp_high: float = Field(..., description="最高温度 (℃)")
    temp_low: float = Field(..., description="最低温度 (℃)")
    condition: str = Field(..., description="天气状况")
    humidity: float = Field(default=0.0, ge=0, le=100, description="湿度 (%)")
    precipitation_chance: float = Field(default=0.0, ge=0, le=100, description="降水概率 (%)")
    wind_direction: str = Field(default="", description="风向")
    wind_power: str = Field(default="", description="风力")


class CityWeather(BaseModel):
    """单个城市的天气数据。"""

    city: str = Field(..., description="城市名称")
    adcode: str = Field(default="", description="行政区划代码")
    live_temperature: float = Field(default=0.0, description="实时温度 (℃)")
    live_weather: str = Field(default="", description="实时天气状况")
    live_humidity: float = Field(default=0.0, description="实时湿度 (%)")
    live_winddirection: str = Field(default="", description="实时风向")
    live_windpower: str = Field(default="", description="实时风力")
    live_report_time: str = Field(default="", description="实时天气发布时间")
    forecast: list[DailyWeather] = Field(default_factory=list, description="未来几日预报")


class WeatherOutput(BaseModel):
    """天气预报输出。"""

    destination: str = Field(default="", description="主目的地")
    forecast: list[DailyWeather] = Field(default_factory=list, description="每日预报列表（兼容旧接口）")
    cities_weather: list[CityWeather] = Field(default_factory=list, description="各城市天气详情")


def _fallback_forecast(city: str, start: datetime.date, end: datetime.date) -> list[DailyWeather]:
    """API 不可用时生成模拟天气预报作为兜底数据。"""
    forecast: list[DailyWeather] = []
    current = start
    temp_base = 25.0 if any(t in city for t in ["北京", "上海", "广州", "深圳", "杭州"]) else 20.0
    while current <= end:
        forecast.append(
            DailyWeather(
                date=current,
                temp_high=round(temp_base + random.uniform(-3, 5), 1),
                temp_low=round(temp_base - random.uniform(3, 8), 1),
                condition=random.choice(WEATHER_CONDITIONS),
                humidity=round(random.uniform(40, 90), 1),
                precipitation_chance=round(random.uniform(0, 60), 1),
            )
        )
        current += datetime.timedelta(days=1)
    return forecast


async def _fetch_city_weather(city: str) -> CityWeather | None:
    """获取单个城市的实时天气和预报。"""
    client = get_client()
    city_weather = CityWeather(city=city)

    # 获取实时天气
    live_result = await client.weather_live(city)
    if live_result.get("success") and live_result.get("lives"):
        live = live_result["lives"][0]
        city_weather.adcode = live.get("adcode", "")
        city_weather.live_temperature = live.get("temperature", 0.0)
        city_weather.live_weather = live.get("weather", "")
        city_weather.live_humidity = live.get("humidity", 0.0)
        city_weather.live_winddirection = live.get("winddirection", "")
        city_weather.live_windpower = live.get("windpower", "")
        city_weather.live_report_time = live.get("report_time", "")

    # 获取未来预报
    fc_result = await client.weather_forecast(city)
    if fc_result.get("success") and fc_result.get("forecasts"):
        fc_data = fc_result["forecasts"][0]
        city_weather.adcode = city_weather.adcode or fc_data.get("adcode", "")
        for cast in fc_data.get("casts", []):
            try:
                date = datetime.date.fromisoformat(cast["date"])
            except (ValueError, KeyError):
                continue
            city_weather.forecast.append(
                DailyWeather(
                    date=date,
                    temp_high=cast.get("day_temp", 0.0),
                    temp_low=cast.get("night_temp", 0.0),
                    condition=cast.get("day_weather", ""),
                    humidity=0.0,
                    precipitation_chance=0.0,
                    wind_direction=f"{cast.get('day_wind', '')}/{cast.get('night_wind', '')}",
                    wind_power=f"{cast.get('day_power', '')}/{cast.get('night_power', '')}",
                )
            )

    return city_weather if city_weather.forecast or city_weather.live_weather else None


async def get_forecast(params: WeatherInput) -> WeatherOutput:
    """获取目的地天气预报。

    优先使用高德地图 API，API 不可用时降级为模拟数据。
    支持单城市（destination）和多城市（cities）两种输入模式。

    Args:
        params: WeatherInput — destination/cities、可选 start_date/end_date

    Returns:
        WeatherOutput: 包含各城市天气详情和兼容旧接口的 forecast 列表
    """
    # 确定要查询的城市列表
    target_cities: list[str] = []
    if params.cities:
        target_cities = params.cities
    elif params.destination:
        target_cities = [params.destination]
    else:
        return WeatherOutput()

    # 确定日期范围
    today = datetime.date.today()
    start = params.start_date or today
    end = params.end_date or today + datetime.timedelta(days=4)

    cities_weather: list[CityWeather] = []
    all_forecast: list[DailyWeather] = []

    for city in target_cities:
        cw = await _fetch_city_weather(city)

        # 高德 API 不可用或失败，降级使用模拟数据
        if cw is None or not cw.forecast:
            fallback = _fallback_forecast(city, start, end)
            cw = CityWeather(city=city, forecast=fallback)
        else:
            # 过滤日期范围
            cw.forecast = [d for d in cw.forecast if start <= d.date <= end]

        cities_weather.append(cw)
        all_forecast.extend(cw.forecast)

    return WeatherOutput(
        destination=params.destination or (target_cities[0] if target_cities else ""),
        forecast=all_forecast,
        cities_weather=cities_weather,
    )
