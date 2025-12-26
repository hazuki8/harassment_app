import streamlit as st
import uuid

def init_session():
    """
    セッションIDの発行と管理
    """
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    
    
    return st.session_state.session_id