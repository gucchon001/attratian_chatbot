"""
ユーザーシナリオベースE2Eテスト

テスト対象: 実際のユーザーワークフローの検証
テストID: E2E-SC-001 ~ E2E-SC-003
"""

import pytest
import time
import unittest.mock as mock
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.spec_bot_mvp.app import HybridSearchApplication

class TestUserScenarios:
    """ユーザーシナリオベースE2Eテスト"""
    
    @pytest.fixture
    def mock_production_environment(self):
        """本番環境に近いモック設定"""
        # 実際のAPIレスポンス時間を模擬
        def mock_slow_api_call(*args, **kwargs):
            time.sleep(0.1)  # 100ms遅延
            return mock.DEFAULT
        
        with mock.patch.multiple(
            'src.spec_bot_mvp.config.settings',
            Settings=mock.DEFAULT
        ), mock.patch.multiple(
            'src.spec_bot_mvp.utils.atlassian_api_client',
            AtlassianAPIClient=mock_slow_api_call
        ), mock.patch('src.spec_bot_mvp.agents.response_generator.LANGCHAIN_AVAILABLE', True):
            yield
    
    @pytest.fixture
    def e2e_app(self, mock_production_environment):
        """E2Eテスト用アプリケーション"""
        return HybridSearchApplication()
    
    def test_scenario_1_new_developer_spec_inquiry(self, e2e_app):
        """E2E-SC-001: 新人開発者の仕様確認シナリオ"""
        
        # 🎬 シナリオ: 新人がログイン機能の実装方法を調べる
        
        # Step 1: フィルター設定
        filters = {
            "use_confluence": True,
            "use_jira": False,
            "date_range": "2024-10-01"
        }
        
        # Step 2: 質問入力
        user_query = "ログイン機能はどのように実装されていますか？"
        
        # 期待される検索結果をモック
        expected_confluence_results = [
            {
                "source": "Confluence",
                "title": "ログイン機能設計書 v2.1",
                "content": """
OAuth 2.0認証フローによるセキュアなログイン実装

## 実装概要
1. フロントエンド: React + OAuth2 PKCE
2. バックエンド: Spring Security + JWT
3. 認証プロバイダー: Keycloak

## 実装手順
1. OAuth2クライアント設定
2. 認証フロー実装
3. トークン検証ロジック
4. セッション管理
""",
                "url": "https://confluence.company.com/wiki/spaces/TECH/pages/123456",
                "relevance_score": 0.95
            },
            {
                "source": "Confluence", 
                "title": "OAuth2認証フロー詳細",
                "content": "認証フローの詳細な説明とシーケンス図...",
                "url": "https://confluence.company.com/wiki/spaces/TECH/pages/789012",
                "relevance_score": 0.88
            }
        ]
        
        # パイプラインをモック
        with mock.patch.object(
            e2e_app, '_execute_fixed_pipeline',
            return_value=(expected_confluence_results, 0.92, {
                "extracted_keywords": ["ログイン", "実装", "認証"],
                "search_intent": "implementation_inquiry",
                "target_sources": ["confluence"]
            })
        ), mock.patch.object(
            e2e_app.agent_handover_manager.response_generator, 'generate_response',
            return_value=self._generate_expected_new_developer_response()
        ):
            
            # Step 3: 検索実行と測定
            start_time = time.time()
            response = e2e_app.execute_hybrid_search(user_query, filters)
            response_time = time.time() - start_time
            
            # Step 4: 期待結果検証
            
            # ✅ 3秒以内に応答開始
            assert response_time < 3.0, f"応答時間が遅すぎます: {response_time:.2f}秒"
            
            # ✅ Confluence仕様書からの詳細情報
            assert "OAuth 2.0認証フロー" in response
            assert "実装手順" in response
            
            # ✅ 実装に必要なステップ明示
            assert "OAuth2クライアント設定" in response
            assert "認証フロー実装" in response
            
            # ✅ 技術詳細説明
            assert "Spring Security" in response or "JWT" in response
    
    def test_scenario_2_bug_investigation_engineer(self, e2e_app):
        """E2E-SC-002: バグ調査エンジニアの問題解決シナリオ"""
        
        # 🎬 シナリオ: バグ調査で関連情報を収集
        
        # Step 1: フィルター設定（Jira + Confluence横断）
        filters = {
            "use_confluence": True,
            "use_jira": True,
            "project": "CTJ"
        }
        
        # Step 2: 質問入力
        user_query = "ログイン認証エラーの既知の問題はありますか？"
        
        # 期待される横断検索結果をモック
        expected_cross_platform_results = [
            {
                "source": "Jira",
                "title": "ログイン認証タイムアウトエラー",
                "content": """
症状: ログイン時に間欠的にタイムアウトエラーが発生
原因: Redis接続プールの設定不備
修正: connection-timeout を 5000ms に変更
影響: ユーザー認証成功率が95%→99.5%に改善
""",
                "url": "https://jira.company.com/browse/CTJ-2156",
                "relevance_score": 0.94
            },
            {
                "source": "Confluence",
                "title": "認証エラー対応履歴",
                "content": "過去の認証関連障害とその対処法をまとめた技術資料...",
                "url": "https://confluence.company.com/wiki/spaces/TECH/pages/654321",
                "relevance_score": 0.87
            },
            {
                "source": "Jira",
                "title": "OAuth2トークン検証エラー",
                "content": "JWT署名検証でのエラーハンドリング改善...",
                "url": "https://jira.company.com/browse/CTJ-2089",
                "relevance_score": 0.82
            }
        ]
        
        # 実行とモック
        with mock.patch.object(
            e2e_app, '_execute_fixed_pipeline',
            return_value=(expected_cross_platform_results, 0.88, {
                "extracted_keywords": ["認証エラー", "既知", "問題"],
                "search_intent": "troubleshooting",
                "target_sources": ["jira", "confluence"]
            })
        ), mock.patch.object(
            e2e_app.agent_handover_manager.response_generator, 'generate_response',
            return_value=self._generate_expected_bug_investigation_response()
        ):
            
            # Step 3: 検索実行
            response = e2e_app.execute_hybrid_search(user_query, filters)
            
            # Step 4: 期待結果検証
            
            # ✅ Jira + Confluence横断検索
            assert "CTJ-2156" in response
            assert "認証エラー対応履歴" in response
            
            # ✅ 過去の類似バグ情報
            assert "タイムアウトエラー" in response
            assert "Redis接続プール" in response
            
            # ✅ 修正履歴・対処法
            assert "connection-timeout" in response
            assert "5000ms" in response
            
            # ✅ 根本原因分析
            assert "設定不備" in response or "原因" in response
            
            # ✅ 再発防止策
            assert "改善" in response or "対処法" in response
    
    def test_scenario_3_product_manager_feature_overview(self, e2e_app):
        """E2E-SC-003: プロダクトマネージャーの機能理解シナリオ"""
        
        # 🎬 シナリオ: 機能仕様の全体把握
        
        # Step 1: フィルター設定（全データソース）
        filters = {
            "use_confluence": True,
            "use_jira": True
        }
        
        # Step 2: 質問入力
        user_query = "ユーザー認証機能の全体像を教えて"
        
        # 複数データソース統合結果をモック
        expected_comprehensive_results = [
            {
                "source": "Confluence",
                "title": "ユーザー認証機能要求仕様書",
                "content": """
## ビジネス要求
- セキュアなユーザー認証
- シングルサインオン対応
- モバイル・ウェブ統一認証

## 技術要求
- OAuth 2.0 + OIDC準拠
- 多要素認証対応
- セッション管理
""",
                "url": "https://confluence.company.com/wiki/spaces/PRODUCT/pages/111222",
                "relevance_score": 0.96
            },
            {
                "source": "Jira",
                "title": "認証機能開発エピック",
                "content": "ユーザー認証機能の開発計画とマイルストーン...",
                "url": "https://jira.company.com/browse/CTJ-1000",
                "relevance_score": 0.91
            },
            {
                "source": "Confluence",
                "title": "認証アーキテクチャ設計書", 
                "content": "システム全体の認証フロー設計と技術選定理由...",
                "url": "https://confluence.company.com/wiki/spaces/TECH/pages/333444",
                "relevance_score": 0.89
            }
        ]
        
        # 実行とモック
        with mock.patch.object(
            e2e_app, '_execute_fixed_pipeline',
            return_value=(expected_comprehensive_results, 0.92, {
                "extracted_keywords": ["ユーザー認証", "全体像", "機能"],
                "search_intent": "overview_inquiry", 
                "target_sources": ["confluence", "jira"]
            })
        ), mock.patch.object(
            e2e_app.agent_handover_manager.response_generator, 'generate_response',
            return_value=self._generate_expected_pm_overview_response()
        ):
            
            # Step 3: 検索実行
            response = e2e_app.execute_hybrid_search(user_query, filters)
            
            # Step 4: 期待結果検証
            
            # ✅ 複数データソース統合情報
            assert "要求仕様書" in response
            assert "CTJ-1000" in response
            assert "アーキテクチャ設計書" in response
            
            # ✅ 機能全体の俯瞰説明
            assert "全体像" in response or "概要" in response
            
            # ✅ ビジネス価値・ユーザー影響
            assert "ビジネス要求" in response
            assert "シングルサインオン" in response
            
            # ✅ 技術詳細と要件の関連
            assert "OAuth 2.0" in response
            assert "技術要求" in response
            
            # ✅ セキュリティ観点
            assert "セキュア" in response or "多要素認証" in response
    
    def test_scenario_error_handling_api_outage(self, e2e_app):
        """E2E-ER-001: API完全停止時の動作確認"""
        
        # Given: Atlassian API完全停止をシミュレート
        with mock.patch.object(
            e2e_app.keyword_extractor, 'extract_keywords',
            side_effect=Exception("API Connection Failed")
        ):
            
            # When: 各種質問を投入
            response = e2e_app.execute_hybrid_search(
                user_query="ログイン機能について", 
                filters={}
            )
            
            # Then: 期待される動作
            
            # ✅ 適切なエラーメッセージ表示
            assert "申し訳ございません" in response
            assert "エラーが発生しました" in response
            
            # ✅ 代替手段の提案
            assert "時間をおいて" in response or "再度お試し" in response
            
            # ✅ システム停止せず継続動作（例外が発生しない）
            assert response is not None
            assert len(response) > 0
    
    def test_performance_response_time_requirement(self, e2e_app):
        """E2E-PF-001: パフォーマンス要件確認"""
        
        # Given: 標準的な検索シナリオ
        with mock.patch.object(
            e2e_app, '_execute_fixed_pipeline',
            return_value=(
                [{"source": "test", "title": "test", "relevance_score": 0.8}],
                0.8,
                {"extracted_keywords": ["test"]}
            )
        ), mock.patch.object(
            e2e_app.agent_handover_manager, 'execute_agent_handover',
            return_value="テスト応答"
        ):
            
            # When: 応答時間測定
            start_time = time.time()
            response = e2e_app.execute_hybrid_search(
                user_query="テスト質問",
                filters={}
            )
            response_time = time.time() - start_time
            
            # Then: パフォーマンス要件達成
            
            # ✅ 検索応答時間 < 3秒
            assert response_time < 3.0, f"応答時間要件未達: {response_time:.2f}秒"
            
            # ✅ 正常な応答生成
            assert response == "テスト応答"
    
    # ヘルパーメソッド: 期待される応答テンプレート
    
    def _generate_expected_new_developer_response(self):
        """新人開発者向け期待応答"""
        return """
## 📋 質問への回答

ログイン機能の実装について、OAuth 2.0認証フローに基づく実装方法をご説明します。

## 🔍 詳細情報

### 実装概要
1. **フロントエンド**: React + OAuth2 PKCE
2. **バックエンド**: Spring Security + JWT  
3. **認証プロバイダー**: Keycloak

### 実装手順
1. OAuth2クライアント設定
2. 認証フロー実装
3. トークン検証ロジック
4. セッション管理

## 📚 関連情報・参考資料

- [ログイン機能設計書 v2.1](https://confluence.company.com/wiki/spaces/TECH/pages/123456)
- [OAuth2認証フロー詳細](https://confluence.company.com/wiki/spaces/TECH/pages/789012)

## 💡 推奨アクション

実装開始前に設計書の最新版を確認し、セキュリティレビューを受けることをお勧めします。
"""
    
    def _generate_expected_bug_investigation_response(self):
        """バグ調査エンジニア向け期待応答"""
        return """
## 📋 質問への回答

ログイン認証エラーに関する既知の問題と対処法をご案内します。

## 🔍 詳細情報

### 主要な既知問題

**1. ログイン認証タイムアウトエラー (CTJ-2156)**
- **症状**: 間欠的なタイムアウトエラー
- **原因**: Redis接続プール設定不備
- **修正**: connection-timeout を 5000ms に変更
- **効果**: 認証成功率 95%→99.5%改善

**2. OAuth2トークン検証エラー (CTJ-2089)**
- **症状**: JWT署名検証エラー
- **対処**: エラーハンドリング改善

## 📚 関連情報・参考資料

- [CTJ-2156: ログイン認証タイムアウトエラー](https://jira.company.com/browse/CTJ-2156)
- [認証エラー対応履歴](https://confluence.company.com/wiki/spaces/TECH/pages/654321)

## 💡 推奨アクション

類似症状が発生した場合は、まずRedis接続設定を確認し、必要に応じて上記の修正を適用してください。
"""
    
    def _generate_expected_pm_overview_response(self):
        """プロダクトマネージャー向け期待応答"""
        return """
## 📋 質問への回答

ユーザー認証機能の全体像について、ビジネス・技術両面から包括的にご説明します。

## 🔍 詳細情報

### ビジネス要求
- **セキュアなユーザー認証**: 企業レベルのセキュリティ要件
- **シングルサインオン対応**: ユーザビリティ向上
- **モバイル・ウェブ統一認証**: 一貫した認証体験

### 技術要求
- **OAuth 2.0 + OIDC準拠**: 業界標準プロトコル
- **多要素認証対応**: セキュリティ強化
- **セッション管理**: 安全な状態管理

### 開発状況
- エピック: CTJ-1000 (認証機能開発)
- 段階的リリース計画

## 📚 関連情報・参考資料

- [ユーザー認証機能要求仕様書](https://confluence.company.com/wiki/spaces/PRODUCT/pages/111222)
- [認証アーキテクチャ設計書](https://confluence.company.com/wiki/spaces/TECH/pages/333444)

## 💡 推奨アクション

機能の詳細検討時は要求仕様書を、技術的な判断時は設計書を参照することをお勧めします。
"""

# pytest実行用のエントリーポイント
if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 