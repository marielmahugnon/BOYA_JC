@echo off
TITLE BOYA JC - Serveur HTTPS
color 0A
echo ========================================================
echo       DEMARRAGE DU SERVEUR SECURISE BOYA JC
echo ========================================================
cd /d "%~dp0"

:: Activation de l'environnement virtuel s'il existe
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

echo.
echo Lancement de Flask sur https://192.168.100.8:5000 ...
echo Appuyez sur Ctrl+C pour arreter le serveur a tout moment.
echo --------------------------------------------------------

python app.py
pause