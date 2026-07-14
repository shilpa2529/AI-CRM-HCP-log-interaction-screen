from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str = "your_groq_api_key_here"
    groq_model_primary: str = "llama-3.3-70b-versatile"
    groq_model_context: str = "llama-3.3-70b-versatile"
    database_url: str = "postgresql+psycopg2://hcp_user:hcp_pass@localhost:5432/hcp_crm"
    frontend_origin: str = "http://localhost:5173"

    class Config:
        env_file = ".env"


settings = Settings()
