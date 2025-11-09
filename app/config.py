from typing import Optional
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DEFAULT_CITY: str = "nyc"
    HOME_ADDRESS: Optional[str] = None

    GOOGLE_CALENDAR_ICS_URL: Optional[str] = None
    GOOGLE_MAPS_API_KEY: Optional[str] = None
    OPENWEATHER_API_KEY: Optional[str] = None
    MTA_API_KEY: Optional[str] = None

    REQUEST_TIMEOUT_SECONDS: float = 3.0
    WEATHER_UNITS: str = "metric"  # or "imperial"
    OSM_OVERPASS_URL: str = "https://overpass-api.de/api/interpreter"

    MOCK_MODE: bool = True
    LOG_LEVEL: str = "INFO"


class RuntimeState(BaseModel):
    home_address: Optional[str] = None
    last_context_package: Optional[dict] = None


settings = Settings()
state = RuntimeState(home_address=settings.HOME_ADDRESS)

