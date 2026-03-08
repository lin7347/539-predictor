import streamlit as st
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
import json

st.set_page_config(page_title="量化雷達 雙彩種切換版", layout="wide")

# ==========================================
# 📝 側邊欄：彩種切換開關 (必須在最上面先選)
# ==========================================
st.sidebar.title("🎲 選擇分析彩種")
game_choice = st.sidebar.radio("目前分析目標：", ["539", "天天樂"])

# 🔄 新增：強制清除快取、同步最新雲端資料的按鈕
if st.sidebar.button("🔄 強制同步雲端資料庫"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")

# ==========================================
# ⚙️ 核心演算法參數微調 (實戰控制台)
# ==========================================
st.sidebar.header("⚙️ 演算法參數微調")
death_sea_gap = st.sidebar.slider(
    "💀 死亡之海斷層間距", 
    min_value=4, max_value=12, value=7, step=1, 
    help="當兩個號碼之間的間隔大於此數值，中間區域將被視為動能真空的死亡之海。數值越大，冷號區越小，中等機率號碼越多。"
)
include_repeat = st.sidebar.checkbox(
    "♻️ 包含連莊號 (解除昨日號碼封印)", 
    value=True, 
    help="勾選後，昨日開出的號碼將保留在短線動能觀察池中；取消勾選，則將昨日號碼視為全殺棄子。"
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
    # ⚠️ 請把下面這行換成你自己的專屬網址！
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
# 🧠 空間演算法核心引擎 (動態參數版)
# ==========================================
def get_predictions(target_draw, gap_limit, allow_repeat):
    target_draw = sorted(target_draw)
    extended_draw = [0] + target_draw + [40]
    
    # 1. 尋找死亡之海 (使用面板設定的 gap_limit)
    death_seas = []
    for i in range(len(extended_draw)-1):
        start, end = extended_draw[i], extended_draw[i+1]
        if end - start - 1 >= gap_limit: 
            death_seas.append((start, end))
            
    # 2. 短線順勢 (+1 / -1)
    short_picks = []
    for n in target_draw:
        for c in [n-1, n+1]:
            if 1 <= c <= 39 and not any(sea_start < c < sea_end for sea_start, sea_end in death_seas):
                short_picks.append(int(c))
                
    # 🌟 動態決定是否擁抱連莊慣性
    if allow_repeat:
        short_picks.extend(target_draw)
        
    short_picks = list(set(short_picks))
            
    # 3. 尋找完美夾心缺口
    sandwiches = [int(target_draw[i]+1) for i in range(len(target_draw)-1) if target_draw[i+1]-target_draw[i]==2]
            
    # 4. 尋找史詩斷層幾何中心
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

    # 5. 同尾數共鳴
    tails = [n % 10 for n in target_draw]
    hot_tails = [t for t in set(tails) if tails.count(t) >= 2]
    
    tail_resonances = []
    if hot_tails:
        for t in hot_tails:
            for n in range(1, 40):
                if n % 10 == t:
                    tail_resonances.append(n)

    # 如果不允許連莊，則從長線名單中剔除原班人馬
    if not allow_repeat:
        short_picks = [p for p in short_picks if p not in target_draw]
        sandwiches = [p for p in sandwiches if p not in target_draw]
        geometric_centers = [p for p in geometric_centers if p not in target_draw]
        tail_resonances = [p for p in tail_resonances if p not in target_draw]

    long_picks = list(set(geometric_centers + sandwiches + tail_resonances))
    consensus_picks = sorted(list(set(short_picks).intersection(set(long_picks))))
    
    return short_picks, long_picks, consensus_picks, death_seas, sandwiches, geometric_centers, tail_resonances, max_gap

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

# 🤖 智慧自動遞增邏輯
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
            st.error(f"⚠️ 期數 {new_issue} 已經存在【{game_choice}】資料庫中了！")
        else:
            sorted_nums = sorted([n1, n2, n3, n4, n5])
            new_row = [new_date, new_issue, sorted_nums[0], sorted_nums[1], sorted_nums[2], sorted_nums[3], sorted_nums[4]]
            
            with st.spinner(f'正在寫入 {game_choice} Google 雲端資料庫...'):
                sheet = get_google_sheet(game_choice)
                sheet.append_row(new_row, value_input_option="USER_ENTERED")
            st.success(f"✅ 成功將期數 {new_issue} 寫入【{game_choice}】！")
            st.cache_data.clear()
            if f"time_machine_{game_choice}" in st.session_state:
                del st.session_state[f"time_machine_{game_choice}"]
            st.rerun()

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

short_picks, long_picks, consensus_picks, death_seas, sandwiches, geometric_centers, tail_resonances, max_gap = get_predictions(target_draw, death_sea_gap, include_repeat)

# ==========================================
# 🖥️ 頁面 1：🎯 39碼全解析雷達
# ==========================================
if page == "🎯 39碼全解析雷達":
    st.title(f"🎯 {game_choice} 39碼全解析雷達")
    st.markdown(f"### 基準日：{target_date} (期數 {target_issue}) | 開出號碼： `{target_draw}`")
    
    # === 原本的 Dataframe 隱藏或保留，這裡直接進入全新的動態 HTML 戰略報表 ===
    st.markdown("---")
    st.markdown("### 📊 長短線雙核心深度戰略報表 (實戰動態微調版)")
    
    # 嚴格過濾、保證無重複且自動排序
    def get_category_picks(picks, category_name):
        sorted_picks = sorted(list(set(picks))) if picks else []
        
        if category_name == "HOT":
            return ", ".join([str(p) for p in sorted_picks[:5]]) if sorted_picks else "無"
        elif category_name == "WARM":
            return ", ".join([str(p) for p in sorted_picks[5:10]]) if len(sorted_picks) > 5 else "無"
        elif category_name == "REPEAT_OR_DEAD":
            if include_repeat:
                repeats = [p for p in target_draw if p not in sorted_picks[:10]]
                return ", ".join([str(p) for p in repeats]) if repeats else "無 (皆已升級為主推)"
            else:
                return ", ".join([str(p) for p in target_draw])
        elif category_name == "NEUTRAL":
            others = [p for p in range(1, 40) if p not in sorted_picks[:10] and p not in target_draw and not any(s < p < e for s,e in death_seas)]
            return ", ".join([str(p) for p in others]) if others else "無"
        elif category_name == "COLD":
            cold = [p for p in range(1, 40) if any(s < p < e for s,e in death_seas) and p not in target_draw and p not in sorted_picks[:10]]
            return ", ".join([str(p) for p in cold]) if cold else "無"

    # 動態決定第三列的標題與敘述
    row3_icon = "♻️ **連莊觀察區**<br>*(昨日開出)*" if include_repeat else "💀 **最不可能開出**<br>*(全殺棄子)*"
    row3_long_desc = "• (長線視角：保留慣性，觀察連莊潛力)" if include_repeat else "• 全殺原因：【能量耗盡】。明天系統能量必定轉移，連莊機率極低。"
    row3_short_desc = "• (短線視角：保留慣性動能，具備連莊潛力)" if include_repeat else "• 原班人馬交棒：動能已向兩側外溢釋放完畢。"

    # 動態產生 HTML 表格字串 (解決 Markdown 排版不穩定的問題)
    html_table = f"""
    <table style="width:100%; border-collapse: collapse; text-align: left; font-size: 16px;">
        <tr style="background-color: #f0f2f6;">
            <th style="padding: 12px; border: 1px solid #ddd; width: 15%;">推薦等級</th>
            <th style="padding: 12px; border: 1px solid #ddd; width: 42%;">200 期（長線平衡派 - 抄底補洞）</th>
            <th style="padding: 12px; border: 1px solid #ddd; width: 43%;">100 期（短線動能派 - 順勢擴散）</th>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #ddd;">🔥 **極可能開出**<br>*(必買主支)*</td>
            <td style="padding: 12px; border: 1px solid #ddd;"><b style="color: #d9534f; font-size: 18px;">{get_category_picks(long_picks, 'HOT')}</b><br><br><span style="color: #666; font-size: 14px;">• (長線演算法核心推薦：涵蓋深海中心與黃金夾心)</span></td>
            <td style="padding: 12px; border: 1px solid #ddd;"><b style="color: #d9534f; font-size: 18px;">{get_category_picks(short_picks, 'HOT')}</b><br><br><span style="color: #666; font-size: 14px;">• (短線演算法核心推薦：涵蓋連號外溢與懸崖起點防守)</span></td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #ddd;">⭐ **高機率開出**<br>*(強勢輔助)*</td>
            <td style="padding: 12px; border: 1px solid #ddd;"><b style="color: #f0ad4e; font-size: 18px;">{get_category_picks(long_picks, 'WARM')}</b><br><br><span style="color: #666; font-size: 14px;">• (長線演算法邊緣防禦：大峽谷起步磚)</span></td>
            <td style="padding: 12px; border: 1px solid #ddd;"><b style="color: #f0ad4e; font-size: 18px;">{get_category_picks(short_picks, 'WARM')}</b><br><br><span style="color: #666; font-size: 14px;">• (短線演算法次級動能：熱點次外圍)</span></td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #ddd;">{row3_icon}</td>
            <td style="padding: 12px; border: 1px solid #ddd;"><b style="color: #5bc0de; font-size: 18px;">{get_category_picks(long_picks, 'REPEAT_OR_DEAD')}</b><br><br><span style="color: #666; font-size: 14px;">{row3_long_desc}</span></td>
            <td style="padding: 12px; border: 1px solid #ddd;"><b style="color: #5bc0de; font-size: 18px;">{get_category_picks(short_picks, 'REPEAT_OR_DEAD')}</b><br><br><span style="color: #666; font-size: 14px;">{row3_short_desc}</span></td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #ddd;">⚖️ **中等機率**<br>*(中立觀望)*</td>
            <td style="padding: 12px; border: 1px solid #ddd;"><b>{get_category_picks(long_picks, 'NEUTRAL')}</b><br><br><span style="color: #666; font-size: 14px;">• (填補各大峽谷的次要邊緣號碼，數量平均分佈)</span></td>
            <td style="padding: 12px; border: 1px solid #ddd;"><b>{get_category_picks(short_picks, 'NEUTRAL')}</b><br><br><span style="color: #666; font-size: 14px;">• (受惠於熱度微弱外溢，表現中規中矩的常態號碼)</span></td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #ddd;">❄️ **低機率**<br>*(死亡深海)*</td>
            <td style="padding: 12px; border: 1px solid #ddd;"><b style="color: #999;">{get_category_picks(long_picks, 'COLD')}</b><br><br><span style="color: #666; font-size: 14px;">• (極端斷層深處，動能絕對真空)</span></td>
            <td style="padding: 12px; border: 1px solid #ddd;"><b style="color: #999;">{get_category_picks(short_picks, 'COLD')}</b><br><br><span style="color: #666; font-size: 14px;">• (距離熱點太遙遠，動能難以傳遞的冰凍區)</span></td>
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
        st.error("🔴 100期 短線動能派")
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
        st.info("🔵 200期 長線平衡派")
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
    st.title(f"📈 {game_choice} 策略勝率與回測追蹤 (近 100 期)")
    
    test_periods = 100
    if len(df) > test_periods:
        results = []
        start_idx = len(df) - test_periods - 1
        for i in range(start_idx, len(df) - 1):
            past_draw = [int(x) for x in df.iloc[i][['N1', 'N2', 'N3', 'N4', 'N5']].tolist()]
            actual_next_draw = [int(x) for x in df.iloc[i+1][['N1', 'N2', 'N3', 'N4', 'N5']].tolist()]
            draw_date = df.iloc[i+1]['Date']
            
            # 回測時也要套用側邊欄的動態參數！
            sp, lp, cp, _, _, _, _, _ = get_predictions(past_draw, death_sea_gap, include_repeat)
            
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
        col1.metric("🔴 短線派累積命中", f"{res_df['🔴 短線累積'].iloc[-1]} 顆")
        col2.metric("🔵 長線派累積命中", f"{res_df['🔵 長線累積'].iloc[-1]} 顆")
        col3.metric("⭐️ 雙重共識累積命中", f"{res_df['⭐️ 共識累積'].iloc[-1]} 顆")
        
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
    st.markdown("""
    這套系統內建**動態參數微調面板**，允許操作者針對不同的市場週期，隨時改變演算法的嚴格程度，實現真正的量化操盤。
    *(詳細理論文字保留，可自行擴充)*
    """)
