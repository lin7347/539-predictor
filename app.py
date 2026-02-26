import streamlit as st
import pandas as pd
import numpy as np

# --- 網頁介面設計 ---
st.set_page_config(page_title="539 量化雷達 v6.0", layout="wide")
st.title("🎯 539 量化雷達 v6.0 (空間型態演算法)")

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

# ==========================================
# 🧠 模組 2：雙核心空間運算引擎
# ==========================================
# 取得最新一期的號碼作為基準
latest_draw = df.iloc[-1][['N1', 'N2', 'N3', 'N4', 'N5']].tolist()
latest_date = df.iloc[-1]['Date']

# 為了計算邊界距離，我們把 0 和 40 加入虛擬邊界
extended_draw = [0] + latest_draw + [40]

# --- 短線引擎：+1/-1 與 避開深海 ---
raw_candidates = set()
for n in latest_draw:
    if n + 1 <= 39: raw_candidates.add(n + 1)
    if n - 1 >= 1:  raw_candidates.add(n - 1)

death_seas = [] # 儲存死亡之海區間
for i in range(len(extended_draw)-1):
    start = extended_draw[i]
    end = extended_draw[i+1]
    gap = end - start - 1
    if gap > 5: # 如果間距大於 5，標記為死亡之海
        death_seas.append((start, end))

# 剔除掉入死亡之海的號碼
short_term_picks = []
for c in raw_candidates:
    in_sea = False
    for sea_start, sea_end in death_seas:
        if sea_start < c < sea_end:
            in_sea = True
            break
    if not in_sea:
        short_term_picks.append(c)

# --- 長線引擎：幾何中心 與 夾心陷阱 ---
sandwiches = [] # 夾心陷阱
for i in range(len(latest_draw)-1):
    if latest_draw[i+1] - latest_draw[i] == 2: # 例如 01, 03，差值為 2
        sandwiches.append(latest_draw[i] + 1)

max_gap = 0
geometric_centers = []
for i in range(len(extended_draw)-1):
    gap = extended_draw[i+1] - extended_draw[i] - 1
    if gap > max_gap:
        max_gap = gap
        center = (extended_draw[i+1] + extended_draw[i]) / 2
        # 如果中心點是小數 (例如 23.5)，就把 23 和 24 都抓出來
        geometric_centers = [int(np.floor(center)), int(np.ceil(center))] if center % 1 != 0 else [int(center)]
    elif gap == max_gap and gap > 0:
        center = (extended_draw[i+1] + extended_draw[i]) / 2
        if center % 1 != 0:
            geometric_centers.extend([int(np.floor(center)), int(np.ceil(center))])
        else:
            geometric_centers.append(int(center))

# 過濾掉超出 1~39 範圍的無效號碼
geometric_centers = [c for c in geometric_centers if 1 <= c <= 39]

# 找出「雙重共識牌」 (短線與長線都推薦的號碼)
all_long_term = set(geometric_centers + sandwiches)
consensus_picks = list(set(short_term_picks).intersection(all_long_term))

# ==========================================
# 🖥️ 模組 3：預測輸出面板 (Dashboard)
# ==========================================
st.markdown("---")
st.markdown(f"### 📅 基準日：{latest_date} | 開出號碼： `{latest_draw}`")

col1, col2, col3 = st.columns(3)

with col1:
    st.error("💀 **避開深海 (死亡之海)**")
    st.markdown("以下區間的間距過大，能量處於真空狀態，**強烈建議刪牌**：")
    for sea in death_seas:
        # 不要顯示虛擬邊界 0 和 40
        s_text = "01" if sea[0] == 0 else f"{sea[0]+1:02d}"
        e_text = "39" if sea[1] == 40 else f"{sea[1]-1:02d}"
        st.write(f"🚫 `{s_text} ~ {e_text}` (間距: {sea[1]-sea[0]-1})")

with col2:
    st.success("🔥 **短線順勢 (+1/-1 過濾版)**")
    st.markdown("從昨日鄰居號碼中，**成功避開死亡之海**的強勢號碼：")
    if short_term_picks:
        st.markdown(f"### {sorted(short_term_picks)}")
    else:
        st.markdown("*(今日無號碼存活)*")
        
    st.warning("🥪 **必補夾心陷阱**")
    if sandwiches:
        st.markdown(f"### {sorted(sandwiches)}")
    else:
        st.markdown("*(今日未成形)*")

with col3:
    st.info("🎯 **長線均值 (幾何中心)**")
    st.markdown(f"最大斷層間距為 **{max_gap}**。空間引力將把號碼拉向以下中心點：")
    if geometric_centers:
        st.markdown(f"### {sorted(geometric_centers)}")
    else:
        st.markdown("*(無明顯斷層)*")

st.markdown("---")
st.header("🌟 雙重共識牌 (極高勝率主支)")
if consensus_picks:
    st.success(f"系統偵測到以下號碼同時具備「短線動能」與「長線引力」： **{sorted(consensus_picks)}**")
else:
    st.markdown("今日無雙重共識牌，建議分開參考上方指標。")

st.markdown("*(本系統為量化數據教學使用，請理性參考)*")
