import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client, Client

# キャッシュ設定
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Supabase接続エラー: {e}")
        return None

supabase: Client = init_connection()

# -------------------------------------------------------
# ユーザー登録
# -------------------------------------------------------
def register_user(session_id, age, gender, employment, service_years, position, industry, job):
    data = {
        "session_id": session_id,
        "age": age,
        "gender": gender,
        "employment_status": employment,
        "service_years": service_years,
        "position": position,
        "industry": industry,
        "job_type": job
    }
    try:
        response = supabase.table("users").insert(data).execute()
        if response.data:
            return response.data[0]["user_id"]
        return None
    except Exception as e:
        st.error(f"ユーザー登録エラー: {e}")
        return None

# -------------------------------------------------------
# シナリオ取得
# -------------------------------------------------------
@st.cache_data(ttl=3600)
def get_all_scenarios():
    try:
        response = supabase.table("scenarios").select("*").order("scenario_id").execute()
        return response.data
    except Exception as e:
        st.error(f"シナリオ取得エラー: {e}")
        return []

# -------------------------------------------------------
# 回答保存 (高速化: Bulk Insert)
# -------------------------------------------------------
def save_responses_bulk(user_id, responses_dict):
    """
    ループではなく一括で保存して高速化
    """
    if not responses_dict: return True
    data_list = [{"user_id": user_id, "scenario_id": sid, "rating": rating} for sid, rating in responses_dict.items()]
    try:
        supabase.table("responses").upsert(data_list).execute()
        return True
    except Exception as e:
        st.error(f"保存エラー: {e}")
        return False

# 後方互換性のため残すが、基本はbulkを使う
def save_response(user_id, scenario_id, rating):
    return save_responses_bulk(user_id, {scenario_id: rating})

# -------------------------------------------------------
# データ取得 (高速化: Join & View)
# -------------------------------------------------------

def get_user_responses(user_id):
    """
    ユーザー回答とシナリオを一括取得 (Join)
    """
    try:
        # responses テーブルから rating を取得
        response = supabase.table("responses").select(
            "rating, scenario_id"
        ).eq("user_id", user_id).execute()
        
        if not response.data:
            return []
        
        responses_data = response.data
        
        # scenarios テーブルから全シナリオを取得してキャッシュ
        scenarios_response = supabase.table("scenarios").select("*").execute()
        scenarios_dict = {s["scenario_id"]: s for s in scenarios_response.data}
        
        # マージ処理
        flattened_data = []
        for item in responses_data:
            scenario_id = item.get("scenario_id")
            scenario = scenarios_dict.get(scenario_id)
            
            if not scenario:
                continue
            
            # フラットな辞書に統合
            merged = {
                "rating": item.get("rating"),
                "scenario_id": scenario_id,
                "title": scenario.get("title", ""),
                "text": scenario.get("text", ""),
                "category": scenario.get("category", ""),
                "type": scenario.get("type", ""), 
                "explanation": scenario.get("explanation", ""),
                "advice": scenario.get("advice", ""),
                "legal_ref": scenario.get("legal_ref", ""),
            }
            flattened_data.append(merged)
        
        return flattened_data
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        return []

def get_global_averages_stats():
    """
    統計テーブル(scenario_stats)から集計済みデータを取得
    Page 2 で重い計算をさせないために使用
    
    Returns:
        pd.DataFrame: scenario_id, avg_rating, std_dev を含むDataFrame
    """
    try:
        response = supabase.table("scenario_stats").select(
            "scenario_id, avg_rating, std_dev, count"
        ).execute()
        
        if not response.data:
            return pd.DataFrame()
        
        df = pd.DataFrame(response.data)
        
        # データ型の確認と修正
        df['scenario_id'] = df['scenario_id'].astype(int)
        df['avg_rating'] = pd.to_numeric(df['avg_rating'], errors='coerce')
        df['std_dev'] = pd.to_numeric(df['std_dev'], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"統計データ取得エラー: {e}")
        return pd.DataFrame()

def get_global_analysis_data_view():
    """
    SQLビューから分析用データを一括取得
    Page 3 で使用
    
    Returns:
        list: users, responses, scenarios が結合されたレコード一覧
    """
    try:
        response = supabase.table("view_analysis_data").select("*").execute()
        
        if not response.data:
            return []
        
        # データはそのまま返す（employment_status は view で定義されている列名）
        return response.data
    except Exception as e:
        st.error(f"分析データ取得エラー: {e}")
        return []

# Page 2の既存ロジック互換用
def get_global_averages():
    # 互換性のためダミー構造を返すか、必要なデータだけ返す
    # 今回はPage 2側で get_global_averages_stats を使うように書き換えるため
    # この関数は最低限の全体平均だけ返すようにする
    try:
        stats = supabase.table("scenario_stats").select("avg_rating, count").execute()
        df = pd.DataFrame(stats.data)
        if df.empty: return None
        return {
            "overall": df["avg_rating"].mean(),
            "total_count": df["count"].sum()
        }
    except:
        return None

# -------------------------------------------------------
# デモデータ生成（研究・実験用）
# -------------------------------------------------------
def generate_demo_data():
    """
    実際のシナリオメタデータ（title/text/category/type など）を使用しつつ、
    回答のみをシミュレーション生成するデモデータ（25人×シナリオ数）。
    """
    scenarios = get_all_scenarios() or []
    if not scenarios:
        # シナリオが取得できない場合は空データを返す
        st.info("シナリオデータが未登録のため、デモ生成をスキップします。")
        return pd.DataFrame()

    ages = ["20代", "30代", "40代", "50代"]
    genders = ["男性", "女性"]
    positions = ["一般社員", "主任・係長クラス (現場リーダー)", "課長クラス (マネジメント層)", "部長クラス (上級管理職)"]
    industries = ["メーカー・製造", "IT・通信・インターネット", "金融・商社・コンサル", "小売・飲食・サービス", "医療・福祉・介護"]
    employments = ["正社員 (公務員含む)", "契約・嘱託社員", "派遣社員"]
    job_types = ["営業系", "事務・管理系", "技術・研究系", "サービス・販売・現場系"]
    service_years_list = ["3年未満 (新人・若手)", "3年〜10年 (中堅)", "10年以上 (ベテラン)"]

    demo_records = []
    num_users = 25

    for user_idx in range(1, num_users + 1):
        user_attrs = {
            "user_id": user_idx,
            "age": np.random.choice(ages),
            "gender": np.random.choice(genders),
            "position": np.random.choice(positions),
            "industry": np.random.choice(industries),
            "employment_status": np.random.choice(employments),
            "job_type": np.random.choice(job_types),
            "service_years": np.random.choice(service_years_list)
        }

        for scenario in scenarios:
            s_type = scenario.get("type", "Gray")
            if s_type == "Black":
                rating = int(np.clip(np.random.normal(5.0, 0.8), 1, 6))
            elif s_type == "White":
                rating = int(np.clip(np.random.normal(2.5, 0.8), 1, 6))
            else:
                rating = int(np.clip(np.random.normal(3.5, 1.5), 1, 6))

            record = {
                "response_id": len(demo_records) + 1,
                "rating": rating,
                **user_attrs,
                # 実シナリオのフィールドをそのまま埋め込む
                "scenario_id": scenario.get("scenario_id"),
                "category": scenario.get("category"),
                "type": s_type,
                "title": scenario.get("title"),
                "text": scenario.get("text"),
            }
            demo_records.append(record)

    return pd.DataFrame(demo_records)

# ==========================================
# ユーザーテスト（フィードバック）関連
# utils/db.py の末尾に追加
# ==========================================

def save_feedback(user_id, q_anxiety_pre, q_anxiety_post, q_self_awareness, q_clarity, q_confusion, helpful_features, free_comment):
    """
    ユーザーテストの回答を保存する
    """
    # リストで渡される機能一覧を文字列に変換（例: "法的基準,散布図"）
    features_str = ",".join(helpful_features) if helpful_features else ""
    
    data = {
        "user_id": user_id,
        "q_anxiety_pre": q_anxiety_pre,
        "q_anxiety_post": q_anxiety_post,
        "q_self_awareness": q_self_awareness,
        "q_clarity": q_clarity,
        "q_confusion": q_confusion,
        "helpful_features": features_str,
        "free_comment": free_comment
    }
    try:
        supabase.table("user_feedback").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"フィードバック保存エラー: {e}")
        return False

def check_feedback_status(user_id):
    """
    ユーザーがすでにフィードバック回答済みか確認
    """
    try:
        response = supabase.table("user_feedback").select("feedback_id").eq("user_id", user_id).execute()
        return len(response.data) > 0
    except:
        return False
