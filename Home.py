import streamlit as st

# ページ設定
st.set_page_config(
    page_title="ホーム",
    page_icon="🔎",
    layout="wide"
)

# タイトル
st.title("🔎 パワハラ認識傾向チェック")
st.info("パワーハラスメントに対する「あなたの認識」を法的・社会的基準と比較分析します。")
st.caption("※ PCおよびスマートフォンで診断可能ですが、グラフの視認性の観点からPCでのご利用を推奨します。")

st.subheader("🎓 本研究の背景と目的")
st.markdown("""
    本システムは、「**ハラスメント判断の曖昧さ**」や「**認識のズレ**」に着目し、それらを可視化することで判断の迷いや心理的負担にどのような変化が生じるかを検証するための研究用プロトタイプです。\n
    個人の認識を「**法的規範（判例・ガイドライン）**」および「**世の中の認識（統計）**」と比較することで、自身の判断傾向を客観的に可視化します。
""")
st.divider()

st.subheader("📊 実験の流れ")
s1, s2, s3, s4 = st.columns(4)

with s1:
    st.info("""
    **📝 STEP 1 (約1分)**
    
    **属性情報の入力**
    
    分析精度を高めるため、年代・性別・役職などの統計情報を収集します。
    """)

with s2:
    st.info("""
    **📏 STEP 2 (約5分)**
    
    **ケーススタディ診断**
    
    実際の判例等に基づいた30のシナリオに対し、評価を行います。
    """)

with s3:
    st.info("""
    **📊 STEP 3 (約5分~)**
    
    **フィードバック**
    
    あなたの回答傾向を分析し、世の中の平均や法的基準とのズレを表示します。
    """)

with s4:
    st.info("""
    **📋 STEP 4 (約3分)**
    
    **ユーザーアンケート**
    
    本システムの使いやすさや、気づきに関する簡単なアンケートを行います。
    """)

st.write("")

st.divider()

# --- 4. データの取り扱い ---
st.subheader("🔒 データの取り扱いとプライバシー")

st.markdown("##### 収集する情報の範囲")
st.markdown("""
    本研究の分析および傾向把握のために、以下のデータを収集いたします。
    * **属性データ**: 年代、性別、雇用形態、役職、勤続年数、業界、職種
    * **回答データ**: 診断シナリオ（30問）への評価、利用後のアンケート回答
    """)
    
st.write("")

st.markdown("**✅ 匿名による厳重管理**")
st.caption("""
    データはセッションIDを用いた**匿名状態で管理**され、回答者個人を特定・追跡することは不可能です。
    """)
    
st.divider()

st.markdown("##### データの利用目的と制限")
st.markdown("""
* **統計的利用**: 収集データは統計的に処理され、学術研究の目的（論文発表、学会発表等）でのみ使用されます。個人が識別される形式で公表されることはありません。
* **第三者提供の禁止**: 法令に基づく場合を除き、データを第三者に提供したり、商用目的で利用したりすることはありません。
""")

# チェックボックスと説明
consented = st.checkbox(
    "研究の趣旨を理解し、データ利用に同意します",
    key="consent_given",
)

st.write("")
# 大きなボタンで誘導 (type="primary")
if st.button(
    "📝 実験を開始する",
    type="primary",
    use_container_width=True,
    disabled=not st.session_state.get("consent_given", False)
):
    if not st.session_state.get("consent_given", False):
        st.warning("診断を開始するには、上記の研究参加への同意が必要です。", icon="⚠️")
    else:
        # ★修正ポイント: ウィジェットのキーとは別の変数に「同意済み」フラグを保存する
        # これによりページ遷移しても変数が勝手に消されなくなります
        st.session_state["agreed_to_research"] = True
        
        # クエリパラメータも念のためセット（リロード対策）
        try:
            st.query_params["consent"] = "1"
        except Exception:
            st.experimental_set_query_params(consent="1")
        st.switch_page("pages/1_📝_パワハラ認識傾向チェック.py")

st.caption("⏱️ 所要時間：約 15分 ／ 📝 登録不要・匿名で利用可能")

