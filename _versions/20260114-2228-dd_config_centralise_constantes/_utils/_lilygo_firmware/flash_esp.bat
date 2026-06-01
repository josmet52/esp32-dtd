@echo off
echo ============================================
echo Flashage ESP32 / ESP32-S3
echo ============================================
echo.

echo Tentative d'effacage de la mémoire pour ESP32
python -m esptool --port COM36 erase-flash

echo.
echo ============================================
echo.
pause

echo Tentative de flashage pour ESP32-S3...
echo python -m esptool --chip esp32s3 --port COM36 --baud 460800 write-flash -z 0x1000 firmware_2025_01_05.bin
python -m esptool --chip esp32s3 --port COM36 --baud 460800 write-flash -z 0x1000 firmware_2025_12_08.bin

echo.
echo ============================================
echo Flashage terminé!
echo ============================================
pause