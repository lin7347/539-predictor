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
    "🧬 關聯矩陣(拖牌)實驗室", 
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

if selected_idx + 1 < len(df):
    next_draw = df.loc[selected_idx + 1][['N1', 'N2', 'N3', 'N4', 'N5']].tolist()
else:
    next_draw = []

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
            *(今日無符合條件的起漲號碼)*
            """)

    st.markdown("---")
    st.markdown("### 📊 長短線雙核心深度戰略報表 (實戰動態微調版)")
    
    st.markdown("""
    💡 **圖例說明**： 
    <span style='color: #d9534f; background-color: #fff5f5; border: 1px solid #d9534f; padding: 2px 6px; border-radius: 4px; font-weight: bold;'>紅底框號碼</span> 代表為**基準日當天**開出之號碼。
    <span style='color: #3c763d; background-color: #dff0d8; border: 1px solid #4cae4c; padding: 2px 6px; border-radius: 4px; font-weight: bold;'>綠底框號碼</span> 代表成功命中**下一期**實際開獎！(僅限歷史期數回測可見)
    """, unsafe_allow_html=True)
    
    def get_category_picks_html(picks, category_name):
        sorted_picks = sorted(list(set(picks))) if picks else []
        sub_list = []
        if category_name == "HOT": sub_list = sorted_picks[:5]
        elif category_name == "WARM": sub_list = sorted_picks[5:10] if len(sorted_picks) > 5 else []
        elif category_name == "REPEAT_OR_DEAD":
            if include_repeat: sub_list = [p for p in target_draw if p not in sorted_picks[:10]]
            else: sub_list = target_draw
        elif category_name == "NEUTRAL":
            sub_list = [p for p in range(1, 40) if p not in sorted_picks[:10] and p not in target_draw and not any(s < p < e for s,e in death_seas)]
        elif category_name == "COLD":
            sub_list = [p for p in range(1, 40) if any(s < p < e for s,e in death_seas) and p not in target_draw and p not in sorted_picks[:10]]
        
        if not sub_list: return "無"
        
        formatted = []
        for p in sub_list:
            is_target = p in target_draw
            is_next = p in next_draw
            
            if is_target and is_next:
                formatted.append(f"<span style='color: #fff; background-color: #8a6d3b; padding: 2px 6px; border-radius: 4px; font-weight:bold;'>{p:02d}</span>")
            elif is_next:
                formatted.append(f"<span style='color: #3c763d; background-color: #dff0d8; border: 1px solid #4cae4c; padding: 2px 6px; border-radius: 4px; font-weight:bold;'>{p:02d}</span>")
            elif is_target:
                formatted.append(f"<span style='color: #d9534f; background-color: #fff5f5; border: 1px solid #d9534f; padding: 2px 6px; border-radius: 4px; font-weight:bold;'>{p:02d}</span>")
            else:
                formatted.append(f"<span style='font-size:16px;'>{p:02d}</span>")
                
        return "<span style='line-height: 2.2;'>" + "&nbsp;&nbsp;".join(formatted) + "</span>"

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
<td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(long_picks, 'HOT')}</td>
<td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(short_picks, 'HOT')}</td>
</tr>
<tr>
<td style="padding: 12px; border: 1px solid #ddd;">⭐ **高機率開出**<br>*(強勢輔助)*</td>
<td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(long_picks, 'WARM')}</td>
<td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(short_picks, 'WARM')}</td>
</tr>
<tr>
<td style="padding: 12px; border: 1px solid #ddd;">{row3_icon}</td>
<td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(long_picks, 'REPEAT_OR_DEAD')}</td>
<td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(short_picks, 'REPEAT_OR_DEAD')}</td>
</tr>
<tr>
<td style="padding: 12px; border: 1px solid #ddd;">⚖️ **中等機率**</td>
<td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(long_picks, 'NEUTRAL')}</td>
<td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(short_picks, 'NEUTRAL')}</td>
</tr>
<tr>
<td style="padding: 12px; border: 1px solid #ddd;">❄️ **低機率**</td>
<td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(long_picks, 'COLD')}</td>
<td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(short_picks, 'COLD')}</td>
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
# 🖥️ 頁面 4：📊 頻率機率回測實驗室
# ==========================================
elif page == "📊 頻率機率回測實驗室":
    st.title(f"📊 {game_choice} 頻率機率回測實驗室")
    st.markdown("""
    這裡專門驗證**「條件機率」**：如果一個號碼在過去 N 期內出現了 M 次，它下一期**不開出來（殺牌成功）**的真實機率到底是多少？
    透過歷史回測，我們可以直接找出最安全的**無腦剔除區間**！
    """)
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        test_window = st.number_input("🔍 主期數 (跑回測用，近 N 期)", min_value=5, max_value=100, value=30, step=5)
    with col2:
        test_window_2 = st.number_input("🔭 副期數 (對比動能用，近 M 期)", min_value=5, max_value=300, value=100, step=10)
    with col3:
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
            st.success(f"✅ 回測完成！以下是近 {test_periods} 期內，以【主期數 {test_window} 期】為觀察窗的機率分佈：")
            
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
                    歷史回測顯示，主期數出現「**{best_kill_freq} 次**」的號碼，下期不開機率高達 **{best_kill_prob}**。
                    明日建議優先剔除：
                    ## `{kill_nums}`
                    """)
                with col_guide2:
                    st.success(f"""
                    🚀 **最強主支區 (建議買進)**
                    歷史回測顯示，主期數出現「**{best_hit_freq} 次**」的號碼，下期開出機率高達 **{best_hit_prob}**。
                    明日建議優先考慮：
                    ## `{hit_nums}`
                    """)
            
            with st.expander("🔍 詳細查看：39碼目前各頻率狀態 (視覺標籤升級版)"):
                
                st.markdown("""
                💡 **圖例說明**： 
                <span style='color: #d9534f; background-color: #fff5f5; border: 1px solid #d9534f; padding: 2px 6px; border-radius: 4px; font-weight: bold;'>紅底框號碼</span> 代表為**基準日當天**開出之號碼。
                <span style='color: #3c763d; background-color: #dff0d8; border: 1px solid #4cae4c; padding: 2px 6px; border-radius: 4px; font-weight: bold;'>綠底框號碼</span> 代表成功命中**下一期**實際開獎！(僅限歷史期數回測可見)
                """, unsafe_allow_html=True)
                
                latest_window_2 = historical_df.tail(test_window_2)[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
                latest_freq_2 = pd.Series(0, index=np.arange(1, 40)).add(pd.Series(latest_window_2).value_counts(), fill_value=0).astype(int)
                
                freq_dict = {}
                for n in range(1, 40):
                    f = latest_freq[n]
                    if f not in freq_dict: freq_dict[f] = []
                    freq_dict[f].append(n)
                
                avg_f = test_window * 5 / 39
                
                html_freq_table = f"""
<table style="width:100%; border-collapse: collapse; text-align: left; font-size: 16px; line-height: 2.2;">
<tr style="background-color: #f0f2f6;">
<th style="padding: 12px; border: 1px solid #ddd; width: 20%;">短線熱度 ({test_window}期)</th>
<th style="padding: 12px; border: 1px solid #ddd; width: 80%;">號碼分佈 <span style='font-size:13px; font-weight:normal; color:#666;'>&nbsp;*(灰色括號內為 {test_window_2} 期之長線基期次數)*</span></th>
</tr>
"""
                for f in sorted(freq_dict.keys(), reverse=True):
                    if f >= avg_f * 1.5: icon, color = "🔥", "#d9534f"
                    elif f >= avg_f: icon, color = "⭐", "#f0ad4e"
                    elif f > 1: icon, color = "⚖️", "#333333"
                    elif f == 1: icon, color = "❄️", "#5bc0de"
                    else: icon, color = "💀", "#999999"
                        
                    nums_html = []
                    for n in sorted(freq_dict[f]):
                        long_f = latest_freq_2[n]
                        is_target = n in target_draw
                        is_next = n in next_draw
                        
                        if is_target and is_next:
                            nums_html.append(f"<span style='display:inline-block; margin-right:15px;'><span style='color: #fff; background-color: #8a6d3b; padding: 2px 6px; border-radius: 4px; font-weight:bold; font-size:18px;'>{n:02d}</span> <span style='color:#888; font-size:13px;'>(長: {long_f}次)</span></span>")
                        elif is_next:
                            nums_html.append(f"<span style='display:inline-block; margin-right:15px;'><span style='color: #3c763d; background-color: #dff0d8; border: 1px solid #4cae4c; padding: 2px 6px; border-radius: 4px; font-weight:bold; font-size:18px;'>{n:02d}</span> <span style='color:#888; font-size:13px;'>(長: {long_f}次)</span></span>")
                        elif is_target:
                            nums_html.append(f"<span style='display:inline-block; margin-right:15px;'><span style='color: #d9534f; background-color: #fff5f5; border: 1px solid #d9534f; padding: 2px 6px; border-radius: 4px; font-weight:bold; font-size:18px;'>{n:02d}</span> <span style='color:#d9534f; font-size:13px;'>(長: {long_f}次)</span></span>")
                        else:
                            nums_html.append(f"<span style='display:inline-block; margin-right:15px;'><b style='font-size:18px;'>{n:02d}</b> <span style='color:#888; font-size:13px;'>(長: {long_f}次)</span></span>")
                    
                    nums_str = "".join(nums_html)
                    
                    html_freq_table += f"""
<tr>
<td style="padding: 12px; border: 1px solid #ddd; color: {color};"><b>{icon} 出現 {f} 次</b></td>
<td style="padding: 12px; border: 1px solid #ddd;">{nums_str}</td>
</tr>
"""
                html_freq_table += "</table>"
                
                st.markdown(html_freq_table, unsafe_allow_html=True)

    else:
        st.warning(f"⚠️ 資料庫數據不足！需要至少 {test_window + test_periods} 期資料才能進行此回測。")

# ==========================================
# 🖥️ 頁面 6：🧬 關聯矩陣(拖牌)實驗室 (✨ 殺牌絕緣體大升級版)
# ==========================================
elif page == "🧬 關聯矩陣(拖牌)實驗室":
    st.title(f"🧬 {game_choice} 關聯矩陣 (拖牌與絕緣) 實驗室")
    st.markdown("""
    利用**「馬可夫鏈（Markov Chain）」**概念打造的條件機率尋標器。
    系統會掃描歷史數據庫：**「當某個號碼開出時，下一期哪顆號碼最常跟著開出？又有哪顆號碼『絕對不跟著開』？」** 幫您找出號碼間的最強量子糾纏（買進）與絕對絕緣體（殺牌）！
    """)
    st.markdown("---")
    
    st.header(f"🎯 明日戰略：今日開出號碼的「最強拖牌與絕緣矩陣」")
    st.markdown(f"**今日（基準日）開出號碼：** `{target_draw}`")
    
    lookback = st.slider("歷史追溯期數 (分析過去 N 期內的拖牌關聯)", min_value=50, max_value=500, value=200, step=50)
    
    if len(df) > lookback:
        with st.spinner("正在進行矩陣交叉運算..."):
            hist_subset = historical_df.tail(lookback).reset_index(drop=True)
            
            matrix_data = []
            all_recommendations = []
            all_never_drawn = []
            
            # 針對今天開出的每一顆號碼，去尋找它的歷史拖牌與絕緣牌
            for draw_num in target_draw:
                appearances = 0
                next_draws = []
                
                for i in range(len(hist_subset) - 1):
                    curr_draw = hist_subset.iloc[i][['N1', 'N2', 'N3', 'N4', 'N5']].values
                    if draw_num in curr_draw:
                        appearances += 1
                        next_draws.extend(hist_subset.iloc[i+1][['N1', 'N2', 'N3', 'N4', 'N5']].values)
                
                if appearances > 0:
                    freq = pd.Series(next_draws).value_counts()
                    
                    # 抓出最常跟著開出的前 3 名
                    top_3 = freq.head(3)
                    top_3_str = ", ".join([f"{int(k):02d} ({v}次)" for k, v in top_3.items()])
                    
                    for k in top_3.keys():
                        all_recommendations.append(int(k))
                        
                    # ✨ 核心升級：抓出「0 次開出」的絕對絕緣牌
                    never_drawn_for_this = [n for n in range(1, 40) if n not in freq.index]
                    all_never_drawn.extend(never_drawn_for_this)
                    
                    if never_drawn_for_this:
                        # 如果有從未開出的號碼，直接列出
                        never_drawn_str = ", ".join([f"{n:02d}" for n in never_drawn_for_this])
                    else:
                        # 如果全部39碼都至少開過一次，就列出頻率最低的墊底牌
                        bottom_3 = freq.tail(3)
                        never_drawn_str = "無 0次 (墊底冷牌: " + ", ".join([f"{int(k):02d} ({v}次)" for k, v in bottom_3.items()]) + ")"
                        
                    matrix_data.append({
                        "今日開出號碼": f"{draw_num:02d}",
                        "歷史樣本(次)": appearances,
                        "🏆 下期最常跟著開 (最強拖牌)": top_3_str,
                        "🛑 下期從未跟著開 (絕對絕緣)": never_drawn_str
                    })
            
            if matrix_data:
                matrix_df = pd.DataFrame(matrix_data)
                st.dataframe(matrix_df, use_container_width=True)
                
                col_res1, col_res2 = st.columns(2)
                
                with col_res1:
                    # 尋找「共振主支」：被多顆號碼同時拖出的牌
                    rec_counts = pd.Series(all_recommendations).value_counts()
                    strong_resonances = rec_counts[rec_counts >= 2].index.tolist()
                    
                    if strong_resonances:
                        st.success(f"""
                        ### 🔥 終極共振主支 (建議買進)
                        ## `{sorted(strong_resonances)}`
                        *(這些號碼同時被今日「多顆」號碼強烈拖出，爆發機率極高！)*
                        """)
                    else:
                        st.info("### 🔥 終極共振主支\n*(今日號碼拖牌較為分散，無強烈共振現象，請直接參考上方表格的首選拖牌)*")

                with col_res2:
                    # 尋找「共振殺牌」：被多顆號碼同時排斥 (0次拖出) 的牌
                    kill_counts = pd.Series(all_never_drawn).value_counts()
                    
                    # 只要被今天開出的其中 3 顆以上號碼給「聯合排斥」，就是神級殺牌
                    strong_kills = kill_counts[kill_counts >= 3].index.tolist()
                    
                    if strong_kills:
                        st.error(f"""
                        ### 🛡️ 終極共振絕緣牌 (強力殺牌)
                        ## `{sorted(strong_kills)}`
                        *(這些號碼被今日高達 3 顆以上的號碼「聯合排斥(0次紀錄)」，下期極難開出，建議大膽剔除！)*
                        """)
                    else:
                        # 退一步看有沒有被 2 顆號碼排斥的
                        strong_kills_2 = kill_counts[kill_counts >= 2].index.tolist()
                        if strong_kills_2:
                            st.error(f"""
                            ### 🛡️ 次級共振絕緣牌 (建議殺牌)
                            ## `{sorted(strong_kills_2)}`
                            *(這些號碼被今日 2 顆號碼聯合排斥，建議優先避開)*
                            """)
                        else:
                            st.info("### 🛡️ 終極共振絕緣牌\n*(今日無明顯的聯合排斥現象，請參考表格中各號碼的絕緣牌)*")
            else:
                st.warning("歷史數據不足以分析這些號碼的拖牌。")

        st.markdown("---")
        
        # ==========================================
        # 🔍 手動拖牌查詢器
        # ==========================================
        st.header("🔍 手動拖牌與殺牌查詢器")
        target_num = st.selectbox("選擇要分析的『母體號碼』", range(1, 40), index=0)
        
        appearances = 0
        next_draws = []
        for i in range(len(hist_subset) - 1):
            curr_draw = hist_subset.iloc[i][['N1', 'N2', 'N3', 'N4', 'N5']].values
            if target_num in curr_draw:
                appearances += 1
                next_draws.extend(hist_subset.iloc[i+1][['N1', 'N2', 'N3', 'N4', 'N5']].values)
                
        if appearances > 0:
            st.write(f"過去 **{lookback} 期** 中，號碼 **{target_num:02d}** 共開出 **{appearances} 次**。")
            freq = pd.Series(next_draws).value_counts().reset_index()
            freq.columns = ['下期開出號碼', '開出次數']
            freq['拖牌機率'] = (freq['開出次數'] / appearances * 100).round(1).astype(str) + " %"
            
            # ✨ 抓出絕對不會跟著這顆號碼開的「絕緣體」
            never_drawn_manual = [n for n in range(1, 40) if n not in next_draws]
            if never_drawn_manual:
                st.error(f"🛑 **絕對絕緣體 (0次開出)**：在過去 {lookback} 期中，只要 **{target_num:02d}** 開出，**從未**跟著開出的號碼有： `{never_drawn_manual}`")
            
            col_chart1, col_chart2 = st.columns([1, 2])
            with col_chart1:
                st.dataframe(freq.head(10), hide_index=True)
            with col_chart2:
                chart_data = freq.head(10).set_index('下期開出號碼')['開出次數']
                st.bar_chart(chart_data, color="#f0ad4e")
        else:
            st.write(f"在過去 {lookback} 期內，沒有找到號碼 {target_num} 的開出紀錄。")
            
    else:
        st.warning(f"⚠️ 資料庫數據不足！需要至少 {lookback} 期資料才能進行拖牌分析。")

# ==========================================
# 🖥️ 頁面 7：📖 核心理論白皮書
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
    
    ### 🧬 馬可夫鏈關聯矩陣 (拖牌與絕緣)
    不看單一號碼，而是計算號碼間的「量子糾纏」。透過海量歷史數據比對出「A 開出後最容易開出 B (拖牌)」以及「A 開出後絕對不開 C (絕緣)」的規律。透過多顆號碼的交叉共振，能找出極高勝率的主支與殺牌。
    """)
