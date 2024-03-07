@echo off
chcp 65001 > nul

pip show telethon > nul
if errorlevel 1 (
    pip install telethon
)

pip show tgcrypto > nul
if errorlevel 1 (
    pip install tgcrypto
)

pip show cryptg > nul
if errorlevel 1 (
	pip install cryptg
)