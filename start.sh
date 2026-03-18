#!/usr/bin/env bash
set -euo pipefail

# ── Colors ──
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# ── Cleanup handler ──
PIDS=()
cleanup() {
    echo -e "\n${YELLOW}[SHUTDOWN]${NC} Stopping all services..."
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done
    wait 2>/dev/null
    echo -e "${GREEN}[DONE]${NC} All services stopped."
    exit 0
}
trap cleanup SIGINT SIGTERM

# ── 1. Start FastAPI (uvicorn) ──
echo -e "${CYAN}[1/4]${NC} Starting FastAPI server..."
uvicorn main:app --reload --port 8000 &
PIDS+=($!)

echo -n "       Waiting for FastAPI on :8000"
for i in $(seq 1 30); do
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo -e " ${GREEN}OK${NC}"
        break
    fi
    echo -n "."
    sleep 1
    if [ "$i" -eq 30 ]; then
        echo -e " ${RED}TIMEOUT${NC}"
        cleanup
        exit 1
    fi
done

# ── 2. Start Cloudflare Tunnel ──
echo -e "${CYAN}[2/4]${NC} Starting Cloudflare tunnel..."
TUNNEL_LOG=$(mktemp /tmp/cloudflared_log.XXXXXX)
cloudflared tunnel --url http://localhost:8000 2>"$TUNNEL_LOG" &
PIDS+=($!)

echo -n "       Waiting for tunnel URL"
TUNNEL_URL=""
for i in $(seq 1 30); do
    TUNNEL_URL=$(grep -o 'https://[a-zA-Z0-9-]*\.trycloudflare\.com' "$TUNNEL_LOG" 2>/dev/null | head -1 || true)
    if [ -n "$TUNNEL_URL" ]; then
        echo -e " ${GREEN}OK${NC}"
        echo -e "       Tunnel URL: ${GREEN}${TUNNEL_URL}${NC}"
        break
    fi
    echo -n "."
    sleep 1
    if [ "$i" -eq 30 ]; then
        echo -e " ${RED}TIMEOUT${NC}"
        echo "       cloudflared log:"
        cat "$TUNNEL_LOG"
        cleanup
        exit 1
    fi
done
rm -f "$TUNNEL_LOG"

# ── 3. Register MS Graph webhook ──
echo -e "${CYAN}[3/4]${NC} Registering SharePoint webhook..."
python3.11 subscribe_webhook.py "$TUNNEL_URL"

# ── 4. Start Streamlit ──
echo -e "${CYAN}[4/4]${NC} Starting Streamlit UI..."
streamlit run app.py --server.port 8501 &
PIDS+=($!)

# ── Summary ──
echo ""
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo -e "${GREEN}  All services running!${NC}"
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo -e "  FastAPI:    http://localhost:8000"
echo -e "  Streamlit:  http://localhost:8501"
echo -e "  Tunnel:     ${TUNNEL_URL}"
echo -e ""
echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop all services."
echo -e "${GREEN}════════════════════════════════════════════${NC}"

# Keep script alive, waiting on background processes
wait
