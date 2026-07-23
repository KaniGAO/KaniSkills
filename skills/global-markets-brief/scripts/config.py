"""配置管理 - 从 .env 加载 API Keys 和设置"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录（.env 文件所在目录）
ROOT_DIR = Path(__file__).parent

# 加载 .env 文件
env_path = ROOT_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # 尝试从环境变量读取（Automation 场景下通过 env 传入）
    pass


class Config:
    # API Keys
    FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
    ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY", "")
    NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
    FRED_API_KEY = os.getenv("FRED_API_KEY", "")

    # Hunyuan 校验模型（用于每日 6 点实跑时的网页核验 / 多源检测）
    HUNYUAN_API_KEY = os.getenv("HUNYUAN_API_KEY", "")
    HUNYUAN_BASE_URL = os.getenv("HUNYUAN_BASE_URL", "https://api.hunyuan.cloud.tencent.com/v1")
    ENABLE_WEB_VERIFY = os.getenv("ENABLE_WEB_VERIFY", "0") == "1"
    # 网页核验证据目录：由自动化(每日 6 点 Hunyuan 实跑)写出的独立核验基准 JSON
    WEB_EVIDENCE_DIR = os.getenv("WEB_EVIDENCE_DIR", str(ROOT_DIR / ".." / "data"))

    # Email
    GMAIL_SENDER_EMAIL = os.getenv("GMAIL_SENDER_EMAIL", "")
    GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

    # Recipients (JSON array string)
    _recipients = os.getenv("RECIPIENT_EMAILS", "[]")
    if isinstance(_recipients, str):
        import json
        try:
            RECIPIENT_EMAILS = json.loads(_recipients)
        except (json.JSONDecodeError, TypeError):
            RECIPIENT_EMAILS = []
    else:
        RECIPIENT_EMAILS = _recipients

    # Output
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/Users/gaokanglin/CodeBuddy/Claw/reports")

    @classmethod
    def validate(cls) -> list[str]:
        """检查必要配置是否完整，返回缺失项列表"""
        missing = []
        if not cls.FINNHUB_API_KEY:
            missing.append("FINNHUB_API_KEY")
        if not cls.ALPHA_VANTAGE_KEY:
            missing.append("ALPHA_VANTAGE_KEY")
        if not cls.NEWSAPI_KEY:
            missing.append("NEWSAPI_KEY")
        if not cls.FRED_API_KEY:
            missing.append("FRED_API_KEY")
        return missing
