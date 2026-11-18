"""Read-only snapshot contracts; no JWT minting or customer content output."""
import json
from sqlalchemy import select, text
from app.api.deps import Principal
from app.api.routes.workspace import home
from app.core.config import settings
from app.core.db import SessionLocal
from app.models.models import User, Membership, Application
assert settings.workspace_ask_enabled is False
with SessionLocal() as db:
    db.execute(text('SET TRANSACTION READ ONLY'))
    rows = db.execute(select(User, Membership).join(Membership, Membership.user_id == User.id)
                      .where(User.is_active.is_(True), Membership.status == 'active')).all()
    checked=set()
    for user, member in rows:
        if user.tenant_id in checked or member.tenant_id != user.tenant_id:
            continue
        result=home(None, Principal(user=user,tenant_id=user.tenant_id,role=member.role), db)
        assert result['tenant']['id']==str(user.tenant_id)
        assert result['ask_enabled'] is False
        for project in result['projects']:
            assert str(db.get(Application, project['id']).tenant_id)==str(user.tenant_id)
        checked.add(user.tenant_id)
        if len(checked)==2: break
    print(json.dumps({'snapshot_home_tenants_checked':len(checked),'read_only':True,'ask_enabled':False}))
