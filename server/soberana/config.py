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
    # Desde mayo 2025 EOG usa OpenID con client propio: hay que pedir
    # client_id y client_secret por mail a eog@mines.edu (gratuito).
    # Sin estos, se intenta el flujo legado (puede estar dado de baja).
    eog_client_id: str = ""
    eog_client_secret: str = ""

    # --- Área de interés ---
    # bbox de vigilancia satelital (lon_min, lat_min, lon_max, lat_max).
    # Deliberadamente MÁS GRANDE que la ZEE: incluye la franja de altamar
    # adyacente a la milla 200 (donde la flota extranjera "estaciona"), el
    # Agujero Azul, las aguas de Malvinas, Georgias y Sandwich del Sur, y el
    # Sector Antártico Argentino (25°O-74°O / hasta ~80°S donde hay cobertura AIS real).
    bbox_zee: tuple[float, float, float, float] = (-74.0, -80.0, -20.0, -33.0)
    # bbox de cobertura AIS terrestre razonable (Río de la Plata + Hidrovía + litoral)
    bbox_ais_costero: tuple[float, float, float, float] = (-62.5, -41.5, -54.0, -26.0)
    # bbox de tráfico aéreo (continente + Malvinas + corredor Atlántico Sur
    # hasta Georgias/Sandwich; cobertura real limitada por receptores)
    bbox_aereo: tuple[float, float, float, float] = (-76.0, -58.0, -25.0, -21.0)

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
