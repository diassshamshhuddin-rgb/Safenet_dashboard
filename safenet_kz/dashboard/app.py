"""SafeNet KZ bilingual, role-aware Streamlit workspace."""
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import streamlit as st
from dashboard import store
from dashboard.theme import inject_theme
from dashboard.translations import translate
from src.core.config import AppConfig
from src.core.types import InputCase
from src.preprocessing.extractor import mask_personal_data
from src.graph.network import InvestigationGraph
from src.scoring.engine import ScoringEngine

st.set_page_config(page_title='SafeNet KZ',page_icon='',layout='wide',initial_sidebar_state='expanded')
store.init()
st.session_state.setdefault('lang','ru')
st.session_state.setdefault('theme','dark')
def t(key):return translate(key,st.session_state.lang)
def language(key):
    st.radio(t('language'),['ru','kk'],format_func=lambda v:'RU' if v=='ru' else 'KZ',horizontal=True,key=key,on_change=lambda:st.session_state.update(lang=st.session_state[key]))
def clear_session():
    token=st.session_state.get('token')
    if token:store.logout(token)
    lang=st.session_state.lang
    st.session_state.clear();st.session_state.lang=lang
    st.rerun()
inject_theme(st.session_state.theme)

if not store.has_admin():
    st.title('SafeNet KZ');language('setup_lang');st.subheader(t('bootstrap'))
    with st.form('bootstrap'):
        name=st.text_input(t('name'));login=st.text_input(t('login'));password=st.text_input(t('password'),type='password');department=st.text_input(t('department'))
        submitted=st.form_submit_button(t('setup'),type='primary')
    if submitted:
        try:store.add_user(name,login,password,department,bootstrap=True);st.rerun()
        except (ValueError,PermissionError):st.error(t('validation'))
    st.stop()
user=store.current(st.session_state.get('token',''))
if not user:
    st.session_state.pop('token',None)
    a,b,c=st.columns([1,1.5,1])
    with b:
        st.title(' SafeNet KZ');st.caption(t('workspace'));language('login_lang')
        role=st.radio(t('position'),['analyst','admin'],format_func=lambda x:t('admin_login' if x=='admin' else 'employee_login'),horizontal=True)
        with st.form('login_form'):
            login=st.text_input(t('login'));password=st.text_input(t('password'),type='password')
            submitted=st.form_submit_button(t('enter'),type='primary',use_container_width=True)
        if submitted:
            token=store.login(login,password,role)
            if token:st.session_state.token=token;st.session_state.page='home';st.rerun()
            else:st.error(t('invalid'))
    st.stop()
token=st.session_state.token
admin=user['role']=='admin'
work='staff' if admin else 'registry'
with st.sidebar:
    st.title(' SafeNet KZ');st.caption(t('workspace'))
    st.caption(f"{user['name']} · {t(user['role'])}")
    st.divider()
    page=st.radio(t('workspace'),['home','profile',work,'settings','support'],format_func=t,key='page',label_visibility='collapsed')
    st.button(t('logout'),key='logout',on_click=clear_session,use_container_width=True)

@st.fragment(run_every='1s')
def clock():
    now=datetime.now(ZoneInfo('Asia/Almaty'))
    months={'ru':['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'],'kk':['қаңтар','ақпан','наурыз','сәуір','мамыр','маусым','шілде','тамыз','қыркүйек','қазан','қараша','желтоқсан']}
    with st.container(key='dashboard-clock'):
        st.caption(f"{now.day} {months[st.session_state.lang][now.month-1]} {now.year} · {now:%H:%M:%S} · {t('time')}")
clock();st.title(t(page))

@st.cache_data(show_spinner=False)
def load_cases():
    graph=InvestigationGraph();engine=ScoringEngine(config=AppConfig.load(ROOT/'config/settings.yaml'),graph=graph)
    cases=[]
    # Добавьте encoding='utf-8' внутрь read_text()
    for line in (ROOT/'data/synthetic/test.jsonl').read_text(encoding='utf-8').splitlines():
        if line.strip():
            raw=json.loads(line);case=InputCase(**raw);result=engine.analyze_case(case);cases.append((case,result))
    return sorted(cases,key=lambda x:x[1].score,reverse=True)

def status_map():
    latest={}
    for r in store.reviews(token):latest.setdefault(r['case_id'],r['status'])
    return latest

def history(personal=True):
    records=store.reviews(token,personal)
    if not records:st.info(t('empty'));return
    st.dataframe([{t('case'):r['case_id'],t('status'):t(r['status']),t('time'):r['time']} for r in records],hide_index=True,use_container_width=True)

def quality():
    path=ROOT/'artifacts/metrics.json'
    if path.exists():
        st.subheader(t('quality'));data=json.loads(path.read_text())['test_results_full_pipeline']['overall']
        for col,k in zip(st.columns(4),['precision','recall','f1','fpr']):col.metric(t(k),f"{data[k]*100:.1f}%")

if page=='home':
    st.subheader(f"{t('welcome')}, {user['name']}")
    cases=load_cases();statuses=status_map()
    values=[(t('cases'),len(cases)),(t('pending'),sum(c.id not in statuses for c,_ in cases)),(t('history'),len(store.reviews(token,True)))]
    if admin:values[-1]=(t('active'),sum(u['active'] for u in store.users() if u['role']=='analyst'))
    for col,(label,value) in zip(st.columns(3),values):col.metric(label,value)
    st.caption(t('demo'))
    st.button(t('open'),on_click=lambda:st.session_state.update(page=work),type='primary')
    if admin:quality()
    else:
        st.subheader(t('pending'))
        st.dataframe([{t('case'):c.id,t('track'):t(r.primary_track.value),t('risk'):round(r.score,1)} for c,r in cases if c.id not in statuses][:8],hide_index=True,use_container_width=True)
elif page=='profile':
    with st.container(border=True):
        for label,value in [('name',user['name']),('login',user['login']),('position',t(user['role'])),('department',user['department'])]:st.write(f"**{t(label)}:** {value}")
    records=store.reviews(token,True)
    for col,k in zip(st.columns(3),['confirmed','false','more']):col.metric(t(k),sum(r['status']==k for r in records))
    st.subheader(t('history'));history()
elif page=='registry' and not admin:
    cases=load_cases();statuses=status_map()
    cols=st.columns(3)
    tracks=cols[0].multiselect(t('track'),['lottery','casino','pyramid','benign'],format_func=t)
    levels=cols[1].multiselect(t('risk'),['high','medium','low'],format_func=t)
    statuses_filter=cols[2].multiselect(t('status'),['pending','confirmed','false','more'],format_func=t)
    query=st.text_input(t('search')).casefold()
    risk={'Высокий':'high','Средний':'medium','Низкий':'low'}
    filtered=[(c,r) for c,r in cases if (not tracks or r.primary_track.value in tracks) and (not levels or risk[r.level.value] in levels) and (not statuses_filter or statuses.get(c.id,'pending') in statuses_filter) and (not query or query in (c.id+' '+r.masked_text).casefold())]
    if not filtered:st.info(t('empty'));st.stop()
    left,right=st.columns([1,1.5])
    with left:
        selected=st.selectbox(t('case'),[c.id for c,r in filtered])
        st.dataframe([{t('case'):c.id,t('track'):t(r.primary_track.value),t('risk'):round(r.score),t('status'):t(statuses.get(c.id,'pending'))} for c,r in filtered],hide_index=True,use_container_width=True)
    c,r=next((c,r) for c,r in filtered if c.id==selected)
    with right:
        with st.container(border=True):
            st.subheader(c.id);st.metric(t('risk'),f'{r.score:.1f} / 100',t(risk[r.level.value]),delta_color='off')
            st.caption(t(r.primary_track.value));st.text_area(t('text'),r.masked_text,disabled=True,height=150)
            st.caption(t(statuses.get(c.id,'pending')))
            for col,k in zip(st.columns(3),['confirmed','false','more']):
                if col.button(t(k),key=k,type='primary' if k=='confirmed' else 'secondary'):
                    store.decide(token,c.id,k);st.rerun()
    evidence,ocr,links=st.tabs([t('evidence'),t('ocr'),t('links')])
    with evidence:
        if r.triggered_features:st.dataframe([{t('feature'):f'{t("feature")} {i+1} · {t(f.track.value)}',t('weight'):f.weight,t('fragment'):mask_personal_data(f.snippet)} for i,f in enumerate(r.triggered_features)],hide_index=True,use_container_width=True)
        else:st.info(t('empty'))
    with ocr:
        if not c.image_paths:st.info(t('no_ocr'))
        for image in c.image_paths:
            path=(ROOT/image).resolve()
            if not path.is_relative_to(ROOT):continue
            if path.exists():st.image(str(path),use_container_width=True)
            else:st.info(t('missing_image'))
            sidecar=Path(str(path)+'.txt')
            if sidecar.exists():
                # Sidecar source is masked before rendering, just like case content.
                from src.preprocessing.extractor import mask_personal_data
                st.text(mask_personal_data(sidecar.read_text()))
    with links:
        if r.graph_links:
            # Escape all source-derived graph labels before Graphviz rendering.
            edges=[]
            for link in r.graph_links:
                source=json.dumps(link.source_entity,ensure_ascii=False);target=json.dumps(link.target_entity,ensure_ascii=False)
                edges.append(f'{source} -> {target} [label={json.dumps(t(link.relation_type) if link.relation_type in ("shared_card","shared_phone","shared_domain","shared_promo","shared_promocode","repost_chain") else t("links"),ensure_ascii=False)}];')
            st.graphviz_chart('digraph { bgcolor="transparent"; node [style=filled fillcolor="#F7CE2E"]; '+''.join(edges)+' }')
        else:st.info(t('empty'))
    st.caption(t('decision_notice'))
elif page=='staff' and admin:
    import sqlite3
    staff=[u for u in store.users() if u['role']=='analyst']
    st.dataframe([{t('name'):u['name'],t('login'):u['login'],t('department'):u['department'],t('status'):t('active' if u['active'] else 'inactive')} for u in staff],hide_index=True,use_container_width=True)
    with st.expander(t('create')):
        with st.form('add_employee',clear_on_submit=True):
            name=st.text_input(t('name'));login=st.text_input(t('login'));password=st.text_input(t('password'),type='password');department=st.text_input(t('department'))
            submit=st.form_submit_button(t('create'),type='primary')
        if submit:
            try:store.add_user(name,login,password,department,token);st.rerun()
            except (ValueError,sqlite3.IntegrityError):st.error(t('validation'))
    active=[u for u in staff if u['active']]
    if active:
        with st.expander(t('delete')):
            uid=st.selectbox(t('name'),[u['id'] for u in active],format_func=lambda i:next(u['name']+' · '+u['login'] for u in active if u['id']==i))
            confirm=st.checkbox(t('confirm_delete'))
            if st.button(t('delete'),disabled=not confirm):store.deactivate(token,uid);st.rerun()
    quality();st.subheader(t('activity'))
    st.dataframe([{t('time'):r['time'],t('login'):r['login'] or '—',t('event'):t(r['event']+'_event'),t('detail'):r['detail']} for r in store.audit(token)],hide_index=True,use_container_width=True)
elif page=='settings':
    language('settings_lang')
    st.radio(t('theme'),['dark','light'],format_func=t,key='theme',on_change=lambda:None,horizontal=True)
    st.button(t('reset'),on_click=clear_session)
elif page=='support':
    st.caption(t('support_note'))
    for m in store.messages(token):
        with st.chat_message('user'):
            st.caption(f"{m['login']} · {m['time']}");st.write(m['body'])
        with st.chat_message('assistant'):st.write(t('receipt'))
    body=st.chat_input(t('message'),max_chars=4000)
    if body:store.messages(token,body);st.rerun()
