#!/bin/bash

# ============================================================
# Telegram Bot Control Script
# Usage: ./bot.sh {start|stop|restart|status}
# ============================================================

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$APP_DIR/bot.pid"
LOG_FILE="$APP_DIR/bot.log"
VENV_DIR="$APP_DIR/.venv"
BOT_SCRIPT="$APP_DIR/bot.py"

start() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "⚠️ Bot is already running (PID: $PID)"
            return 1
        else
            echo "🧹 Removing stale PID file..."
            rm -f "$PID_FILE"
        fi
    fi

    echo "🚀 Starting the bot..."
    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate"
    else
        echo "❌ Virtual environment not found at $VENV_DIR"
        exit 1
    fi

    # Run bot in the background, redirecting output to log file
    nohup python "$BOT_SCRIPT" > "$LOG_FILE" 2>&1 &
    PID=$!
    echo $PID > "$PID_FILE"
    
    echo "✅ Bot started successfully with PID: $PID"
    echo "📄 Logs are being written to: $LOG_FILE"
}

stop() {
    if [ ! -f "$PID_FILE" ]; then
        echo "⚠️ Bot is not running (no PID file found)."
        return 1
    fi

    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "🛑 Stopping the bot (PID: $PID)..."
        kill "$PID"
        
        # Wait up to 5 seconds for graceful shutdown
        for i in {1..5}; do
            if ! ps -p "$PID" > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done
        
        # Force kill if still running
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "⚠️ Bot did not stop gracefully, forcing kill..."
            kill -9 "$PID"
        fi
        echo "✅ Bot stopped."
    else
        echo "⚠️ Bot was not running (stale PID file)."
    fi
    rm -f "$PID_FILE"
}

status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "🟢 Bot is RUNNING (PID: $PID)"
            return 0
        else
            echo "🔴 Bot is NOT RUNNING (stale PID file found)"
            return 1
        fi
    else
        echo "🔴 Bot is NOT RUNNING"
        return 1
    fi
}

restart() {
    echo "🔄 Restarting the bot..."
    stop
    sleep 1
    start
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    status)
        status
        ;;
    restart)
        restart
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
esac
