@echo off
REM 仕様書作成支援ボット 起動スクリプト (Batch)
REM このスクリプトを実行すると http://192.168.1.227:8401/ でアクセス可能になります

echo 🤖 仕様書作成支援ボットを起動中...
echo URL: http://192.168.1.227:8401/
echo.

REM 仮想環境のアクティベート
if exist "venv\Scripts\activate.bat" (
    echo 仮想環境をアクティベート中...
    call venv\Scripts\activate.bat
) else (
    echo 仮想環境が見つかりません。requirements.txtから依存関係をインストールしてください
    pause
    exit /b 1
)

REM Streamlitアプリケーションの起動
echo Streamlitアプリケーションを起動中...
echo ブラウザで http://192.168.1.227:8401/ にアクセスしてください
echo 終了する場合は Ctrl+C を押してください
echo.

streamlit run app.py --server.address=192.168.1.227 --server.port=8401

echo.
echo アプリケーションが終了しました
pause 