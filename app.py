import streamlit as st
import pandas as pd
import numpy as np

# --- 網頁介面設計 ---
st.set_page_config(page_title="539 量化雷達系統 v3.0", layout="wide")
st.title("🎯 539 量化雷達系統 v3.0 (雙引擎獨立榜單)")

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
    nums_100 = history_df.tail(100)[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
    s_100 = pd.Series(0, index=np.arange(1, 40)).add(pd.Series(nums_100).value_counts(), fill_value=0).astype(int)
    
    nums_200 = history_df.tail(200)[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
    s_200 = pd.Series(0, index=np.arange(1, 40)).add(pd.Series(nums_200).value_counts(), fill_value=0).astype(int)
    return s_100, s_200

def get_psychological_scores():
    scores = {}
    for num in range(1, 40):
        score = 0
        if num > 31: score += 2 
        if num % 10 == 4: score += 1 
        if num <= 31 and (num % 10 in [6, 8] or num // 10 in [6, 8]): score -= 1 
        scores[num] = score
    return pd.Series(scores)

s_100, s_200 = get_stats(df)
psy_scores = get_psychological_scores()

# ==========================================
# 榜單 1：🔥 100期短線動能榜 (追熱門)
# ==========================================
df_100 = pd.DataFrame({
    '號碼': range(1, 40),
    '🔥 短線次數 (100期)': s_100.values,
    '🧠 反市場心理分數': psy_scores.values
})
# 評分邏輯：次數越多越好 + 心理分數權重
df_100['🌟 短線綜合評分'] = df_100['🔥 短線次數 (100期)'] + (df_100['🧠 反市場心理分數'] * 2)
# 排序：評分由高到低
df_100 = df_100.sort_values(by=['🌟 短線綜合評分', '🔥 短線次數 (100期)'], ascending=[False, False])
df_100.insert(0, '推薦名次', range(1, 40))
df_100 = df_100.set_index('推薦名次')

# ==========================================
# 榜單 2：❄️ 200期長線補洞榜 (撿冷門)
# ==========================================
df_200 = pd.DataFrame({
    '號碼': range(1, 40),
    '❄️ 長線次數 (200期)': s_200.values,
    '🧠 反市場心理分數': psy_scores.values
})
# 評分邏輯：因為是補洞，次數「越少」越好。我們將次數反轉轉換成「飢渴度」。
# 假設200期內最多開出45次，飢渴度 = 45 - 開出次數。飢渴度越高越欠補。
max_count = df_200['❄️ 長線次數 (200期)'].max()
df_200['長線飢渴度 (隱藏)'] = max_count - df_200['❄️ 長線次數 (200期)']
df_200['🌟 補洞綜合評分'] = df_200['長線飢渴度 (隱藏)'] + (df_200['🧠 反市場心理分數'] * 2)

# 排序：評分由高到低
df_200 = df_200.sort_values(by=['🌟 補洞綜合評分', '長線飢渴度 (隱藏)'], ascending=[False, False])
df_200 = df_200.drop(columns=['長線飢渴度 (隱藏)']) # 隱藏計算用的過渡欄位
df_200.insert(0, '推薦名次', range(1, 40))
df_200 = df_200.set_index('推薦名次')


# --- 顯示網頁結果 (使用 Tabs 分頁) ---
st.markdown("---")
st.success("🧠 **心理分數提醒：**\n\n"
        "🟢 **大於 0 分：** 散戶不愛買，籌碼乾淨，中獎期望值極高。\n\n"
        "🔴 **小於 0 分：** 散戶最愛的幸運號，中獎要跟一堆人平分，期望值低。")

# 建立兩個分頁標籤
tab1, tab2 = st.tabs(["🔥 100期短線動能榜 (順勢追擊)", "❄️ 200期長線補洞榜 (逆勢撿漏)"])

with tab1:
    st.header("🔥 100期短線動能榜")
    st.markdown("適合喜歡**「順勢操作」**的你。這裡排名越高的號碼，代表近期氣勢極旺，且沒什麼散戶跟你搶。")
    # 套用暖色系漸層 (YlOrRd = 黃橘紅)
    st.dataframe(df_100.style.background_gradient(cmap='YlOrRd', subset=['🌟 短線綜合評分']), height=600, use_container_width=True)

with tab2:
    st.header("❄️ 200期長線補洞榜")
    st.markdown("適合喜歡**「逆勢摸底」**的你。這裡排名越高的號碼，代表它已經沉寂超級久了，隨時準備大爆發補洞，而且籌碼極度乾淨！")
    # 套用冷色系漸層 (PuBu = 紫藍)
    st.dataframe(df_200.style.background_gradient(cmap='PuBu', subset=['🌟 補洞綜合評分']), height=600, use_container_width=True)

st.markdown("*(本系統為量化數據教學使用，請理性參考)*")
