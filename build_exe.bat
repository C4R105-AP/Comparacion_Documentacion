@echo off
cd /d "%~dp0"
echo Instalando PyInstaller y dependencias...
python -m pip install -r requirements-dev.txt
if errorlevel 1 goto :fail
echo Generando Comparador_DOC.exe...
python -m PyInstaller --noconfirm --distpath dist --workpath build packaging\comparador.spec
if errorlevel 1 goto :fail
echo.
echo Listo: dist\Comparador_DOC\Comparador_DOC.exe
echo Copia toda la carpeta dist\Comparador_DOC a otros PCs y abre el exe.
pause
exit /b 0
:fail
echo Error al generar el exe.
pause
exit /b 1
