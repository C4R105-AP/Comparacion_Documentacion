@echo off
cd /d "%~dp0"
echo Instalando PyInstaller y dependencias...
python -m pip install -r requirements-dev.txt
if errorlevel 1 goto :fail
echo Generando Comparador_DOC.exe...
python -m PyInstaller --noconfirm --distpath dist --workpath build packaging\comparador.spec
if errorlevel 1 goto :fail
echo Empaquetando zip para GitHub...
if exist "dist\Comparador_DOC.zip" del /q "dist\Comparador_DOC.zip"
tar -a -c -f "dist\Comparador_DOC.zip" -C dist Comparador_DOC
if errorlevel 1 goto :fail
echo.
echo Listo: dist\Comparador_DOC\Comparador_DOC.exe
echo Zip: dist\Comparador_DOC.zip
echo Copia toda la carpeta dist\Comparador_DOC a otros PCs y abre el exe.
pause
exit /b 0
:fail
echo Error al generar el exe.
pause
exit /b 1
