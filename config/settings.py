"""Stock_AI_Holding — 最小設定（截圖辨識用）"""
import os

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_CODE_OAUTH_TOKEN = os.getenv("CLAUDE_CODE_OAUTH_TOKEN", "")
ANTHROPIC_AUTH_TOKEN = CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
