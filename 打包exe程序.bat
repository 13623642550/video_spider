@echo off

pyinstaller -w --icon=favicon.ico videoSpider.py

copy favicon.ico dist\videoSpider

pause