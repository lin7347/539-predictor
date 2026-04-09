import streamlit as st
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
import json

st.set_page_config(page_title="量化雷達 雙彩種切換版", layout="wide")

# ==========================================
# ⚙️ 系統與資料庫設定模組
# ==========================================
class DatabaseManager:
    @staticmethod
    def get_google_sheet(sheet_name):
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(st.secrets["gcp_json"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        doc = client.open_by_url("https://docs.google.com/spreadsheets/d/1PrG36Oebngqhm7DrhEUNpfTtSk8k50jdAo2069aBJw8/edit?gid=978302798#gid=978302798")
        return doc.worksheet(sheet_name)

    @staticmethod
    @st.cache_data(ttl=600)
    def load_data(game_name):
        sheet = DatabaseManager.get_google_sheet(game_name)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if df.empty: return pd.DataFrame(columns=['Date', 'Issue', 'N1', 'N2', 'N3', 'N4', 'N5'])
        rename_dict = {'Date (開獎日期)': 'Date', 'Issue (期數)': 'Issue', 'N1 (號碼1)': 'N1', 'N2 (號碼2)': 'N2', 'N3 (號碼3)': 'N3', 'N4 (號碼4)': 'N4', 'N5 (號碼5)': 'N5'}
        df = df.rename(columns=rename_dict)
        df['Issue'] = pd.to_numeric(df['Issue'], errors='coerce')
        df = df.dropna(subset=['Issue'])
        df['Issue'] = df['Issue'].astype(int)
        return df

# ==========================================
# 🧠 空間演算法核心引擎 (HFT 升級版)
# ==========================================
class LotteryEngine:
    @staticmethod
    def analyze(target_draw, gap_limit, allow_repeat, s_long_series, s_short_series, 
                long_thresh, short_thresh, momentum_multiplier, deep_freeze_only,
                long_period, short_period):
        
        target_draw = sorted(target_draw)
        extended_draw = [0] + target_draw + [40]
        
        # 1. 斷層計算
        death_seas = [(extended_draw[i], extended_draw[i+1]) for i in range(len(extended_draw)-1) if extended_draw[i+1] - extended_draw[i] - 1 >= gap_limit]
                
        # 2. 短線推薦
        short_picks = []
        for n in target_draw:
            for c in [n-1, n+1]:
                if 1 <= c <= 39 and not any(sea_start < c < sea_end for sea_start, sea_end in death_seas):
                    short_picks.append(int(c))
        if allow_repeat: short_picks.extend(target_draw)
        short_picks = list(set(short_picks))
                
        # 3. 夾心與斷層中心
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
        tail_resonances = [n for t in hot_tails for n in range(1, 40) if n % 10 == t] if hot_tails else []

        if not allow_repeat:
            short_picks = [p for p in short_picks if p not in target_draw]
            sandwiches = [p for p in sandwiches if p not in target_draw]
            geometric_centers = [p for p in geometric_centers if p not in target_draw]
            tail_resonances = [p for p in tail_resonances if p not in target_draw]

        long_picks = list(set(geometric_centers + sandwiches + tail_resonances))
        consensus_picks = sorted(list(set(short_picks).intersection(set(long_picks))))
        
        # 🛡️ 4. HFT 級絕緣殺牌計算
        worst_10_picks = []
        absolute_dead_pool = []
        
        if s_long_series is not None:
            # 尋找「身處死亡之海且短線0次」的絕對冰凍牌
            for p in range(1, 40):
                is_in_death_sea = any(s < p < e for s,e in death_seas)
                if is_in_death_sea and s_short_series.get(p, 0) == 0 and p not in target_draw:
                    absolute_dead_pool.append(p)

            cold_nums = [p for p in range(1, 40) if any(s < p < e for s,e in death_seas) and p not in target_draw and p not in short_picks[:10] and p not in long_picks[:10]]
            neutral_nums = [p for p in range(1, 40) if p not in target_draw and p not in short_picks[:10] and p not in long_picks[:10] and p not in cold_nums]
            
            cold_sorted = sorted(cold_nums, key=lambda x: s_long_series.get(x, 0))
            neutral_sorted = sorted(neutral_nums, key=lambda x: s_long_series.get(x, 0))
            dead_pool = target_draw if not allow_repeat else []
            
            # 根據深凍開關決定殺牌嚴格度
            if deep_freeze_only:
                worst_10_pool = absolute_dead_pool + dead_pool + cold_sorted
            else:
                worst_10_pool = absolute_dead_pool + dead_pool + cold_sorted + neutral_sorted
                
            # 去除重複並取前十
            for p in worst_10_pool:
                if p not in worst_10_picks: worst_10_picks.append(p)
            worst_10_picks = worst_10_picks[:10]

        # 🚀 5. HFT 級動能倍數計算 (突破號)
        breakout_picks = []
        if s_long_series is not None and s_short_series is not None:
            for p in range(1, 40):
                # 計算真實平均發生率
                long_avg_freq = s_long_series.get(p, 0) / long_period if long_period > 0 else 0.001
                short_avg_freq = s_short_series.get(p, 0) / short_period if short_period > 0 else 0
                
                # 必須滿足：1.長線冷 2.短線熱 3.短線動能大於長線倍數
                if s_long_series.get(p, 0) <= long_thresh and s_short_series.get(p, 0) >= short_thresh:
                    if short_avg_freq >= (long_avg_freq * momentum_multiplier):
                        if p not in worst_10_picks: breakout_picks.append(p)
        
        return {
            "short_picks": short_picks, "long_picks": long_picks, "consensus_picks": consensus_picks,
            "death_seas": death_seas, "sandwiches": sandwiches, "geometric_centers": geometric_centers,
            "tail_resonances": tail_resonances, "max_gap": max_gap, "worst_10_picks": worst_10_picks,
            "breakout_picks": breakout_picks
        }

# ==========================================
# 🎨 UI 輔助繪圖組件 (不變)
# ==========================================
def render_html_table(long_picks, short_picks, target_draw, next_draw, include_repeat, death_seas):
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
            is_target, is_next = (p in target_draw), (p in next_draw)
            if is_target and is_next: formatted.append(f"<span style='color: #fff; background-color: #8a6d3b; padding: 2px 6px; border-radius: 4px; font-weight:bold;'>{p:02d}</span>")
            elif is_next: formatted.append(f"<span style='color: #3c763d; background-color: #dff0d8; border: 1px solid #4cae4c; padding: 2px 6px; border-radius: 4px; font-weight:bold;'>{p:02d}</span>")
            elif is_target: formatted.append(f"<span style='color: #d9534f; background-color: #fff5f5; border: 1px solid #d9534f; padding: 2px 6px; border-radius: 4px; font-weight:bold;'>{p:02d}</span>")
            else: formatted.append(f"<span style='font-size:16px;'>{p:02d}</span>")
        return "<span style='line-height: 2.2;'>" + "&nbsp;&nbsp;".join(formatted) + "</span>"

    row3_icon = "♻️ **連莊觀察區**<br>*(昨日開出)*" if include_repeat else "💀 **最不可能開出**<br>*(全殺棄子)*"
    return f"""<table style="width:100%; border-collapse: collapse; text-align: left; font-size: 16px;">
    <tr style="background-color: #f0f2f6;"><th style="padding: 12px; border: 1px solid #ddd; width: 15%;">推薦等級</th><th style="padding: 12px; border: 1px solid #ddd; width: 42%;">長線平衡派</th><th style="padding: 12px; border: 1px solid #ddd; width: 43%;">短線動能派</th></tr>
    <tr><td style="padding: 12px; border: 1px solid #ddd;">🔥 **極可能開出**</td><td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(long_picks, 'HOT')}</td><td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(short_picks, 'HOT')}</td></tr>
    <tr><td style="padding: 12px; border: 1px solid #ddd;">⭐ **高機率開出**</td><td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(long_picks, 'WARM')}</td><td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(short_picks, 'WARM')}</td></tr>
    <tr><td style="padding: 12px; border: 1px solid #ddd;">{row3_icon}</td><td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(long_picks, 'REPEAT_OR_DEAD')}</td><td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(short_picks, 'REPEAT_OR_DEAD')}</td></tr>
    <tr><td style="padding: 12px; border: 1px solid #ddd;">⚖️ **中等機率**</td><td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(long_picks, 'NEUTRAL')}</td><td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(short_picks, 'NEUTRAL')}</td></tr>
    <tr><td style="padding: 12px; border: 1px solid #ddd;">❄️ **低機率**</td><td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(long_picks, 'COLD')}</td><td style="padding: 12px; border: 1px solid #ddd;">{get_category_picks_html(short_picks, 'COLD')}</td></tr>
    </table>"""

# ==========================================
# 📝 側邊欄設定區 (新增 HFT 參數)
# ==========================================
st.sidebar.title("🎲 選擇分析彩種")
game_choice = st.sidebar.radio("目前分析目標：", ["539", "天天樂"])
if st.sidebar.button("🔄 強制同步雲端資料庫"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("⚙️ 演算法參數微調")
death_sea_gap = st.sidebar.slider("💀 死亡之海斷層間距", min_value=4, max_value=12, value=7, step=1)
include_repeat = st.sidebar.checkbox("♻️ 包含連莊號 (解除封印)", value=True)

st.sidebar.markdown("---")
st.sidebar.header("🚀 突破與殺牌參數微調")
breakout_long_period = st.sidebar.number_input("🔭 長線觀察期數 (近 N 期)", min_value=30, max_value=300, value=100, step=10)
breakout_long_thresh = st.sidebar.number_input(f"📉 長線冷門標準 (開出 ≤)", min_value=1, max_value=50, value=12, step=1)
st.sidebar.markdown("---")
breakout_short_period = st.sidebar.number_input("🔍 短線觀察期數 (近 N 期)", min_value=5, max_value=50, value=20, step=1)
breakout_short_thresh = st.sidebar.number_input(f"📈 短線爆發標準 (開出 ≥)", min_value=1, max_value=15, value=3, step=1)

# 💡 這裡就是新加入的 HFT 面板
st.sidebar.markdown("---")
st.sidebar.header("🧠 量化模型進階微調 (HFT 級)")
momentum_multiplier = st.sidebar.slider("⚡ 動能爆發倍數", min_value=1.1, max_value=3.0, value=1.5, step=0.1, help="短線發生頻率必須大於長線平均的幾倍，才算真實突破。數值越高，抓出的突破號越少但越精準。")
deep_freeze_only = st.sidebar.checkbox("🌌 僅殺『死亡之海』內的絕緣牌", value=False, help="打勾後，系統只會把身處死亡斷層中且短線為0次的號碼列為殺牌，防守更保守嚴格。")

st.sidebar.markdown("---")
st.sidebar.title("🧭 系統導覽")
page = st.sidebar.radio("選擇分析面板：", [
    "🎯 39碼全解析雷達", "⚔️ 雙引擎策略看板", "📈 回測與勝率追蹤", 
    "📊 頻率機率回測實驗室", "🧬 關聯矩陣(拖牌)實驗室", "📖 核心理論白皮書"
])

df = DatabaseManager.load_data(game_choice)

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
    st.stop()

auto_next_issue = int(df.iloc[-1]['Issue']) + 1 if not df.empty else 1
auto_next_date = (pd.to_datetime(df.iloc[-1]['Date']) + pd.Timedelta(days=1)).strftime('%Y-%m-%d') if not df.empty else "2026-03-01"

with st.sidebar.expander(f"📝 輸入【{game_choice}】最新開獎號碼"):
    new_date = st.text_input("開獎日期 (YYYY-MM-DD)", value=auto_next_date)
    new_issue = st.number_input("期數", min_value=1, value=auto_next_issue, step=1)
    n1, n2, n3, n4, n5 = [st.number_input(f"號碼 {i}", min_value=1, max_value=39, value=i) for i in range(1, 6)]
    if st.button("🚀 寫入雲端並重新計算"):
        if new_issue in df['Issue'].values: st.error(f"⚠️ 期數 {new_issue} 已經存在！")
        else:
            sorted_nums = sorted([n1, n2, n3, n4, n5])
            new_row = [new_date, new_issue] + sorted_nums
            with st.spinner(f'正在寫入 {game_choice} Google 雲端資料庫...'):
                sheet = DatabaseManager.get_google_sheet(game_choice)
                sheet.append_row(new_row, value_input_option="USER_ENTERED")
            st.success(f"✅ 成功寫入期數 {new_issue}！")
            st.cache_data.clear()
            st.rerun()

# ==========================================
# 🧠 當前選定日的狀態計算
# ==========================================
historical_df = df.loc[:selected_idx]
target_draw = historical_df.iloc[-1][['N1', 'N2', 'N3', 'N4', 'N5']].tolist()
target_date = historical_df.iloc[-1]['Date']
target_issue = historical_df.iloc[-1]['Issue']
next_draw = df.loc[selected_idx + 1][['N1', 'N2', 'N3', 'N4', 'N5']].tolist() if selected_idx + 1 < len(df) else []

nums_long = historical_df.tail(breakout_long_period)[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
s_long = pd.Series(0, index=np.arange(1, 40)).add(pd.Series(nums_long).value_counts(), fill_value=0).astype(int)

nums_short = historical_df.tail(breakout_short_period)[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
s_short = pd.Series(0, index=np.arange(1, 40)).add(pd.Series(nums_short).value_counts(), fill_value=0).astype(int)

# 💡 傳入所有新參數給核心引擎
analysis_res = LotteryEngine.analyze(
    target_draw, death_sea_gap, include_repeat, s_long, s_short, 
    breakout_long_thresh, breakout_short_thresh, 
    momentum_multiplier, deep_freeze_only,
    breakout_long_period, breakout_short_period
)

# ==========================================
# 🖥️ 頁面渲染邏輯 (主面板不變)
# ==========================================
if page == "🎯 39碼全解析雷達":
    st.title(f"🎯 {game_choice} 39碼全解析雷達")
    st.markdown(f"### 基準日：{target_date} (期數 {target_issue}) | 開出號碼： `{target_draw}`")
    col_a, col_b = st.columns(2)
    with col_a: st.error(f"### 🛑 十大避開地雷 (終極殺牌)\n## **{', '.join([str(n) for n in analysis_res['worst_10_picks']])}**")
    with col_b:
        if analysis_res['breakout_picks']: st.success(f"### 🚀 底部爆量起漲 (冷轉熱突破號)\n## **{', '.join([str(n) for n in analysis_res['breakout_picks']])}**")
        else: st.info("### 🚀 底部爆量起漲 (冷轉熱突破號)\n*(今日無符合倍數條件的起漲號碼)*")
    st.markdown("---")
    st.markdown("### 📊 長短線雙核心深度戰略報表 (實戰動態微調版)")
    st.markdown(render_html_table(analysis_res['long_picks'], analysis_res['short_picks'], target_draw, next_draw, include_repeat, analysis_res['death_seas']), unsafe_allow_html=True)

elif page == "⚔️ 雙引擎策略看板":
    st.title(f"⚔️ {game_choice} 雙引擎策略決策看板")
    st.markdown(f"### 基準日：{target_date} (期數 {target_issue}) | 開出號碼： `{target_draw}`")
    col1, col2 = st.columns(2)
    with col1:
        st.error("🔴 短線動能派")
        st.info(f"建議名單： {analysis_res['short_picks']}" if analysis_res['short_picks'] else "*(今日無)*")
        st.markdown(f"#### 💀 避開死水 (斷層 > {death_sea_gap})")
        if analysis_res['death_seas']:
            for sea in analysis_res['death_seas']: st.warning(f"🚫 `{sea[0]+1:02d} ~ {sea[1]-1:02d}` (間距: {sea[1]-sea[0]-1})")
        else: st.success("今日無大型斷層區。")
    with col2:
        st.info("🔵 長線平衡派")
        st.markdown(f"#### 🎯 史詩斷層 (最大間距: {analysis_res['max_gap']})")
        st.error(f"建議名單： {analysis_res['geometric_centers']}" if analysis_res['geometric_centers'] else "*(無明顯斷層)*")
        st.markdown("#### 🥪 黃金對稱 (必補夾心)")
        st.error(f"建議名單： {analysis_res['sandwiches']}" if analysis_res['sandwiches'] else "*(今日未成形)*")
        st.markdown("#### 🧲 同尾數共鳴")
        st.error(f"建議名單： {analysis_res['tail_resonances']}" if analysis_res['tail_resonances'] else "*(無)*")
    st.markdown("---")
    if analysis_res['consensus_picks']: st.success(f"### 🎯 雙重共識極高勝率主支： {analysis_res['consensus_picks']}")
    else: st.warning("今日兩派未達成共識，建議分開參考上方指標。")

elif page == "📈 回測與勝率追蹤":
    st.title(f"📈 {game_choice} 策略勝率與全面回測追蹤")
    test_periods = 100
    if len(df) > test_periods:
        results = []
        for i in range(len(df) - test_periods - 1, len(df) - 1):
            past_draw = df.iloc[i][['N1', 'N2', 'N3', 'N4', 'N5']].tolist()
            actual_next_draw = df.iloc[i+1][['N1', 'N2', 'N3', 'N4', 'N5']].tolist()
            hist_bt = df.iloc[:i+1]
            s_long_bt = pd.Series(0, index=np.arange(1, 40)).add(pd.Series(hist_bt.tail(breakout_long_period)[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()).value_counts(), fill_value=0).astype(int)
            s_short_bt = pd.Series(0, index=np.arange(1, 40)).add(pd.Series(hist_bt.tail(breakout_short_period)[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()).value_counts(), fill_value=0).astype(int)
            
            # 💡 同步傳入回測所需的 HFT 新參數
            res_bt = LotteryEngine.analyze(
                past_draw, death_sea_gap, include_repeat, s_long_bt, s_short_bt, 
                breakout_long_thresh, breakout_short_thresh,
                momentum_multiplier, deep_freeze_only,
                breakout_long_period, breakout_short_period
            )
            
            results.append({
                "Date": df.iloc[i+1]['Date'], "✅ 實際開獎": str(actual_next_draw),
                "🔴 短線推薦": str(res_bt['short_picks']), "🔴 命中": len(set(res_bt['short_picks']).intersection(set(actual_next_draw))),
                "🔵 長線推薦": str(res_bt['long_picks']), "🔵 命中": len(set(res_bt['long_picks']).intersection(set(actual_next_draw))),
                "🚀 突破轉強": str(res_bt['breakout_picks']), "🚀 命中數": len(set(res_bt['breakout_picks']).intersection(set(actual_next_draw))),
                "💀 十大殺牌": str(res_bt['worst_10_picks']), "🛡️ 成功閃避": 10 - len(set(res_bt['worst_10_picks']).intersection(set(actual_next_draw)))
            })
        res_df = pd.DataFrame(results).set_index("Date")
        res_df["🔴 短線累積"] = res_df["🔴 命中"].cumsum()
        res_df["🔵 長線累積"] = res_df["🔵 命中"].cumsum()
        col1, col2, col3 = st.columns(3)
        col1.metric("🔴 短線累積命中", f"{res_df['🔴 短線累積'].iloc[-1]} 顆")
        col2.metric("🔵 長線累積命中", f"{res_df['🔵 長線累積'].iloc[-1]} 顆")
        col3.metric("🛡️ 殺牌防守率", f"{(res_df['🛡️ 成功閃避'].sum() / (len(res_df)*10) * 100):.1f} %")
        st.line_chart(res_df[["🔴 短線累積", "🔵 長線累積"]])
        with st.expander("📝 展開查看明細"): st.dataframe(res_df, use_container_width=True)

# ===== 以下為保留原本架構的實驗室模組 (省略部分以維持輸出長度，請保留您原本檔案中的 📊 與 🧬 實驗室程式碼) =====
elif page in ["📊 頻率機率回測實驗室", "🧬 關聯矩陣(拖牌)實驗室", "📖 核心理論白皮書"]:
    st.info("請將這段之後的程式碼，保留您原本檔案中的 📊 頻率實驗室、🧬 關聯矩陣實驗室 與 📖 白皮書 的區塊即可！")
