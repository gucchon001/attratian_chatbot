@echo off
echo 🚀 仕様書作成支援ボット MVP - 新UI起動スクリプト
echo ========================================
echo Port: 8402
echo URL: http://localhost:8402
echo ========================================

cd /d C:\dev\attratian_chatbot

echo 📂 ディレクトリ移動完了: %CD%
echo 🔧 Streamlitアプリを起動中...

streamlit run src/spec_bot_mvp/ui/streamlit_app_integrated.py --server.port 8402 --server.address 0.0.0.0

pause 