import streamlit as st
import time

def simple_streaming_test():
    """シンプルなストリーミングテスト"""
    for i in range(5):
        yield f"テスト {i+1}: これはストリーミングテストです。\n"
        time.sleep(1)
    yield "✅ ストリーミングテスト完了！"

st.title("🧪 ストリーミングテスト")

if st.button("ストリーミングテスト実行"):
    st.write("## ストリーミング結果")
    result = st.write_stream(simple_streaming_test)
    st.success(f"完了！結果: {len(str(result))}文字") 