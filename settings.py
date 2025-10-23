from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Публичный RPC для Solana (можно заменить на свой/провайдера)
    SOLANA_RPC_URL: str = "https://api.mainnet-beta.solana.com"
    # Сколько блоков тянуть по умолчанию
    SOL_BLOCKS: int = 3

    ETH_RPC_URL: str = ""                 # напр., https://mainnet.infura.io/v3/<key>
    ETH_CONFIRMATIONS: int = 15           # "финализация по числу подтверждений"
    BTC_API_BASE: str = "https://blockstream.info/api"
    BTC_CONFIRMATIONS: int = 6

settings = Settings()
