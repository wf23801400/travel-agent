"""获取天气预报节点。"""

from src.tools import WeatherInput, get_forecast

from ..state import TravelAgentState


async def fetch_weather(state: TravelAgentState) -> dict:
    """调用 weather_tool.get_forecast 获取目的地天气预报。"""
    request = state.get("request")
    if request is None:
        return {"weather_data": None}

    weather_input = WeatherInput(
        destination=request.destination,
        start_date=request.start_date,
        end_date=request.end_date,
    )
    weather_data = await get_forecast(weather_input)
    return {"weather_data": weather_data}
