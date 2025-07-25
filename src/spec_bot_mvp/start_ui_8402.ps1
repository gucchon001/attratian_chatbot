# 仕様書作成支援ボット MVP - 新UI起動スクリプト
Write-Host "🚀 仕様書作成支援ボット MVP - 新UI起動スクリプト" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "Port: 8402" -ForegroundColor Cyan
Write-Host "URL: http://localhost:8402" -ForegroundColor Cyan
Write-Host "URL: http://192.168.1.227:8402" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Yellow

# プロジェクトルートに移動
Set-Location "C:\dev\attratian_chatbot"

Write-Host "📂 ディレクトリ移動完了: $(Get-Location)" -ForegroundColor Blue
Write-Host "🔧 Streamlitアプリを起動中..." -ForegroundColor Magenta

# 仮想環境がアクティブかチェック
if ($env:VIRTUAL_ENV) {
    Write-Host "✅ 仮想環境アクティブ: $env:VIRTUAL_ENV" -ForegroundColor Green
} else {
    Write-Host "⚠️ 仮想環境を有効化中..." -ForegroundColor Yellow
    & ".\venv\Scripts\Activate.ps1"
}

# Streamlitアプリ起動
streamlit run src/spec_bot_mvp/ui/streamlit_app_integrated.py --server.port 8402 --server.address 0.0.0.0 