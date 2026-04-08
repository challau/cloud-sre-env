@echo off
echo ============================================
echo  Cloud SRE Sandbox — GitHub Push Script
echo ============================================

cd /d "C:\Users\chall\OneDrive\Desktop\SRE"

echo [1/8] Initializing git...
git init

echo [2/8] Setting user config...
git config user.name "challau"
git config user.email "challaudaykumar@gmail.com"

echo [3/8] Setting default branch to main...
git branch -M main 2>nul

echo [4/8] Removing old remotes...
git remote remove origin 2>nul

echo [5/8] Adding GitHub remote...
git remote add origin https://github.com/challau/cloud-sre-env.git

echo [6/8] Staging all files...
git add -A

echo [7/8] Committing...
git commit -m "Initial commit: Cloud SRE Sandbox - OpenEnv MCP environment (mirrors echo_env)"

echo [8/8] Pushing to GitHub...
git push -u origin main --force

echo.
echo ============================================
echo  DONE! Check https://github.com/challau/cloud-sre-env
echo ============================================
pause
