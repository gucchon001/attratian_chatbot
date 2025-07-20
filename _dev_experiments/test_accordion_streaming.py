import streamlit as st
import time

def accordion_streaming_test():
    """アコーディオン内ストリーミングテスト"""
    yield "## 🔍 プロセス開始\n\n"
    time.sleep(1)
    
    yield "📝 **Step 1: 準備中...**\n"
    time.sleep(1)
    
    yield "🛠️ **Step 2: 処理中...**\n"
    time.sleep(1)
    
    yield "🔍 **Step 3: 検索中...**\n"
    time.sleep(1)
    
    yield "\n### **結果**\n"
    yield "これはアコーディオン内のストリーミング表示です。"
    time.sleep(0.5)
    yield "文字が段階的に表示されています。"
    time.sleep(0.5)
    yield "\n\n✅ **完了！**"

st.title("🧪 アコーディオン内ストリーミングテスト")

if st.button("テスト実行"):
    # アコーディオン内でストリーミング
    with st.expander("🔍 処理プロセス詳細", expanded=True):
        result = st.write_stream(accordion_streaming_test)
        st.success(f"テスト完了: {len(str(result))}文字") 