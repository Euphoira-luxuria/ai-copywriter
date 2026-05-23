import sys
from pathlib import Path

# Vercel 环境：把项目根目录加入 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app  # noqa: E402
