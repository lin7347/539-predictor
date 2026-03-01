import streamlit as st
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
import json

st.set_page_config(page_title="量化雷達 雙彩種切換版", layout="wide")

# ==========================================
# 📝 側邊欄設定區 (導覽、時光機、新增數據)
# ==========================================
st.sidebar.title("🧭 系統導覽")
page = st.sidebar.radio("選擇分析面板：", [
    "🎯 39碼全解析雷達", 
    "⚔️ 雙引擎策略看板", 
    "📈 回測與勝率追蹤", 
    "📖 核心理論白皮書"
])

st.sidebar.markdown("---")
st.sidebar.header("⏳ 時光機設定")

# 檢查資料庫是否有資料，避免天天樂剛建好時報錯
if not df.empty:
    options = df.index.tolist()
    options.reverse()
    def format_option(idx):
        row = df.loc[idx]
        return f"期數 {row['Issue']} ({row['Date']})"
    selected_idx = st.sidebar.selectbox("選擇分析基準日：", options, format_func=format_option, key=f"time_machine_{game_choice}")
else:
    st.sidebar.warning(f"⚠️ 你的【{game_choice}】資料庫目前是空的！請先新增開獎數據。")
    selected_idx = None

st.sidebar.markdown("---")

# 🤖 智慧自動遞增邏輯：讀取最後一筆資料來決定預設值
if not df.empty:
    # 抓取最後一筆期數，自動 +1
    auto_next_issue = int(df.iloc[-1]['Issue']) + 1
    # 抓取最後一筆日期，自動加一天
    try:
        last_date = pd.to_datetime(df.iloc[-1]['Date'])
        auto_next_date = (last_date + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    except:
        # 如果日期格式有誤讀不出來，給一個備用預設值
        auto_next_date = "2026-03-01"
else:
    auto_next_issue = 1
    auto_next_date = "2026-03-01"

with st.sidebar.expander(f"📝 輸入【{game_choice}】最新開獎號碼"):
    # 這裡的 value 已經換成了剛剛算出來的最新推測值！
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
            st.error(f"⚠️ 期數 {new_issue} 已經存在【{game_choice}】資料庫中了！")
        else:
            sorted_nums = sorted([n1, n2, n3, n4, n5])
            new_row = [new_issue, new_date, sorted_nums[0], sorted_nums[1], sorted_nums[2], sorted_nums[3], sorted_nums[4]]
            with st.spinner(f'正在寫入 {game_choice} Google 雲端資料庫...'):
                sheet = get_google_sheet(game_choice)
                sheet.append_row(new_row)
            st.success(f"✅ 成功將期數 {new_issue} 寫入【{game_choice}】！")
            st.cache_data.clear()
            if f"time_machine_{game_choice}" in st.session_state:
                del st.session_state[f"time_machine_{game_choice}"]
            st.rerun()

# ==========================================
# 🔗 連接 Google Sheets 資料庫 (加入分頁動態切換)
# ==========================================
def get_google_sheet(sheet_name):
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["gcp_json"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    # ⚠️ 請把下面這行換成你自己的專屬網址！
    doc = client.open_by_url("https://docs.google.com/spreadsheets/d/1PrG36Oebngqhm7DrhEUNpfTtSk8k50jdAo2069aBJw8/edit?gid=978302798#gid=978302798")
    # 根據左邊選的彩種，打開對應的分頁
    return doc.worksheet(sheet_name)

@st.cache_data(ttl=600)
def load_data(game_name):
    sheet = get_google_sheet(game_name)
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    # 防呆：如果該分頁目前沒資料，給一個空的 DataFrame
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

# 動態載入使用者選擇的彩種資料庫
df = load_data(game_choice)

# ==========================================
# 🧠 空間演算法核心引擎 (維持不變)
# ==========================================
def get_predictions(target_draw):
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
    
    return short_picks, long_picks, consensus_picks, death_seas, sandwiches, geometric_centers, max_gap

# ==========================================
# 📝 側邊欄設定區 (導覽、時光機、新增數據)
# ==========================================
st.sidebar.title("🧭 系統導覽")
page = st.sidebar.radio("選擇分析面板：", [
    "🎯 39碼全解析雷達", 
    "⚔️ 雙引擎策略看板", 
    "📈 回測與勝率追蹤", 
    "📖 核心理論白皮書"
])

st.sidebar.markdown("---")
st.sidebar.header("⏳ 時光機設定")

# 檢查資料庫是否有資料，避免天天樂剛建好時報錯
if not df.empty:
    options = df.index.tolist()
    options.reverse()
    def format_option(idx):
        row = df.loc[idx]
        return f"期數 {row['Issue']} ({row['Date']})"
    selected_idx = st.sidebar.selectbox("選擇分析基準日：", options, format_func=format_option, key=f"time_machine_{game_choice}")
else:
    st.sidebar.warning(f"⚠️ 你的【{game_choice}】資料庫目前是空的！請先新增開獎數據。")
    selected_idx = None

st.sidebar.markdown("---")
with st.sidebar.expander(f"📝 輸入【{game_choice}】最新開獎號碼"):
    new_date = st.text_input("開獎日期 (YYYY-MM-DD)", "2026-02-25")
    new_issue = st.number_input("期數", min_value=1, value=115048, step=1)
    st.markdown("*(輸入順序不拘，系統會自動排序)*")
    n1 = st.number_input("號碼 1", min_value=1, max_value=39, value=1)
    n2 = st.number_input("號碼 2", min_value=1, max_value=39, value=2)
    n3 = st.number_input("號碼 3", min_value=1, max_value=39, value=3)
    n4 = st.number_input("號碼 4", min_value=1, max_value=39, value=4)
    n5 = st.number_input("號碼 5", min_value=1, max_value=39, value=5)

    if st.button("🚀 寫入雲端並重新計算"):
        if not df.empty and new_issue in df['Issue'].values:
            st.error(f"⚠️ 期數 {new_issue} 已經存在【{game_choice}】資料庫中了！")
        else:
            sorted_nums = sorted([n1, n2, n3, n4, n5])
            new_row = [new_issue, new_date, sorted_nums[0], sorted_nums[1], sorted_nums[2], sorted_nums[3], sorted_nums[4]]
            with st.spinner(f'正在寫入 {game_choice} Google 雲端資料庫...'):
                sheet = get_google_sheet(game_choice)
                sheet.append_row(new_row)
            st.success(f"✅ 成功將期數 {new_issue} 寫入【{game_choice}】！")
            st.cache_data.clear()
            if f"time_machine_{game_choice}" in st.session_state:
                del st.session_state[f"time_machine_{game_choice}"]
            st.rerun()

# 如果資料庫是空的，就不往下執行分析畫面，直接提示使用者新增資料
if df.empty:
    st.title(f"🎯 歡迎啟用【{game_choice}】分析雷達")
    st.info("👈 請先從左側邊欄輸入第一筆歷史開獎紀錄，系統才能開始運作喔！")
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

short_picks, long_picks, consensus_picks, death_seas, sandwiches, geometric_centers, max_gap = get_predictions(target_draw)

# ==========================================
# 🖥️ 頁面 1：🎯 39碼全解析雷達
# ==========================================
if page == "🎯 39碼全解析雷達":
    st.title(f"🎯 {game_choice} 39碼全解析雷達")
    st.markdown(f"### 基準日：{target_date} (期數 {target_issue}) | 開出號碼： `{target_draw}`")
    
    nums_100 = historical_df.tail(100)[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
    s_100 = pd.Series(0, index=np.arange(1, 40)).add(pd.Series(nums_100).value_counts(), fill_value=0).astype(int)

    nums_200 = historical_df.tail(200)[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
    s_200 = pd.Series(0, index=np.arange(1, 40)).add(pd.Series(nums_200).value_counts(), fill_value=0).astype(int)
    
    full_39_data = []
    for n in range(1, 40):
        if n in consensus_picks: status = "🌟 雙重共識 (強推主支)"
        elif any(sea_start < n < sea_end for sea_start, sea_end in death_seas): status = "💀 死亡深海 (強烈刪牌)"
        elif n in geometric_centers: status = "🎯 幾何中心 (長線引力)"
        elif n in sandwiches: status = "🥪 必補夾心 (型態缺口)"
        elif n in short_picks: status = "🔥 短線順勢 (+1/-1)"
        else: status = "⚖️ 中立觀望"
        
        if next_draw: next_status = "✅ 命中" if n in next_draw else ""
        else: next_status = "⏳ 尚未開獎"
        
        full_39_data.append({
            "號碼": n, "📍 本期基準": "🔵 開出" if n in target_draw else "",
            "空間狀態判定": status, "🔮 下期實盤": next_status,
            "🔥 100期開出": s_100[n], "❄️ 200期開出": s_200[n]
        })

    df_full_39 = pd.DataFrame(full_39_data).set_index("號碼")

    def color_status(val):
        if isinstance(val, str):
            if '🌟' in val: return 'background-color: #d4edda; color: #155724; font-weight: bold'
            elif '💀' in val: return 'background-color: #f8d7da; color: #721c24'
            elif '🔥' in val or '🎯' in val or '🥪' in val: return 'background-color: #fff3cd; color: #856404'
        return ''
    def color_base(val): return 'background-color: #cce5ff; color: #004085; font-weight: bold' if '🔵' in str(val) else ''
    def color_next(val): 
        if '✅' in str(val): return 'background-color: #28a745; color: white; font-weight: bold'
        elif '⏳' in str(val): return 'color: #6c757d; font-style: italic'
        return ''

    st.dataframe(
        df_full_39.style.map(color_status, subset=['空間狀態判定'])
                        .map(color_base, subset=['📍 本期基準'])
                        .map(color_next, subset=['🔮 下期實盤'])
                        .background_gradient(cmap='YlOrRd', subset=['🔥 100期開出'])
                        .background_gradient(cmap='PuBu', subset=['❄️ 200期開出']), 
        height=700, use_container_width=True
    )

# ==========================================
# 🖥️ 頁面 2：⚔️ 雙引擎策略看板
# ==========================================
elif page == "⚔️ 雙引擎策略看板":
    st.title(f"⚔️ {game_choice} 雙引擎策略決策看板")
    st.markdown(f"### 基準日：{target_date} (期數 {target_issue}) | 開出號碼： `{target_draw}`")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.error("🔴 **100期 短線動能派**")
        st.markdown("#### 🔥 順勢動能 (+1 / -1)")
        st.info(f"建議名單： **{short_picks}**" if short_picks else "*(今日無)*")
        st.markdown("#### 💀 避開死水 (死亡之海區間)")
        if death_seas:
            for sea in death_seas:
                s_text = "01" if sea[0] == 0 else f"{sea[0]+1:02d}"
                e_text = "39" if sea[1] == 40 else f"{sea[1]-1:02d}"
                st.warning(f"🚫 `{s_text} ~ {e_text}` (間距: {sea[1]-sea[0]-1})")
        else:
            st.success("今日無大型斷層區。")

    with col2:
        st.info("🔵 **200期 長線平衡派**")
        st.markdown("#### 🎯 史詩斷層 (幾何中心)")
        st.markdown(f"*(當前最大斷層間距為: **{max_gap}**)*")
        st.error(f"建議名單： **{geometric_centers}**" if geometric_centers else "*(無明顯斷層)*")
        st.markdown("#### 🥪 黃金對稱 (必補夾心)")
        st.error(f"建議名單： **{sandwiches}**" if sandwiches else "*(今日未成形)*")

    st.markdown("---")
    st.header("⭐️ 雙重共識牌 (疊加勝率)")
    if consensus_picks: st.success(f"### 🎯 極高勝率主支： {consensus_picks}")
    else: st.warning("今日兩派未達成共識，建議分開參考上方指標。")
        
    if next_draw:
        st.markdown("---")
        st.header("🔮 實盤對答案 (下一期實際開出)")
        st.write(f"下一期號碼為：`{next_draw}`")
        hit_consensus = [n for n in consensus_picks if n in next_draw]
        if hit_consensus: st.success(f"🎉 **神準命中！** 共識牌命中了： **{hit_consensus}**")

# ==========================================
# 🖥️ 頁面 3：📈 回測與勝率追蹤
# ==========================================
elif page == "📈 回測與勝率追蹤":
    st.title(f"📈 {game_choice} 策略勝率與回測追蹤 (近 100 期)")
    
    test_periods = 100
    if len(df) > test_periods:
        results = []
        start_idx = len(df) - test_periods - 1
        for i in range(start_idx, len(df) - 1):
            past_draw = [int(x) for x in df.iloc[i][['N1', 'N2', 'N3', 'N4', 'N5']].tolist()]
            actual_next_draw = [int(x) for x in df.iloc[i+1][['N1', 'N2', 'N3', 'N4', 'N5']].tolist()]
            draw_date = df.iloc[i+1]['Date']
            
            sp, lp, cp, _, _, _, _ = get_predictions(past_draw)
            
            short_hits = len(set(sp).intersection(set(actual_next_draw)))
            long_hits = len(set(lp).intersection(set(actual_next_draw)))
            consensus_hits = len(set(cp).intersection(set(actual_next_draw)))
            
            results.append({
                "Date": draw_date,
                "✅ 實際開獎": str(actual_next_draw),
                "🔴 短線推薦": str(sp) if sp else "-",
                "🔴 命中": short_hits,
                "🔵 長線推薦": str(lp) if lp else "-",
                "🔵 命中": long_hits,
                "⭐️ 共識推薦": str(cp) if cp else "-",
                "⭐️ 命中": consensus_hits
            })
        
        res_df = pd.DataFrame(results).set_index("Date")
        res_df["🔴 短線累積"] = res_df["🔴 命中"].cumsum()
        res_df["🔵 長線累積"] = res_df["🔵 命中"].cumsum()
        res_df["⭐️ 共識累積"] = res_df["⭐️ 命中"].cumsum()
        
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        col1.metric("🔴 100期短線派 (近百期命中)", f"{res_df['🔴 短線累積'].iloc[-1]} 顆")
        col2.metric("🔵 200期長線派 (近百期命中)", f"{res_df['🔵 長線累積'].iloc[-1]} 顆")
        col3.metric("⭐️ 雙重共識牌 (近百期命中)", f"{res_df['⭐️ 共識累積'].iloc[-1]} 顆")
        
        st.line_chart(res_df[["🔴 短線累積", "🔵 長線累積", "⭐️ 共識累積"]])
        
        with st.expander("📝 展開查看：每日命中覆盤明細對帳單"):
            st.dataframe(res_df[["✅ 實際開獎", "🔴 短線推薦", "🔴 命中", "🔵 長線推薦", "🔵 命中", "⭐️ 共識推薦", "⭐️ 命中"]], use_container_width=True)
            
    else:
        st.warning(f"⚠️ 【{game_choice}】資料庫目前只有 {len(df)} 期，不足 100 期，無法進行完整回測。請先累積多一點資料喔！")

# ==========================================
# 🖥️ 頁面 4：📖 核心理論白皮書
# ==========================================
elif page == "📖 核心理論白皮書":
    st.title("📖 核心理論與策略解析 (Whitepaper)")
    st.image("https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?q=80&w=1200&auto=format&fit=crop", caption="結合統計學機率觀念與金融市場趨勢邏輯")
    # (白皮書內文維持不變，省略避免佔用篇幅)
    st.markdown("這套分析方法是將**「股市的技術分析」**與**「彩迷常見的行為心理學」**，完美移植到了彩券的數據模型中...")

