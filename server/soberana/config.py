"""Configuración central. Todo sale de variables de entorno (ver .env.example en la raíz).

El sistema funciona en modo degradado sin tokens: cada fuente que no tiene
credenciales simplemente no se ingiere, y la API lo informa en /api/health.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # sqlite por defecto para desarrollo sin docker; en producción, Postgres (Supabase / VM)
    database_url: str = "sqlite:///./soberana.db"

    # --- Tokens de fuentes (opcionales: sin token, la fuente queda inactiva) ---
    gfw_api_token: str = ""        # https://globalfishingwatch.org/our-apis/
    aisstream_api_key: str = ""    # https://aisstream.io/
    eog_username: str = ""         # VIIRS VBD: https://eogdata.mines.edu/
    eog_password: str = ""

    # --- Área de interés ---
    # bbox amplio: ZEE argentina + milla 201 + Hidrovía (lon_min, lat_min, lon_max, lat_max)
    bbox_zee: tuple[float, float, float, float] = (-70.0, -58.5, -52.0, -33.0)
    # bbox de cobertura AIS terrestre razonable (Río de la Plata + Hidrovía + litoral)
    bbox_ais_costero: tuple[float, float, float, float] = (-62.5, -41.5, -54.0, -26.0)
    # bbox de tráfico aéreo (continente + Malvinas + corredor Atlántico Sur)
    bbox_aereo: tuple[float, float, float, float] = (-76.0, -56.5, -50.0, -21.0)

    # --- Detector propio de gaps AIS (costero, near real-time) ---
    gap_minutos_silencio: int = 45      # minutos sin transmitir para considerar gap
    gap_radio_puerto_km: float = 8.0    # si el último contacto fue cerca de un puerto, no alarmar
    posiciones_retencion_dias: int = 14 # retención "hot" en la DB (límite free tier)

    # --- Salidas de jobs batch (las consume el frontend en modo estático) ---
    data_dir: str = "../frontend/public/data"

    # CORS del API
    cors_origins: str = "*"

    model_config = {"env_prefix": "SOBERANA_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
