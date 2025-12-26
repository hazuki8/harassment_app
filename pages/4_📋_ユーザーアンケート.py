import streamlit as st
from utils.db import save_feedback, check_feedback_status

# ページ設定
st.set_page_config(page_title="ユーザーアンケート", page_icon="📋", layout="centered")

st.title("📋 ユーザーアンケート")
st.markdown("""
本システムの有効性を検証するための**研究用アンケート**（ユーザーテスト）です。  
いただいた回答は研究データとして統計的に処理されます。システムを使った率直なご感想をお聞かせください。
""")
st.divider()

# -------------------------------------------
# 1. ログイン & 閲覧チェック（制御ロジック）
# -------------------------------------------
# ログインチェック
if "user_id" not in st.session_state or not st.session_state.user_id:
    st.warning("⚠️ 先に「パワハラ認識傾向チェック」を実施してください。")
    if st.button("診断ページへ移動"):
        st.switch_page("pages/1_📝_パワハラ認識傾向チェック.py")
    st.stop()

# ページ閲覧チェック（結果を見ていない人をブロック）
has_seen_p2 = st.session_state.get("visited_page2", False)
has_seen_p3 = st.session_state.get("visited_page3", False)

if not has_seen_p2 or not has_seen_p3:
    st.warning("ℹ️ アンケートに回答するには、診断結果（あなたの認識傾向・世の中の認識傾向）の両方を確認していただく必要があります。")
    col1, col2 = st.columns(2)
    with col1:
        if not has_seen_p2:
            st.error("未確認: 👤 あなたの認識傾向")
            if st.button("ページへ移動", type="primary", key="go_p2"): st.switch_page("pages/2_👤_あなたの認識傾向.py")
        else:
            st.success("✅ 確認済: 👤 あなたの認識傾向")
    with col2:
        if not has_seen_p3:
            st.error("未確認: 🌍 世の中の認識傾向")
            if st.button("ページへ移動", type="primary", key="go_p3"): st.switch_page("pages/3_🌍_世の中の認識傾向.py")
        else:
            st.success("✅ 確認済: 🌍 世の中の認識傾向")
    st.stop()

# 回答済みチェック
if check_feedback_status(st.session_state.user_id):
    st.success("✅ アンケートへのご協力ありがとうございました！")
    st.info("回答は送信されました。ブラウザを閉じて終了してください。")
    st.stop()

# -------------------------------------------
# アンケートフォーム
# -------------------------------------------

# カスタムCSS（フォームの見た目を整える）
st.markdown("""
    <style>
    /* ラジオボタンのラベルのフォントウェイト */
    .stRadio label { font-weight: 500; }
    
    /* フォーム全体の枠線とパディング */
    div[data-testid="stForm"] { 
        border: 1px solid #e0e0e0; 
        padding: 24px; 
        border-radius: 12px;
    }
    
    /* 質問番号のスタイル統一 */
    .stMarkdown h4 {
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

with st.form("feedback_form"):
    
    # --- Q1 ---
    st.markdown("##### Q1-a. 他者の言動に対して意見を言う際、あるいは自分の言動を振り返る際、「どこまでなら許されるのか（ハラスメントにならないか）」の線引きに迷うことはありますか？")
    q1_a = st.radio(
        "Q1-a", 
        ["1. 全くない", "2. あまりない", "3. 時々ある", "4. よくある", "5. 常に感じる"], 
        index=None, label_visibility="collapsed"
    )

    st.divider()
    
    st.markdown("##### Q1-b. 本システムで「法的基準との比較（認識不足・過剰の判定）」等の明確な基準を確認したことで、線引きに対する迷いは整理されましたか？")
    q1_b = st.radio(
        "Q1-b", 
        ["1. 変化しない（迷うまま）", "2. あまり変化しない", "3. どちらとも言えない", "4. 少し整理/安心できた", "5. 非常に整理/安心できた"], 
        index=None, label_visibility="collapsed"
    )

    st.divider()

    st.markdown("##### Q1-c. 各シナリオの「解説」や「アドバイス」を読むことで、なぜその判断になるのかの理由や具体的な対策について、十分に納得・理解できましたか？")
    q1_c = st.radio(
        "Q1-c", 
        ["1. 全く理解できなかった", "2. あまり理解できなかった", "3. どちらとも言えない", "4. ある程度理解できた", "5. 非常に納得・理解できた"], 
        index=None, label_visibility="collapsed"
    )

    st.divider()

    # --- Q2 ---
    st.markdown("##### Q2-a. 「自分の常識や感覚は、今の世の中や他の世代とズレているのではないか？」と不安に感じることはありますか？")
    q2_a = st.radio(
        "Q2-a", 
        ["1. 全くない", "2. あまりない", "3. 時々ある", "4. よくある", "5. 常に感じる"], 
        index=None, label_visibility="collapsed"
    )
    
    st.divider()
    
    st.markdown("##### Q2-b. 本システムで「世の中の認識との比較（過敏・鈍感などの判定）」や「属性間ギャップ分析」により自身の立ち位置が可視化されたことで、ズレに対する漠然とした不安は軽減されましたか？")
    q2_b = st.radio(
        "Q2-b", 
        ["1. 変化しない（不安なまま）", "2. あまり変化しない", "3. どちらとも言えない", "4. 少し解消/安心できた", "5. 非常に解消/安心できた"], 
        index=None, label_visibility="collapsed"
    )

    st.divider()

    # --- Q3 ---
    st.markdown("##### Q3-a. 「ハラスメントだと言われるのが怖い」「関係が悪化するのが怖い」という理由で、必要な発言やコミュニケーションをためらうことはありますか？")
    q3_a = st.radio(
        "Q3-a", 
        ["1. 全くない", "2. あまりない", "3. 時々ある", "4. よくある", "5. 常に感じる"], 
        index=None, label_visibility="collapsed"
    )
    
    st.divider()
    
    st.markdown("##### Q3-b. 本システムで「パワハラ判断傾向マップ（2軸の散布図）」などにより「社会的な境界線（リスクやグレーゾーン）」が可視化されたことで、「自信を持って伝えても大丈夫だ」あるいは「ここは注意しよう」という「判断の自信」につながりそうですか？")
    q3_b = st.radio(
        "Q3-b", 
        ["1. つながらない", "2. あまりつながらない", "3. どちらとも言えない", "4. ややつながる", "5. 非常につながる"], 
        index=None, label_visibility="collapsed"
    )

    st.divider()

    # --- Q4, 5, 6 ---
    st.markdown("##### Q4. 本システムの「世間との認識ギャップ分布」や「平均との比較」を通して、ご自身の判断傾向（厳しさ・甘さの癖）に気づく助けになりましたか？")
    q4 = st.radio(
        "Q4", 
        ["1. 全くそう思わない", "2. あまりそう思わない", "3. どちらとも言えない", "4. ややそう思う", "5. 強くそう思う"], 
        index=None, label_visibility="collapsed"
    )

    st.divider()
    
    st.markdown("##### Q5. 本システムの「属性間ギャップ分析（年代・役職別などの比較）」などの可視化機能は、自分とは異なる感じ方をする人（相手）の視点を想像するきっかけになりましたか？")
    q5 = st.radio(
        "Q5", 
        ["1. 全くそう思わない", "2. あまりそう思わない", "3. どちらとも言えない", "4. ややそう思う", "5. 強くそう思う"], 
        index=None, label_visibility="collapsed"
    )

    st.divider()
    
    st.markdown("##### Q6. 本システムの診断結果を受けて、今後の「ご自身の言動」や、「他者とのコミュニケーションのあり方」を「見直そう・注意しよう」という意識は高まりましたか？")
    q6 = st.radio(
        "Q6", 
        ["1. 全くそう思わない", "2. あまりそう思わない", "3. どちらとも言えない", "4. ややそう思う", "5. 強くそう思う"], 
        index=None, label_visibility="collapsed"
    )

    st.divider()

    # --- Q7, 8, 9 ---
    st.markdown("##### Q7. 提示された診断結果（自分の傾向や、世の中とのズレ）は、ご自身の実感と照らし合わせて「納得できる・信頼できる」と感じましたか？")
    q7 = st.radio(
        "Q7", 
        ["1. 全く納得できない", "2. あまり納得できない", "3. どちらとも言えない", "4. おおむね納得できる", "5. 非常に納得できる"], 
        index=None, label_visibility="collapsed"
    )

    st.divider()
    
    st.markdown("##### Q8. 画面の操作や、グラフ・文字の見やすさはどうでしたか？")
    q8 = st.radio(
        "Q8", 
        ["1. 非常に使いにくい", "2. やや使いにくい", "3. どちらとも言えない", "4. 問題なく使えた", "5. 非常に使いやすい"], 
        index=None, label_visibility="collapsed"
    )

    st.divider()
    
    st.markdown("##### Q9. 自身の傾向（ズレやリスク）を指摘された際、不快感や「納得いかない」という反発を感じましたか？")
    q9 = st.radio(
        "Q9", 
        ["1. 強い不快感・反発を感じた", "2. 少し複雑な気持ちになった", "3. どちらとも言えない", "4. 特に気にならなかった", "5. 素直に受け入れられた"], 
        index=None, label_visibility="collapsed"
    )

    st.divider()
    
    st.markdown("##### Q10. ご自身の「判断の助け」や「気づき」に特につながったと感じる機能を教えてください（複数選択可）。")
    q10 = st.multiselect(
        "Q10",
        options=[
                "法的基準との比較（認識不足・過剰の判定）",
                "世の中の認識との比較（過敏・鈍感などの判定）",
                "パワハラ判断傾向マップ（社会的なグレーゾーンの把握）",
                "属性間ギャップ分析（属性ごとの認識差の比較）",
                "シナリオごとの解説・アドバイス（具体的な判断ポイントの学習）",
                "類型別分析（パワハラ6類型ごとの傾向把握）",
                "世間との認識ギャップ分布（世の中の分布における自分の位置）",
                "全シナリオ詳細データ（シナリオごとの他者回答割合の確認）"
                ],
        label_visibility="collapsed"
    )

    st.divider()
    
    st.markdown("##### Q11. 周囲でパワハラの判断に迷っている同僚や知人がいた場合、このシステムを利用するよう勧めたいと思いますか？")
    q11 = st.radio(
        "Q11", 
        ["1. 全くそう思わない", "2. あまりそう思わない", "3. どちらとも言えない", "4. ややそう思う", "5. 強くそう思う"], 
        index=None, label_visibility="collapsed"
    )

    st.divider()
    
    st.markdown("##### Q12. ご意見・ご感想（任意）")
    st.caption("使ってみた感想、改善点などがあればご自由にお書きください。")
    q12 = st.text_area("", height=100, label_visibility="collapsed")
    
    st.markdown("")
    submitted = st.form_submit_button("回答を送信する", type="primary", use_container_width=True)

    if submitted:
        # Q12以外は必須
        required = [q1_a, q1_b, q1_c, q2_a, q2_b, q3_a, q3_b, 
                    q4, q5, q6, 
                    q7, q8, q9, q11]
        
        if not all(required):
            st.error("⚠️ 未回答の項目があります。Q1〜Q11は必須回答です。")
        else:
            def to_int(val):
                return int(val.split(".")[0])

            # DB保存 (save_feedbackの実装に合わせて呼び出し)
            if save_feedback(
                st.session_state.user_id,
                to_int(q1_a), to_int(q1_b), to_int(q1_c),
                to_int(q2_a), to_int(q2_b), 
                to_int(q3_a), to_int(q3_b),
                to_int(q4), to_int(q5), to_int(q6), 
                to_int(q7), to_int(q8), to_int(q9),
                q10, to_int(q11), q12
            ):
                st.balloons()
                st.success("送信完了しました。ご協力ありがとうございました！")
                st.rerun()