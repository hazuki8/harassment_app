import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import textwrap
from utils.db import get_user_responses, get_global_averages_stats, generate_demo_data

# ページ設定
st.set_page_config(page_title="あなたの認識傾向", layout="wide")

# ツールチップ用にテキストを改行する関数
def format_hover_text(text, width=40):
    if not isinstance(text, str): return ""
    return "<br>".join(textwrap.wrap(text, width=width))

# ==========================================
# 0. データ取得 & 前処理
# ==========================================

# ログインチェック
if "user_id" not in st.session_state or not st.session_state.user_id:
    st.warning("⚠️ まずはパワハラ認識傾向チェックから診断を開始してください。")
    if st.button("認識チェックへ戻る"):
        st.switch_page("pages/1_📝_パワハラ認識傾向チェック.py")
    st.stop()

# ユーザー回答の取得
user_responses = get_user_responses(st.session_state.user_id)
if not user_responses:
    st.error("回答データが見つかりませんでした。")
    st.stop()

# 全体平均データの取得
stats_df = get_global_averages_stats()
use_demo_data = False

# データ不足時はデモデータ生成
if stats_df.empty:
    use_demo_data = True
    st.info("🔬 統計データがまだ蓄積されていないため、研究用のデモデータを使用します。", icon="ℹ️")
elif len(stats_df) < 10:
    use_demo_data = True
    st.info("🔬 データ数が不足しているため、研究用のデモデータで補完します。", icon="ℹ️")

with st.spinner("診断結果を分析中..."):
    # 1. ベースのデータフレーム作成
    df = pd.DataFrame(user_responses)
    
    # カラム名の正規化
    if 'text' not in df.columns and 'title' in df.columns:
        df['text'] = df['title']
    
    # scenario_id を int に統一
    if 'scenario_id' in df.columns:
        df['scenario_id'] = df['scenario_id'].astype(int)
    
    # 2. 全体平均データのマージ
    if stats_df.empty:
        # 実シナリオを用いたデモデータから統計を生成
        demo_df = generate_demo_data()
        stats_df = demo_df.groupby('scenario_id').agg(
            avg_rating=('rating', 'mean'),
            std_dev=('rating', 'std')
        ).reset_index()
        stats_df['scenario_id'] = stats_df['scenario_id'].astype(int)
        
    # scenario_id のデータ型を揃えてマージ
    stats_df['scenario_id'] = stats_df['scenario_id'].astype(int)
    df = df.merge(stats_df[['scenario_id', 'avg_rating', 'std_dev']], on='scenario_id', how='left')
    
    # 欠損値を補填
    df['avg_rating'] = df['avg_rating'].fillna(3.5)
    df['std_dev'] = df['std_dev'].fillna(1.0)

    # -------------------------------------------------------
    # ロジック計算エンジン (元のコードのまま)
    # -------------------------------------------------------
    
    # --- A. 法的規範との比較ロジック (回答値による直接判定) ---
    def calc_legal_risk(row):
        # 戻り値: (リスクレベル) "重"(重度), "軽"(軽度), "なし"(正常)
        if row['type'] == 'Black':
            if row['rating'] <= 2: return "重" # 重度：1-2 (全く/あまり)
            elif row['rating'] == 3: return "軽" # 軽度：3 (どちらかと言えば)
        elif row['type'] == 'White':
            if row['rating'] >= 5: return "重" # 重度：5-6 (かなり/強く)
            elif row['rating'] == 4: return "軽" # 軽度：4 (どちらかと言えば)
        return "なし"

    df['legal_level'] = df.apply(calc_legal_risk, axis=1)

    # 集計：Black 
    cnt_critical_lenient = len(df[(df['type'] == 'Black') & (df['legal_level'] == '重')])
    cnt_mild_lenient     = len(df[(df['type'] == 'Black') & (df['legal_level'] == '軽')])
    total_lenient = cnt_critical_lenient + cnt_mild_lenient

    # 集計：White 
    cnt_critical_strict = len(df[(df['type'] == 'White') & (df['legal_level'] == '重')])
    cnt_mild_strict     = len(df[(df['type'] == 'White') & (df['legal_level'] == '軽')])
    total_strict = cnt_critical_strict + cnt_mild_strict

    # --- B. 世の中の感覚との比較ロジック ---
    # 標準偏差で重み付けした標準化スコアを算出（最小値0.5で固定）
    df['std_clipped'] = df['std_dev'].clip(lower=0.5)
    df['standardized_bias'] = (df['rating'] - df['avg_rating']) / df['std_clipped']
    
    # 全体的なバイアス指標（標準化スコアの平均）
    bias_mean = df['standardized_bias'].mean()
    
    # 世間平均との差が2ポイント以上の設問をカウント
    df['raw_gap'] = abs(df['rating'] - df['avg_rating'])
    large_gap_count = len(df[df['raw_gap'] >= 2.0])


# ==========================================
# UI表示：トップサマリー
# ==========================================

demo_notice = " 💻 (デモデータ使用)" if use_demo_data else ""
st.title(f"👤 あなたの認識傾向{demo_notice}")
st.markdown("""
あなたの回答データをもとに、**法的規範との整合性**および**世の中の感覚とのズレ**を分析・可視化しました。
""")

if use_demo_data:
    st.info("""
    **📌 透明性に関する注意：**
    - 「世の中の感覚」の比較には、統計的に生成された **デモデータ** を使用しています
    - 実際のユーザーが10人以上になると、自動的に実データに切り替わります
    """, icon="ℹ️")

# -------------------------------------------------------
# 1. 左右比較パネル 
# -------------------------------------------------------
col1, col2 = st.columns(2)

# パネルのスタイル
card_style = """
    border-radius: 8px;
    padding: 20px;
    height: 100%;
    min-height: 360px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    background-color: white;
    display: flex;
    flex-direction: column;
"""

# --- 左側：法的規範との比較 ---
with col1:
    if total_lenient > 0 and total_strict > 0:
        legal_status = "🔴 認識基準が不安定"
        legal_color = "#dc3545" # Red
        legal_desc = (
            "違法とされる行為を許容する一方で、適法とされる行為をハラスメントと評価するなど、判断基準が一貫していません。<br>"
            "厚生労働省のパワハラ防止指針などを確認し、認識を整理する必要があります。<br><br>"
            f"<b>【不足: {total_lenient}件】</b> (重度 {cnt_critical_lenient} / 軽度 {cnt_mild_lenient})<br>"
            f"<b>【過剰: {total_strict}件】</b> (重度 {cnt_critical_strict} / 軽度 {cnt_mild_strict})<br><br>"
            "👇 詳細は下部の「<b>回答詳細</b>」で、法的基準を再確認し、ご自身の基準をチューニングすることをお勧めします。"
        )
    elif total_lenient > 0:
        legal_status = "🔴 認識が不足"
        legal_color = "#dc3545"
        legal_desc = (
            "法的規範と比べて、違法とされる行為の問題性を十分に捉えられていない傾向があります。<br>"
            "そのため、自覚のないままパワハラに該当する行為を行ったり問題行為を見逃し、後から問題が表面化して組織的対応や法的なトラブルにつながる可能性があります。<br><br>"
            f"<b>⚠️ 検出されたリスク: {total_lenient}件</b><br>"
            f"・重度（是正必須）: {cnt_critical_lenient}件<br>"
            f"・軽度（要確認）: {cnt_mild_lenient}件<br><br>"
            "あなたの感覚よりも「法的なラインはもっと手前にある」と意識し、認識をアップデートする必要があります。<br>"
            "👇 詳細は下部の「<b>回答詳細</b>」セクションで各シナリオの解説をご確認ください。"
        )
    elif total_strict > 0:
        legal_status = "🔴 認識が過剰"
        legal_color = "#dc3545"
        legal_desc = (
            "法的規範と比べて、本来は問題とされない行為の問題性を強く捉えすぎる傾向が見られます。<br>"
            "その結果、自分自身が指導や注意を控えてしまったり、周囲も萎縮して必要な指導やフィードバックを受けにくくなったりと適切な育成や改善の機会が失われる可能性があります。<br><br>"
            f"<b>⚠️ 検出されたリスク: {total_strict}件</b><br>"
            f"・重度（是正必須）: {cnt_critical_strict}件<br>"
            f"・軽度（要確認）　: {cnt_mild_strict}件<br><br>"
            "厚生労働省のパワハラ防止指針などを確認し、認識を整理する必要があります。<br>"
            "👇 詳細は下部の「<b>回答詳細</b>」セクションで各シナリオの解説をご確認ください。"
        )
    else:
        legal_status = "🟢 基準と合致"
        legal_color = "#28a745" # Green
        legal_desc = (
            "法的に白黒が明確な事例について、あなたの認識は法的規範と概ね一致しています。<br>"
            "現時点では、法的な観点から見て大きなズレは見られません。"
        )

    st.markdown(f"""
    <div style="border-top: 5px solid {legal_color}; {card_style}">
        <h4 style="margin-top:0; font-size:16px; color:#555;">⚖ 法的規範との比較</h4>
        <div style="margin-top: 20px; margin-bottom: 15px; flex-grow: 1;">
            <span style="font-size: 28px; font-weight: bold; color: {legal_color};">{legal_status}</span>
        </div>
        <div style="font-size: 14px; color: #333; line-height: 1.6;">
            {legal_desc}
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- 右側：世の中の感覚との比較 ---
with col2:
    if bias_mean >= 1.0:
        # 過敏
        pos_title = "過敏"
        pos_color = "#6f42c1" # Purple
        pos_desc = (
            "全体として世間より<b>著しく厳しい判断</b>を行う傾向があります。<br>"
            "統計的には「最も厳しい上位16%」に含まれる水準です。<br><br>"
            f"<b>バイアス指標:</b> {bias_mean:+.2f}<br><br>"
            "⚠️ <b>注意点:</b> あなたが「許せない」と感じることでも、周囲は「許容範囲」と捉えている可能性があります。<br>"
            "自分の感覚で相手を断罪すると、相手を過度に萎縮させ、**円滑なコミュニケーションや報告・相談が滞る**リスクがあります。"
        )
    elif bias_mean <= -1.0:
        # 鈍感
        pos_title = "鈍感"
        pos_color = "#dc3545" # Red
        pos_desc = (
            "全体として世間より<b>著しく甘い判断</b>を行う傾向があります。<br>"
            "平均して標準偏差の1倍以上、甘い側に偏っており、統計的には下位およそ16%前後に相当します。<br><br>"
            f"<b>バイアス指標:</b> {bias_mean:+.2f}<br><br>"
            "⚠️ <b>注意点:</b> あなたが「これくらい大丈夫」と思って行った言動が、相手にとっては「深い苦痛」である可能性が高いです。<br>"
            "部下のSOSサインを見逃さないよう、意識的に感度を上げる必要があります。"
        )
    elif -0.5 <= bias_mean <= 0.5 and large_gap_count >= 2:
        # 判断分化傾向
        pos_title = "判断分化傾向"
        pos_color = "#ffc107" # Yellow
        pos_desc = (
            "全体的な判断の厳しさ・甘さには大きな偏りがない一方で、<b>特定のシナリオにおいて世間と決定的に異なる判断</b>が繰り返し見られます。<br><br>"
            f"<b>バイアス指標:</b> {bias_mean:+.2f} (全体は平均的)<br>"
            f"<b>大きなズレ:</b> {large_gap_count}問で世間と乖離<br><br>"
            "⚠️ <b>注意点:</b> 自分にとっての「当たり前」が通じない場面があります。どのテーマでズレが生じているか、下部の詳細リストで確認してください。"
        )
    elif 0.5 <= bias_mean < 1.0:
        # 厳格傾向
        pos_title = "厳格傾向"
        pos_color = "#0d6efd" # Blue
        pos_desc = (
            "世間一般よりも、<b>やや規律を重んじる</b>傾向があります。<br>"
            "統計的には「厳しい側の上位30%」程度に含まれます。<br><br>"
            f"<b>バイアス指標:</b> {bias_mean:+.2f}<br><br>"
            "真面目な姿勢は評価されますが、相手に「少し息苦しい」と感じさせ、**部下からの自発的なコミュニケーションが減ってしまう**可能性があります。<br>"
            "「世の中にはもう少し緩い考え方の人も多い」と知っておくだけで、対人摩擦を減らせます。"
        )
    elif -1.0 < bias_mean <= -0.5:
        pos_color = "#fd7e14" # Orange
        pos_desc = (
            "世間よりも<b>やや甘めの判断</b>を行う傾向があります。<br>"
            "統計的には「気にならない側の下位30%」程度に含まれます。<br><br>"
            f"<b>バイアス指標:</b> {bias_mean:+.2f}<br><br>"
            "細かいことを気にしない大らかさは長所ですが、ハラスメントの初期兆候を見逃す懸念もわずかにあります。<br>"
            "相手が「嫌だ」と言い出しにくい立場にいないか、配慮を忘れないようにしましょう。"
        )
    else:
        pos_title = "平均的"
        pos_color = "#28a745" # Green
        pos_desc = (
            "世間一般の感覚と<b>おおむね一致</b>しています。<br>"
            "統計的にはボリュームゾーン（中央38%）に含まれ、極端な偏りがありません。<br><br>"
            f"<b>バイアス指標:</b> {bias_mean:+.2f}<br><br>"
            "✅ 世の中と調和したバランスの良い認識ができています。<br>"
            "独りよがりな判断になりにくく、円滑なコミュニケーションが期待できます。"
        )

    st.markdown(f"""
    <div style="border-top: 5px solid {pos_color}; {card_style}">
        <h4 style="margin-top:0; font-size:16px; color:#555;">👥 世の中の感覚との比較</h4>
        <div style="margin-top: 20px; margin-bottom: 15px; flex-grow: 1;">
            <span style="font-size: 28px; font-weight: bold; color: {pos_color};">{pos_title}</span>
        </div>
        <div style="font-size: 14px; color: #333; line-height: 1.6;">
            {pos_desc}
        </div>
    </div>
    """, unsafe_allow_html=True)

st.write("") 
st.markdown("---")

# ==========================================
# UI表示：2. 6類型別詳細分析
# ==========================================
st.subheader("📊 類型別分析")

tab_cat_legal, tab_cat_social = st.tabs(["⚖️ 法的規範との比較 ", "👥 世の中の感覚との比較 "])

# ----------------------------------------------------
# タブ1：法的規範との比較 
# ----------------------------------------------------
with tab_cat_legal:
    st.markdown("##### ⚖️ 類型別：認識のズレ分析")
    st.caption("パワハラ6類型ごとに「認識が不足」（違反行為を見落とすリスク）があるか「認識が過剰」（過剰に厳しく判断するリスク）があるかを分析します。バーが出ていない（0）項目は、法的に「問題なし（セーフ）」であることを表します。")

    black_df = df[df['type'] == 'Black'].copy()
    if not black_df.empty:
        black_df['miss_score'] = (4 - black_df['rating']).clip(lower=0)
        legal_miss = black_df.groupby('category')['miss_score'].mean().reset_index()
        legal_miss.rename(columns={'miss_score': 'legal_miss'}, inplace=True)
    else:
        legal_miss = pd.DataFrame(columns=['category', 'legal_miss'])

    white_df = df[df['type'] == 'White'].copy()
    if not white_df.empty:
        white_df['over_score'] = (white_df['rating'] - 3).clip(lower=0)
        legal_over = white_df.groupby('category')['over_score'].mean().reset_index()
        legal_over.rename(columns={'over_score': 'legal_over'}, inplace=True)
    else:
        legal_over = pd.DataFrame(columns=['category', 'legal_over'])

    if not legal_miss.empty or not legal_over.empty:
        df_legal_summary = pd.merge(legal_miss, legal_over, on='category', how='outer').fillna(0)
        
        fig_legal = go.Figure()
        # 左側（認識が不足）
        fig_legal.add_trace(go.Bar(
            y=df_legal_summary['category'], x=-df_legal_summary['legal_miss'], orientation='h',
            name='認識が不足 ', marker_color='#ef4444',
            text=df_legal_summary['legal_miss'].apply(lambda x: f"{x:.1f}" if x > 0 else ""), textposition='inside',
            hovertemplate='<b>%{y}</b><br><b>不足度:</b> %{x:.1f}<extra></extra>'
        ))
        # 右側（認識が過剰）
        fig_legal.add_trace(go.Bar(
            y=df_legal_summary['category'], x=df_legal_summary['legal_over'], orientation='h',
            name='認識が過剰 ', marker_color='#f97316',
            text=df_legal_summary['legal_over'].apply(lambda x: f"{x:.1f}" if x > 0 else ""), textposition='inside',
            hovertemplate='<b>%{y}</b><br><b>過剰度:</b> %{x:.1f}<extra></extra>'
        ))
        
        fig_legal.add_vline(x=0, line_width=1.5, line_color="#666")
        fig_legal.update_layout(
            xaxis=dict(
                range=[-3, 3], 
                title="← 認識が不足  ｜ 認識が過剰  →",
                tickvals=[-2, 0, 2],
                ticktext=['要注意', '適正', '要注意']
            ),
            yaxis=dict(autorange="reversed"), 
            barmode='relative', 
            height=400,
            margin=dict(l=0,r=0,t=10,b=0), 
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_legal, use_container_width=True)
    else:
        st.info("データが不足しています")

# ----------------------------------------------------
# タブ2：世の中の感覚との比較 
# ----------------------------------------------------
with tab_cat_social:
    st.markdown("##### 👥 類型別：認識のズレ分析")
    st.caption("パワハラ6類型ごとの**世間平均とのズレ**を分析します。**中心（0）が世間平均と一致**しています。")

    gap_summary = df.groupby('category')['standardized_bias'].mean().reset_index()
    colors = ['#0d6efd' if x >= 0 else '#fd7e14' for x in gap_summary['standardized_bias']]
    
    fig_gap = go.Figure()
    fig_gap.add_trace(go.Bar(
        y=gap_summary['category'], 
        x=gap_summary['standardized_bias'], 
        orientation='h',
        marker_color=colors,
        text=gap_summary['standardized_bias'].apply(lambda x: f"{x:+.1f}"),
        textposition='outside',
        hovertemplate='<b>%{y}</b><br><b>世間とのズレ:</b> %{x:+.2f}<extra></extra>'
    ))
    
    fig_gap.add_vline(x=0, line_width=2, line_color="#333", line_dash="solid")
    fig_gap.add_vrect(x0=0, x1=2.5, fillcolor="#0d6efd", opacity=0.05, layer="below", line_width=0)
    fig_gap.add_vrect(x0=-2.5, x1=0, fillcolor="#fd7e14", opacity=0.05, layer="below", line_width=0)

    fig_gap.update_layout(
        xaxis=dict(
            range=[-2.5, 2.5], 
            title="← 甘い (寛容) ｜ 厳しい (厳格) →",
            tickvals=[-2, 0, 2],
            ticktext=['甘い', '世間平均', '厳しい']
        ),
        yaxis=dict(autorange="reversed"), 
        margin=dict(l=0,r=0,t=10,b=0), 
        height=400,
        showlegend=False
    )
    st.plotly_chart(fig_gap, use_container_width=True)

st.markdown("---")

# ==========================================
# UI表示：3. 世の中との認識ギャップ分布
# ==========================================
st.subheader("📍 世の中との認識ギャップ分布")
st.caption("全30問における、あなたの認識と世の中の平均との差を示しています。")

st.info("""
**グラフの見方(プロット上のシンボルをホバー/タップするとシナリオの詳細が表示されます)**

**軸の意味：**
- **X軸（横）**：世の中の平均スコア → 右に行くほど「世間はハラスメントだと感じる」
- **Y軸（縦）**：あなたのスコア → 上に行くほど「あなたはハラスメントだと感じる」
- **点線（対角線）**：世間と同じ判断のライン。この線上にあれば認識が一致しています

**シンボルの意味：**
- **● (丸)**: 法的リスクなし → 判断が基準内
- **× (バツ)**: 法的リスクあり → 法的基準とズレている項目

**背景色の意味：**
- 🟢 **緑ゾーン（対角線付近）**: 認識が一致している安全領域
- 🟡 **黄ゾーン（中距離）**: やや認識に差がある注意領域  
- 🔴 **赤ゾーン（遠距離）**: 認識のズレが大きい危険領域

**位置の意味：**
- **対角線より上**: あなたの方が厳しい判断（過敏傾向）
- **対角線より下**: あなたの方が甘い判断（鈍感傾向）
""", icon="ℹ️")

# --- 散布図描画ロジック ---
def plot_scatter_analysis(df_scatter: pd.DataFrame):
    df_plot = df_scatter.copy()
    
    # ホバーテキスト準備
    if 'text' not in df_plot.columns:
        df_plot['text_body'] = df_plot['title']
    else:
        df_plot['text_body'] = df_plot['text']
        
    df_plot['hover_text'] = df_plot['text_body'].apply(lambda x: format_hover_text(x, 40))
    df_plot['is_legal_risk'] = df_plot['legal_level'].apply(lambda x: True if x != "なし" else False)

    fig = go.Figure()

    # 背景：等高線
    # Z = |Y - X| で中心線からの距離を計算
    # 色: 緑(安全) -> 黄(注意) -> 赤(危険)
    x_grid = np.linspace(0.5, 6.5, 100)
    y_grid = np.linspace(0.5, 6.5, 100)
    X, Y = np.meshgrid(x_grid, y_grid)
    Z = np.abs(Y - X) 

    fig.add_trace(go.Contour(
        z=Z, x=x_grid, y=y_grid,
        colorscale=[
            [0.0, 'rgba(46, 204, 113, 0.15)'], # 0.0: Green
            [0.2, 'rgba(46, 204, 113, 0.15)'], # 1.0付近まで緑
            [0.2, 'rgba(241, 196, 15, 0.15)'], # 1.0から黄色
            [0.5, 'rgba(241, 196, 15, 0.15)'], # 2.5付近まで黄色
            [0.5, 'rgba(231, 76, 60, 0.15)'],  # 2.5から赤
            [1.0, 'rgba(231, 76, 60, 0.15)'],  # 最後まで赤
        ],
        contours=dict(
            start=0, end=6, 
            coloring='fill', 
            showlines=False
        ),
        showscale=False, 
        hoverinfo='skip',
    ))

    # データ点
    categories = df_plot['category'].unique()
    colors = px.colors.qualitative.Bold

    for i, cat in enumerate(categories):
        df_cat = df_plot[df_plot['category'] == cat]
        
        fig.add_trace(go.Scatter(
            x=df_cat['avg_rating'], 
            y=df_cat['rating'], 
            mode='markers', 
            name=cat,
            marker=dict(
                size=12, 
                color=colors[i % len(colors)], 
                symbol=['x' if r else 'circle' for r in df_cat['is_legal_risk']], 
                line=dict(width=1, color='white')
            ),
            text=df_cat['title'], 
            customdata=df_cat['hover_text'],
            # タイトル、本文、あなた、世の中の順で表示
            hovertemplate="%{text}<br><br>%{customdata}<br><br><b>あなたの回答:</b> %{y:.0f}<br><b>世間の平均:</b> %{x:.2f}<extra></extra>"
        ))

    # 対角線（基準線）
    fig.add_shape(type="line", x0=0.5, y0=0.5, x1=6.5, y1=6.5, line=dict(color="gray", width=2, dash="dot"))
    
    fig.update_layout(
        xaxis_title="世の中の平均", 
        yaxis_title="あなたの回答", 
        height=500, 
        margin=dict(l=20,r=20,t=20,b=20), 
        plot_bgcolor='white',
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )
    return fig

fig_map = plot_scatter_analysis(df)
st.plotly_chart(fig_map, use_container_width=True)

st.markdown("---")

# ==========================================
# UI表示：4. 詳細リスト
# ==========================================
st.subheader("📝 回答詳細")
st.caption("あなたの回答に基づき、各シナリオの詳細な分析結果を表示します。 法的リスクや世の中の感覚とのズレを確認できます。")

# フィルタ状態のセッション管理
st.session_state.setdefault("show_all_details", False)
# デフォルトで「法的リスク項目」を選択
st.session_state.setdefault("detail_filter", "⚠️ 法的リスク項目")

# コールバックで相互同期
def _on_show_all_change():
    if st.session_state.get("show_all_details"):
        st.session_state["detail_filter"] = None

def _on_filter_change():
    # pills選択時に全表示をオフにする
    sel = st.session_state.get("detail_filter")
    if sel:
        st.session_state["show_all_details"] = False

# フィルタ解除トグル（見た目用、チェックONでpillsを外す）
show_all = st.checkbox(
    "フィルタを解除して全シナリオを表示",
    value=st.session_state["show_all_details"],
    key="show_all_details",
    on_change=_on_show_all_change
)

# Pillsフィルタ（全シナリオ一覧は「フィルタ解除」で制御）
filter_options = ["⚠️ 法的リスク項目", "📈 世間より「厳しい」項目", "📉 世間より「甘い」項目"]
try:
    # セッション状態で初期値管理
    selection = st.pills("表示フィルタ", filter_options, key="detail_filter", on_change=_on_filter_change)
except AttributeError:
    # radioには未選択状態がないため、全表示時はNone扱いにする
    if show_all:
        selection = None
    else:
        selection = st.radio("表示フィルタ", filter_options, horizontal=True, key="detail_filter_radio")
        st.session_state["detail_filter"] = selection
        _on_filter_change()

# 事後評価用のフラグ（派生値として利用）
active_filter = selection if selection else None
show_all = st.session_state.get("show_all_details", False) or active_filter is None

# ------------------------------------------
# ヘルパー関数定義
# ------------------------------------------

def get_rating_label(score):
    """数値スコアに対応するリッカート尺度ラベルを返す"""
    score_int = int(round(score))
    labels = {
        1: "全く感じない",
        2: "あまり感じない",
        3: "どちらかと言えば感じない",
        4: "どちらかと言えば感じる",
        5: "かなり感じる",
        6: "強く感じる"
    }
    return labels.get(score_int, "")

def create_distribution_chart(user_rating, avg_rating):
    """世間の回答分布と自分の位置を示すミニグラフを作成"""
    x = [1, 2, 3, 4, 5, 6]
    y = []
    # 分布推計 (平均値を中心とした山を作る)
    for i in x:
        dist = abs(i - avg_rating)
        weight = max(0.1, 5.0 - dist * 1.5)
        y.append(weight)
    
    sum_y = sum(y)
    y_per = [(val / sum_y) * 100 for val in y]
    
    user_idx = int(user_rating) - 1
    user_percentage = y_per[user_idx] if 0 <= user_idx < 6 else 0
    
    colors = ['#e0e0e0'] * 6 
    if 0 <= user_idx < 6:
        colors[user_idx] = '#0d6efd' 

    fig = go.Figure(data=[go.Bar(
        x=x, y=y_per,
        marker_color=colors,
        text=[f"{v:.0f}%" for v in y_per],
        textposition='auto',
        hoverinfo='none'
    )])
    
    # 平均値ライン
    fig.add_vline(x=avg_rating, line_width=1, line_dash="dash", line_color="#555")

    # レイアウト設定
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=30),
        height=120,
        xaxis=dict(
            tickmode='array',
            tickvals=[1, 2, 3, 4, 5, 6],
            ticktext=['1', '2', '3', '4', '5', '6'],
            showgrid=False,
            title=None,
            fixedrange=True,
            showticklabels=True
        ),
        yaxis=dict(showgrid=False, showticklabels=False, fixedrange=True),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
        bargap=0.2
    )
    return fig, user_percentage

def render_detail_card(row, tag_text, tag_color, bg_color, show_severity=False):
    """詳細カードを描画する関数"""
    expander_title = f"{tag_text}： {row['title']} "
    
    # 深刻度レベルによるアイコン付与（法的リスクフィルター時のみ）
    if show_severity:
        if row['legal_level'] == "重":
            expander_title = f"{tag_text} [重度] {row['title']} "
        elif row['legal_level'] == "軽":
            expander_title = f"{tag_text} [軽度] {row['title']} "
    
    with st.expander(expander_title, expanded=False):
        
        # 0. 類型とambiguity
        c1, c2 = st.columns([3, 1])
        with c1:
            st.caption(f"📂 {row['category']}")
        with c2:
            st.markdown(f"""<div style="background-color:{tag_color}15; color:{tag_color}; border:1px solid {tag_color}; padding:4px 10px; border-radius:15px; text-align:center; font-weight:bold; font-size:0.8em;">{tag_text}</div>""", unsafe_allow_html=True)
        
        # 1. シナリオ本文
        st.write(row['text'])
        st.markdown("---")
        
        # 2. 3つの情報
        c1, c2, c3 = st.columns(3)
        
        # あなたの回答
        with c1:
            label = get_rating_label(row['rating'])
            st.markdown(f"""
            <div style="text-align: center; border-right: 1px solid #eee;">
                <div style="color: #777; font-size: 0.8em; margin-bottom: 5px;">あなたの回答</div>
                <div style="font-size: 1.8em; font-weight: bold; color: {tag_color}; line-height: 1;">{int(row['rating'])}</div>
                <div style="font-size: 0.9em; font-weight: bold; color: {tag_color}; margin-top: 5px;">{label}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # 法的基準
        with c2:
            if row['type'] == 'Black':
                judge_text = "パワハラに該当する"
                judge_color = "#dc3545" # 赤
            elif row['type'] == 'White':
                judge_text = "パワハラに該当しない"
                judge_color = "#28a745" # 緑
            else:
                judge_text = "グレーゾーン"
                judge_color = "#6c757d" # グレー
            
            st.markdown(f"""
            <div style="text-align: center; border-right: 1px solid #eee;">
                <div style="color: #777; font-size: 0.8em; margin-bottom: 5px;">法的基準</div>
                <div style="font-size: 1.2em; font-weight: bold; color: {judge_color}; margin-top: 10px;">{judge_text}</div>
            </div>
            """, unsafe_allow_html=True)

        # 世間の平均
        with c3:
            avg_label = get_rating_label(row['avg_rating'])
            st.markdown(f"""
            <div style="text-align: center;">
                <div style="color: #777; font-size: 0.8em; margin-bottom: 5px;">世間の平均</div>
                <div style="font-size: 1.8em; font-weight: bold; color: #555; line-height: 1;">{row['avg_rating']:.1f}</div>
                <div style="font-size: 0.9em; color: #555; margin-top: 5px;">{avg_label}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)

        # 3. 分布図
        st.caption("📊 世間の回答分布とあなたの位置 (青)")
        fig, user_share = create_distribution_chart(row['rating'], row['avg_rating'])
        # ★変更点：キー引数を追加してID重複エラーを回避
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"chart_{row['scenario_id']}")

        # マイノリティ判定
        if user_share < 15:
            st.markdown(f"<div style='text-align:center; color:#dc3545; font-size:0.9em;'>⚠️ あなたと同じ回答は <b>{user_share:.0f}%</b> (少数派)</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='text-align:center; color:#28a745; font-size:0.9em;'>✅ あなたと同じ回答は <b>{user_share:.0f}%</b> (多数派)</div>", unsafe_allow_html=True)

        # 4. 解説とアドバイス
        st.markdown("---")
        explanation = row.get('explanation', '解説データなし')
        advice = row.get('action_guide') or row.get('advice') or 'アドバイスデータなし'
        legal_ref = row.get('legal_ref', '')
        
        st.markdown(f"""
        <div style="margin-top:10px; background-color:{bg_color}; padding:15px; border-radius:8px; border:1px solid {tag_color}30;">
            <div style="font-weight:bold; font-size:1.0em; color:#444;">💡 解説</div>
            <div style="font-size:0.95em; margin-bottom:12px; line-height:1.5;">{explanation}</div>
            <div style="font-weight:bold; font-size:1.0em; color:#444;">🚀 改善アクション</div>
            <div style="font-size:0.95em; font-weight:bold; color:{tag_color}; line-height:1.5;">{advice}</div>
        """, unsafe_allow_html=True)
        
        # 根拠がある場合は追加表示
        if legal_ref and legal_ref.strip():
            st.markdown(f"""
            <div style="margin-top:12px;">
                <div style="font-weight:bold; font-size:0.95em; color:#666;">📋 根拠</div>
                <div style="font-size:0.9em; color:#666; line-height:1.5; margin-top:5px; font-style:italic;">{legal_ref}</div>
            </div>
            </div>
        """, unsafe_allow_html=True)
        else:
            st.markdown("        </div>", unsafe_allow_html=True)

# ------------------------------------------
# データフィルタリングと描画実行
# ------------------------------------------

df_display = pd.DataFrame()
empty_msg = ""

if show_all:
    df_display = df.copy()
    df_display = df_display.sort_values('scenario_id')
    empty_msg = "データがありません。"
    def get_all_tag(row):
        bias = row['standardized_bias']
        if bias >= 1.0:
            return ("🟣 過敏", "#6f42c1", "#f5f0ff")
        elif bias <= -1.0:
            return ("🔴 鈍感", "#dc3545", "#fff5f5")
        elif 0.5 <= bias < 1.0:
            return ("🔵 厳格傾向", "#0d6efd", "#f0f7ff")
        elif -1.0 < bias <= -0.5:
            return ("🟠 寛容傾向", "#fd7e14", "#fffaf0")
        else:
            return ("✅ 平均的", "#28a745", "#f0fff4")
    tags = df_display.apply(get_all_tag, axis=1)
    df_display['tag_text'] = [t[0] for t in tags]
    df_display['tag_color'] = [t[1] for t in tags]
    df_display['bg_color'] = [t[2] for t in tags]

elif active_filter == "⚠️ 法的リスク項目":
    df_display = df[df['legal_level'] != "なし"].copy()
    empty_msg = "法的基準と大きく乖離している項目はありません。素晴らしい判断力です。"
    # 法的規範ベースのタグに切り替え（不足/過剰）
    df_display['tag_text'] = df_display.apply(lambda r: "🏴 認識不足" if r['type'] == 'Black' else "🏳️ 認識過剰", axis=1)
    df_display['tag_color'] = df_display.apply(lambda r: "#dc3545" if r['type'] == 'Black' else "#fd7e14", axis=1)
    df_display['bg_color'] = df_display.apply(lambda r: "#fff5f5" if r['type'] == 'Black' else "#fffaf0", axis=1)

elif active_filter == "📈 世間より「厳しい」項目":
    df_display = df[(df['legal_level'] == "なし") & (df['standardized_bias'] >= 1.5)].copy()
    empty_msg = "世間よりも極端に厳しく捉えている項目はありません。"
    # 厳しい方向のタグ（過敏 or 厳格傾向）
    def get_strict_tag(row):
        if row['standardized_bias'] >= 1.0:
            return ("🟣 過敏", "#6f42c1", "#f5f0ff")
        else:
            return ("🔵 厳格傾向", "#0d6efd", "#f0f7ff")
    tags = df_display.apply(get_strict_tag, axis=1)
    df_display['tag_text'] = [t[0] for t in tags]
    df_display['tag_color'] = [t[1] for t in tags]
    df_display['bg_color'] = [t[2] for t in tags]

elif active_filter == "📉 世間より「甘い」項目":
    df_display = df[(df['legal_level'] == "なし") & (df['standardized_bias'] <= -1.5)].copy()
    empty_msg = "世間よりも極端に甘く捉えている項目はありません。"
    # 甘い方向のタグ（鈍感 or 寛容傾向）
    def get_lenient_tag(row):
        if row['standardized_bias'] <= -1.0:
            return ("🔴 鈍感", "#dc3545", "#fff5f5")
        else:
            return ("🟠 寛容傾向", "#fd7e14", "#fffaf0")
    tags = df_display.apply(get_lenient_tag, axis=1)
    df_display['tag_text'] = [t[0] for t in tags]
    df_display['tag_color'] = [t[1] for t in tags]
    df_display['bg_color'] = [t[2] for t in tags]

else: # フォールバック（想定外の値）
    df_display = df.copy()
    df_display = df_display.sort_values('scenario_id')
    empty_msg = "データがありません。"

# リスト描画ループ
if not df_display.empty:
    for i, row in df_display.iterrows():
        render_detail_card(
            row,
            row['tag_text'],
            row['tag_color'],
            row['bg_color'],
            show_severity=(active_filter == "⚠️ 法的リスク項目")
        )
else:
    st.info(empty_msg)