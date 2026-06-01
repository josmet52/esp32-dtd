@echo off
echo ============================================
echo Flashage ESP32 / ESP32-S3
echo ============================================
echo.

echo Tentative d'effacage de la memoire pour ESP32
python -m esptool --port COM7 erase-flash

echo.
echo ============================================
echo.
pause

echo Tentative de flashage pour ESP32-S3...
echo python -m esptool --chip esp32s3 --port COM7 --baud 460800 write-flash -z 0x1000 C:\Users\jmetr\kDrive_jo\technique\_projets\DTD\_utils\lilygo\Lilygo_Waveshare_Amoled_Micropython\firmware\firmware_2025_01_08.bin
python -m esptool --chip esp32s3 --port COM7 --baud 460800 write-flash -z 0x1000 lilygo\Lilygo_Waveshare_Amoled_Micropython\firmware\firmware_2025_01_08.bin

echo.
echo ============================================
echo Flashage termine!
echo ============================================
pause