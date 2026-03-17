import streamlit as st
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
import json

st.set_page_config(page_title="量化雷達 雙彩種切換版", layout="wide")

# ==========================================
# 📝 側邊欄：彩種切換開關
# ==========================================
st.sidebar.title("🎲 選擇分析彩種")
game_choice = st.sidebar.radio("目前分析目標：", ["539", "天天樂"])

if st.sidebar.button("🔄 強制同步雲端資料庫"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")

# ==========================================
# ⚙️ 核心演算法參數微調
# ==========================================
st.sidebar.header("⚙️ 演算法參數微調")
death_sea_gap = st.sidebar.slider(
    "💀 死亡之海斷層間距", 
    min_value=4, max_value=12, value=7, step=1, 
    help="當兩個號碼間隔大於此數值，視為死亡之海。"
)
include_repeat = st.sidebar.checkbox(
    "♻️ 包含連莊號 (解除封印)", 
    value=True, 
    help="勾選後保留昨日號碼在動能觀察池；取消則視為全殺棄子。"
)

st.sidebar.markdown("---")

# ==========================================
# 🚀 突破號 & 殺牌 (冷轉熱) 參數微調
# ==========================================
st.sidebar.header("🚀 突破與殺牌參數微調")
breakout_long_period = st.sidebar.number_input(
    "🔭 長線觀察期數 (近 N 期)", 
    min_value=30, max_value=300, value=100, step=10
)
breakout_long_thresh = st.sidebar.number_input(
    f"📉 長線冷門標準 (近 {breakout_long_period} 期開出 ≤)", 
    min_value=1, max_value=50, value=12, step=1
)
st.sidebar.markdown("---")
breakout_short_period = st.sidebar.number_input(
    "🔍 短線觀察期數 (近 N 期)", 
    min_value=5, max_value=50, value=20, step=1
)
breakout_short_thresh = st.sidebar.number_input(
    f"📈 短線爆發標準 (近 {breakout_short_period} 期開出 ≥)", 
    min_value=1, max_value=15, value=3, step=1
)

st.sidebar.markdown("---")

# ==========================================
# 🔗 連接 Google Sheets 資料庫
# ==========================================
def get_google_sheet(sheet_name):
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["gcp_json"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    doc = client.open_by_url("https://docs.google.com/spreadsheets/d/1PrG36Oebngqhm7DrhEUNpfTtSk8k50jdAo2069aBJw8/edit?gid=978302798#gid=978302798")
    return doc.worksheet(sheet_name)

@st.cache_data(ttl=600)
def load_data(game_name):
    sheet = get_google_sheet(game_name)
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    if df.empty:
        return pd.DataFrame(columns=['Date', 'Issue', 'N1', 'N2', 'N3', 'N4', 'N5'])
        
    rename_dict = {
        'Date (開獎日期)': 'Date', 'Issue (期數)': 'Issue',
        'N1 (號碼1)': 'N1', 'N2 (號碼2)': 'N2', 'N3 (號碼3)': 'N3',
        'N4 (號碼4)': 'N4', 'N5 (號碼5)': 'N5'
    }
    df = df.rename(columns=rename_dict)
    df['Issue'] = pd.to_numeric(df['Issue'], errors='coerce')
    df = df.dropna(subset=['Issue'])
    df['Issue'] = df['Issue'].astype(int)
    return df

df = load_data(game_choice)

# ==========================================
# 🧠 空間演算法核心引擎
# ==========================================
def get_predictions(target_draw, gap_limit, allow_repeat, s_long_series, s_short_series, long_thresh, short_thresh):
    target_draw = sorted(target_draw)
    extended_draw = [0] + target_draw + [40]
    
    death_seas = []
    for i in range(len(extended_draw)-1):
        start, end = extended_draw[i], extended_draw[i+1]
        if end - start - 1 >= gap_limit: 
            death_seas.append((start, end))
            
    short_picks = []
    for n in target_draw:
        for c in [n-1, n+1]:
            if 1 <= c <= 39 and not any(sea_start < c < sea_end for sea_start, sea_end in death_seas):
                short_picks.append(int(c))
                
    if allow_repeat: short_picks.extend(target_draw)
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

    tails = [n % 10 for n in target_draw]
    hot_tails = [t for t in set(tails) if tails.count(t) >= 2]
    
    tail_resonances = []
    if hot_tails:
        for t in hot_tails:
            for n in range(1, 40):
                if n % 10 == t: tail_resonances.append(n)

    if not allow_repeat:
        short_picks = [p for p in short_picks if p not in target_draw]
        sandwiches = [p for p in sandwiches if p not in target_draw]
        geometric_centers = [p for p in geometric_centers if p not in target_draw]
        tail_resonances = [p for p in tail_resonances if p not in target_draw]

    long_picks = list(set(geometric_centers + sandwiches + tail_resonances))
    consensus_picks = sorted(list(set(short_picks).intersection(set(long_picks))))
    
    worst_10_picks = []
    breakout_picks = []
    
    if s_long_series is not None:
        cold_nums = [p for p in range(1, 40) if any(s < p < e for s,e in death_seas) and p not in target_draw and p not in short_picks[:10] and p not in long_picks[:10]]
        neutral_nums = [p for p in range(1, 40) if p not in target_draw and p not in short_picks[:10] and p not in long_picks[:10] and p not in cold_nums]
        
        cold_sorted = sorted(cold_nums, key=lambda x: s_long_series.get(x, 0))
        neutral_sorted = sorted(neutral_nums, key=lambda x: s_long_series.get(x, 0))
        
        dead_pool = target_draw if not allow_repeat else []
        worst_10_pool = dead_pool + cold_sorted + neutral_sorted
        worst_10_picks = sorted(worst_10_pool[:10])

    if s_long_series is not None and s_short_series is not None:
        for p in range(1, 40):
            if s_long_series.get(p, 0) <= long_thresh and s_short_series.get(p, 0) >= short_thresh:
                if p not in worst_10_picks: breakout_picks.append(p)
    
    return short_picks, long_picks, consensus_picks, death_seas, sandwiches, geometric_centers, tail_resonances, max_gap, worst_10_picks, breakout_picks

# ==========================================
# 📝 側邊欄設定區
# ==========================================
st.sidebar.title("🧭 系統導覽")
page = st.sidebar.radio("選擇分析面板：", [
    "🎯 39碼全解析雷達", 
    "⚔️ 雙引擎策略看板", 
    "📈 回測與勝率追蹤", 
    "📊 頻率機率回測實驗室", 
    "📖 核心理論白皮書"
])

st.sidebar.markdown("---")
st.sidebar.header("⏳ 時光機設定")

if not df.empty:
    options = df.index.tolist()
    options.reverse()
    def format_option(idx):
        row = df.loc[idx]
        return f"期數 {row['Issue']} ({row['Date']})"
    selected_idx = st.sidebar.selectbox("選擇分析基準日：", options, format_func=format_option, key=f"time_machine_{game_choice}")
else:
    st.sidebar.warning(f"⚠️ 你的【{game_choice}】資料庫目前是空的！")
    selected_idx = None

st.sidebar.markdown("---")

if not df.empty:
    auto_next_issue = int(df.iloc[-1]['Issue']) + 1
    try:
        last_date = pd.to_datetime(df.iloc[-1]['Date'])
        auto_next_date = (last_date + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    except:
        auto_next_date = "2026-03-01"
else:
    auto_next_issue = 1
    auto_next_date = "2026-03-01"

with st.sidebar.expander(f"📝 輸入【{game_choice}】最新開獎號碼"):
    new_date = st.text_input("開獎日期 (YYYY-MM-DD)", value=auto_next_date)
    new_issue = st.number_input("期數", min_value=1, value=auto_next_issue, step=1)
    st.markdown("*(輸入順序不拘，系統會自動排序)*")
    n1 = st.number_input("號碼 1", min_value=1, max_value=39, value=1)
    n2 = st.number_input("號碼 2", min_value=1, max_value=39, value=2)
    n3 = st.number_input("號碼 3", min_value=1, max_value=39, value=3)
    n4 = st.number_input("號碼 4", min_value=1, max_value=39, value=4)
    n5 = st.number_input("號碼 5", min_value=1, max_value=39, value=5)

    if st.button("🚀 寫入雲端並重新計算"):
        if not df.empty and new_issue in df['Issue'].values:
            st.error(f"⚠️ 期數 {new_issue} 已經存在！")
        else:
            sorted_nums = sorted([n1, n2, n3, n4, n5])
            new_row = [new_date, new_issue, sorted_nums[0], sorted_nums[1], sorted_nums[2], sorted_nums[3], sorted_nums[4]]
            with st.spinner(f'正在寫入 {game_choice} Google 雲端資料庫...'):
                sheet = get_google_sheet(game_choice)
                sheet.append_row(new_row, value_input_option="USER_ENTERED")
            st.success(f"✅ 成功寫入期數 {new_issue}！")
            st.cache_data.clear()
            st.rerun()

if df.empty:
    st.title(f"🎯 歡迎啟用【{game_choice}】分析雷達")
    st.stop()

# ==========================================
# 🧠 當前選定日的狀態計算
# ==========================================
historical_df = df.loc[:selected_idx]
target_draw = historical_df.iloc[-1][['N1', 'N2', 'N3', 'N4', 'N5']].tolist()
target_date = historical_df.iloc[-1]['Date']
target_issue = historical_df.iloc[-1]['Issue']

nums_long = historical_df.tail(breakout_long_period)[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
s_long = pd.Series(0, index=np.arange(1, 40)).add(pd.Series(nums_long).value_counts(), fill_value=0).astype(int)

nums_short = historical_df.tail(breakout_short_period)[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
s_short = pd.Series(0, index=np.arange(1, 40)).add(pd.Series(nums_short).value_counts(), fill_value=0).astype(int)

short_picks, long_picks, consensus_picks, death_seas, sandwiches, geometric_centers, tail_resonances, max_gap, worst_10_picks, breakout_picks = get_predictions(
    target_draw, death_sea_gap, include_repeat, s_long, s_short, breakout_long_thresh, breakout_short_thresh
)

# ==========================================
# 🖥️ 頁面 1：🎯 39碼全解析雷達
# ==========================================
if page == "🎯 39碼全解析雷達":
    st.title(f"🎯 {game_choice} 39碼全解析雷達")
    st.markdown(f"### 基準日：{target_date} (期數 {target_issue}) | 開出號碼： `{target_draw}`")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.error(f"""
        ### 🛑 十大避開地雷 (終極殺牌)
        歷史頻率與深海交叉比對，動能極度冰凍，建議 **優先剔除**：
        ## **{', '.join([str(n) for n in worst_10_picks])}**
        """)
    with col_b:
        if breakout_picks:
            st.success(f"""
            ### 🚀 底部爆量起漲 (冷轉熱突破號)
            符合「近{breakout_long_period}期冷門(≤{breakout_long_thresh}次)、近{breakout_short_period}期爆發(≥{breakout_short_thresh}次)」強勢表態：
            ## **{', '.join([str(n) for n in breakout_picks])}**
            """)
        else:
            st.info(f"""
            ### 🚀 底部爆量起漲 (冷轉熱突破號)
            *(今日無符合「近{breakout_long_period}期冷門(≤{breakout_long_thresh}次)、近{breakout_short_period}期爆發(≥{breakout_short_thresh}次)」的號碼)*
            """)

    st.markdown("---")
    st.markdown("### 📊 長短線雙核心深度戰略報表 (實戰動態微調版)")
    
    def get_category_picks(picks, category_name):
        sorted_picks = sorted(list(set(picks))) if picks else []
        if category_name == "HOT": return ", ".join([str(p) for p in sorted_picks[:5]]) if sorted_picks else "無"
        elif category_name == "WARM": return ", ".join([str(p) for p in sorted_picks[5:10]]) if len(sorted_picks) > 5 else "無"
        elif category_name == "REPEAT_OR_DEAD":
            if include_repeat:
                repeats = [p for p in target_draw if p not in sorted_picks[:10]]
                return ", ".join([str(p) for p in repeats]) if repeats else "無 (皆已升級為主推)"
            else: return ", ".join([str(p) for p in target_draw])
        elif category_name == "NEUTRAL":
            others = [p for p in range(1, 40) if p not in sorted_picks[:10] and p not in target_draw and not any(s < p < e for s,e in death_seas)]
            return ", ".join([str(p) for p in others]) if others else "無"
        elif category_name == "COLD":
            cold = [p for p in range(1, 40) if any(s < p < e for s,e in death_seas) and p not in target_draw and p not in sorted_picks[:10]]
            return ", ".join([str(p) for p in cold]) if cold else "無"

    row3_icon = "♻️ **連莊觀察區**<br>*(昨日開出)*" if include_repeat else "💀 **最不可能開出**<br>*(全殺棄子)*"

    html_table = f"""
    <table style="width:100%; border-collapse: collapse; text-align: left; font-size: 16px;">
        <tr style="background-color: #f0f2f6;">
            <th style="padding: 12px; border: 1px solid #ddd; width: 15%;">推薦等級</th>
            <th style="padding: 12px; border: 1px solid #ddd; width: 42%;">長線平衡派 (抄底與修補)</th>
            <th style="padding: 12px; border: 1px solid #ddd; width: 43%;">短線動能派 (順勢與擴散)</th>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #ddd;">🔥 **極可能開出**<br>*(必買主支)*</td>
            <td style="padding: 12px; border: 1px solid #ddd;"><b style="color: #d9534f; font-size: 18px;">{get_category_picks(long_picks, 'HOT')}</b></td>
            <td style="padding: 12px; border: 1px solid #ddd;"><b style="color: #d9534f; font-size: 18px;">{get_category_picks(short_picks, 'HOT')}</b></td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #ddd;">⭐ **高機率開出**<br>*(強勢輔助)*</td>
            <td style="padding: 12px; border: 1px solid #ddd;"><b style="color: #f0ad4e; font-size: 18px;">{get_category_picks(long_picks, 'WARM')}</b></td>
            <td style="padding: 12px; border: 1px solid #ddd;"><b style="color: #f0ad4e; font-size: 18px;">{get_category_picks(short_picks, 'WARM')}</b></td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #ddd;">{row3_icon}</td>
            <td style="padding: 12px; border: 1px solid #ddd;"><b style="color: #5bc0de; font-size: 18px;">{get_category_picks(long_picks, 'REPEAT_OR_DEAD')}</b></td>
            <td style="padding: 12px; border: 1px solid #ddd;"><b style="color: #5bc0de; font-size: 18px;">{get_category_picks(short_picks, 'REPEAT_OR_DEAD')}</b></td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #ddd;">⚖️ **中等機率**</td>
            <td style="padding: 12px; border: 1px solid #ddd;"><b>{get_category_picks(long_picks, 'NEUTRAL')}</b></td>
            <td style="padding: 12px; border: 1px solid #ddd;"><b>{get_category_picks(short_picks, 'NEUTRAL')}</b></td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #ddd;">❄️ **低機率**</td>
            <td style="padding: 12px; border: 1px solid #ddd;"><b style="color: #999;">{get_category_picks(long_picks, 'COLD')}</b></td>
            <td style="padding: 12px; border: 1px solid #ddd;"><b style="color: #999;">{get_category_picks(short_picks, 'COLD')}</b></td>
        </tr>
    </table>
    """
    st.markdown(html_table, unsafe_allow_html=True)

# ==========================================
# 🖥️ 頁面 2：⚔️ 雙引擎策略看板
# ==========================================
elif page == "⚔️ 雙引擎策略看板":
    st.title(f"⚔️ {game_choice} 雙引擎策略決策看板")
    st.markdown(f"### 基準日：{target_date} (期數 {target_issue}) | 開出號碼： `{target_draw}`")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.error("🔴 短線動能派")
        st.markdown("#### 🔥 順勢動能 (+1 / -1)")
        st.info(f"建議名單： {short_picks}" if short_picks else "*(今日無)*")
        st.markdown(f"#### 💀 避開死水 (斷層大於 {death_sea_gap} 碼的區間)")
        if death_seas:
            for sea in death_seas:
                s_text = "01" if sea[0] == 0 else f"{sea[0]+1:02d}"
                e_text = "39" if sea[1] == 40 else f"{sea[1]-1:02d}"
                st.warning(f"🚫 `{s_text} ~ {e_text}` (間距: {sea[1]-sea[0]-1})")
        else:
            st.success("今日無大型斷層區。")

    with col2:
        st.info("🔵 長線平衡派")
        st.markdown("#### 🎯 史詩斷層 (幾何中心)")
        st.markdown(f"*(當前最大斷層間距為: {max_gap})*")
        st.error(f"建議名單： {geometric_centers}" if geometric_centers else "*(無明顯斷層)*")
        st.markdown("#### 🥪 黃金對稱 (必補夾心)")
        st.error(f"建議名單： {sandwiches}" if sandwiches else "*(今日未成形)*")
        st.markdown("#### 🧲 同尾數共鳴 (家族召喚)")
        st.error(f"建議名單： {tail_resonances}" if tail_resonances else "*(今日無同尾數)*")

    st.markdown("---")
    st.header("⭐️ 雙重共識牌 (疊加勝率)")
    if consensus_picks: st.success(f"### 🎯 極高勝率主支： {consensus_picks}")
    else: st.warning("今日兩派未達成共識，建議分開參考上方指標。")
        
    if next_draw:
        st.markdown("---")
        st.header("🔮 實盤對答案 (下一期實際開出)")
        st.write(f"下一期號碼為：`{next_draw}`")
        hit_consensus = [n for n in consensus_picks if n in next_draw]
        if hit_consensus: st.success(f"🎉 神準命中！ 共識牌命中了： {hit_consensus}")

# ==========================================
# 🖥️ 頁面 3：📈 回測與勝率追蹤
# ==========================================
elif page == "📈 回測與勝率追蹤":
    st.title(f"📈 {game_choice} 策略勝率與全面回測追蹤")
    
    test_periods = 100
    if len(df) > test_periods:
        results = []
        start_idx = len(df) - test_periods - 1
        for i in range(start_idx, len(df) - 1):
            past_draw = [int(x) for x in df.iloc[i][['N1', 'N2', 'N3', 'N4', 'N5']].tolist()]
            actual_next_draw = [int(x) for x in df.iloc[i+1][['N1', 'N2', 'N3', 'N4', 'N5']].tolist()]
            draw_date = df.iloc[i+1]['Date']
            
            historical_for_backtest = df.iloc[:i+1]
            
            nums_long_bt = historical_for_backtest.tail(breakout_long_period)[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
            s_long_bt = pd.Series(0, index=np.arange(1, 40)).add(pd.Series(nums_long_bt).value_counts(), fill_value=0).astype(int)
            
            nums_short_bt = historical_for_backtest.tail(breakout_short_period)[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
            s_short_bt = pd.Series(0, index=np.arange(1, 40)).add(pd.Series(nums_short_bt).value_counts(), fill_value=0).astype(int)
            
            sp, lp, cp, _, _, _, _, _, worst_10, breakout = get_predictions(
                past_draw, death_sea_gap, include_repeat, s_long_bt, s_short_bt, breakout_long_thresh, breakout_short_thresh
            )
            
            short_hits = len(set(sp).intersection(set(actual_next_draw)))
            long_hits = len(set(lp).intersection(set(actual_next_draw)))
            breakout_hits = len(set(breakout).intersection(set(actual_next_draw)))
            breakout_suggested = len(breakout)
            kill_fails = len(set(worst_10).intersection(set(actual_next_draw)))
            successful_kills = 10 - kill_fails
            
            results.append({
                "Date": draw_date,
                "✅ 實際開獎": str(actual_next_draw),
                "🔴 短線推薦": str(sp) if sp else "-",
                "🔴 命中": short_hits,
                "🔵 長線推薦": str(lp) if lp else "-",
                "🔵 命中": long_hits,
                "🚀 突破轉強": str(breakout) if breakout else "-",
                "🚀 推薦數": breakout_suggested,  
                "🚀 命中數": breakout_hits,       
                "💀 十大殺牌": str(worst_10) if worst_10 else "-",
                "🛡️ 成功閃避": successful_kills
            })
        
        res_df = pd.DataFrame(results).set_index("Date")
        res_df["🔴 短線累積"] = res_df["🔴 命中"].cumsum()
        res_df["🔵 長線累積"] = res_df["🔵 命中"].cumsum()
        
        total_kills_attempted = len(res_df) * 10
        total_successful_kills = res_df["🛡️ 成功閃避"].sum()
        kill_defense_rate = (total_successful_kills / total_kills_attempted) * 100
        
        total_breakout_suggested = res_df["🚀 推薦數"].sum()
        total_breakout_hits = res_df["🚀 命中數"].sum()
        breakout_win_rate = (total_breakout_hits / total_breakout_suggested) * 100 if total_breakout_suggested > 0 else 0.0
        
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🔴 短線累積命中", f"{res_df['🔴 短線累積'].iloc[-1]} 顆")
        col2.metric("🔵 長線累積命中", f"{res_df['🔵 長線累積'].iloc[-1]} 顆")
        col3.metric(
            "🚀 突破號狙擊勝率", 
            f"{breakout_win_rate:.1f} %", 
            f"共抓出 {total_breakout_suggested} 顆，命中 {total_breakout_hits} 顆",
            delta_color="normal"
        )
        col4.metric("🛡️ 十大殺牌防守率", f"{kill_defense_rate:.1f} %", "越高越好", delta_color="normal")
        
        st.line_chart(res_df[["🔴 短線累積", "🔵 長線累積"]])
        
        with st.expander("📝 展開查看：每日覆盤明細對帳單"):
            st.dataframe(res_df[["✅ 實際開獎", "🔴 短線推薦", "🔴 命中", "🔵 長線推薦", "🔵 命中", "🚀 突破轉強", "🚀 命中數", "💀 十大殺牌", "🛡️ 成功閃避"]], use_container_width=True)
            
    else:
        st.warning("⚠️ 資料庫目前不足 100 期，無法進行完整回測。")

# ==========================================
# 🖥️ 頁面 4：📊 頻率機率回測實驗室 (✨ 殺牌/不出機率大升級)
# ==========================================
elif page == "📊 頻率機率回測實驗室":
    st.title(f"📊 {game_choice} 頻率機率回測實驗室")
    st.markdown("""
    這裡專門驗證**「條件機率」**：如果一個號碼在過去 N 期內出現了 M 次，它下一期**不開出來（殺牌成功）**的真實機率到底是多少？
    透過歷史回測，我們可以直接找出最安全的**無腦剔除區間**！
    """)
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        test_window = st.number_input("🔍 設定頻率觀察期數 (N 期內)", min_value=5, max_value=100, value=30, step=5)
    with col2:
        test_periods = st.number_input("⏳ 歷史回測樣本數 (近 X 期)", min_value=50, max_value=500, value=150, step=50)
        
    st.markdown("---")

    if len(df) >= test_window + test_periods:
        with st.spinner('正在進行百萬次交叉比對運算中...'):
            results = {} 
            start_idx = len(df) - test_periods - 1
            
            for i in range(start_idx, len(df) - 1):
                past_window = df.iloc[i - test_window + 1 : i + 1]
                flat_past = past_window[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
                freq_counts = pd.Series(0, index=np.arange(1, 40)).add(pd.Series(flat_past).value_counts(), fill_value=0).astype(int)
                
                actual_next_draw = df.iloc[i+1][['N1', 'N2', 'N3', 'N4', 'N5']].tolist()
                
                for num in range(1, 40):
                    f = freq_counts[num]
                    if f not in results:
                        results[f] = {'總遇見次數': 0, '開出次數': 0, '不開次數': 0}
                    results[f]['總遇見次數'] += 1
                    
                    if num in actual_next_draw:
                        results[f]['開出次數'] += 1
                    else:
                        results[f]['不開次數'] += 1
            
            output = []
            for f in sorted(results.keys()):
                total = results[f]['總遇見次數']
                hits = results[f]['開出次數']
                misses = results[f]['不開次數']
                
                hit_rate = (hits / total * 100) if total > 0 else 0
                miss_rate = (misses / total * 100) if total > 0 else 0
                
                output.append({
                    "近 N 期出現次數 (M)": f"{f} 次",
                    "歷史樣本總數": total,
                    "下期開出": hits,
                    "下期不開 (殺牌)": misses,
                    "✨ 開出機率 (做多)": f"{hit_rate:.1f} %",
                    "🛡️ 不出機率 (殺牌)": f"{miss_rate:.1f} %",
                    "Raw_Miss_Rate": miss_rate, 
                    "Raw_Hit_Rate": hit_rate
                })
            
            prob_df = pd.DataFrame(output)
            st.success(f"✅ 回測完成！以下是近 {test_periods} 期內，以 {test_window} 期為觀察窗的機率分佈：")
            
            display_df = prob_df.drop(columns=["Raw_Miss_Rate", "Raw_Hit_Rate"])
            st.dataframe(display_df, use_container_width=True)
            
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.markdown("### 🛡️ 殺牌專屬：不出機率長條圖")
                st.caption("柱子越高，代表該頻率下期「絕對不開」的機率越大，最適合剔除。")
                miss_chart_data = prob_df.set_index("近 N 期出現次數 (M)")["Raw_Miss_Rate"]
                st.bar_chart(miss_chart_data, color="#d9534f")
                
            with col_chart2:
                st.markdown("### ✨ 做多專屬：開出機率長條圖")
                st.caption("柱子越高，代表該頻率下期「爆發開出」的機率越大，適合買進。")
                hit_chart_data = prob_df.set_index("近 N 期出現次數 (M)")["Raw_Hit_Rate"]
                st.bar_chart(hit_chart_data, color="#5cb85c")
            
            st.markdown("---")
            st.markdown(f"### 🎯 明日實戰指南：以 {test_window} 期頻率精準打擊")
            
            latest_window = historical_df.tail(test_window)[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
            latest_freq = pd.Series(0, index=np.arange(1, 40)).add(pd.Series(latest_window).value_counts(), fill_value=0).astype(int)
            
            valid_probs = prob_df[prob_df["歷史樣本總數"] >= 5]
            if not valid_probs.empty:
                best_kill_row = valid_probs.loc[valid_probs["Raw_Miss_Rate"].idxmax()]
                best_kill_freq = int(best_kill_row["近 N 期出現次數 (M)"].replace(" 次", ""))
                best_kill_prob = best_kill_row["🛡️ 不出機率 (殺牌)"]
                kill_nums = [n for n in range(1, 40) if latest_freq[n] == best_kill_freq]
                
                best_hit_row = valid_probs.loc[valid_probs["Raw_Hit_Rate"].idxmax()]
                best_hit_freq = int(best_hit_row["近 N 期出現次數 (M)"].replace(" 次", ""))
                best_hit_prob = best_hit_row["✨ 開出機率 (做多)"]
                hit_nums = [n for n in range(1, 40) if latest_freq[n] == best_hit_freq]
                
                col_guide1, col_guide2 = st.columns(2)
                with col_guide1:
                    st.error(f"""
                    🛑 **最強殺牌區 (建議剔除)**
                    歷史回測顯示，出現「**{best_kill_freq} 次**」的號碼，下期不開機率高達 **{best_kill_prob}**。
                    明日建議優先剔除：
                    ## `{kill_nums}`
                    """)
                with col_guide2:
                    st.success(f"""
                    🚀 **最強主支區 (建議買進)**
                    歷史回測顯示，出現「**{best_hit_freq} 次**」的號碼，下期開出機率高達 **{best_hit_prob}**。
                    明日建議優先考慮：
                    ## `{hit_nums}`
                    """)
            
            with st.expander("詳細查看：39碼目前各自的頻率狀態"):
                freq_dict = {}
                for n in range(1, 40):
                    f = latest_freq[n]
                    if f not in freq_dict: freq_dict[f] = []
                    freq_dict[f].append(n)
                for f in sorted(freq_dict.keys(), reverse=True):
                    st.write(f"**出現 {f} 次：** {freq_dict[f]}")

    else:
        st.warning(f"⚠️ 資料庫數據不足！需要至少 {test_window + test_periods} 期資料才能進行此回測。")

# ==========================================
# 🖥️ 頁面 5：📖 核心理論白皮書
# ==========================================
elif page == "📖 核心理論白皮書":
    st.title("📖 核心理論與策略解析 (Whitepaper)")
    st.markdown("""
    ### 🎯 系統開發核心理念
    本系統採用了量化金融中經典的**均值回歸**與**動能突破**理論，並將其轉化為彩券分析模型。系統具備雙核心判斷邏輯，並內建動態參數微調面板，允許操作者針對不同的市場週期，隨時改變演算法的嚴格程度。

    ### 🚀 突破號 (冷轉熱) 策略
    此策略源自於股市中的「底部爆量起漲」。透過比對大週期（長線基期）的冷門號碼，在小週期（短線基期）內是否出現異常的資金動能（頻繁開出），來精準捕捉即將發動的強勢主支。

    ### 🛑 十大殺牌防禦機制
    在所有投資市場中，學會「不買什麼」比「買什麼」更能保護本金。系統結合了空間斷層理論（死亡之海）與歷史開出機率，為您自動剃除動能陷入冰凍的十顆地雷，大幅提升投資組合的勝率與期望值。
    
    ### 📊 頻率機率回測 (條件機率)
    利用過去數百期的真實數據，嚴格計算出特定頻率號碼的「真實開出機率」與「不出機率(殺牌機率)」，打破憑感覺選號的盲點，用科學證據尋找莊家破綻。
    """)
