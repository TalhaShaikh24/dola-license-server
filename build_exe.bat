@echo off
echo ===================================================
echo   Building Dola AI Watermark Remover (.exe)
echo ===================================================
echo.

pip install pyinstaller pyinstaller-hooks-contrib

echo Compiling Standalone Windows Executable...
pyinstaller --noconsole --onefile ^
    --icon="app_icon.ico" ^
    --name="Dola_AI_Watermark_Remover" ^
    --add-data "app_icon.ico;." ^
    --add-data "app_icon.png;." ^
    --add-data "license_config.json;." ^
    --hidden-import "cv2" ^
    --hidden-import "PyQt6" ^
    --hidden-import "numpy" ^
    --hidden-import "requests" ^
    main.py

echo.
echo ===================================================
echo   BUILD COMPLETED!
echo   Output file: dist\Dola_AI_Watermark_Remover.exe
echo ===================================================
pause
