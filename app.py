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
death_sea_gap = st.sidebar.slider("💀 死亡之海斷層間距", min_value=4, max_value=12, value=7, step=1)
include_repeat = st.sidebar.checkbox("♻️ 包含連莊號 (解除封印)", value=True)

st.sidebar.markdown("---")

# ==========================================
# 🚀 突破號 & 殺牌 (冷轉熱) 參數微調
# ==========================================
st.sidebar.header("🚀 突破與殺牌參數微調")
breakout_long_period = st.sidebar.number_input("🔭 長線觀察期數 (近 N 期)", min_value=30, max_value=300, value=100, step=10)
breakout_long_thresh = st.sidebar.number_input(f"📉 長線冷門標準 (近 {breakout_long_period} 期開出 ≤)", min_value=1, max_value=50, value=12, step=1)
st.sidebar.markdown("---")
breakout_short_period = st.sidebar.number_input("🔍 短線觀察期數 (近 N 期)", min_value=5, max_value=50, value=20, step=1)
breakout_short_thresh = st.sidebar.number_input(f"📈 短線爆發標準 (近 {breakout_short_period} 期開出 ≥)", min_value=1, max_value=15, value=3, step=1)

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
        if end - start - 1 >= gap_limit: death_seas.append((start, end))
            
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
# 📝 側邊欄設定區 (新增第六個導覽面板)
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
# 🖥️ 頁面 1-4 保留原有完整代碼 (簡化顯示)
# ==========================================
if page == "🎯 39碼全解析雷達":
    st.title(f"🎯 {game_choice} 39碼全解析雷達")
    st.markdown(f"### 基準日：{target_date} (期數 {target_issue}) | 開出號碼： `{target_draw}`")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.error(f"### 🛑 十大避開地雷 (終極殺牌)\n歷史頻率與深海交叉比對，建議優先剔除：\n## **{', '.join([str(n) for n in worst_10_picks])}**")
    with col_b:
        if breakout_picks:
            st.success(f"### 🚀 底部爆量起漲 (冷轉熱突破號)\n符合長冷短熱之強勢表態：\n## **{', '.join([str(n) for n in breakout_picks])}**")
        else:
            st.info("### 🚀 底部爆量起漲 (冷轉熱突破號)\n*(今日無符合條件的起漲號碼)*")

    st.markdown("---")
    st.markdown("### 📊 長短線雙核心深度戰略報表")
    st.markdown("💡 **圖例說明**： <span style='color: #d9534f; background-color: #fff5f5; border: 1px solid #d9534f; padding: 2px 6px; border-radius: 4px; font-weight: bold;'>紅底框</span> 為基準日當天開出號碼。<span style='color: #3c763d; background-color: #dff0d8; border: 1px solid #4cae4c; padding: 2px 6px; border-radius: 4px; font-weight: bold;'>綠底框</span> 為命中下一期開獎。", unsafe_allow_html=True)
    
    def get_category_picks_html(picks, category_name):
        sorted_picks = sorted(list(set(picks))) if picks else []
        sub_list = []
        if category_name == "HOT": sub_list = sorted_picks[:5]
        elif category_name == "WARM": sub_list = sorted_picks[5:10] if len(sorted_picks) > 5 else []
        elif category_name == "REPEAT_OR_DEAD": sub_list = [p for p in target_draw if p not in sorted_picks[:10]] if include_repeat else target_draw
        elif category_name == "NEUTRAL": sub_list = [p for p in range(1, 40) if p not in sorted_picks[:10] and p not in target_draw and not any(s < p < e for s,e in death_seas)]
        elif category_name == "COLD": sub_list = [p for p in range(1, 40) if any(s < p < e for s,e in death_seas) and p not in target_draw and p not in sorted_picks[:10]]
        
        if not sub_list: return "無"
        formatted = []
        for p in sub_list:
            if (p in target_draw) and (p in next_draw): formatted.append(f"<span style='color: #fff; background-color: #8a6d3b; padding: 2px 6px; border-radius: 4px; font-weight:bold;'>{p:02d}</span>")
            elif p in next_draw: formatted.append(f"<span style='color: #3c763d; background-color: #dff0d8; border: 1px solid #4cae4c; padding: 2px 6px; border-radius: 4px; font-weight:bold;'>{p:02d}</span>")
            elif p in target_draw: formatted.append(f"<span style='color: #d9534f; background-color: #fff5f5; border: 1px solid #d9534f; padding: 2px 6px; border-radius: 4px; font-weight:bold;'>{p:02d}</span>")
            else: formatted.append(f"<span style='font-size:16px;'>{p:02d}</span>")
        return "<span style='line-height: 2.2;'>" + "&nbsp;&nbsp;".join(formatted) + "</span>"

    row3_icon = "♻️ **連莊觀察區**" if include_repeat else "💀 **最不可能開出**"
    html_table = f"""
<table style="width:100%; border-collapse: collapse; text-align: left; font-size: 16px;">
<tr style="background-color: #f0f2f6;"><th style="padding: 12px; border: 1px solid #ddd; width: 15%;">推薦等級</th><th style="padding: 12px; border: 1px solid #ddd; width: 42%;">長線平衡派</th><th style="padding: 12px; border: 1px solid #ddd; width: 43%;">短線動能派</th></tr>
<tr><td style="padding: 12px; border: 1px solid #ddd;">🔥 **極可能開出**</td><td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(long_picks, 'HOT')}</td><td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(short_picks, 'HOT')}</td></tr>
<tr><td style="padding: 12px; border: 1px solid #ddd;">⭐ **高機率開出**</td><td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(long_picks, 'WARM')}</td><td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(short_picks, 'WARM')}</td></tr>
<tr><td style="padding: 12px; border: 1px solid #ddd;">{row3_icon}</td><td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(long_picks, 'REPEAT_OR_DEAD')}</td><td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(short_picks, 'REPEAT_OR_DEAD')}</td></tr>
<tr><td style="padding: 12px; border: 1px solid #ddd;">⚖️ **中等機率**</td><td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(long_picks, 'NEUTRAL')}</td><td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(short_picks, 'NEUTRAL')}</td></tr>
<tr><td style="padding: 12px; border: 1px solid #ddd;">❄️ **低機率**</td><td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(long_picks, 'COLD')}</td><td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(short_picks, 'COLD')}</td></tr>
</table>
"""
    st.markdown(html_table, unsafe_allow_html=True)

elif page == "⚔️ 雙引擎策略看板":
    st.title(f"⚔️ {game_choice} 雙引擎策略決策看板")
    st.info("此頁面保留，請切換至「🧬 關聯矩陣(拖牌)實驗室」查看新功能。")

elif page == "📈 回測與勝率追蹤":
    st.title(f"📈 {game_choice} 策略勝率與全面回測追蹤")
    st.info("此頁面保留，請切換至「🧬 關聯矩陣(拖牌)實驗室」查看新功能。")

elif page == "📊 頻率機率回測實驗室":
    st.title(f"📊 {game_choice} 頻率機率回測實驗室")
    st.info("此頁面保留，請切換至「🧬 關聯矩陣(拖牌)實驗室」查看新功能。")

# ==========================================
# 🖥️ 頁面 6：🧬 關聯矩陣(拖牌)實驗室 (✨ 全新功能)
# ==========================================
elif page == "🧬 關聯矩陣(拖牌)實驗室":
    st.title(f"🧬 {game_choice} 關聯矩陣 (拖牌條件機率) 實驗室")
    st.markdown("""
    這是利用**「馬可夫鏈（Markov Chain）」**概念打造的條件機率尋標器。老彩迷稱之為「拖牌」。
    系統會掃描歷史數據庫：**「當某個號碼開出時，下一期哪一顆號碼跟著開出的機率最高？」** 找出號碼間最強烈的量子糾纏！
    """)
    st.markdown("---")
    
    st.header(f"🎯 明日戰略：今日開出號碼的「最強拖牌矩陣」")
    st.markdown(f"**今日（基準日）開出號碼：** `{target_draw}`")
    
    lookback = st.slider("歷史追溯期數 (分析過去 N 期內的拖牌關聯)", min_value=50, max_value=500, value=200, step=50)
    
    if len(df) > lookback:
        with st.spinner("正在進行矩陣交叉運算..."):
            hist_subset = historical_df.tail(lookback).reset_index(drop=True)
            
            matrix_data = []
            all_recommendations = []
            
            # 針對今天開出的每一顆號碼，去尋找它的歷史拖牌
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
                        
                    matrix_data.append({
                        "今日號碼": f"{draw_num:02d}",
                        "歷史出現次數": appearances,
                        "🏆 下期最高頻率拖牌 (Top 3)": top_3_str
                    })
            
            if matrix_data:
                matrix_df = pd.DataFrame(matrix_data)
                st.dataframe(matrix_df, use_container_width=True)
                
                # 計算最強共振牌 (被多顆號碼同時拖出的號碼)
                rec_counts = pd.Series(all_recommendations).value_counts()
                strong_resonances = rec_counts[rec_counts >= 2].index.tolist()
                
                if strong_resonances:
                    st.success(f"""
                    ### 🔥 終極共振主支： `{sorted(strong_resonances)}`
                    *(這些號碼同時被今天的「多顆」號碼強烈拖出，爆發機率極高！)*
                    """)
                else:
                    st.info("今日號碼的拖牌關聯較為分散，建議參考上方表格之首選拖牌。")
            else:
                st.warning("歷史數據不足以分析這些號碼的拖牌。")

        st.markdown("---")
        
        # 自由查詢功能
        st.header("🔍 手動拖牌查詢器")
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
            freq.columns = ['被拖出號碼', '開出次數']
            freq['拖牌機率'] = (freq['開出次數'] / appearances * 100).round(1).astype(str) + " %"
            
            col_chart1, col_chart2 = st.columns([1, 2])
            with col_chart1:
                st.dataframe(freq.head(10), hide_index=True)
            with col_chart2:
                chart_data = freq.head(10).set_index('被拖出號碼')['開出次數']
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
