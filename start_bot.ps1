# 仕様書作成支援ボット 起動スクリプト (PowerShell)
# このスクリプトを実行すると http://192.168.1.227:8401/ でアクセス可能になります

Write-Host "🤖 仕様書作成支援ボットを起動中..." -ForegroundColor Green
Write-Host "URL: http://192.168.1.227:8401/" -ForegroundColor Cyan

# 仮想環境のアクティベート
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "仮想環境をアクティベート中..." -ForegroundColor Yellow
    & "venv\Scripts\Activate.ps1"
} else {
    Write-Host "仮想環境が見つかりません。requirements.txtから依存関係をインストールしてください" -ForegroundColor Red
}

# Streamlitアプリケーションの起動
Write-Host "Streamlitアプリケーションを起動中..." -ForegroundColor Yellow
streamlit run app.py --server.address=192.168.1.227 --server.port=8401

Write-Host "アプリケーションが終了しました" -ForegroundColor Green 