import streamlit as st
import pandas as pd
import numpy as np

# --- 網頁介面設計 ---
st.set_page_config(page_title="539 量化雷達系統 v2.0", layout="wide")
st.title("🎯 539 量化雷達系統 v2.0 (結合反市場心理學)")

# 讀取與清洗資料庫
@st.cache_data
def load_data():
    df = pd.read_excel('539.xlsx')
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

if st.sidebar.button("🚀 加入數據並重新計算"):
    new_data = pd.DataFrame({
        'Date': [new_date], 'Issue': [new_issue],
        'N1': [n1], 'N2': [n2], 'N3': [n3], 'N4': [n4], 'N5': [n5]
    })
    df = pd.concat([df, new_data], ignore_index=True)
    st.sidebar.success(f"✅ 已成功加入最新開獎紀錄！")

# --- 策略核心運算引擎 ---
def get_stats(history_df):
    # 短線動能 (100期)
    nums_100 = history_df.tail(100)[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
    s_100 = pd.Series(0, index=np.arange(1, 40)).add(pd.Series(nums_100).value_counts(), fill_value=0).astype(int)
    
    # 長線補洞 (200期)
    nums_200 = history_df.tail(200)[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
    s_200 = pd.Series(0, index=np.arange(1, 40)).add(pd.Series(nums_200).value_counts(), fill_value=0).astype(int)
    return s_100, s_200

def get_psychological_scores():
    scores = {}
    for num in range(1, 40):
        score = 0
        if num > 31: score += 2  # 避開生日牌 (+2分)
        if num % 10 == 4: score += 1  # 避開忌諱尾數 (+1分)
        if num <= 31 and (num % 10 in [6, 8] or num // 10 in [6, 8]): score -= 1 # 散戶最愛熱門號 (-1分)
        scores[num] = score
    return pd.Series(scores)

s_100, s_200 = get_stats(df)
psy_scores = get_psychological_scores()

# 建立主資料表
master_df = pd.DataFrame({
    '號碼': range(1, 40),
    '🔥 短線次數 (動能)': s_100.values,
    '❄️ 長線次數 (補洞)': s_200.values,
    '🧠 反市場心理分數': psy_scores.values
})

# 計算【終極期望值分數】：短線動能次數 + (心理分數 * 權重倍數)
master_df['🌟 綜合期望值評分'] = master_df['🔥 短線次數 (動能)'] + (master_df['🧠 反市場心理分數'] * 2)

# 依照綜合評分由高到低排序，產出最終排行榜
final_df = master_df.sort_values(by=['🌟 綜合期望值評分', '🔥 短線次數 (動能)'], ascending=[False, False])
final_df.insert(0, '推薦名次', range(1, 40))
final_df = final_df.set_index('推薦名次')

# --- 顯示網頁結果 ---
st.markdown("---")
st.header("🏆 39 碼高期望值綜合排行榜")
st.markdown("本排行榜不僅考量了**『號碼開出的機率』**，更加入了**『散戶心理學』**的籌碼分析。排在越前面的號碼，代表它近期很常開出，而且**全台灣沒什麼人想買它**。一旦開出，你能抱走大獎的機率極高！")

col1, col2 = st.columns([1, 2.5])

with col1:
    st.success("🧠 **心理分數說明：**\n\n"
            "🟢 **正分 (>0)：** \n號碼大於31、或是尾數4。散戶不愛買，籌碼乾淨，中獎期望值極高。\n\n"
            "🔴 **負分 (<0)：** \n號碼小於31且包含6或8。全台灣人都在買的生日幸運號碼，一旦中獎要跟一堆人平分，期望值低。\n\n"
            "💡 **選號建議：** \n直接從排行榜**前 5 名**挑選號碼組合，避開最後 5 名的『地雷擁擠區』。")

with col2:
    # 將特定欄位上色，讓表格更容易閱讀
    st.dataframe(final_df.style.background_gradient(cmap='YlOrRd', subset=['🌟 綜合期望值評分']), height=600, use_container_width=True)

st.markdown("*(本系統為量化數據教學使用，請理性參考)*")
