@echo off
cd /d "%~dp0"
python -m robot --outputdir results\EarnPoints "tests\Earn Points.robot"
