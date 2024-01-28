@echo off

SET PARAMS=%*

docker-compose up -d

timeout /t 5 /nobreak >nul
