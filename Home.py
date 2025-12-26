import streamlit as st

# ページ設定
st.set_page_config(
    page_title="ホーム",
    page_icon="🔎",
    layout="wide"
)

# タイトル
st.title("🔎 パワハラ認識傾向チェック")

st.markdown("職場の人間関係における「あなたの認識」を、法的・社会的基準と比較分析します。")
st.divider()

# セクション1
st.markdown("### 📋 本システムについて")
st.markdown("""
職場における人間関係トラブルやコミュニケーション・指導の萎縮を減らすための研究です。  
あなたの「ハラスメント認識」が、法的・社会的な基準とどの程度ズレているかを分析し、
認識の傾向を可視化することで、より安全で実効的なコミュニケーションの実現を目指しています。
""")
st.divider()

# セクション2
st.markdown("### データの使用方法")
st.markdown("**収集する情報**")
st.markdown("""
年代 / 性別 / 雇用形態 / 役職 / 勤続年数 / 業界 / 職種 / 診断時の30問の回答
""")

col1, col2 = st.columns(2)
with col1:
    st.markdown("**✅ 個人特定情報は収集しません**")
    st.caption("""
    氏名・メールアドレス・住所・電話番号などは一切取得しません
    """)
with col2:
    st.markdown("**✅ 匿名で安全に管理**")
    st.caption("""
    セッションIDで管理・個人特定が不可能です
    """)

st.markdown("**📊 統計処理と利用**")
st.markdown("""
- 集計時は統計的に処理 → 個人が特定される形での公開・利用なし
- 研究目的に限定 → 商用利用・第三者提供なし  
""")
st.write("")

# チェックボックスと説明
consented = st.checkbox(
    "研究目的での匿名データ利用に同意します",
    key="consent_given",
)

st.write("")
# 大きなボタンで誘導 (type="primary")
if st.button(
    "📝 診断をスタートする",
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

st.caption("⏱️ 所要時間：約 15分（診断5分、結果・アンケート10分） ／ 📝 登録不要・匿名で利用可能")

