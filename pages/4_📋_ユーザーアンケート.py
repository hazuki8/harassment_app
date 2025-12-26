import streamlit as st
from utils.db import save_feedback, check_feedback_status

# ページ設定
st.set_page_config(page_title="ユーザーテスト", page_icon="🗣️", layout="centered")

st.title("🗣️ 利用後アンケート")
st.markdown("""
本システムの有効性を検証するための**研究用アンケート**（ユーザーテスト）です。  
診断結果を見た率直な感想をお聞かせください。
""")
st.divider()

# -------------------------------------------
# 1. ログイン & 回答済みチェック
# -------------------------------------------
if "user_id" not in st.session_state or not st.session_state.user_id:
    st.warning("⚠️ 先に「パワハラ認識傾向チェック」を実施してください。")
    if st.button("診断ページへ移動"):
        st.switch_page("pages/1_📝_パワハラ認識傾向チェック.py")
    st.stop()

# -------------------------------------------
# 2. 閲覧チェック（Page2 と Page3 が必須）
# -------------------------------------------
has_seen_p2 = st.session_state.get("visited_page2", False)
has_seen_p3 = st.session_state.get("visited_page3", False)

# どちらか一方でも見ていなければブロック
if not has_seen_p2 or not has_seen_p3:
    st.warning("⚠️ アンケートに回答するには、診断結果（あなたの認識傾向 / 世の中の認識傾向）の両方を確認する必要があります。")
    
    col1, col2 = st.columns(2)
    
    # Page 2 のチェック状況
    with col1:
        if not has_seen_p2:
            st.error("「👤 あなたの認識傾向」が未確認です")
            if st.button("ページ2へ移動", type="primary", key="go_p2"):
                st.switch_page("pages/2_👤_あなたの認識傾向.py")
        else:
            st.success("✅ 「👤 あなたの認識傾向」確認済み")
            
    # Page 3 のチェック状況
    with col2:
        if not has_seen_p3:
            st.error("「🌍 世の中の認識傾向」が未確認です")
            if st.button("ページ3へ移動", type="primary", key="go_p3"):
                st.switch_page("pages/3_🌍_世の中の認識傾向.py")
        else:
            st.success("✅ 「🌍 世の中の認識傾向」確認済み")
            
    st.stop() # ここで処理を止める

# -------------------------------------------
# 3. 回答済みチェック
# -------------------------------------------
if check_feedback_status(st.session_state.user_id):
    st.success("✅ アンケートへのご協力ありがとうございました！")
    st.info("あなたの回答は正常に記録されています。ブラウザを閉じて終了してください。")
    st.stop()

# -------------------------------------------
# 4. 選択肢の定義（分析しやすい数値入りラベル）
# -------------------------------------------
# 5段階評価（基本）
OPTS_5 = [
    "1. 全くそう思わない",
    "2. あまりそう思わない",
    "3. どちらとも言えない",
    "4. ややそう思う",
    "5. 強くそう思う"
]

# 変化の度合い
OPTS_CHANGE = [
    "1. 全く変化しない（迷うまま）",
    "2. あまり変化しない",
    "3. どちらとも言えない",
    "4. 少し解消されそうだ",
    "5. 大きく解消されそうだ（迷わなくなる）"
]

# 理解度
OPTS_UNDERSTAND = [
    "1. 全く理解できなかった",
    "2. あまり理解できなかった",
    "3. どちらとも言えない",
    "4. ある程度理解できた",
    "5. よく理解できた"
]

# 整理感
OPTS_CLARITY = [
    "1. 全く整理できなかった",
    "2. あまり整理できなかった",
    "3. どちらとも言えない",
    "4. ある程度整理がついた",
    "5. 非常にスッキリした"
]

# -------------------------------------------
# 5. アンケートフォーム
# -------------------------------------------
with st.form("feedback_form"):
    st.markdown("### 1. 気持ちの変化について")
    st.caption("このシステムを利用する「前」と「後」の気持ちを比較して教えてください。")
    
    st.markdown("**Q1. 利用する【前】の不安**")
    st.markdown("部下への指導や注意をする際、「パワハラになるかもしれない」と不安や迷いを感じていましたか？")
    q_anxiety_pre = st.radio(
        "Q1", OPTS_5, index=None, horizontal=True, label_visibility="collapsed"
    )
        
    st.write("")
    st.markdown("**Q2. 利用した【後】の変化**")
    st.markdown("自分の判断基準や傾向が可視化されたことで、その不安や迷いはどう変化しそうですか？")
    q_anxiety_post = st.radio(
        "Q2", OPTS_CHANGE, index=None, horizontal=True, label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("### 2. システムの評価")
    
    st.markdown("**Q3. 自己理解（内省）**")
    st.markdown("自分が「どのような場面で厳しく（または甘く）判断しやすいか」という傾向を理解できましたか？")
    q_self_awareness = st.radio(
        "Q3", OPTS_UNDERSTAND, index=None, horizontal=True, label_visibility="collapsed"
    )

    st.write("")
    st.markdown("**Q4. 納得感・整理感**")
    st.markdown("「白黒はっきりしないグレーな事例」や「世の中とのズレ」を見て、判断の整理がつきましたか？")
    q_clarity = st.radio(
        "Q4", OPTS_CLARITY, index=None, horizontal=True, label_visibility="collapsed"
    )
    
    st.write("")
    st.markdown("**Q5. 混乱（逆質問）**")
    st.markdown("逆に、情報が多すぎて「余計にどう判断していいか分からなくなった」ということはありましたか？")
    q_confusion = st.radio(
        "Q5", ["いいえ、混乱はしていない", "はい、余計に混乱した"], index=None, horizontal=True, label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("### 3. 効果の要因")
    
    st.markdown("**Q6. 役立った機能（複数選択可）**")
    st.markdown("あなたの「気づき」や「安心」に特に効果があったと思うものを全て選んでください。")
    helpful_features = st.multiselect(
        "Q6",
        options=[
            "法的基準との比較（赤・青の判定）",
            "世の中の感覚とのズレ（散布図・マップ）",
            "類型別の分析（6類型のグラフ）",
            "シナリオごとの解説・弁護士基準",
            "行動指針（Advice）",
            "自分と似た属性（年代・役職など）との比較"
        ],
        label_visibility="collapsed"
    )

    st.write("")
    st.markdown("**Q7. 自由記述（任意）**")
    free_comment = st.text_area("気づいた点、感想、改善要望などをご自由にお書きください。", height=100)
    
    # 送信ボタン
    submitted = st.form_submit_button("回答を送信する", type="primary", use_container_width=True)

    if submitted:
        # 必須項目のチェック
        required_fields = [q_anxiety_pre, q_anxiety_post, q_self_awareness, q_clarity, q_confusion]
        if not all(required_fields):
            st.error("⚠️ 未回答の項目があります。Q1〜Q5は必須回答です。")
        else:
            # 回答データの整形（文字列から数値を取り出す）
            v_pre = int(q_anxiety_pre.split(".")[0])
            v_post = int(q_anxiety_post.split(".")[0])
            v_self = int(q_self_awareness.split(".")[0])
            v_clarity = int(q_clarity.split(".")[0])
            # 混乱フラグ（はい=5, いいえ=1）
            v_conf = 5 if q_confusion == "はい、余計に混乱した" else 1
            
            # DB保存
            if save_feedback(
                st.session_state.user_id,
                v_pre, v_post, v_self, v_clarity, v_conf,
                helpful_features,
                free_comment
            ):
                st.balloons()
                st.success("送信完了しました。ご協力ありがとうございました！")
                # 完了状態を反映するためにリロード
                st.rerun()