import streamlit as st
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
import json

st.set_page_config(page_title="539 量化雷達 雙引擎策略版", layout="wide")

# ==========================================
# 🔗 連接 Google Sheets 資料庫
# ==========================================
def get_google_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["gcp_json"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    # ⚠️ 請把下面這行換成你自己的專屬網址！
    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1PrG36Oebngqhm7DrhEUNpfTtSk8k50jdAo2069aBJw8/edit?gid=978302798#gid=978302798").sheet1
    return sheet

@st.cache_data(ttl=600)
def load_data():
    sheet = get_google_sheet()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    rename_dict = {
        'Date (開獎日期)': 'Date', 'Issue (期數)': 'Issue',
        'N1 (號碼1)': 'N1', 'N2 (號碼2)': 'N2', 'N3 (號碼3)': 'N3',
        'N4 (號碼4)': 'N4', 'N5 (號碼5)': 'N5'
    }
    df = df.rename(columns=rename_dict)
    return df

df = load_data()

# ==========================================
# 📝 側邊欄設定區 (導覽、時光機、新增數據)
# ==========================================
st.sidebar.title("🧭 系統導覽")
page = st.sidebar.radio("選擇你想查看的頁面：", ["🎯 39碼全解析雷達", "⚔️ 雙引擎策略看板", "📖 核心理論白皮書"])

st.sidebar.markdown("---")
st.sidebar.header("⏳ 時光機設定")
options = df.index.tolist()
options.reverse()
def format_option(idx):
    row = df.loc[idx]
    return f"期數 {row['Issue']} ({row['Date']})"
selected_idx = st.sidebar.selectbox("選擇分析基準日：", options, format_func=format_option)

st.sidebar.markdown("---")
with st.sidebar.expander("📝 輸入今日最新開獎號碼"):
    new_date = st.text_input("開獎日期 (YYYY-MM-DD)", "2026-02-25")
    new_issue = st.number_input("期數", min_value=113000, value=115048, step=1)
    st.markdown("*(輸入順序不拘，系統會自動排序)*")
    n1 = st.number_input("號碼 1", min_value=1, max_value=39, value=1)
    n2 = st.number_input("號碼 2", min_value=1, max_value=39, value=2)
    n3 = st.number_input("號碼 3", min_value=1, max_value=39, value=3)
    n4 = st.number_input("號碼 4", min_value=1, max_value=39, value=4)
    n5 = st.number_input("號碼 5", min_value=1, max_value=39, value=5)

    if st.button("🚀 寫入雲端並重新計算"):
        if new_issue in df['Issue'].astype(int).values:
            st.error(f"⚠️ 期數 {new_issue} 已經存在雲端資料庫中了！")
        else:
            sorted_nums = sorted([n1, n2, n3, n4, n5])
            new_row = [new_date, new_issue, sorted_nums[0], sorted_nums[1], sorted_nums[2], sorted_nums[3], sorted_nums[4]]
            with st.spinner('正在寫入 Google 雲端資料庫...'):
                sheet = get_google_sheet()
                sheet.append_row(new_row)
            st.success(f"✅ 成功寫入期數 {new_issue}！")
            st.cache_data.clear()
            st.rerun()

# ==========================================
# 🧠 全域核心運算：歷史次數 + 空間型態 (時光機基準)
# ==========================================
historical_df = df.loc[:selected_idx]

nums_100 = historical_df.tail(100)[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
s_100 = pd.Series(0, index=np.arange(1, 40)).add(pd.Series(nums_100).value_counts(), fill_value=0).astype(int)

nums_200 = historical_df.tail(200)[['N1', 'N2', 'N3', 'N4', 'N5']].values.flatten()
s_200 = pd.Series(0, index=np.arange(1, 40)).add(pd.Series(nums_200).value_counts(), fill_value=0).astype(int)

target_draw = historical_df.iloc[-1][['N1', 'N2', 'N3', 'N4', 'N5']].tolist()
target_date = historical_df.iloc[-1]['Date']
target_issue = historical_df.iloc[-1]['Issue']

if selected_idx + 1 < len(df):
    next_draw = df.loc[selected_idx + 1][['N1', 'N2', 'N3', 'N4', 'N5']].tolist()
else:
    next_draw = []

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
# 🖥️ 頁面 1：🎯 39碼全解析雷達
# ==========================================
if page == "🎯 39碼全解析雷達":
    st.title("🎯 39碼全解析雷達 (歷史次數與空間驗證)")
    st.markdown(f"### 基準日：{target_date} (期數 {target_issue}) | 開出號碼： `{target_draw}`")
    
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
    st.title("⚔️ 雙引擎策略決策看板")
    st.markdown(f"### 基準日：{target_date} (期數 {target_issue}) | 開出號碼： `{target_draw}`")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.error("🔴 **短線動能派 (100期順勢)**")
        st.markdown("**核心思維：** 熱度外溢與慣性，避開無量死水。")
        st.markdown("---")
        st.markdown("#### 🔥 順勢動能 (+1 / -1)")
        st.info(f"建議名單： **{short_picks}**" if short_picks else "*(今日無號碼存活)*")
        
        st.markdown("#### 💀 避開死水 (死亡之海區間)")
        if death_seas:
            for sea in death_seas:
                s_text = "01" if sea[0] == 0 else f"{sea[0]+1:02d}"
                e_text = "39" if sea[1] == 40 else f"{sea[1]-1:02d}"
                st.warning(f"🚫 `{s_text} ~ {e_text}` (間距: {sea[1]-sea[0]-1})")
        else:
            st.success("今日無大型斷層區。")

    with col2:
        st.info("🔵 **長線平衡派 (200期均值)**")
        st.markdown("**核心思維：** 大數法則與均值回歸，填平機率凹洞。")
        st.markdown("---")
        st.markdown("#### 🎯 史詩斷層 (幾何中心)")
        st.markdown(f"*(當前最大斷層間距為: **{max_gap}**)*")
        st.error(f"建議名單： **{geometric_centers}**" if geometric_centers else "*(無明顯斷層)*")
        
        st.markdown("#### 🥪 黃金對稱 (必補夾心)")
        st.error(f"建議名單： **{sandwiches}**" if sandwiches else "*(今日未成形)*")

    st.markdown("---")
    st.header("⭐️ 雙重共識牌 (疊加勝率)")
    st.markdown("當號碼同時符合「短線邊緣防守」與「長線引力中心」時，為邏輯支撐力最強之主支。")
    if consensus_picks:
        st.success(f"### 🎯 極高勝率主支： {consensus_picks}")
    else:
        st.warning("今日兩派未達成共識，建議分開參考上方指標，或保持觀望。")
        
    if next_draw:
        st.markdown("---")
        st.header("🔮 實盤對答案 (下一期實際開出)")
        st.write(f"下一期號碼為：`{next_draw}`")
        hit_consensus = [n for n in consensus_picks if n in next_draw]
        if hit_consensus:
            st.success(f"🎉 **神準命中！** 共識牌命中了： **{hit_consensus}**")

# ==========================================
# 🖥️ 頁面 3：📖 核心理論白皮書
# ==========================================
elif page == "📖 核心理論白皮書":
    st.title("📖 核心理論與策略解析 (Whitepaper)")
    st.image("https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?q=80&w=1200&auto=format&fit=crop", caption="結合統計學機率觀念與金融市場趨勢邏輯")
    
    st.markdown("""
    這套分析方法是將**「股市的技術分析（Technical Analysis）」**與**「彩迷常見的行為心理學」**，完美移植到了彩券的數據模型中。它主要建構在以下兩大核心理論：

    ### 🔵 200期（長線平衡派）：建構在「均值回歸」理論
    長線派的腦袋，就像是股市裡的**「價值投資者」**與**「抄底大師」**。他們的分析基於以下三個假設：
    * **大數法則與均值回歸 (Mean Reversion)：**
      * **邏輯：** 長期來看，1 到 39 號每一顆球被抽出的機率應該是相等的。如果某個區間（例如連續 20 個號碼）長期沒開出，在統計學上就形成了「機率凹洞」。
      * **行動：** 系統認定這個凹洞「遲早必須被填平」來回歸平均值。這就是為什麼長線派看到「史詩級大斷層」，會興奮地想要重押幾何中心點（填海造陸）。
    * **圖形對稱性 (Symmetry & Patterns)：**
      * **邏輯：** 數據分佈會傾向尋找平衡。當出現「05、07」卻獨缺「06」時，這在視覺與機率上形成了一個極度不穩定的「真空」。
      * **行動：** 這就是我們常說的「完美黃金夾心」，長線派認為這種微小且對稱的破口，被系統強制修復的優先級最高。
    * **同尾數的磁場共鳴：**
      * **邏輯：** 這屬於彩迷長期的統計觀察，當特定的尾數（例如 9 尾的 09、39）在兩端強勢出現時，往往會帶動中間同家族的號碼（19、29）跟著開出。

    ### 🔴 100期（短線動能派）：建構在「順勢動能」理論
    短線派的腦袋，就像是股市裡的**「當沖客」**與**「動能交易員」**。他們完全不相信「填補凹洞」這套，他們的分析基於以下兩個假設：
    * **熱度外溢與慣性 (Momentum & Trend Following)：**
      * **邏輯：** 他們認為開獎號碼雖然隨機，但「資金與熱度」是有慣性的。昨天開出的號碼就像一顆投入水中的石頭，熱度會向左右兩邊擴散形成漣漪。
      * **行動：** 這就是最強大且無腦的 「+1 / -1 順勢戰法」。06 開出，明天就買 07；避開冷門號碼，只跟著「剛開出的熱點」旁邊買，收割外溢的能量。
    * **避開無量死水 (Avoid the Void)：**
      * **邏輯：** 在股市中，「沒有成交量的地方不要去」。短線派認為，如果一個區間長期沒開出號碼，代表那個地方完全沒有動能。
      * **行動：** 絕對不進去大斷層裡「接刀子」，寧願站在斷層邊緣（懸崖起步磚）防守。

    ---
    ### ⭐️ 為什麼要同時用這兩套互相矛盾的方法？
    您會發現，這兩派的觀點經常是完全相反的（一派要跳進深海，一派叫你遠離深海）。
    這套分析系統之所以強大，就在於它**「尋找雙方的交集（共識牌）」**。

    當一個號碼（例如前面的 10 號或 32 號），既符合長線的「斷層邊緣防守」，又符合短線的「+1 動能推移」時，這個號碼就疊加了雙重的數學邏輯與策略意義。
    在完全隨機的機率海中，選擇這種「邏輯支撐力最強」的共識號碼，是我們唯一能做到「在策略上優於盲目瞎猜」的方法。
    """)

st.sidebar.markdown("---")
st.sidebar.markdown("*(本系統為量化數據教學使用，請理性參考)*")
