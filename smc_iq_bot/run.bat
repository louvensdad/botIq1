@echo off
setlocal

if not exist ".venv" (
    echo Ambiente virtual nao encontrado em .venv
    echo Usando Python do sistema.
)

if "%~1"=="dashboard" (
    python -m streamlit run dashboard\app.py
) else (
    python main.py
)

endlocal
