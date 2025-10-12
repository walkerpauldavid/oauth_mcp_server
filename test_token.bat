@echo off
REM Test Azure OAuth2 token request using curl

echo Testing Azure OAuth2 token request...
echo.

REM Read values from .env file
for /f "tokens=1,2 delims==" %%a in (.env) do (
    if "%%a"=="TENANT_ID" set TENANT_ID=%%b
    if "%%a"=="CLIENT_ID" set CLIENT_ID=%%b
    if "%%a"=="CLIENT_SECRET" set CLIENT_SECRET=%%b
    if "%%a"=="OAUTH2_SCOPE" set OAUTH2_SCOPE=%%b
)

set TOKEN_URL=https://login.microsoftonline.com/%TENANT_ID%/oauth2/v2.0/token

echo Making token request to: %TOKEN_URL%
echo Using scope: %OAUTH2_SCOPE%
echo.

curl -X POST "%TOKEN_URL%" ^
  -H "Content-Type: application/x-www-form-urlencoded" ^
  -d "grant_type=client_credentials&client_id=%CLIENT_ID%&client_secret=%CLIENT_SECRET%&scope=%OAUTH2_SCOPE%" ^
  --verbose

echo.
echo Done.
pause