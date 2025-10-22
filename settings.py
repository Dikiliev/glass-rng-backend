from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Публичный RPC для Solana (можно заменить на свой/провайдера)
    SOLANA_RPC_URL: str = "https://api.mainnet-beta.solana.com"
    # Сколько блоков тянуть по умолчанию
    SOL_BLOCKS: int = 3

settings = Settings()
