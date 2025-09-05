@echo off
cd /d G:\My Drive\Sage\Project_Billing\css-billing
git add .
git commit -m "Auto-sync: %date% %time%"
git push
pause
