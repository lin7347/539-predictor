import streamlit as st
import pandas as pd
import numpy as np

# --- 策略模組：39碼全排行 ---
def get_full_ranking_short_term(history_df, lookback=100):
    # 短線邏輯：找熱門。出現次數越多，排名越前面 (大到小排序)
    recent_data = history_df.tail(lookback)
    all_numbers = recent_data[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
    counts = pd.Series(all_numbers).value_counts()
    full_counts = pd.Series(0, index=np.arange(1, 40)).add(counts, fill_value=0)
    
    # 依照出現次數降冪排列
    ranked_series = full_counts.sort_values(ascending=False)
    return ranked_series.index.astype(int).tolist(), ranked_series.values.astype(int).tolist()

def get_full_ranking_long_term(history_df, lookback=200):
    # 長線邏輯：找冷門補洞。出現次數越少，排名越前面 (小到大排序)
    recent_data = history_df.tail(lookback)
    all_numbers = recent_data[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
    counts = pd.Series(all_numbers).value_counts()
    full_counts = pd.Series(0, index=np.arange(1, 40)).add(counts, fill_value=0)
    
    # 依照出現次數升冪排列
    ranked_series = full_counts.sort_values(ascending=True)
    return ranked_series.index.astype(int).tolist(), ranked_series.values.astype(int).tolist()

# --- 網頁介面設計 ---
st.set_page_config(page_title="539 量化雷達系統", layout="wide")
st.title("🎯 539 量化雷達系統 (39碼全排行)")

# 讀取與清洗資料庫
@st.cache_data
def load_data():
    df = pd.read_excel('539.xlsx')
    # 清洗欄位名稱
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
    df = pd.concat([df, new_data], ignore_index=True)
    st.sidebar.success(f"✅ 已成功加入最新開獎紀錄！")

# 執行策略排名計算
short_nums, short_freq = get_full_ranking_short_term(df)
long_nums, long_freq = get_full_ranking_long_term(df)

# 建立 39 碼全排行資料表
ranking_df = pd.DataFrame({
    '推薦名次': range(1, 40),
    '🔥短線號碼 (追熱)': short_nums,
    '(近100期開出次數)': short_freq,
    '❄️長線號碼 (補洞)': long_nums,
    '(近200期開出次數)': long_freq
})

# 將「推薦名次」設為 Index，讓表格更好看
ranking_df = ranking_df.set_index('推薦名次')

# 顯示結果
st.markdown("---")
st.header("🏆 39 碼終極勝率排行榜")
st.markdown("在這裡，你可以清楚看到每個號碼的「潛力」。**排在最上面的，就是系統認為最有可能開出的號碼；排在最下面的，可以考慮作為『刪牌』的參考。**")

# 使用 columns 讓畫面並排
col1, col2 = st.columns([1, 2])

with col1:
    st.info("💡 **榜單解讀指南：**\n\n"
            "**1. 短線榜首：** 近期氣勢最強的號碼，適合喜歡『順勢操作』的你。\n\n"
            "**2. 長線榜首：** 沉寂最久、隨時可能反彈的號碼，適合喜歡『逆勢摸底』的你。\n\n"
            "**3. 殺牌區 (第35~39名)：** 兩邊策略都不看好的墊底號碼，建議可以大膽剔除，省下包牌成本！")

with col2:
    # 顯示漂亮的 DataFrame，並設定高度讓他可以上下捲動查看全部 39 個
    st.dataframe(ranking_df, height=600, use_container_width=True)

st.markdown("*(本系統為量化數據教學使用，請理性參考)*")
