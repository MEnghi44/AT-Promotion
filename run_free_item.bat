@echo off
cd /d "%~dp0"
python -m robot --outputdir results\FreeItem "tests\Free Item.robot"
