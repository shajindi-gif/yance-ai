"""Release recovery verification. Prints hashes and aggregates, never row data."""
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess as sp
import sys
import time

os.umask(0o077)
root = Path(sys.argv[1]); root.mkdir(mode=0o700, parents=True, exist_ok=False)
source = 'yance-prod-db-1'
recovery = 'yance-recovery-' + root.name
recovery_db = 'yance_recovery_verify'

def run(args, **kwargs):
    return sp.run(args, check=True, **kwargs)

def psql(container, database, query):
    return run(['docker','exec','-i',container,'psql','-X','-qAt','-v','ON_ERROR_STOP=1','-U','yance','-d',database], input=query, text=True, capture_output=True).stdout

def hashes(container, database, snapshot=None, compatible=False):
    prefix = 'BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;\n'
    if snapshot:
        if not re.fullmatch(r'[0-9A-Fa-f-]+', snapshot): raise RuntimeError('invalid snapshot token')
        prefix += "SET TRANSACTION SNAPSHOT '"+snapshot+"';\n"
    # Hash each canonical row inside PostgreSQL, then sort fixed-size row hashes.
    # Only hashes and counts cross the container boundary.
    payload = 'to_jsonb(t)'
    if compatible:
        payload = "(to_jsonb(t) - CASE %L WHEN 'users' THEN ARRAY['auth_version'] WHEN 'policies' THEN ARRAY['expires_at'] WHEN 'policy_versions' THEN ARRAY['application_deadline'] ELSE ARRAY[]::text[] END)"
    if compatible:
        payload = payload.replace("'", "''")
        fmt = "SELECT format('SELECT %L, count(*), md5(coalesce(string_agg(md5("+payload+"::text), '''' ORDER BY md5("+payload+"::text)), '''')) FROM %I.%I t', tablename, tablename, tablename, schemaname, tablename)"
    else:
        fmt = "SELECT format('SELECT %L, count(*), md5(coalesce(string_agg(md5(to_jsonb(t)::text), '''' ORDER BY md5(to_jsonb(t)::text)), '''')) FROM %I.%I t', tablename, schemaname, tablename)"
    query = prefix+"SET LOCAL timezone='UTC';\n"+fmt+" FROM pg_tables WHERE schemaname='public' ORDER BY tablename\n\\gexec\nCOMMIT;\n"
    output = psql(container, database, query)
    return {parts[0]: {'rows':int(parts[1]),'md5':parts[2]} for line in output.splitlines() if len(parts:=line.split('|'))==3}

keeper = sp.Popen(['docker','exec','-i',source,'psql','-X','-qAt','-v','ON_ERROR_STOP=1','-U','yance','-d','yance_prod'], stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE, text=True)
keeper.stdin.write('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY; SELECT pg_export_snapshot();\n'); keeper.stdin.flush()
snapshot = keeper.stdout.readline().strip()
if not re.fullmatch(r'[0-9A-Fa-f-]+', snapshot): raise RuntimeError('could not export consistent snapshot')
started=time.monotonic()
dump=root/'database.dump'
with dump.open('wb') as target:
    run(['docker','exec',source,'pg_dump','-U','yance','-Fc','--snapshot',snapshot,'yance_prod'],stdout=target)
exact=hashes(source,'yance_prod',snapshot)
compatible=hashes(source,'yance_prod',snapshot,True)
keeper.stdin.write('COMMIT;\n\\q\n'); keeper.stdin.flush(); keeper.wait(timeout=15)
if keeper.returncode: raise RuntimeError('snapshot transaction failed')
backup_seconds=time.monotonic()-started
run(['docker','run','-d','--name',recovery,'--network','none','--memory','512m','--pids-limit','150','-e','POSTGRES_HOST_AUTH_METHOD=trust','-e','POSTGRES_USER=yance','-e','POSTGRES_DB='+recovery_db,'pgvector/pgvector:pg16'],stdout=sp.DEVNULL)
for attempt in range(60):
    if sp.run(['docker','exec',recovery,'pg_isready','-U','yance','-d',recovery_db],stdout=sp.DEVNULL,stderr=sp.DEVNULL).returncode==0: break
    time.sleep(.5)
else: raise RuntimeError('isolated recovery PostgreSQL not ready')
started=time.monotonic()
with dump.open('rb') as source_file:
    run(['docker','exec','-i',recovery,'pg_restore','--exit-on-error','--no-owner','--no-acl','-U','yance','-d',recovery_db],stdin=source_file,capture_output=True)
restored=hashes(recovery,recovery_db)
restore_seconds=time.monotonic()-started
if exact != restored: raise RuntimeError('restored table fingerprints do not match source snapshot')
plain_hash=hashlib.file_digest(dump.open('rb'),'sha256').hexdigest()
passfile=root/'encryption-pass.tmp'; passfile.write_text(secrets.token_hex(48))
cipher=root/'database.dump.enc'; wrapped=root/'encryption-key.oaep'
run(['openssl','enc','-aes-256-cbc','-pbkdf2','-iter','250000','-salt','-in',str(dump),'-out',str(cipher),'-pass','file:'+str(passfile)])
run(['openssl','pkeyutl','-encrypt','-pubin','-inkey','/tmp/yance-recovery-public.pem','-in',str(passfile),'-out',str(wrapped),'-pkeyopt','rsa_padding_mode:oaep','-pkeyopt','rsa_oaep_md:sha256'])
verify=sp.Popen(['openssl','enc','-d','-aes-256-cbc','-pbkdf2','-iter','250000','-in',str(cipher),'-pass','file:'+str(passfile)],stdout=sp.PIPE)
roundtrip=hashlib.file_digest(verify.stdout,'sha256').hexdigest()
if verify.wait()!=0 or roundtrip!=plain_hash: raise RuntimeError('encrypted backup round-trip failed')
report={'verified':True,'consistent_snapshot':True,'recovery_container':recovery,'recovery_database':recovery_db,'network':'none','table_count':len(exact),'row_count':sum(x['rows'] for x in exact.values()),'backup_seconds':round(backup_seconds,3),'restore_seconds':round(restore_seconds,3),'plain_sha256':plain_hash,'cipher_sha256':hashlib.file_digest(cipher.open('rb'),'sha256').hexdigest(),'wrapped_key_sha256':hashlib.file_digest(wrapped.open('rb'),'sha256').hexdigest(),'compatibility_hashes':compatible}
(root/'verification.json').write_text(json.dumps(report,indent=2))
dump.unlink(); passfile.unlink()
print(json.dumps({k:v for k,v in report.items() if k!='compatibility_hashes'},indent=2))
