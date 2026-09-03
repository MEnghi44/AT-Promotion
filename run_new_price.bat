@echo off
cd /d "%~dp0"
python -m robot --outputdir results\NewPrice "tests\New Price.robot"
