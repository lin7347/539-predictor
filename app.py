import streamlit as st
import pandas as pd
import numpy as np

# --- 網頁介面設計 ---
st.set_page_config(page_title="539 量化雷達系統 v4.0", layout="wide")
st.title("🎯 539 量化雷達系統 v4.0 (含落點區塊分析)")

# 讀取與清洗資料庫
@st.cache_data
def load_data():
    df = pd.read_excel('539.xlsx')
    rename_dict = {
        'Date (開獎日期)': 'Date', 'Issue (期數)': 'Issue',
        'N1 (號碼1)': 'N1', 'N2 (號碼2)': 'N2', 'N3 (號碼3)': 'N3',
        'N4 (號碼4)': 'N4', 'N5 (號碼5)': 'N5'
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

if st.sidebar.button("🚀 加入數據並重新計算"):
    new_data = pd.DataFrame({
        'Date': [new_date], 'Issue': [new_issue],
        'N1': [n1], 'N2': [n2], 'N3': [n3], 'N4': [n4], 'N5': [n5]
    })
    df = pd.concat([df, new_data], ignore_index=True)
    st.sidebar.success(f"✅ 已成功加入最新開獎紀錄！")

# --- 策略核心運算引擎 ---
nums_100 = df.tail(100)[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
s_100 = pd.Series(0, index=np.arange(1, 40)).add(pd.Series(nums_100).value_counts(), fill_value=0).astype(int)

nums_200 = df.tail(200)[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
s_200 = pd.Series(0, index=np.arange(1, 40)).add(pd.Series(nums_200).value_counts(), fill_value=0).astype(int)

# 心理分數
scores = {}
for num in range(1, 40):
    score = 0
    if num > 31: score += 2 
    if num % 10 == 4: score += 1 
    if num <= 31 and (num % 10 in [6, 8] or num // 10 in [6, 8]): score -= 1 
    scores[num] = score
psy_scores = pd.Series(scores)

# 計算短線綜合評分
short_score = s_100 + (psy_scores * 2)

# ==========================================
# 🗺️ 製作 39 碼全景落點熱區圖 (Grid Heatmap)
# ==========================================
# 準備一個 4x10 的空陣列 (代表 4 個字頭、10 個尾數)
grid = np.full(40, np.nan) 
# 把每個號碼的分數填入對應的位子
for n in range(1, 40):
    grid[n-1] = short_score[n]
grid = grid.reshape(4, 10)

# 轉換成 DataFrame，設定字頭與尾數標籤
heatmap_df = pd.DataFrame(
    grid, 
    index=['01~10 (0字頭)', '11~20 (1字頭)', '21~30 (2字頭)', '31~39 (3字頭)'],
    columns=[f'尾數 {i}' for i in list(range(1, 10)) + [0]]
)

st.markdown("---")
st.header("🗺️ 39 碼全景落點熱區圖 (Zone Heatmap)")
st.markdown("這個區塊幫你把 39 個號碼攤開來。**顏色越紅（分數越高）的格子，代表該號碼近期的動能越強、期望值越高。** 你可以一眼看出哪個「字頭」或哪個「尾數」正在發燙！")

# 顯示熱力圖表格，數值格式化為整數，並套用紅黃漸層
st.dataframe(
    heatmap_df.style.background_gradient(cmap='YlOrRd', axis=None, vmin=short_score.min(), vmax=short_score.max())
                    .format(precision=0, na_rep="-"), 
    use_container_width=True
)

# ==========================================
# 榜單列表 (保留原本的詳細清單供查詢)
# ==========================================
df_100 = pd.DataFrame({'號碼': range(1, 40), '短線次數': s_100.values, '心理分數': psy_scores.values, '🌟 綜合評分': short_score.values})

# 我把這裡拆成兩行，這樣就不怕太長被截斷了！
df_100 = df_100.sort_values(by=['🌟 綜合評分', '短線次數'], ascending=[False, False])
df_100 = df_100.set_index(pd.Index(range(1, 40), name='名次'))

st.markdown("---")
st.header("📋 詳細號碼戰力排行榜")
with st.expander("點擊展開/收合：查看 1~39 名完整清單"):
    st.dataframe(df_100.style.background_gradient(cmap='YlOrRd', subset=['🌟 綜合評分']), height=400, use_container_width=True)

st.markdown("*(本系統為量化數據教學使用，請理性參考)*")
