"""Compact responsive workspace theme. Keep native sidebar controls visible."""
import streamlit as st

def inject_theme(mode='dark'):
    page,card,text,line,muted = ('#121214','#1C1C20','#F3F3F5','#2E2E34','#A2A2AC') if mode=='dark' else ('#F5F6FA','#FFFFFF','#17171C','#D5D7E0','#585866')
    st.markdown(f'''<style>
    :root {{color-scheme:{mode};--text-color:{text};--background-color:{page};--secondary-background-color:{card};}}
    .stApp,[data-testid="stHeader"] {{background:{page};color:{text};}}
    .stApp {{font-family:Manrope,'Segoe UI',sans-serif;}}
    .stApp p,.stApp label,.stApp h1,.stApp h2,.stApp h3,.stApp h4 {{color:{text};}}
    [data-testid="stSidebar"] {{background:{card};border-right:1px solid {line};}}
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] button,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {{font-size:1.3rem;}}
    [data-testid="stSidebar"] h1 {{font-size:1.8rem;}}
    [data-testid="stSidebarContent"] {{display:flex;flex-direction:column;}}
    [data-testid="stSidebarUserContent"] {{min-height:85vh;}}
    .st-key-logout {{margin-top:clamp(2rem,26vh,22rem);}}
    .st-key-dashboard-clock {{padding-top:1rem;}}
    [data-testid="stVerticalBlockBorderWrapper"], [data-testid="stMetric"] {{border:1px solid {line};border-radius:16px;background:{card};padding:16px;}}
    [data-testid="stMetric"] {{transition:transform .18s,border-color .18s;}}
    [data-testid="stMetric"]:hover {{transform:translateY(-2px);border-color:#F7CE2E;}}
    .stButton button,.stFormSubmitButton button {{border-radius:10px;transition:filter .18s,transform .18s;}}
    .stButton button:hover {{border-color:#F7CE2E;transform:translateY(-1px);}}
    .stButton button[kind="primary"],.stFormSubmitButton button[kind="primary"] {{background:#F7CE2E;color:#121214;}}
    [data-baseweb="input"],[data-baseweb="select"]>div,textarea {{background:{card}!important;color:{text}!important;border-color:{line}!important;border-radius:10px!important;}}
    [data-testid="stCaptionContainer"] p {{color:{muted};}}
    .block-container {{max-width:1500px;padding-top:2rem;}}
    [data-testid="stSidebarCollapsedControl"], [data-testid="stSidebarCollapseButton"] {{visibility:visible!important;}}
    @media(max-width:700px){{.block-container{{padding:1rem;}}}}
    @media(prefers-reduced-motion:reduce){{*{{transition:none!important;}}}}
    </style>''',unsafe_allow_html=True)
