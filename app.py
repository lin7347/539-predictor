import streamlit as st
import pandas as pd
import numpy as np

# --- 策略模組 ---
def strategy_short_term_neighbors(history_df, lookback=100, hot_count=3):
    recent_data = history_df.tail(lookback)
    all_numbers = recent_data[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
    number_counts = pd.Series(all_numbers).value_counts()
    hot_numbers = number_counts.head(hot_count).index.tolist()
    predictions = set()
    for num in hot_numbers:
        if num + 1 <= 39: predictions.add(num + 1)
        if num - 1 >= 1:  predictions.add(num - 1)
    return list(predictions), hot_numbers

def strategy_long_term_gap(history_df, lookback=200, cold_count=5):
    recent_data = history_df.tail(lookback)
    all_numbers = recent_data[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
    number_counts = pd.Series(all_numbers).value_counts()
    all_539_numbers = pd.Series(0, index=np.arange(1, 40))
    full_counts = all_539_numbers.add(number_counts, fill_value=0)
    cold_numbers = full_counts.sort_values(ascending=True).head(cold_count).index.tolist()
    return [int(x) for x in cold_numbers]

# --- 網頁介面設計 ---
st.set_page_config(page_title="539 量化預測系統", layout="wide")
st.title("🎯 539 量化預測系統 v1.0")

# 讀取資料庫
@st.cache_data
def load_data():
    df = pd.read_excel('539.xlsx')

    # 把中文欄位名稱換成簡單的英文，策略模組才認得！
    rename_dict = {
        'Date (開獎日期)': 'Date',
        'Issue (期數)': 'Issue',
        'N1 (號碼1)': 'N1',
        'N2 (號碼2)': 'N2',
        'N3 (號碼3)': 'N3',
        'N4 (號碼4)': 'N4',
        'N5 (號碼5)': 'N5'
    }
    df = df.rename(columns=rename_dict)
    return df

df = load_data()

# 側邊欄：輸入今日最新數據
st.sidebar.header("📝 輸入今日最新開獎號碼")
new_date = st.sidebar.text_input("開獎日期 (YYYY-MM-DD)", "2026-02-25")
new_issue = st.sidebar.number_input("期數", min_value=113000, value=115048, step=1)
n1 = st.sidebar.number_input("號碼 1 (最小)", min_value=1, max_value=39, value=1)
n2 = st.sidebar.number_input("號碼 2", min_value=1, max_value=39, value=2)
n3 = st.sidebar.number_input("號碼 3", min_value=1, max_value=39, value=3)
n4 = st.sidebar.number_input("號碼 4", min_value=1, max_value=39, value=4)
n5 = st.sidebar.number_input("號碼 5 (最大)", min_value=1, max_value=39, value=5)

if st.sidebar.button("🚀 加入數據並預測明日"):
    new_data = pd.DataFrame({
        'Date': [new_date], 'Issue': [new_issue],
        'N1': [n1], 'N2': [n2], 'N3': [n3], 'N4': [n4], 'N5': [n5]
    })
    # 將新輸入的資料暫時加入記憶體中的資料庫
    df = pd.concat([df, new_data], ignore_index=True)
    st.sidebar.success(f"✅ 已成功加入最新開獎紀錄！")

# 顯示資料庫狀態
st.subheader("📚 歷史資料庫 (最後 5 期)")
st.dataframe(df.tail(5))

# 執行策略預測
st.markdown("---")
st.header("🔮 系統推薦號碼")

col1, col2 = st.columns(2)

with col1:
    st.info("🔥 短線策略 (+1/-1)")
    preds_short, hots = strategy_short_term_neighbors(df)
    st.write(f"**近100期熱門號碼:** {hots}")
    st.write(f"**推薦包牌號碼:** {preds_short}")

with col2:
    st.info("❄️ 長線策略 (補洞)")
    preds_long = strategy_long_term_gap(df)
    st.write(f"**近200期冷門號碼:** {preds_long}")
    st.write(f"**推薦包牌號碼:** {preds_long}")


st.markdown("*(本系統為量化數據教學使用，請理性參考)*")

