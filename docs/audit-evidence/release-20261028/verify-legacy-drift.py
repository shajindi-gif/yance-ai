"""Explicit legacy-schema exception, not a passing Alembic check.

Compare both old baseline and migrated recovery. Only five known pre-existing
nullable differences are allowed; never assign tenants or rewrite row values.
"""
import json
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from app import models  # noqa: F401
from app.core.config import settings
from app.core.db import Base

url = make_url(settings.database_url)
assert settings.app_env == 'test' and url.host == '127.0.0.1'
assert url.database in {'yance_baseline_test','yance_release_test'}
expected = {('analytics_events','tenant_id'),('policy_rules','tenant_id'),
            ('deliverables','created_at'),('deliverables','updated_at'),('tasks','progress')}
with create_engine(settings.database_url).connect() as db:
    diffs = compare_metadata(MigrationContext.configure(db,opts={'compare_type': True}),Base.metadata)
    observed = set()
    for group in diffs:
        assert isinstance(group,list) and len(group)==1, 'Unexpected non-nullability schema drift'
        item = group[0]
        assert item[0]=='modify_nullable' and item[-2:] == (True,False), 'Unexpected schema operation'
        observed.add((item[2],item[3]))
    assert observed == expected, 'Drift changed from reviewed baseline'
    null_counts = {table+'.'+column:db.scalar(text(f'SELECT count(*) FROM "{table}" WHERE "{column}" IS NULL')) for table,column in sorted(expected)}
    assert all(null_counts[k] == 0 for k in ['deliverables.created_at','deliverables.updated_at','tasks.progress'])
    revision = db.scalar(text('SELECT version_num FROM alembic_version'))
print(json.dumps({'baseline_exception_verified':True,'standard_alembic_check_passed':False,'revision':revision,'nullable_differences':[list(v) for v in sorted(observed)],'null_counts':null_counts,'row_rewrites':False}))
