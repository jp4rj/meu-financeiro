#!/bin/bash
# Inicia backend (uvicorn) e frontend (streamlit) do Meu Financeiro

cd "$(dirname "$0")" || exit 1
source .venv/bin/activate

# libera a porta 8000 se estiver ocupada
if lsof -ti :8000 > /dev/null 2>&1; then
    echo "Liberando porta 8000..."
    lsof -ti :8000 | xargs kill -9 2>/dev/null
    sleep 1
fi

echo "Iniciando backend em http://127.0.0.1:8000 ..."
uvicorn backend.main:app &
BACKEND_PID=$!

sleep 2

echo "Iniciando frontend em http://localhost:8501 ..."
streamlit run frontend/app.py &
FRONTEND_PID=$!

sleep 3
xdg-open http://localhost:8501 >/dev/null 2>&1 &

echo ""
echo "Backend PID: $BACKEND_PID | Frontend PID: $FRONTEND_PID"
echo "Para encerrar os dois: Ctrl+C"
echo ""

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
