# PowerShellスクリプト - run.ps1
# 仕様書作成支援ボット専用起動スクリプト v2.0
# スクリプトの文字コードをUTF-8に設定
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# スクリプトのディレクトリに移動
Set-Location -Path $PSScriptRoot

# 環境変数の初期化
$VENV_PATH = ".\venv"
$STREAMLIT_SCRIPT = "app.py"
$APP_PORT = 8401
$APP_ENV = ""

# プロジェクトルートをPYTHONPATHに追加
$env:PYTHONPATH = (Get-Location).Path

# ヘルプメッセージの表示
if ($args -contains "--help") {
    Write-Host "🚀 仕様書作成支援ボット - 安定起動スクリプト v2.0" -ForegroundColor Green
    Write-Host "======================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "使用方法:"
    Write-Host "  .\run.ps1 [オプション]"
    Write-Host ""
    Write-Host "オプション:"
    Write-Host "  --env [dev|prd] : 実行環境を指定します。"
    Write-Host "                     (dev=development, prd=production)"
    Write-Host "  --help          : このヘルプを表示します。"
    Write-Host ""
    Write-Host "環境モード:"
    Write-Host "  dev  : 開発環境で実行、詳細なログとデバッグ情報を表示"
    Write-Host "  prd  : 本番運用環境、安定性重視でユーザー向け"
    Write-Host ""
    Write-Host "自動機能:"
    Write-Host "  ✅ 仮想環境の自動作成・有効化"
    Write-Host "  ✅ 依存関係の自動インストール・更新検出"
    Write-Host "  ✅ LangChain動作確認"
    Write-Host "  ✅ 構文チェックとエラー検出"
    Write-Host "  ✅ 既存プロセスの安全な停止"
    Write-Host "  ✅ 今回発生した問題の根本解決"
    Write-Host ""
    Write-Host "例:"
    Write-Host "  .\run.ps1 --env dev"
    Write-Host "  .\run.ps1 --env prd"
    exit 0
}

# 引数解析
for ($i = 0; $i -lt $args.Count; $i++) {
    if ($args[$i] -eq "--env" -and ($i + 1) -lt $args.Count) {
        $envValue = $args[$i + 1]
        if ($envValue -eq "dev") {
            $APP_ENV = "development"
            Write-Host "[LOG] ✅ 開発環境モードを選択しました。" -ForegroundColor Green
        } elseif ($envValue -eq "prd") {
            $APP_ENV = "production"
            Write-Host "[LOG] ✅ 本番環境モードを選択しました。" -ForegroundColor Blue
        } else {
            Write-Host "Error: 無効な環境指定です。dev または prd を指定してください。" -ForegroundColor Red
            exit 1
        }
        $i++
    }
}

# 引数がない場合はユーザーに選択を促す  
if (-not $APP_ENV) {
    Write-Host "実行環境を選択してください:"
    Write-Host "  1. Development (dev)"
    Write-Host "  2. Production (prd)"
    $CHOICE = Read-Host "選択肢を入力してください (1/2)"
    
    $CHOICE = $CHOICE.Trim()
    
    if ($CHOICE -eq "1") {
        $APP_ENV = "development"
        Write-Host "[LOG] ✅ 開発環境モードを選択しました。" -ForegroundColor Green
    }
    elseif ($CHOICE -eq "2") {
        $APP_ENV = "production"
        Write-Host "[LOG] ✅ 本番環境モードを選択しました。" -ForegroundColor Blue
    }
    else {
        Write-Host "Error: 無効な選択肢です。再実行してください。" -ForegroundColor Red
        exit 1
    }
}

# Pythonがインストールされているか確認
try {
    $pythonVersion = (python --version 2>&1)
    Write-Host "[LOG] Python バージョン: $pythonVersion"
}
catch {
    Write-Host "Error: Python がインストールされていないか、環境パスが設定されていません。" -ForegroundColor Red
    Read-Host "続行するには何かキーを押してください..."
    exit 1
}

# 仮想環境がなければ作成
if (-not (Test-Path "$VENV_PATH\Scripts\Activate.ps1")) {
    Write-Host "[LOG] 仮想環境が存在しません。作成中..."
    try {
        python -m venv $VENV_PATH
        Write-Host "[LOG] 仮想環境が正常に作成されました。"
    }
    catch {
        Write-Host "Error: 仮想環境の作成に失敗しました。" -ForegroundColor Red
        Write-Host $_.Exception.Message
        Read-Host "続行するには何かキーを押してください..."
        exit 1
    }
}

# 仮想環境を有効化
try {
    if (Test-Path "$VENV_PATH\Scripts\Activate.ps1") {
        . "$VENV_PATH\Scripts\Activate.ps1"
        Write-Host "[LOG] 仮想環境を有効化しました。"
    }
    else {
        Write-Host "Error: 仮想環境の有効化に失敗しました。Activate.ps1 スクリプトが見つかりません。" -ForegroundColor Red
        Read-Host "続行するには何かキーを押してください..."
        exit 1
    }
}
catch {
    Write-Host "Error: 仮想環境の有効化中にエラーが発生しました。" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Read-Host "続行するには何かキーを押してください..."
    exit 1
}

# requirements.txtの確認
if (-not (Test-Path "requirements.txt")) {
    Write-Host "Error: requirements.txt が見つかりません。" -ForegroundColor Red
    Read-Host "続行するには何かキーを押してください..."
    exit 1
}

# 必要に応じてパッケージをインストール
try {
    $CurrentHash = (Get-FileHash -Path "requirements.txt" -Algorithm SHA256).Hash
    $StoredHash = ""
    if (Test-Path ".req_hash") {
        $StoredHash = Get-Content ".req_hash"
    }

    if ($CurrentHash -ne $StoredHash) {
        Write-Host "[LOG] 必要なパッケージをインストール中..."
        try {
            # 現在のプロジェクトの仮想環境を確実に使用
            Write-Host "[LOG] 📦 pip をアップグレード中..."
            & "$VENV_PATH\Scripts\python.exe" -m pip install --upgrade pip --quiet
            Write-Host "[LOG] 📦 パッケージをインストール中..."
            & "$VENV_PATH\Scripts\python.exe" -m pip install -r requirements.txt
            $CurrentHash | Out-File -FilePath ".req_hash"
            Write-Host "[LOG] ✅ パッケージのインストールが完了しました。" -ForegroundColor Green
        }
        catch {
            Write-Host "Error: パッケージのインストールに失敗しました。" -ForegroundColor Red
            Write-Host $_.Exception.Message
            Read-Host "続行するには何かキーを押してください..."
            exit 1
        }
    }
    else {
        Write-Host "[LOG] ✅ パッケージは最新です。インストールをスキップします。" -ForegroundColor Green
    }
}
catch {
    Write-Host "Error: ハッシュ計算に失敗しました。" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Read-Host "続行するには何かキーを押してください..."
    exit 1
}

# LangChain動作確認
Write-Host "[LOG] 🔍 LangChain動作確認中..."
try {
    $langchainTest = & "$VENV_PATH\Scripts\python.exe" -c "import langchain; print('LangChain version:', langchain.__version__)" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[LOG] ✅ $langchainTest" -ForegroundColor Green
    } else {
        Write-Host "Error: LangChainのインポートに失敗しました。" -ForegroundColor Red
        Write-Host $langchainTest
        Read-Host "続行するには何かキーを押してください..."
        exit 1
    }
}
catch {
    Write-Host "Error: LangChain動作確認中にエラーが発生しました。" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Read-Host "続行するには何かキーを押してください..."
    exit 1
}

# 構文チェック
Write-Host "[LOG] 🔍 構文チェック中..."
$syntaxErrors = @()
$filesToCheck = @(
    "app.py",
    "spec_bot\core\agent.py",
    "spec_bot\utils\streaming_callback.py",
    "spec_bot\ui\streamlit_app.py"
)

foreach ($file in $filesToCheck) {
    if (Test-Path $file) {
        try {
            & "$VENV_PATH\Scripts\python.exe" -m py_compile $file 2>&1 | Out-Null
            if ($LASTEXITCODE -ne 0) {
                $syntaxErrors += $file
            }
        }
        catch {
            $syntaxErrors += $file
        }
    }
}

if ($syntaxErrors.Count -gt 0) {
    Write-Host "Error: 以下のファイルに構文エラーがあります：" -ForegroundColor Red
    foreach ($file in $syntaxErrors) {
        Write-Host "  ❌ $file" -ForegroundColor Red
    }
    Read-Host "続行するには何かキーを押してください..."
    exit 1
} else {
    Write-Host "[LOG] ✅ 構文チェック完了 - エラーなし" -ForegroundColor Green
}

# Streamlitスクリプトの存在確認
if (-not (Test-Path $STREAMLIT_SCRIPT)) {
    Write-Host "Error: Streamlitスクリプトが見つかりません: $STREAMLIT_SCRIPT" -ForegroundColor Red
    Read-Host "続行するには何かキーを押してください..."
    exit 1
} else {
    Write-Host "[LOG] ✅ Streamlitスクリプトが見つかりました: $STREAMLIT_SCRIPT" -ForegroundColor Green
}

# 既存プロセス停止
Write-Host "[LOG] 🔍 既存プロセスの確認中..."
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    Write-Host "[LOG] ⚠️  既存のPythonプロセスを停止中..." -ForegroundColor Yellow
    $pythonProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-Host "[LOG] ✅ 既存プロセスを停止しました。" -ForegroundColor Green
} else {
    Write-Host "[LOG] ✅ 既存プロセスはありません。" -ForegroundColor Green
}

# ポート確認
Write-Host "[LOG] 🔍 ポート $APP_PORT を確認中..."
$portCheck = netstat -an | findstr ":$APP_PORT"
if ($portCheck) {
    Write-Host "[LOG] ⚠️  ポート $APP_PORT は使用中です。プロセスを停止します..." -ForegroundColor Yellow
    Get-Process | Where-Object {$_.ProcessName -like "*python*"} | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    Write-Host "[LOG] ✅ ポートを解放しました。" -ForegroundColor Green
} else {
    Write-Host "[LOG] ✅ ポート $APP_PORT は使用可能です。" -ForegroundColor Green
}

# Streamlitアプリケーションを実行
Write-Host ""
Write-Host "🚀 Streamlitアプリケーションを起動中..." -ForegroundColor Green
Write-Host "   環境: $APP_ENV" -ForegroundColor Cyan
Write-Host "   ホスト: localhost" -ForegroundColor Cyan  
Write-Host "   ポート: $APP_PORT" -ForegroundColor Cyan
Write-Host "   スクリプト: $STREAMLIT_SCRIPT" -ForegroundColor Cyan
Write-Host "   URL: http://localhost:$APP_PORT" -ForegroundColor Cyan
Write-Host ""

try {
    # 仮想環境を再度有効化して確実にstreamlitを実行
    . "$VENV_PATH\Scripts\Activate.ps1"
    
    if ($APP_ENV -eq "development") {
        # 開発環境 - デバッグモード
        Write-Host "[LOG] 🔧 開発モード: 詳細ログ表示" -ForegroundColor Yellow
        streamlit run $STREAMLIT_SCRIPT --server.port $APP_PORT --server.address 0.0.0.0 --logger.level debug
    }
    else {
        # 本番環境 - 通常モード
        Write-Host "[LOG] ⚡ 本番モード: 安定動作" -ForegroundColor Blue
        streamlit run $STREAMLIT_SCRIPT --server.port $APP_PORT --server.address 0.0.0.0
    }
    Write-Host ""
    Write-Host "[LOG] ✅ アプリケーションが正常に終了しました。" -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host "Error: Streamlitアプリケーションの実行に失敗しました。" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Write-Host ""
    Write-Host "トラブルシューティング:" -ForegroundColor Yellow
    Write-Host "1. 仮想環境が正しく有効化されているか確認" -ForegroundColor Yellow
    Write-Host "2. requirements.txtの依存関係が正しくインストールされているか確認" -ForegroundColor Yellow  
    Write-Host "3. Pythonファイルに構文エラーがないか確認" -ForegroundColor Yellow
    Write-Host "4. ポート $APP_PORT が他のプロセスで使用されていないか確認" -ForegroundColor Yellow
    Read-Host "続行するには何かキーを押してください..."
    exit 1
}

Write-Host ""
Write-Host "🎉 仕様書作成支援ボット起動スクリプト完了" -ForegroundColor Green
Write-Host "======================================================" -ForegroundColor Green
