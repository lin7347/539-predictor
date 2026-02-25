import streamlit as st
import pandas as pd
import numpy as np

# --- 網頁介面設計 ---
st.set_page_config(page_title="539 量化雷達系統 v5.0", layout="wide")
st.title("🎯 539 量化雷達系統 v5.0 (雙引擎 + 落點熱區圖)")

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
# 100期統計
nums_100 = df.tail(100)[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
s_100 = pd.Series(0, index=np.arange(1, 40)).add(pd.Series(nums_100).value_counts(), fill_value=0).astype(int)

# 200期統計
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

# 計算短線綜合評分 (順勢追熱)
short_score = s_100 + (psy_scores * 2)

# 計算長線補洞評分 (逆勢撿冷門) -> 次數越少分數越高
max_count = s_200.max()
long_score = (max_count - s_200) + (psy_scores * 2)

# ==========================================
# 🗺️ 製作熱區圖的通用函式
# ==========================================
def create_heatmap_df(score_series):
    grid = np.full(40, np.nan) 
    for n in range(1, 40):
        grid[n-1] = score_series[n]
    grid = grid.reshape(4, 10)
    return pd.DataFrame(
        grid, 
        index=['01~10 (0字頭)', '11~20 (1字頭)', '21~30 (2字頭)', '31~39 (3字頭)'],
        columns=[f'尾數 {i}' for i in list(range(1, 10)) + [0]]
    )

heatmap_100 = create_heatmap_df(short_score)
heatmap_200 = create_heatmap_df(long_score)

# ==========================================
# 準備排行榜資料表
# ==========================================
df_100 = pd.DataFrame({'號碼': range(1, 40), '短線次數': s_100.values, '心理分數': psy_scores.values, '🌟 綜合評分': short_score.values})
df_100 = df_100.sort_values(by=['🌟 綜合評分', '短線次數'], ascending=[False, False])
df_100 = df_100.set_index(pd.Index(range(1, 40), name='名次'))

df_200 = pd.DataFrame({'號碼': range(1, 40), '長線次數': s_200.values, '心理分數': psy_scores.values, '🌟 補洞評分': long_score.values})
df_200 = df_200.sort_values(by=['🌟 補洞評分', '長線次數'], ascending=[False, True])
df_200 = df_200.set_index(pd.Index(range(1, 40), name='名次'))

# --- 顯示網頁結果 ---
st.markdown("---")
st.success("💡 **使用指南：** 在下方切換「🔥100期短線」或「❄️200期長線」分頁。每種策略都有專屬的**全景落點熱區圖**與**詳細排行榜**！")

tab1, tab2 = st.tabs(["🔥 100期短線動能榜 (追熱門)", "❄️ 200期長線補洞榜 (撿冷門)"])

with tab1:
    st.header("🔥 100期短線落點熱區圖")
    st.markdown("顏色越**紅**，代表近期**出現頻率越高且籌碼越好**。")
    st.dataframe(heatmap_100.style.background_gradient(cmap='YlOrRd', axis=None).format(precision=0, na_rep="-"), use_container_width=True)
    
    with st.expander("點擊展開/收合：查看短線 1~39 名完整清單"):
        st.dataframe(df_100.style.background_gradient(cmap='YlOrRd', subset=['🌟 綜合評分']), height=400, use_container_width=True)

with tab2:
    st.header("❄️ 200期長線補洞熱區圖")
    st.markdown("顏色越**藍**，代表**沉寂越久、最欠補洞且籌碼越乾淨**。")
    st.dataframe(heatmap_200.style.background_gradient(cmap='PuBu', axis=None).format(precision=0, na_rep="-"), use_container_width=True)
    
    with st.expander("點擊展開/收合：查看長線 1~39 名完整清單"):
        st.dataframe(df_200.style.background_gradient(cmap='PuBu', subset=['🌟 補洞評分']), height=400, use_container_width=True)

st.markdown("*(本系統為量化數據教學使用，請理性參考)*")
