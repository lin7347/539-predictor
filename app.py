import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="539 量化雷達 歷史回放版", layout="wide")
st.title("🎯 539 量化雷達 歷史回放版 (空間型態 + 時光機)")

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

if 'history_df' not in st.session_state:
    st.session_state.history_df = load_data()

df = st.session_state.history_df

# ==========================================
# 📝 側邊欄：新增數據區
# ==========================================
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
    st.session_state.history_df = pd.concat([st.session_state.history_df, new_data], ignore_index=True)
    st.sidebar.success(f"✅ 已成功加入最新紀錄！(最新期數：{new_issue})")
    st.rerun()

# ==========================================
# ⏳ 主畫面：時光機選擇器 (回放歷史)
# ==========================================
st.markdown("---")
# 製作下拉選單清單 (期數 + 日期，並反轉讓最新的在最上面)
issue_list = (df['Issue'].astype(str) + " (" + df['Date'].astype(str) + ")").tolist()
issue_list.reverse()

# 讓使用者選擇要分析哪一期
selected_display = st.selectbox("⏳ **時光機：選擇你要分析的基準日 (預設為最新一期)**", issue_list)

# 找出使用者選擇的那一期的 Index
selected_issue_num = int(selected_display.split(" ")[0])
selected_idx = df[df['Issue'] == selected_issue_num].index[0]

# 擷取「選定日」以前的所有歷史資料，避免偷看到未來的數據！
historical_df = df.iloc[:selected_idx + 1]

# ==========================================
# 🧠 核心運算：以「選定日」為基準進行計算
# ==========================================
# 1. 計算選定日當下的 100/200 期歷史統計
nums_100 = historical_df.tail(100)[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
s_100 = pd.Series(0, index=np.arange(1, 40)).add(pd.Series(nums_100).value_counts(), fill_value=0).astype(int)

nums_200 = historical_df.tail(200)[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
s_200 = pd.Series(0, index=np.arange(1, 40)).add(pd.Series(nums_200).value_counts(), fill_value=0).astype(int)

# 2. 空間型態演算法 (使用選定日開出的號碼)
target_draw = historical_df.iloc[-1][['N1', 'N2', 'N3', 'N4', 'N5']].tolist()
target_date = historical_df.iloc[-1]['Date']
extended_draw = [0] + target_draw + [40]

death_seas = []
for i in range(len(extended_draw)-1):
    start, end = extended_draw[i], extended_draw[i+1]
    if end - start - 1 > 5: death_seas.append((start, end))
        
short_picks = []
for n in target_draw:
    for c in [n-1, n+1]:
        if 1 <= c <= 39 and not any(sea_start < c < sea_end for sea_start, sea_end in death_seas):
            short_picks.append(int(c))
short_picks = list(set(short_picks))
        
sandwiches = [int(target_draw[i]+1) for i in range(len(target_draw)-1) if target_draw[i+1]-target_draw[i]==2]
        
max_gap = 0
geometric_centers = []
for i in range(len(extended_draw)-1):
    gap = extended_draw[i+1] - extended_draw[i] - 1
    if gap > max_gap:
        max_gap = gap
        center = (extended_draw[i+1] + extended_draw[i]) / 2
        geometric_centers = [int(np.floor(center)), int(np.ceil(center))] if center % 1 != 0 else [int(center)]
    elif gap == max_gap and gap > 0:
        center = (extended_draw[i+1] + extended_draw[i]) / 2
        geometric_centers.extend([int(np.floor(center)), int(np.ceil(center))] if center % 1 != 0 else [int(center)])
geometric_centers = [int(c) for c in geometric_centers if 1 <= c <= 39]

long_picks = list(set(geometric_centers + sandwiches))
consensus_picks = sorted(list(set(short_picks).intersection(set(long_picks))))

# ==========================================
# 📊 顯示面板：完美融合版 39 碼雷達表
# ==========================================
full_39_data = []
for n in range(1, 40):
    if n in consensus_picks: status = "🌟 雙重共識 (強推主支)"
    elif any(sea_start < n < sea_end for sea_start, sea_end in death_seas): status = "💀 死亡深海 (強烈刪牌)"
    elif n in geometric_centers: status = "🎯 幾何中心 (長線引力)"
    elif n in sandwiches: status = "🥪 必補夾心 (型態缺口)"
    elif n in short_picks: status = "🔥 短線順勢 (+1/-1)"
    else: status = "⚖️ 中立觀望"
    
    full_39_data.append({
        "號碼": n, 
        "空間狀態判定": status,
        "🔥 100期開出次數": s_100[n],
        "❄️ 200期開出次數": s_200[n]
    })

df_full_39 = pd.DataFrame(full_39_data).set_index("號碼")

# --- 網頁顯示 ---
st.markdown("---")
st.markdown(f"### 🎯 分析基準日：{target_date} (期數 {selected_issue_num}) | 開出號碼： `{target_draw}`")

col1, col2 = st.columns([1, 2.5])

with col1:
    st.success("🌟 **雙重共識 (強推主支)**")
    st.markdown(f"### {consensus_picks}" if consensus_picks else "*(該期無)*")
    
    st.error("💀 **避開深海 (死亡之海)**")
    for sea in death_seas:
        s_text = "01" if sea[0] == 0 else f"{sea[0]+1:02d}"
        e_text = "39" if sea[1] == 40 else f"{sea[1]-1:02d}"
        st.write(f"🚫 `{s_text} ~ {e_text}` (間距: {sea[1]-sea[0]-1})")
        
    st.info("🎯 **長短線獨立訊號**")
    st.write(f"🔥 短線順勢: {short_picks}")
    st.write(f"🎯 幾何中心: {geometric_centers}")
    st.write(f"🥪 必補夾心: {sandwiches}")

with col2:
    st.header("📋 39 碼全解析雷達表 (歷史 + 空間)")
    
    def color_status(val):
        if isinstance(val, str):
            if '🌟' in val: return 'background-color: #d4edda; color: #155724; font-weight: bold'
            elif '💀' in val: return 'background-color: #f8d7da; color: #721c24'
            elif '🔥' in val or '🎯' in val or '🥪' in val: return 'background-color: #fff3cd; color: #856404'
        return ''
    
    st.dataframe(
        df_full_39.style.map(color_status, subset=['空間狀態判定'])
                        .background_gradient(cmap='YlOrRd', subset=['🔥 100期開出次數'])
                        .background_gradient(cmap='PuBu', subset=['❄️ 200期開出次數']), 
        height=600, use_container_width=True
    )

st.markdown("*(本系統為量化數據教學使用，請理性參考)*")
