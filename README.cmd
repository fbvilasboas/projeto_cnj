@echo off
echo ========================================
echo  Projeto Extrator de Processos CNJ
echo ========================================
echo.
echo Este script vai:
echo 1. Ativar o ambiente virtual (se existir)
echo 2. Instalar dependências
echo 3. Executar a aplicação Flask
echo.

REM Verifica se ambiente virtual existe
IF EXIST venv\Scripts\activate (
    echo Ativando ambiente virtual...
    call venv\Scripts\activate
) ELSE (
    echo Nenhum ambiente virtual encontrado. Continuando com Python do sistema...
)

echo.
echo Instalando dependências do projeto...
pip install -r requirements.txt

echo.
echo Iniciando o servidor Flask...
python app.py

pause
