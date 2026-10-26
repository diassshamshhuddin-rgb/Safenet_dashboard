import pytest
from dashboard import store

@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(store,'DB',tmp_path/'workspace.db')
    store.init()
    store.add_user('Administrator','admin','Password12345','IT',bootstrap=True)
    admin=store.login('admin','Password12345','admin')
    store.add_user('Employee','employee','Password12345','Monitoring',admin)
    analyst=store.login('employee','Password12345','analyst')
    return admin,analyst

def test_role_enforcement_and_revocation(workspace):
    admin,analyst=workspace
    with pytest.raises(PermissionError):store.decide(admin,'case','confirmed')
    with pytest.raises(PermissionError):store.add_user('Bad','bad','Password12345','IT',analyst)
    store.decide(analyst,'case','confirmed')
    assert store.reviews(analyst,True)[0]['status']=='confirmed'
    uid=store.current(analyst)['id']
    store.deactivate(admin,uid)
    assert store.current(analyst) is None
    with pytest.raises(PermissionError):store.decide(analyst,'case','false')

def test_login_lockout_and_audit(workspace):
    admin,analyst=workspace
    for _ in range(5):assert store.login('employee','wrong','analyst') is None
    assert store.login('employee','Password12345','analyst') is None
    store.logout(analyst)
    assert store.current(analyst) is None
    assert any(r['event']=='logout' for r in store.audit(admin))

def test_personal_history_isolation(workspace):
    admin,analyst=workspace
    store.decide(analyst,'case','more')
    assert store.reviews(admin,True)==[]
    assert len(store.reviews(analyst,True))==1
    store.messages(analyst,'Test support request')
    assert len(store.messages(admin))==1
