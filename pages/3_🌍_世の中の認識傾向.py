import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import textwrap
from utils.db import get_global_analysis_data_view, generate_demo_data

st.set_page_config(page_title="世の中の傾向", page_icon="🌏", layout="wide")

# カスタムCSS
st.markdown("""
    <style>
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        flex-wrap: wrap;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        white-space: pre-wrap;
        border-radius: 4px 4px 0 0;
        font-weight: bold;
        font-size: 12px;
        padding: 0 10px;
    }
    </style>
""", unsafe_allow_html=True)

# ツールチップ用にテキストを改行する関数
def format_hover_text(text, width=40):
    if not isinstance(text, str): return ""
    return "<br>".join(textwrap.wrap(text, width=width))

# ==========================================
# 0. データロード & 前処理
# ==========================================

# Note: キャッシュなし = リアルタイム反映（開発・小規模運用向け）
# 大規模運用時は @st.cache_data(ttl=60) を追加して負荷軽減を検討
def load_data():
    """
    データを読み込む。データが不足している場合はデモデータを使用。
    
    Returns:
        tuple: (DataFrame, is_demo: bool)
    """
    # SQL Viewから一括取得
    view_data = get_global_analysis_data_view()
    
    if not view_data:
        st.info("📊 現在のデータ数: 0人（まだ回答データがありません）")
        st.info("💻 研究・実験用のデモデータを使用します。")
        return generate_demo_data(), True
    
    df_full = pd.DataFrame(view_data)
    
    # 必須カラムの確認
    required_cols = ['user_id', 'rating', 'scenario_id', 'title', 'text', 'category', 'type']
    missing_cols = [col for col in required_cols if col not in df_full.columns]
    
    if missing_cols:
        st.error(f"⚠️ 必須カラムが不足しています: {missing_cols}")
        st.write(f"利用可能なカラム: {df_full.columns.tolist()}")
        st.info("デモデータを使用します。")
        return generate_demo_data(), True
    
    # データ型の修正
    df_full['rating'] = pd.to_numeric(df_full['rating'], errors='coerce')
    df_full['scenario_id'] = df_full['scenario_id'].astype(int)
    
    # ユーザー数をチェック（10人未満ならデモデータ）
    unique_users = df_full['user_id'].nunique()
    
    if unique_users < 10:
        st.info(f"📊 現在のデータ数: {unique_users}人（統計的に十分なデータではありません）")
        st.info("💻 研究・実験用のデモデータを使用します。")
        return generate_demo_data(), True
    
    return df_full, False

with st.spinner("データを分析中..."):
    df, is_demo = load_data()

if df.empty:
    st.warning("⚠️ まだ十分な分析データが集まっていません。")
    st.stop()

# デモデータ使用時の透明性表示
if is_demo:
    st.warning("""
    ### ⚠️ デモデータモード
    
    現在、**研究・実験用のシミュレーションデータ**を表示しています。
    
    **📌 透明性に関する注意事項：**
    - このデータは統計的に妥当な分布を持つように生成された **架空のデータ** です
    - 実際のユーザーの回答ではありません
    - 研究目的のユーザーテストやシステム検証に使用されます
    
    **🎯 実データへの切り替え条件：**
    - ユーザー数が **10人以上** になると、自動的に実データに切り替わります
    """)
    st.markdown("---")

# ==========================================
# 1. コミュニティの認識構造 (現状認識)
# ==========================================
title_suffix = "(デモデータ)" if is_demo else ""
st.title(f"🌏 世の中の認識傾向{title_suffix}")
st.markdown("社会全体のハラスメント認識の傾向を把握し、どのような認識ギャップが存在するかを分析します。")

# --- KPI計算 ---
black_df = df[df['type'] == 'Black']
miss_rate = (black_df['rating'] <= 3).mean() * 100 if not black_df.empty else 0.0

white_df = df[df['type'] == 'White']
over_rate = (white_df['rating'] >= 4).mean() * 100 if not white_df.empty else 0.0

gray_stats = df[df['type'] == 'Gray'].groupby('scenario_id')['rating'].std()
conflict_score = gray_stats.mean() if not gray_stats.empty else 0.0

# --- KPI表示 ---
k1, k2, k3, k4 = st.columns(4)

with k1:
    st.metric("👥 分析対象人数", f"{df['user_id'].nunique():,} 人", help="サンプル数")
with k2:
    st.metric("⚠️ 違法行為の見逃し", f"{miss_rate:.1f}%", help="法的にはパワハラに該当するシナリオを「パワハラではない」とした割合")
with k3:
    st.metric("🛡️ 適法行為の問題視", f"{over_rate:.1f}%", help="法的にはパワハラに該当しないシナリオを「パワハラである」とした割合")
with k4:
    st.metric("⚡ 認識の割れ具合", f"{conflict_score:.2f}", help="グレー事例の標準偏差。基準: 〜1.0=合意形成済み, 1.0〜1.3=解釈の相違, 1.3以上=価値観の対立")
    if conflict_score < 1.0: st.markdown(":green[**✅ 合意形成済み**]")
    elif conflict_score < 1.3: st.markdown(":orange[**⚠️ 解釈の相違**]")
    else: st.markdown(":red[**🚨 価値観の対立**]")

st.write("") 

# --- 中段：属性分布 & 分野別内訳 ---
c_demo, c_breakdown = st.columns([2, 3])

with c_demo:
    with st.expander("📊 参加者の属性分布を詳しく見る", expanded=True):
        st.caption("分析対象となっているユーザーの内訳です。")
        df_users_unique = df.drop_duplicates(subset=['user_id'])
        tabs = st.tabs(["年代", "性別", "役職", "雇用形態", "業界", "職種", "勤続年数"])
        colors_pie = px.colors.qualitative.Pastel
        
        def plot_pie(col):
            c = df_users_unique[col].value_counts().reset_index()
            c.columns = [col, 'count']
            fig = px.pie(c, values='count', names=col, hole=0.4, color_discrete_sequence=colors_pie)
            fig.update_layout(height=220, margin=dict(t=10, b=10, l=10, r=10), showlegend=True)
            st.plotly_chart(fig, use_container_width=True)

        def plot_bar(col):
            c = df_users_unique[col].value_counts().reset_index()
            c.columns = [col, 'count']
            c = c.sort_values('count', ascending=True)
            fig = px.bar(c, x='count', y=col, orientation='h', text_auto=True)
            fig.update_traces(marker_color='#6c5ce7')
            fig.update_layout(height=220, margin=dict(t=10, b=10, l=0, r=0), xaxis=dict(showticklabels=False), yaxis_title=None)
            st.plotly_chart(fig, use_container_width=True)

        with tabs[0]: plot_pie('age')
        with tabs[1]: plot_pie('gender')
        with tabs[2]: plot_bar('position')
        with tabs[3]: plot_pie('employment_status')
        with tabs[4]: plot_bar('industry')
        with tabs[5]: plot_bar('job_type')
        with tabs[6]: plot_bar('service_years')

with c_breakdown:
    with st.expander("📊 【内訳】類型ごとの「認識ギャップ」を見る", expanded=True):
        st.caption("どの類型において、認識のズレや萎縮が起きているかを確認します。")
        cat_risks = []
        _cat_series = df['category'].dropna().astype(str).str.strip()
        for cat in sorted([c for c in _cat_series.unique() if c]):
            cat_df = df[df['category'].astype(str).str.strip() == cat]
            b_df = cat_df[cat_df['type'] == 'Black']
            miss = (b_df['rating'] <= 3).mean() * 100 if not b_df.empty else None
            w_df = cat_df[cat_df['type'] == 'White']
            over = (w_df['rating'] >= 4).mean() * 100 if not w_df.empty else None
            g_df = cat_df[cat_df['type'] == 'Gray']
            std_avg = g_df.groupby('scenario_id')['rating'].std().mean() if not g_df.empty else None
            cat_risks.append({"カテゴリ": cat, "⚠️ 違法行為の見逃し": miss, "🛡️ 適法行為の問題視": over, "⚡ 認識の割れ具合": std_avg})
            
        risk_df = pd.DataFrame(cat_risks).set_index("カテゴリ")
        # 色付けの説明（凡例）
        st.caption(
            """
            色付けのルール：
            - ⚠️ 違法行為の見逃し・🛡️ 適法行為の問題視：低いほど望ましい（緑）／高いほど要注意（赤）
            - ⚡ 認識の割れ具合：〜1.0=緑（合意形成済み）、1.0〜1.3=黄（解釈の相違）、1.3以上=赤（価値観の対立）
            """
        )
        # 認識の割れ具合の閾値ベース着色（〜1.0=緑, 1.0〜1.3=黄, 1.3以上=赤）
        def _conflict_bg(v):
            if pd.isna(v):
                return ''
            if v < 1.0:
                return 'background-color: #e9f7ef; color: black;'  # light green + 黒文字
            elif v < 1.3:
                return 'background-color: #fff9e6; color: black;'  # light yellow + 黒文字
            else:
                return 'background-color: #fdecea; color: black;'  # light red + 黒文字
        # 行数に応じて高さを自動調整（空白行の発生を抑制）
        _row_h = 36
        _base_h = 48
        _df_height = min(600, _base_h + _row_h * max(len(risk_df), 1))
        st.dataframe(
            risk_df.style.background_gradient(cmap='RdYlGn_r', subset=['⚠️ 違法行為の見逃し', '🛡️ 適法行為の問題視'], vmin=0, vmax=50)
                        .format("{:.1f}%", subset=['⚠️ 違法行為の見逃し', '🛡️ 適法行為の問題視'], na_rep="-")
                        .format("{:.2f}", subset=['⚡ 認識の割れ具合'], na_rep="-")
                        .applymap(_conflict_bg, subset=['⚡ 認識の割れ具合'])
                        .highlight_null(color='lightgray'),
            use_container_width=True, height=_df_height
        )

st.markdown("---")


# ------------------------------------------
# 
# ------------------------------------------
st.subheader("パワハラ判断傾向マップ")
st.markdown("各シナリオのハラスメント認識傾向を「ハラスメント強度」（平均スコア）と「認識の割れ具合」（標準偏差）の2軸で可視化します。 ")
st.info("""
**🗺️ グラフの見方 (プロット上のシンボルをホバー/タップするとシナリオの詳細が表示されます)**

**軸の意味:**
- **X軸 (ハラスメント強度)**: スコアが高いほど「ハラスメント」と認識されやすい
- **Y軸 (認識の割れ具合)**: スコアのばらつきが大きいほど、判断にばらつきがある

**シンボルの意味:**
- **× (Black)**: 法的には違法・アウト と判定されるシナリオ
- **▲ (Gray)**: 判断が分かれる グレーゾーンのシナリオ
- **● (White)**: 法的には適正・セーフ と判定されるシナリオ

**ゾーンの意味**:
- 🟢 **低リスクゾーン（左下）**: パワハラではないと判断する人が多く、認識が統一されている
- 🟡 **グレーゾーン（中央）**: 判断が分かれ、解釈が異なりやすい領域
- 🔴 **高リスクゾーン（右側）**: パワハラだと判断する人が多い領域
""")
df_filtered = df.copy()

# セッション既定値（ウィジェット生成前に初期化）
st.session_state.setdefault("map_sel_pos", "全役職")
st.session_state.setdefault("map_sel_serv", "全勤続年数")
st.session_state.setdefault("map_sel_ind", "全業界")
st.session_state.setdefault("map_sel_job", "全職種")

# 詳細フィルター（エクスパンダ）
with st.expander("🔍 詳細フィルター", expanded=False):
    st.caption("役職・勤続年数・業界・職種で絞り込みできます。")
    ind_list = ["全業界"] + sorted([x for x in df['industry'].dropna().unique() if x])
    pos_list = ["全役職"] + sorted([x for x in df['position'].dropna().unique() if x])
    serv_list = ["全勤続年数"] + sorted(list(df['service_years'].dropna().unique()))
    job_list = ["全職種"] + sorted([x for x in df['job_type'].dropna().unique() if x])

    # 解除コールバック（ウィジェット生成前に状態を更新）
    def _reset_map_filters():
        st.session_state["map_sel_pos"] = "全役職"
        st.session_state["map_sel_serv"] = "全勤続年数"
        st.session_state["map_sel_ind"] = "全業界"
        st.session_state["map_sel_job"] = "全職種"

    st.button("フィルターを全て解除", type="secondary", on_click=_reset_map_filters)

    cfa, cfb = st.columns(2)
    with cfa:
        st.selectbox("役職", pos_list, index=0, key="map_sel_pos")
        st.selectbox("業界", ind_list, index=0, key="map_sel_ind")
    with cfb:
        st.selectbox("勤続年数", serv_list, index=0, key="map_sel_serv")
        st.selectbox("職種", job_list, index=0, key="map_sel_job")

# 絞り込みの適用
sel_ind = st.session_state.get("map_sel_ind", "全業界")
sel_pos = st.session_state.get("map_sel_pos", "全役職")
sel_serv = st.session_state.get("map_sel_serv", "全勤続年数")
sel_job = st.session_state.get("map_sel_job", "全職種")

if sel_ind != "全業界":
    df_filtered = df_filtered[df_filtered['industry'] == sel_ind]
if sel_pos != "全役職":
    df_filtered = df_filtered[df_filtered['position'] == sel_pos]
if sel_serv != "全勤続年数":
    df_filtered = df_filtered[df_filtered['service_years'] == sel_serv]
if sel_job != "全職種":
    df_filtered = df_filtered[df_filtered['job_type'] == sel_job]

with st.container():
    if df_filtered.empty:
        st.warning("データが不足しています。")
    else:
        scenario_stats = df_filtered.groupby(['title', 'category', 'type', 'text']).agg(
            mean=('rating', 'mean'), std=('rating', 'std'), count=('rating', 'count')
        ).reset_index()
        
        scenario_stats['hover_text'] = scenario_stats['text'].apply(lambda x: format_hover_text(x, 40))

        fig = go.Figure()
        # Zones
        fig.add_shape(type="rect", x0=1, y0=0, x1=2.5, y1=1.0, fillcolor="rgba(46, 204, 113, 0.1)", line_width=0, layer="below")
        fig.add_shape(type="rect", x0=4.5, y0=0, x1=6, y1=1.0, fillcolor="rgba(231, 76, 60, 0.1)", line_width=0, layer="below")
        fig.add_shape(type="rect", x0=1, y0=1.3, x1=6, y1=2.5, fillcolor="rgba(241, 196, 15, 0.1)", line_width=0, layer="below")
        
        symbol_map = {'Black': 'x', 'Gray': 'triangle-up', 'White': 'circle'}
        color_palette = px.colors.qualitative.Bold 
        cat_colors = {cat: color_palette[i % len(color_palette)] for i, cat in enumerate(sorted(scenario_stats['category'].unique()))}
        
        for t in ['White', 'Gray', 'Black']:
            for cat in sorted(scenario_stats['category'].unique()):
                d = scenario_stats[(scenario_stats['type'] == t) & (scenario_stats['category'] == cat)]
                if not d.empty:
                    fig.add_trace(go.Scatter(
                        x=d['mean'], y=d['std'], mode='markers', name=cat, legendgroup=cat, showlegend=True,
                        marker=dict(size=14, symbol=symbol_map[t], color=cat_colors[cat], line=dict(width=1, color='white'), opacity=0.9),
                        customdata=d['hover_text'],
                        text=d['title'],
                        hovertemplate="%{text}<br><br>%{customdata}<br><br><b>平均スコア:</b> %{x:.2f}<br><b>認識の割れ具合:</b> %{y:.2f}<extra></extra>"
                    ))
        
        fig.update_layout(xaxis_title="ハラスメント強度", yaxis_title="認識の割れ具合", height=550, margin=dict(l=0,r=0,t=10,b=0), legend=dict(orientation="h", y=1.1))
        names = set()
        fig.for_each_trace(lambda trace: trace.update(showlegend=False) if (trace.name in names) else names.add(trace.name))
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ------------------------------------------
# 属性間ギャップ分析
# ------------------------------------------
st.subheader("属性間ギャップ分析")
st.markdown("異なる属性間での**判断傾向の違い**を比較し、同じ行動に対する**判断の分かれやすさ**を確認します。")
if is_demo:
    st.info("デモデータを使用して分析しています", icon="ℹ️")
else:
    st.info("実データに存在しない属性値は、デモデータで補完しています", icon="ℹ️")

axis_map = {
    'position': '役職', 'age': '年代', 'gender': '性別',
    'employment_status': '雇用形態', 'industry': '業界', 'job_type': '職種', 'service_years': '勤続年数'
}

# デモデータ（実シナリオ活用）
demo_df = generate_demo_data()

# 条件設定エリア
with st.container(border=True):
    st.markdown("##### 🛠️ 比較条件の設定")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        target_axis = st.selectbox("① 比較する軸 (切り口)", list(axis_map.keys()), format_func=lambda x: axis_map[x])
        # 実データとデモデータの属性値を統合
        if target_axis in df.columns:
            real_vals = set([str(x) for x in df[target_axis].dropna().unique() if x])
            demo_vals = set([str(x) for x in demo_df[target_axis].dropna().unique() if x])
            u_vals = sorted(list(real_vals | demo_vals))  # 和集合
        else:
            u_vals = []
        
    with c2:
        group_a = st.selectbox("② 比較対象 A", u_vals, index=0 if u_vals else None)
        
    with c3:
        group_b = st.selectbox("③ 比較対象 B", u_vals, index=1 if len(u_vals)>1 else 0)

st.caption("💡 グラフの点をホバー/タップすると、シナリオの全文が表示されます。")

# グラフ描画エリア
if group_a and group_b and group_a != group_b:
    # 実データから取得（存在しない場合はデモデータで補完）
    df_a = df[df[target_axis].astype(str) == group_a]
    df_b = df[df[target_axis].astype(str) == group_b]
    
    # データが不足している場合はデモデータで補完
    used_demo_a = False
    used_demo_b = False
    
    if df_a.empty:
        df_a = demo_df[demo_df[target_axis].astype(str) == group_a]
        used_demo_a = True
    
    if df_b.empty:
        df_b = demo_df[demo_df[target_axis].astype(str) == group_b]
        used_demo_b = True
    
    if not df_a.empty and not df_b.empty:
        # 補完情報を表示
        if used_demo_a or used_demo_b:
            補完情報 = []
            if used_demo_a:
                補完情報.append(f"**{group_a}**")
            if used_demo_b:
                補完情報.append(f"**{group_b}**")
            st.caption(f"💻 {' と '.join(補完情報)} のデータはデモデータで補完されています")
        
        # グルーピング前に必要なカラムの確認
        required_cols = ['title', 'text', 'rating']
        if all(col in df_a.columns for col in required_cols) and all(col in df_b.columns for col in required_cols):
            # scenario_idが存在する場合はそれを使用、なければtitleとtextで
            if 'scenario_id' in df_a.columns and 'scenario_id' in df_b.columns:
                sc_a = df_a.groupby('scenario_id').agg({'rating': 'mean', 'title': 'first', 'text': 'first'})
                sc_b = df_b.groupby('scenario_id').agg({'rating': 'mean', 'title': 'first', 'text': 'first'})
                
                # scenario_idでマージ（両方に存在するものだけ）
                diff = pd.merge(sc_a, sc_b, left_index=True, right_index=True, suffixes=('_a', '_b'))
                if not diff.empty:
                    diff['gap'] = (diff['rating_b'] - diff['rating_a']).abs()
                    diff = diff.rename(columns={'rating_a': 'a', 'rating_b': 'b', 'title_a': 'title', 'text_a': 'text'})
                    top = diff.sort_values('gap', ascending=False).head(10).reset_index()
                else:
                    top = None
            else:
                # フォールバック：titleとtextでグループ化
                sc_a = df_a.groupby(['title', 'text'])['rating'].mean()
                sc_b = df_b.groupby(['title', 'text'])['rating'].mean()
                
                diff = pd.concat([sc_a, sc_b], axis=1, keys=['a', 'b']).reset_index()
                # NaNを含む行を削除（両方のグループにデータがある行のみ残す）
                diff = diff.dropna(subset=['a', 'b'])
                
                if not diff.empty:
                    diff['gap'] = (diff['b'] - diff['a']).abs()
                    top = diff.sort_values('gap', ascending=False).head(10)
                else:
                    top = None
        else:
            st.error(f"⚠️ データの構造が不正です。必要なカラム {required_cols} が見つかりません。")
            top = None
        
        
        
        if top is not None and not top.empty:
            top['hover_text'] = top['text'].apply(lambda x: format_hover_text(x, 40))
            
            fig_d = go.Figure()
            for i, row in top.iterrows():
                fig_d.add_trace(go.Scatter(
                    x=[row['a'], row['b']], y=[row['title'], row['title']], 
                    mode='lines', line=dict(color='#bdc3c7'), showlegend=False,
                    hoverinfo='skip'
                ))
                fig_d.add_trace(go.Scatter(
                    x=[row['a']], y=[row['title']], mode='markers', name=group_a, 
                    marker=dict(color='#3498db', size=14), showlegend=(i==0),
                    customdata=[row['hover_text']],
                    text=[row['title']],
                    hovertemplate="%{text}<br><br>%{customdata}<br><br><b>" + group_a + ":</b> %{x:.2f}<extra></extra>"
                ))
                fig_d.add_trace(go.Scatter(
                    x=[row['b']], y=[row['title']], mode='markers', name=group_b, 
                    marker=dict(color='#e74c3c', size=14), showlegend=(i==0),
                    customdata=[row['hover_text']],
                    text=[row['title']],
                    hovertemplate="%{text}<br><br>%{customdata}<br><br><b>" + group_b + ":</b> %{x:.2f}<extra></extra>"
                ))
                
            fig_d.update_layout(
                title=f"認識ギャップ 大きい順 TOP10 ({group_a} vs {group_b})",
                height=500, 
                legend=dict(orientation="h", y=1.1),
                xaxis=dict(title="ハラスメント評価 (右に行くほど厳しい)"),
                yaxis=dict(autorange="reversed")
            )
            st.plotly_chart(fig_d, use_container_width=True)
        else:
            st.warning("比較対象のシナリオが見つかりませんでした。別の属性を選択してみてください。")
        
    else:
        st.warning("選択されたグループのデータが不足しています。")
else:
    st.info("👆 上記の条件を設定して、異なる2つのグループを比較してください。")

# ==========================================
# 3. 全シナリオ詳細データ (Bottom)
# ==========================================
st.markdown("---")
st.subheader("📚 全シナリオ詳細データ")

def get_mode(x):
    m = x.mode()
    return m.iloc[0] if not m.empty else np.nan

detail_stats = df.groupby(['scenario_id', 'title', 'category', 'type', 'text']).agg(
    avg=('rating', 'mean'),
    median=('rating', 'median'),
    mode=('rating', get_mode),
    std=('rating', 'std'),
    count=('rating', 'count')
).reset_index()

tab_chart, tab_table = st.tabs(["📊 分布可視化チャート", "📋 統計データ一覧"])

# Tab 1: 二極分散グラフ
with tab_chart:
    st.markdown("""
    **二極分散グラフ**: 中心（3と4の間）を境に、左側が「ハラスメントを感じない」、右側が「ハラスメントを感じる」回答の割合を示します。
    """)
    st.caption("💡 グラフの棒をホバー/タップすると、シナリオの全文が表示されます。")
    
    options_map = {
        1: "全く感じない", 2: "あまり感じない", 3: "どちらかと言えば感じない", 
        4: "どちらかと言えば感じる", 5: "かなり感じる", 6: "強く感じる"
    }

    score_counts = df.groupby(['title', 'rating']).size().reset_index(name='count')
    total_counts = df.groupby('title').size().reset_index(name='total')
    score_pct = pd.merge(score_counts, total_counts, on='title')
    score_pct['pct'] = score_pct['count'] / score_pct['total'] * 100
    
    titles = detail_stats.sort_values('avg', ascending=True)['title'].tolist()
    title_text_map = detail_stats.set_index('title')['text'].to_dict()

    fig_div = go.Figure()
    
    colors_neg = ['#2E86C1', '#5DADE2', '#AED6F1'] 
    for i, r in enumerate([1, 2, 3]):
        d = score_pct[score_pct['rating'] == r]
        d_merged = pd.DataFrame({'title': titles}).merge(d, on='title', how='left').fillna(0)
        d_merged['text'] = d_merged['title'].map(title_text_map).fillna('')
        d_merged['hover_text'] = d_merged['text'].apply(lambda x: format_hover_text(x, 40))

        fig_div.add_trace(go.Bar(
            y=d_merged['title'], x=-d_merged['pct'],
            name=f'{r}: {options_map[r]}', 
            orientation='h', 
            marker_color=colors_neg[i], 
            customdata=d_merged[['pct', 'hover_text']],
            hovertemplate="%{y}<br><br>%{customdata[1]}<br><br><b>回答割合:</b> %{customdata[0]:.1f}%<extra></extra>"
        ))

    colors_pos = ['#F5B7B1', '#EC7063', '#C0392B'] 
    for i, r in enumerate([4, 5, 6]):
        d = score_pct[score_pct['rating'] == r]
        d_merged = pd.DataFrame({'title': titles}).merge(d, on='title', how='left').fillna(0)
        d_merged['text'] = d_merged['title'].map(title_text_map).fillna('')
        d_merged['hover_text'] = d_merged['text'].apply(lambda x: format_hover_text(x, 40))

        fig_div.add_trace(go.Bar(
            y=d_merged['title'], x=d_merged['pct'],
            name=f'{r}: {options_map[r]}', 
            orientation='h', 
            marker_color=colors_pos[i], 
            customdata=d_merged[['pct', 'hover_text']],
            hovertemplate="%{y}<br><br>%{customdata[1]}<br><br><b>回答割合:</b> %{customdata[0]:.1f}%<extra></extra>"
        ))
    
    fig_div.update_layout(
        barmode='relative', 
        height=800,
        xaxis=dict(title="回答割合 (%)", tickvals=[-100, -50, 0, 50, 100], ticktext=['100%', '50%', '0', '50%', '100%']),
        yaxis=dict(title=""),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center", yanchor="bottom"),
        margin=dict(l=0, r=0, t=100, b=0)
    )
    fig_div.add_vline(x=0, line_width=1, line_color="black")
    st.plotly_chart(fig_div, use_container_width=True)

# Tab 2: 統計データテーブル
with tab_table:
    display_df = detail_stats.rename(columns={
        'scenario_id': 'ID', 'title': 'シナリオ名', 'category': 'カテゴリ', 'type': '法的定義',
        'text': 'シナリオ本文', 
        'avg': '平均', 'median': '中央値', 'mode': '最頻値', 'std': '認識の割れ具合(SD)', 'count': 'N'
    })
    
    # ★ここにカラム順序の指定を追加
    cols = ['ID', 'シナリオ名', 'シナリオ本文', 'カテゴリ', '法的定義', '平均', '中央値', '最頻値', '認識の割れ具合(SD)', 'N']
    display_df = display_df[cols]
    
    st.dataframe(
        display_df.style.background_gradient(cmap='Oranges', subset=['認識の割れ具合(SD)'])
                .background_gradient(cmap='RdBu_r', subset=['平均'], vmin=1, vmax=6)
                .format("{:.2f}", subset=['平均', '認識の割れ具合(SD)'])
                .format("{:.0f}", subset=['中央値', '最頻値', 'N']),
        use_container_width=True, height=600, hide_index=True,
        column_config={
            "シナリオ本文": st.column_config.TextColumn("シナリオ本文", width="large")
        }
    )

# ==========================================
# 4. ユーザーアンケートへの誘導
# ==========================================
st.divider()

st.markdown("""
<div style="text-align: center; margin-bottom: 20px;">
    <h4 style="margin-bottom: 10px;">📋 研究へのご協力のお願い</h4>
    <p style="color: #666;">
        本システムの利用を通じて、ハラスメントに対する認識に変化はありましたか？<br>
        今後の研究・システム改善のため、簡単なアンケートへのご協力をお願いいたします。<br>
        <span style="font-size: 0.9em;">(所要時間：約3分 / 匿名回答)</span>
    </p>
</div>
""", unsafe_allow_html=True)

col_q_l, col_q_c, col_q_r = st.columns([1, 2, 1])
with col_q_c:
    if st.button("📝 アンケートに回答する", type="primary", use_container_width=True):
        st.switch_page("pages/4_📋_ユーザーアンケート.py")