import streamlit as st
import pandas as pd
import numpy as np

# --- 網頁介面設計 ---
st.set_page_config(page_title="539 量化雷達 v7.0", layout="wide")
st.title("🎯 539 量化雷達 v7.0 (空間型態 + 實盤回測引擎)")

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
# 🧠 模組 2：空間型態演算法核心 (封裝成函式以利回測)
# ==========================================
def run_spatial_algorithm(draw_numbers):
    # draw_numbers 是一組 5 個號碼的 list
    extended_draw = [0] + draw_numbers + [40]
    
    # 1. 找死亡之海
    death_seas = []
    for i in range(len(extended_draw)-1):
        start, end = extended_draw[i], extended_draw[i+1]
        if end - start - 1 > 5:
            death_seas.append((start, end))
            
    # 2. 短線順勢 (+1/-1 且避開深海)
    raw_candidates = set()
    for n in draw_numbers:
        if n + 1 <= 39: raw_candidates.add(n + 1)
        if n - 1 >= 1:  raw_candidates.add(n - 1)
        
    short_picks = []
    for c in raw_candidates:
        in_sea = any(sea_start < c < sea_end for sea_start, sea_end in death_seas)
        if not in_sea: short_picks.append(int(c)) # int() 確保轉為乾淨數字
            
    # 3. 夾心陷阱
    sandwiches = []
    for i in range(len(draw_numbers)-1):
        if draw_numbers[i+1] - draw_numbers[i] == 2:
            sandwiches.append(int(draw_numbers[i] + 1))
            
    # 4. 幾何中心
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
    
    return sorted(short_picks), sorted(long_picks), death_seas, sandwiches, geometric_centers, max_gap

# ==========================================
# 🖥️ 模組 3：今日盤勢預測面板
# ==========================================
latest_draw = df.iloc[-1][['N1', 'N2', 'N3', 'N4', 'N5']].tolist()
latest_date = df.iloc[-1]['Date']

short_picks, long_picks, death_seas, sandwiches, geometric_centers, max_gap = run_spatial_algorithm(latest_draw)
consensus_picks = sorted(list(set(short_picks).intersection(set(long_picks))))

st.markdown("---")
st.markdown(f"### 📅 基準日：{latest_date} | 開出號碼： `{latest_draw}`")

col1, col2, col3 = st.columns(3)
with col1:
    st.error("💀 **避開深海 (死亡之海)**")
    for sea in death_seas:
        s_text = "01" if sea[0] == 0 else f"{sea[0]+1:02d}"
        e_text = "39" if sea[1] == 40 else f"{sea[1]-1:02d}"
        st.write(f"🚫 `{s_text} ~ {e_text}` (間距: {sea[1]-sea[0]-1})")

with col2:
    st.success("🔥 **短線順勢 (+1/-1 過濾版)**")
    st.markdown(f"### {short_picks}" if short_picks else "*(今日無號碼存活)*")
    st.warning("🥪 **必補夾心陷阱**")
    st.markdown(f"### {sandwiches}" if sandwiches else "*(今日未成形)*")

with col3:
    st.info("🎯 **長線均值 (幾何中心)**")
    st.markdown(f"最大斷層間距為 **{max_gap}**。")
    st.markdown(f"### {geometric_centers}" if geometric_centers else "*(無明顯斷層)*")

st.markdown("---")
if consensus_picks:
    st.success(f"🌟 **雙重共識牌 (極高勝率主支)**： **{consensus_picks}**")
else:
    st.markdown("🌟 **雙重共識牌**： 今日無共識，請分開參考上方指標。")

# ==========================================
# 📊 模組 4：殘酷實盤回測引擎 (近100期)
# ==========================================
st.markdown("---")
st.header("📈 模組 4：殘酷實盤回測 (過去 100 期)")
st.markdown("時光機已啟動！系統正在對過去 100 天的歷史開獎進行「蒙眼盲測」，用昨日號碼預測今日，並比對真實命中數。")

# 回測運算
backtest_days = 100
if len(df) > backtest_days + 1:
    results = []
    # 迴圈：走過過去 100 天
    for i in range(len(df) - backtest_days, len(df)):
        # 取得「昨天」的號碼來預測「今天」
        yesterday_draw = df.iloc[i-1][['N1', 'N2', 'N3', 'N4', 'N5']].tolist()
        # 取得「今天」的真實答案
        today_draw = set(df.iloc[i][['N1', 'N2', 'N3', 'N4', 'N5']].tolist())
        today_date = df.iloc[i]['Date']
        
        # 呼叫策略產生預測
        pred_short, pred_long, _, _, _, _ = run_spatial_algorithm(yesterday_draw)
        
        # 對答案
        short_hits = len(set(pred_short).intersection(today_draw))
        long_hits = len(set(pred_long).intersection(today_draw))
        
        results.append({
            'Date': today_date,
            '短線派累積命中': short_hits,
            '長線派累積命中': long_hits
        })
        
    # 將成績單轉成表格並計算「累積」獲利
    bt_df = pd.DataFrame(results).set_index('Date')
    bt_df['短線派累積命中'] = bt_df['短線派累積命中'].cumsum()
    bt_df['長線派累積命中'] = bt_df['長線派累積命中'].cumsum()
    
    # 顯示計分板
    score1, score2 = st.columns(2)
    score1.metric(label="🔥 短線飆風派 (近100期總命中)", value=f"{bt_df['短線派累積命中'].iloc[-1]} 顆")
    score2.metric(label="🎯 長線抄底派 (近100期總命中)", value=f"{bt_df['長線派累積命中'].iloc[-1]} 顆")
    
    # 畫出雙線大對決折線圖
    st.line_chart(bt_df[['短線派累積命中', '長線派累積命中']])
    
else:
    st.warning("資料庫期數不足 100 期，無法進行回測。")

st.markdown("*(本系統為量化數據教學使用，請理性參考)*")
