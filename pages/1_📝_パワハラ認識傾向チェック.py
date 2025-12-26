import streamlit as st
import random
import streamlit.components.v1 as components
from utils.db import register_user, get_all_scenarios, save_responses_bulk, get_user_responses
from utils.session import init_session

# --- ページ設定 ---
st.set_page_config(
    page_title="パワハラ認識傾向チェック", 
    page_icon="📝",
    layout="centered"
)

# =========================================================
# ▼▼▼ 修正箇所: 同意状態の確認ロジック ▼▼▼
# =========================================================

# 1. クエリパラメータからの復帰（ブラウザバックやリロード時用）
try:
    params = dict(st.query_params)
except Exception:
    params = st.experimental_get_query_params()

# クエリパラメータがあれば、永続化用フラグをTrueにする
if params.get("consent") in ("1", ["1"], "true", ["true"], "True", ["True"]):
    st.session_state["agreed_to_research"] = True

# 2. ガード処理
# ウィジェットのkey("consent_given")ではなく、永続化用フラグ("agreed_to_research")をチェックする
if not st.session_state.get("agreed_to_research", False):
    st.warning("診断を開始するには、研究参加への同意が必要です。ホーム画面で同意してください。", icon="⚠️")
    if st.button("ホームへ戻る", type="secondary"):
        st.switch_page("Home.py")
    st.stop()

# =========================================================

# --- 定数定義 ---
OPT_AGE = ["10代以下", "20代", "30代", "40代", "50代", "60代以上"]
OPT_GENDER = ["男性", "女性", "その他・回答しない"]
OPT_STATUS = ["就業中 (社会人・パート・自営業)", "学生 (インターン含む)", "その他 (求職中・主婦/主夫・退職済)"]
OPT_EMP = ["正社員 (公務員含む)", "契約・嘱託社員", "派遣社員", "パート・アルバイト", "業務委託・フリーランス・副業", "経営者・役員", "その他"]
OPT_POS = ["一般社員", "主任・係長クラス (現場リーダー)", "課長クラス (マネジメント層)", "部長クラス (上級管理職)", "経営層 (役員以上)", "その他 (役職なし)"]
OPT_IND = ["メーカー・製造", "建設・不動産・物流", "IT・通信・インターネット", "金融・商社・コンサル", "小売・飲食・サービス", "医療・福祉・介護", "マスコミ・広告・エンタメ", "公務員・教職員・団体", "その他"]
OPT_JOB = ["営業系", "事務・管理系", "企画・マーケティング系", "技術・研究系", "クリエイティブ系", "サービス・販売・現場系", "専門職系 (医師/教師等)", "その他"]
OPT_YEARS = ["3年未満 (新人・若手)", "3年〜10年 (中堅)", "10年以上 (ベテラン)"]

# --- カスタムCSS ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stRadio label { font-weight: 500; color: #333; }
    div[data-testid="stForm"] { border: 1px solid #ddd; padding: 20px; border-radius: 10px; background-color: white; }
    .unanswered-card {
        border: 3px solid #ff4444 !important;
        background-color: #fff8f8 !important;
        box-shadow: 0 0 10px rgba(255, 68, 68, 0.2) !important;
    }
    </style>
""", unsafe_allow_html=True)

# セッション初期化
session_id = init_session()

# --- ステート管理 ---
if "diagnosis_started" not in st.session_state: st.session_state.diagnosis_started = False
if "user_attributes_temp" not in st.session_state: st.session_state.user_attributes_temp = {}
if "show_completion_screen" not in st.session_state: st.session_state.show_completion_screen = False

# =========================================================
# CASE 0: 完了画面
# =========================================================
if st.session_state.show_completion_screen:
    st.title("診断完了")
    st.success("🎉 お疲れ様でした！診断が完了しました。")
    st.balloons()
    st.write("")
    st.markdown("あなたの回答データを分析し、**認識の傾向とズレ**を可視化しました。")
    st.write("")
    if st.button("📊 結果を見る", type="primary", use_container_width=True):
        st.switch_page("pages/2_👤_あなたの認識傾向.py")
    st.stop()

# =========================================================
# CASE 1: 過去に診断完了済みの場合
# =========================================================
if "user_id" in st.session_state and st.session_state.user_id:
    existing_responses = get_user_responses(st.session_state.user_id)
    if existing_responses and len(existing_responses) > 0:
        st.info("### 診断は完了しています", icon="✅")
        st.write("あなたの回答は正常に保存されました。")
        if st.button("診断結果を確認する", type="primary", use_container_width=True):
            st.switch_page("pages/2_👤_あなたの認識傾向.py")
        st.stop()

# =========================================================
# STEP 1: 属性入力
# =========================================================
if not st.session_state.diagnosis_started:
    st.title("📝 診断をはじめる")
    st.info("""
    **以下の情報は、統計分析と認識傾向の比較にのみ使用されます。**
    
    - 氏名・メールアドレスなどの個人を特定できる情報は一切収集しません
    - 入力データは匿名化され、セッションIDで管理されます
    - 集計結果は統計的に処理され、個人が特定されることはありません
    - データは研究目的でのみ使用され、第三者に提供されることはありません
    """, icon="🔒")
    
    st.write("")
    st.markdown("##### 現在の状況")
    
    if "selected_status" not in st.session_state: st.session_state.selected_status = OPT_STATUS[0]
    
    user_status = st.segmented_control("現在の状況ラベル（非表示）", OPT_STATUS, label_visibility="collapsed")
    if user_status is None: user_status = OPT_STATUS[0]
    is_worker = (user_status == OPT_STATUS[0]) 

    st.write("")
    
    with st.form("user_attribute_form"):
        st.markdown("##### 基本属性")
        c1, c2 = st.columns(2)
        age = c1.selectbox("📅 年代", OPT_AGE, index=None, placeholder="選択してください")
        gender = c2.selectbox("👤 性別", OPT_GENDER, index=None, placeholder="選択してください")

        if is_worker:
            st.markdown("---")
            st.markdown("##### お仕事の詳細")
            st.caption("※ あなたと近い立場の人との比較分析に使います")
            wc1, wc2 = st.columns(2)
            employment = wc1.selectbox("💼 雇用形態", OPT_EMP, index=None, placeholder="選択してください")
            industry = wc1.selectbox("🏢 業界", OPT_IND, index=None, placeholder="選択してください")
            position = wc1.selectbox("🏷️ 役職", OPT_POS, index=None, placeholder="選択してください")
            service_years = wc2.selectbox("⏳ 勤続年数", OPT_YEARS, index=None, placeholder="選択してください")
            job = wc2.selectbox("💻 職種", OPT_JOB, index=None, placeholder="選択してください")
        else:
            save_val = "学生" if "学生" in user_status else "その他"
            employment = industry = position = service_years = job = save_val

        st.markdown("---")
        if st.form_submit_button("次へ（診断開始）", type="primary", use_container_width=True):
            required = [age, gender]
            if is_worker: required.extend([employment, industry, position, service_years, job])

            if not all(required):
                st.error("全ての項目を選択してください。")
            else:
                st.session_state.user_attributes_temp = {
                    "age": age, "gender": gender, "employment": employment,
                    "service_years": service_years, "position": position, "industry": industry, "job": job
                }
                st.session_state.diagnosis_started = True
                st.rerun()

# =========================================================
# STEP 2: 診断パート
# =========================================================
else:
    st.markdown('<div id="diagnosis-top"></div>', unsafe_allow_html=True)
    components.html("""<script>setTimeout(()=>{const t=window.parent.document.getElementById('diagnosis-top');if(t)t.scrollIntoView({behavior:'auto',block:'start'});},100);</script>""", height=0)
    
    scenarios = get_all_scenarios()
    if not scenarios:
        st.error("シナリオが見つかりません。")
        st.stop()

    if "scenario_order" not in st.session_state or st.session_state.scenario_order is None:
        scenario_ids = [s['scenario_id'] for s in scenarios]
        random.shuffle(scenario_ids)
        st.session_state.scenario_order = scenario_ids

    scenario_dict = {s['scenario_id']: s for s in scenarios}
    shuffled_scenarios = [scenario_dict[sid] for sid in st.session_state.scenario_order]
    total_q = len(shuffled_scenarios)

    if "temp_responses" not in st.session_state: st.session_state.temp_responses = {}

    st.title("⚖️ パワハラ認識チェック")
    st.progress(len(st.session_state.temp_responses) / total_q, text="回答進捗")
    st.caption(f"全 {total_q} 問。あなたの直感に近いものを選んでください。")

    options = ["全く感じない", "あまり感じない", "どちらかと言えば感じない", "どちらかと言えば感じる", "かなり感じる", "強く感じる"]

    for idx, scenario in enumerate(shuffled_scenarios, 1):
        st.markdown(f'<div id="question-{idx}"></div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(f"**Question {idx} / {total_q}**")
            st.markdown(f"##### {scenario['text']}")
            
            saved_response = st.session_state.temp_responses.get(scenario['scenario_id'])
            default_index = options.index(saved_response) if saved_response in options else None
            
            response = st.radio(
                "この言動に「ハラスメント」を感じますか？",
                options,
                index=default_index,
                key=f"q_{scenario['scenario_id']}",
                label_visibility="collapsed"
            )
            
            if response:
                st.session_state.temp_responses[scenario['scenario_id']] = response
        
        st.write("")

    st.markdown("---")
    
    # 送信中フラグの初期化
    if "is_submitting" not in st.session_state:
        st.session_state.is_submitting = False
    
    if st.button("回答を送信して結果を見る", type="primary", use_container_width=True, disabled=st.session_state.is_submitting):
        # 二重送信防止：すでに送信中なら何もしない
        if st.session_state.is_submitting:
            st.stop()
        
        st.session_state.is_submitting = True  # フラグを立てる
        
        unanswered_ids = [sid for sid in st.session_state.scenario_order 
                          if sid not in st.session_state.temp_responses or st.session_state.temp_responses[sid] is None]
        
        if unanswered_ids:
            st.session_state.is_submitting = False  # エラー時は解除
            unanswered_indices = [st.session_state.scenario_order.index(sid) + 1 for sid in unanswered_ids]
            first_unanswered = unanswered_indices[0]
            st.error(f"未回答の質問があります（残り {len(unanswered_indices)}問）")
            components.html(f"""<script>setTimeout(()=>{{const t=window.parent.document.getElementById('question-{first_unanswered}');if(t)t.scrollIntoView({{behavior:'smooth',block:'center'}});}},200);</script>""", height=0)
        else:
            with st.spinner("結果を生成中..."):
                # 念のため再度チェック（リロードなどの対策）
                if "user_id" in st.session_state and st.session_state.user_id:
                    existing_responses = get_user_responses(st.session_state.user_id)
                    if existing_responses and len(existing_responses) > 0:
                        st.session_state.is_submitting = False
                        st.session_state.show_completion_screen = True
                        st.rerun()
                
                attrs = st.session_state.user_attributes_temp
                new_user_id = register_user(session_id, **attrs)
                
                if new_user_id:
                    responses_dict = {}
                    for scenario_id, response in st.session_state.temp_responses.items():
                        responses_dict[scenario_id] = options.index(response) + 1
                    
                    if save_responses_bulk(new_user_id, responses_dict):
                        st.session_state.user_id = new_user_id
                        st.session_state.temp_responses = {} 
                        st.session_state.user_attributes_temp = {}
                        st.session_state.diagnosis_started = False
                        st.session_state.is_submitting = False  # 完了時にリセット
                        st.session_state.show_completion_screen = True
                        st.rerun()
                    else:
                        st.session_state.is_submitting = False  # エラー時は解除
                        st.error("回答の保存に失敗しました。")
                else:
                    st.session_state.is_submitting = False  # エラー時は解除
                    st.error("データの保存に失敗しました。")