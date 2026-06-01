@echo off
echo ============================================
echo Flashage ESP32 / ESP32-S3
echo ============================================
echo.

echo Tentative d'effacage de la mémoire pour ESP32
rem python -m esptool --port COM36 erase-flash

echo.
echo ============================================
echo.

echo Tentative de flashage pour ESP32-S3...
rem python -m esptool --chip esp32s3 --port COM36 --baud 460800 write_flash -z 0x1000 firmware_2025_01_05.bin
python -m esptool --chip esp32s3 --port COM36 write_flash -z 0x1000 firmware_2026_01_05.bin

echo.
echo ============================================
echo Flashage terminé!
echo ============================================
pause