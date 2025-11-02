# Sofware-AI - اسکریپت اجرا برای شل‌های یونیکس
# این اسکریپت یک virtualenv به نام .venv می‌سازد، وابستگی‌ها را نصب می‌کند،
# در صورت نبودن .env آن را از .env.example می‌سازد و سپس برنامه‌ی اصلی را اجرا می‌کند.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# تعیین دستور پایتون (python3 را ترجیح می‌دهم)
PYTHON_CMD=python3
if ! command -v "$PYTHON_CMD" >/dev/null 2>&1; then
  PYTHON_CMD=python
fi

# در صورت وجود نداشتن virtualenv، آن را ایجاد کنید
if [ ! -f ".venv/bin/python" ]; then
  echo "Creating virtual environment .venv..."
  "$PYTHON_CMD" -m venv .venv
fi

# فعال کنید
# shellcheck source=/dev/null
source .venv/bin/activate

echo "Using Python: $(which python)"

# Upgrade pip and install requirements if present
python -m pip install --upgrade pip
if [ -f "requirements.txt" ]; then
  echo "Installing requirements from requirements.txt..."
  python -m pip install -r requirements.txt
fi

# اگر فایل .env.example وجود ندارد، آن را در .env کپی کنید.
if [ ! -f ".env" ]; then
  if [ -f ".env.example" ]; then
    cp .env.example .env
    echo "Created .env from .env.example. Please edit .env and add real API keys before use."
  else
    echo "Warning: .env not found and .env.example not present."
  fi
fi

# Run the application (forward arguments)
exec python main.py "$@"
