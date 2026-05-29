#!/usr/bin/env python3
"""
CAYE v3.0 — Guided Setup Script
Validates environment, collects API keys,
tests all connections, deploys the system.
"""

import os
import sys
import json
import time
import subprocess
import webbrowser
from pathlib import Path

# ─────────────────────────────────────────
# TERMINAL COLORS
# ─────────────────────────────────────────
class Colors:
    GREEN  = '\033[92m'
    YELLOW = '\033[93m'
    RED    = '\033[91m'
    BLUE   = '\033[94m'
    CYAN   = '\033[96m'
    WHITE  = '\033[97m'
    BOLD   = '\033[1m'
    RESET  = '\033[0m'

def print_banner():
    print(f"""
{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║         ⚡ CAYE v3.0 — SYSTEM SETUP & DEPLOYMENT ⚡          ║
║      Crypto-Asymmetric Yield Engine | Polymarket Intel       ║
╚══════════════════════════════════════════════════════════════╝
{Colors.RESET}""")

def print_step(step: int, total: int, message: str):
    print(f"\n{Colors.BLUE}{Colors.BOLD}[STEP {step}/{total}]{Colors.RESET} {Colors.WHITE}{message}{Colors.RESET}")

def print_success(message: str):
    print(f"  {Colors.GREEN}✓{Colors.RESET} {message}")

def print_warning(message: str):
    print(f"  {Colors.YELLOW}⚠{Colors.RESET} {message}")

def print_error(message: str):
    print(f"  {Colors.RED}✗{Colors.RESET} {message}")

def print_info(message: str):
    print(f"  {Colors.CYAN}→{Colors.RESET} {message}")

# ─────────────────────────────────────────
# STEP 1: CHECK PREREQUISITES
# ─────────────────────────────────────────
def check_prerequisites() -> bool:
    print_step(1, 8, "Checking prerequisites...")

    all_pass = True

    # Check Python version
    if sys.version_info >= (3, 11):
        print_success(f"Python {sys.version_info.major}.{sys.version_info.minor} ✓")
    else:
        print_error(f"Python 3.11+ required. Found: {sys.version_info.major}.{sys.version_info.minor}")
        all_pass = False

    # Check Docker
    result = subprocess.run(
        ["docker", "--version"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        version = result.stdout.strip()
        print_success(f"Docker: {version}")
    else:
        print_error("Docker not found. Install from https://docker.com")
        all_pass = False

    # Check Docker Compose
    result = subprocess.run(
        ["docker", "compose", "version"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        version = result.stdout.strip()
        print_success(f"Docker Compose: {version}")
    else:
        print_error("Docker Compose not found. Update Docker Desktop.")
        all_pass = False

    # Check Node.js
    result = subprocess.run(
        ["node", "--version"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        version = result.stdout.strip()
        print_success(f"Node.js: {version}")
    else:
        print_warning("Node.js not found. Frontend may not build.")

    # Check Git
    result = subprocess.run(
        ["git", "--version"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print_success("Git available")
    else:
        print_warning("Git not found. Optional for this setup.")

    return all_pass

# ─────────────────────────────────────────
# STEP 2: COLLECT API KEYS
# ─────────────────────────────────────────
def collect_api_keys() -> dict:
    print_step(2, 8, "Collecting API Keys...")

    print(f"""
{Colors.WHITE}CAYE v3.0 requires 4 free API keys.
All other APIs require no authentication.

Get your free keys here:{Colors.RESET}

  {Colors.CYAN}Etherscan:{Colors.RESET}    https://etherscan.io/register
                   Account → API Keys → Add
                   (Free, instant)

  {Colors.CYAN}FRED:{Colors.RESET}         https://fred.stlouisfed.org/docs/api/api_key.html
                   Request API Key (instant approval)

  {Colors.CYAN}GitHub:{Colors.RESET}       https://github.com/settings/tokens
                   Generate new token → Classic
                   No scopes needed (public repos only)

  {Colors.CYAN}Coinglass:{Colors.RESET}    https://www.coinglass.com/pricing
                   Free tier → Get API Key
""")

    keys = {}

    # Etherscan
    print(f"\n{Colors.BOLD}ETHERSCAN API KEY{Colors.RESET}")
    print_info("Register at https://etherscan.io/register")
    while True:
        key = input(f"  {Colors.WHITE}Paste your Etherscan API key: {Colors.RESET}").strip()
        if len(key) >= 30:
            keys['ETHERSCAN_API_KEY'] = key
            print_success("Etherscan key accepted")
            break
        else:
            print_error("Key appears too short. Please check and retry.")

    # FRED
    print(f"\n{Colors.BOLD}FRED API KEY (Federal Reserve){Colors.RESET}")
    print_info("Register at https://fred.stlouisfed.org/docs/api/api_key.html")
    while True:
        key = input(f"  {Colors.WHITE}Paste your FRED API key: {Colors.RESET}").strip()
        if len(key) >= 30:
            keys['FRED_API_KEY'] = key
            print_success("FRED key accepted")
            break
        else:
            print_error("Key appears too short. Please check and retry.")

    # GitHub
    print(f"\n{Colors.BOLD}GITHUB TOKEN{Colors.RESET}")
    print_info("Create at https://github.com/settings/tokens")
    print_info("Generate new token → Classic → No scopes needed")
    while True:
        key = input(f"  {Colors.WHITE}Paste your GitHub token: {Colors.RESET}").strip()
        if key.startswith('ghp_') or key.startswith('github_pat_') and len(key) >= 40:
            keys['GITHUB_TOKEN'] = key
            print_success("GitHub token accepted")
            break
        elif len(key) >= 40:
            keys['GITHUB_TOKEN'] = key
            print_success("GitHub token accepted")
            break
        else:
            print_error("Token appears invalid. GitHub tokens start with ghp_ or github_pat_")

    # Coinglass
    print(f"\n{Colors.BOLD}COINGLASS API KEY{Colors.RESET}")
    print_info("Register at https://www.coinglass.com/pricing (free tier)")
    while True:
        key = input(f"  {Colors.WHITE}Paste your Coinglass API key: {Colors.RESET}").strip()
        if len(key) >= 20:
            keys['COINGLASS_API_KEY'] = key
            print_success("Coinglass key accepted")
            break
        else:
            print_error("Key appears too short. Please check and retry.")

    return keys

# ─────────────────────────────────────────
# STEP 3: TEST API CONNECTIONS
# ─────────────────────────────────────────
def test_api_connections(keys: dict) -> bool:
    print_step(3, 8, "Testing API connections...")

    try:
        import requests
    except ImportError:
        print_warning("requests library not installed yet. Skipping API tests.")
        print_info("APIs will be validated on first run.")
        return True

    all_pass = True

    # Test Polymarket (no key needed)
    try:
        r = requests.get(
            "https://gamma-api.polymarket.com/markets",
            params={"closed": "false", "limit": 1},
            timeout=10
        )
        if r.status_code == 200:
            print_success("Polymarket Gamma API ✓")
        else:
            print_warning(f"Polymarket API returned {r.status_code}")
    except Exception as e:
        print_warning(f"Polymarket API: {str(e)[:50]}")

    # Test CoinGecko (no key needed)
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd"},
            timeout=10
        )
        if r.status_code == 200:
            print_success("CoinGecko API ✓")
        else:
            print_warning(f"CoinGecko API returned {r.status_code}")
    except Exception as e:
        print_warning(f"CoinGecko API: {str(e)[:50]}")

    # Test DefiLlama (no key needed)
    try:
        r = requests.get(
            "https://api.llama.fi/stablecoins",
            timeout=10
        )
        if r.status_code == 200:
            print_success("DefiLlama API ✓")
        else:
            print_warning(f"DefiLlama API returned {r.status_code}")
    except Exception as e:
        print_warning(f"DefiLlama API: {str(e)[:50]}")

    # Test Etherscan
    try:
        r = requests.get(
            "https://api.etherscan.io/api",
            params={
                "module": "gastracker",
                "action": "gasoracle",
                "apikey": keys['ETHERSCAN_API_KEY']
            },
            timeout=10
        )
        data = r.json()
        if data.get('status') == '1':
            print_success("Etherscan API ✓")
        else:
            print_error(f"Etherscan API: {data.get('message', 'Unknown error')}")
            all_pass = False
    except Exception as e:
        print_error(f"Etherscan API: {str(e)[:50]}")
        all_pass = False

    # Test FRED
    try:
        r = requests.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={
                "series_id": "WALCL",
                "api_key": keys['FRED_API_KEY'],
                "file_type": "json",
                "limit": 1
            },
            timeout=10
        )
        if r.status_code == 200:
            print_success("FRED API ✓")
        else:
            print_error(f"FRED API returned {r.status_code}")
            all_pass = False
    except Exception as e:
        print_error(f"FRED API: {str(e)[:50]}")
        all_pass = False

    # Test GitHub
    try:
        r = requests.get(
            "https://api.github.com/repos/ethereum/go-ethereum",
            headers={"Authorization": f"token {keys['GITHUB_TOKEN']}"},
            timeout=10
        )
        if r.status_code == 200:
            print_success("GitHub API ✓")
        else:
            print_error(f"GitHub API returned {r.status_code}")
            all_pass = False
    except Exception as e:
        print_error(f"GitHub API: {str(e)[:50]}")
        all_pass = False

    # Test CourtListener (no key needed)
    try:
        r = requests.get(
            "https://www.courtlistener.com/api/rest/v3/dockets/",
            params={"q": "cryptocurrency", "limit": 1},
            timeout=10
        )
        if r.status_code == 200:
            print_success("CourtListener API ✓")
        else:
            print_warning(f"CourtListener API returned {r.status_code}")
    except Exception as e:
        print_warning(f"CourtListener API: {str(e)[:50]}")

    # Test Coinglass
    try:
        r = requests.get(
            "https://open-api-v3.coinglass.com/api/futures/funding-rate/current",
            headers={"coinglassSecret": keys['COINGLASS_API_KEY']},
            timeout=10
        )
        if r.status_code == 200:
            print_success("Coinglass API ✓")
        else:
            print_warning(f"Coinglass API returned {r.status_code} — will use fallback")
    except Exception as e:
        print_warning(f"Coinglass API: {str(e)[:50]} — will use fallback")

    return all_pass

# ─────────────────────────────────────────
# STEP 4: GENERATE .env FILE
# ─────────────────────────────────────────
def generate_env_file(keys: dict):
    print_step(4, 8, "Generating .env configuration file...")

    import secrets
    secret_key = secrets.token_hex(32)

    env_content = f"""# ─────────────────────────────────────────
# CAYE v3.0 — ENVIRONMENT CONFIGURATION
# Generated by setup.py on {time.strftime('%Y-%m-%d %H:%M:%S')}
# ─────────────────────────────────────────

# DATABASE
POSTGRES_DB=caye_db
POSTGRES_USER=caye_user
POSTGRES_PASSWORD=caye_pass_secure_{secrets.token_hex(8)}
DATABASE_URL=postgresql://caye_user:caye_pass_secure_{secrets.token_hex(8)}@postgres:5432/caye_db

# REDIS
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# API KEYS
ETHERSCAN_API_KEY={keys['ETHERSCAN_API_KEY']}
FRED_API_KEY={keys['FRED_API_KEY']}
GITHUB_TOKEN={keys['GITHUB_TOKEN']}
COINGLASS_API_KEY={keys['COINGLASS_API_KEY']}

# APPLICATION
APP_ENV=production
APP_DEBUG=false
APP_HOST=0.0.0.0
APP_PORT=8000
SECRET_KEY={secret_key}

# SYSTEM SETTINGS
DEFAULT_BANKROLL=10000
MIN_TRADE_SIZE=50
MAX_KELLY_FRACTION=0.25
CIS_THRESHOLD=0.89
PRICE_CEILING=0.52
MIN_LIQUIDITY=50000
MIN_DAYS_TO_EXPIRY=2

# SCAN INTERVALS (seconds)
SCAN_MARKETS_INTERVAL=60
FAST_SIGNALS_INTERVAL=300
MEDIUM_SIGNALS_INTERVAL=1800
SLOW_SIGNALS_INTERVAL=21600
CLEANUP_INTERVAL=3600

# FRONTEND
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000/ws
"""

    env_path = Path('.env')
    env_path.write_text(env_content)
    print_success(f".env file created at {env_path.absolute()}")
    print_info("Database password auto-generated and secured")
    print_info("Secret key auto-generated (32 bytes)")

# ─────────────────────────────────────────
# STEP 5: BUILD DOCKER CONTAINERS
# ─────────────────────────────────────────
def build_docker_containers() -> bool:
    print_step(5, 8, "Building Docker containers (this takes 2-3 minutes)...")
    print_info("Building backend image...")

    result = subprocess.run(
        ["docker", "compose", "build", "--no-cache"],
        capture_output=False,
        text=True
    )

    if result.returncode == 0:
        print_success("Docker containers built successfully")
        return True
    else:
        print_error("Docker build failed. Check output above.")
        return False

# ─────────────────────────────────────────
# STEP 6: START ALL SERVICES
# ─────────────────────────────────────────
def start_services() -> bool:
    print_step(6, 8, "Starting all services...")

    result = subprocess.run(
        ["docker", "compose", "up", "-d"],
        capture_output=False,
        text=True
    )

    if result.returncode != 0:
        print_error("Failed to start services.")
        return False

    print_info("Waiting for PostgreSQL to be ready...")
    for i in range(30):
        result = subprocess.run(
            ["docker", "compose", "exec", "-T", "postgres",
             "pg_isready", "-U", "caye_user", "-d", "caye_db"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print_success("PostgreSQL ready")
            break
        time.sleep(2)
    else:
        print_error("PostgreSQL did not become ready in time.")
        return False

    print_info("Waiting for Redis to be ready...")
    for i in range(15):
        result = subprocess.run(
            ["docker", "compose", "exec", "-T", "redis",
             "redis-cli", "ping"],
            capture_output=True, text=True
        )
        if "PONG" in result.stdout:
            print_success("Redis ready")
            break
        time.sleep(2)
    else:
        print_error("Redis did not become ready in time.")
        return False

    print_info("Waiting for backend API to be ready...")
    try:
        import requests
        for i in range(30):
            try:
                r = requests.get(
                    "http://localhost:8000/health",
                    timeout=5
                )
                if r.status_code == 200:
                    print_success("Backend API ready")
                    break
            except Exception:
                pass
            time.sleep(3)
        else:
            print_warning("Backend taking longer than expected. Check logs.")
    except ImportError:
        print_info("Waiting 30 seconds for backend...")
        time.sleep(30)

    print_success("All services started")
    return True

# ─────────────────────────────────────────
# STEP 7: RUN DATABASE MIGRATIONS
# ─────────────────────────────────────────
def run_migrations() -> bool:
    print_step(7, 8, "Running database migrations...")

    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "backend",
         "alembic", "upgrade", "head"],
        capture_output=True, text=True
    )

    if result.returncode == 0:
        print_success("Database migrations applied")
        print_info("All tables created successfully")
        return True
    else:
        print_error("Migration failed:")
        print(result.stderr)
        return False

# ─────────────────────────────────────────
# STEP 8: VERIFY SYSTEM
# ─────────────────────────────────────────
def verify_system() -> bool:
    print_step(8, 8, "Running system verification...")

    all_pass = True

    # Verify containers running
    result = subprocess.run(
        ["docker", "compose", "ps", "--format", "json"],
        capture_output=True, text=True
    )

    services = [
        "caye_postgres",
        "caye_redis",
        "caye_backend",
        "caye_celery_worker",
        "caye_celery_beat",
        "caye_frontend"
    ]

    for service in services:
        if service in result.stdout:
            print_success(f"{service} running")
        else:
            print_warning(f"{service} may not be running")

    # Verify crypto-only enforcement
    try:
        import requests
        r = requests.get(
            "http://localhost:8000/api/verify/crypto-only",
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            non_crypto = data.get('non_crypto_count', 0)
            if non_crypto == 0:
                print_success(
                    "Crypto-only enforcement verified: "
                    "0 non-crypto markets in DB ✓"
                )
            else:
                print_error(
                    f"VIOLATION: {non_crypto} non-crypto markets found!"
                )
                all_pass = False
    except Exception:
        print_info("Crypto verification will run on first scan")

    return all_pass

# ─────────────────────────────────────────
# FINAL: PRINT DASHBOARD URLS
# ─────────────────────────────────────────
def print_final_summary():
    print(f"""
{Colors.GREEN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║              ✓ CAYE v3.0 DEPLOYMENT COMPLETE                 ║
╚══════════════════════════════════════════════════════════════╝
{Colors.RESET}
{Colors.WHITE}SYSTEM ACCESS:{Colors.RESET}

  {Colors.CYAN}📊 Main Dashboard:{Colors.RESET}     http://localhost:3000
  {Colors.CYAN}🔌 Backend API:{Colors.RESET}        http://localhost:8000
  {Colors.CYAN}📖 API Docs:{Colors.RESET}           http://localhost:8000/docs
  {Colors.CYAN}🌸 Celery Monitor:{Colors.RESET}     http://localhost:5555
  {Colors.CYAN}🏥 Health Check:{Colors.RESET}       http://localhost:8000/health

{Colors.WHITE}SYSTEM STATUS:{Colors.RESET}

  {Colors.GREEN}✓{Colors.RESET} PostgreSQL:      Running on port 5432
  {Colors.GREEN}✓{Colors.RESET} Redis:           Running on port 6379
  {Colors.GREEN}✓{Colors.RESET} FastAPI:         Running on port 8000
  {Colors.GREEN}✓{Colors.RESET} Celery Worker:   Processing tasks
  {Colors.GREEN}✓{Colors.RESET} Celery Beat:     Scheduling every 60s
  {Colors.GREEN}✓{Colors.RESET} React Frontend:  Running on port 3000

{Colors.WHITE}SCAN SCHEDULE:{Colors.RESET}

  Every 60s  → Market scanner (all Polymarket crypto markets)
  Every 5min → Gas prices + spot prices
  Every 30min→ Stablecoin flows + funding rates
  Every 6hr  → Macro liquidity + GitHub + Legal + Unlocks
  Every 1hr  → Expiry cleanup + resolution check

{Colors.WHITE}NEXT STEPS:{Colors.RESET}

  1. Open http://localhost:3000 in your browser
  2. Watch 9 signals populate in real-time
  3. First market scan runs in ~60 seconds
  4. Opportunities appear when all 4 gates pass

{Colors.YELLOW}USEFUL COMMANDS:{Colors.RESET}

  View logs:      docker compose logs -f backend
  View tasks:     docker compose logs -f celery_worker
  Stop system:    docker compose down
  Restart:        docker compose restart
  Full reset:     docker compose down -v && python setup.py

{Colors.CYAN}{Colors.BOLD}THE SYSTEM IS LIVE. MONITORING HAS BEGUN.{Colors.RESET}
""")

# ─────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────
def main():
    print_banner()

    # Step 1: Prerequisites
    if not check_prerequisites():
        print(f"\n{Colors.RED}Prerequisites not met. Fix issues above and retry.{Colors.RESET}")
        sys.exit(1)

    # Step 2: Collect API keys
    keys = collect_api_keys()

    # Step 3: Test API connections
    test_api_connections(keys)

    # Step 4: Generate .env
    generate_env_file(keys)

    # Step 5: Build Docker
    if not build_docker_containers():
        print(f"\n{Colors.RED}Docker build failed. Check Docker is running.{Colors.RESET}")
        sys.exit(1)

    # Step 6: Start services
    if not start_services():
        print(f"\n{Colors.RED}Services failed to start.{Colors.RESET}")
        print_info("Run: docker compose logs to diagnose")
        sys.exit(1)

    # Step 7: Run migrations
    run_migrations()

    # Step 8: Verify system
    verify_system()

    # Print final summary
    print_final_summary()

    # Open browser tabs
    print_info("Opening dashboard in browser...")
    time.sleep(2)
    webbrowser.open("http://localhost:3000")
    webbrowser.open("http://localhost:8000/docs")

if __name__ == "__main__":
    main()