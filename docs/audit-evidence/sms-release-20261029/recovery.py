"""Operator-reviewed production snapshot and isolated restore. No row output.

Fixed source container; recovery has no network. Run as root on release host.
No deletion, restore over production, or external data transfer is supported.
"""
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


def run(args, **kwargs):
    return sp.run(args, check=True, **kwargs)


def query(container, database, sql):
    return run(['docker', 'exec', '-i', container, 'psql', '-X', '-qAt', '-v',
                'ON_ERROR_STOP=1', '-U', 'yance', '-d', database],
               input=sql, text=True, capture_output=True).stdout


def metadata(container, database):
    text = query(container, database, "SELECT table_name, string_agg(column_name, ',' ORDER BY ordinal_position) FROM information_schema.columns WHERE table_schema='public' GROUP BY table_name ORDER BY table_name;")
    result = {}
    for line in text.splitlines():
        name, columns = line.split('|')
        assert all(re.fullmatch(r'[a-z_][a-z_0-9]*', value) for value in [name, *columns.split(',')])
        result[name] = columns.split(',')
    return result


def fingerprints(container, database, schema, snapshot=None):
    sql = 'BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY; SET LOCAL timezone=\'UTC\';\n'
    if snapshot:
        assert re.fullmatch(r'[0-9A-Fa-f-]+', snapshot)
        sql += f"SET TRANSACTION SNAPSHOT '{snapshot}';\n"
    for table, columns in schema.items():
        fields = ','.join('"'+c+'"' for c in columns)
        sql += f"SELECT '{table}',count(*),md5(coalesce(string_agg(md5(row_to_json(t)::text),'' ORDER BY md5(row_to_json(t)::text)),'')) FROM (SELECT {fields} FROM public.\"{table}\") t;\n"
    sql += 'COMMIT;\n'
    return {p[0]: {'rows': int(p[1]), 'md5': p[2]} for line in query(container, database, sql).splitlines() if len(p := line.split('|')) == 3}


def verify(root, container, database):
    before = json.loads((root/'private-fingerprints.json').read_text())
    schema = {k: v for k, v in before['schema'].items() if k != 'alembic_version'}
    after = fingerprints(container, database, schema)
    changed = [k for k in schema if after[k] != before['hashes'][k]]
    revision = query(container, database, 'SELECT version_num FROM alembic_version;').strip()
    report = {'verified': not changed, 'existing_tables': len(schema), 'changed_tables': changed, 'revision': revision}
    print(json.dumps(report))
    if changed:
        raise SystemExit(1)


def backup(root):
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    source = 'yance-prod-db-1'
    recovery = 'yance-recovery-'+root.name
    database = 'yance_release_test'
    keeper = sp.Popen(['docker','exec','-i',source,'psql','-X','-qAt','-v','ON_ERROR_STOP=1','-U','yance','-d','yance_prod'], stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE, text=True)
    keeper.stdin.write('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY; SELECT pg_export_snapshot();\n')
    keeper.stdin.flush()
    snapshot = keeper.stdout.readline().strip()
    assert re.fullmatch(r'[0-9A-Fa-f-]+', snapshot)
    started = time.monotonic()
    dump = root/'database.dump'
    with dump.open('wb') as output:
        run(['docker','exec',source,'pg_dump','-U','yance','-Fc','--snapshot',snapshot,'yance_prod'], stdout=output)
    schema = metadata(source, 'yance_prod')
    hashes = fingerprints(source, 'yance_prod', schema, snapshot)
    (root/'private-fingerprints.json').write_text(json.dumps({'schema':schema,'hashes':hashes}))
    keeper.stdin.write('COMMIT;\n\\q\n'); keeper.stdin.flush(); keeper.wait(timeout=15)
    assert keeper.returncode == 0
    backup_seconds = time.monotonic()-started
    run(['docker','run','-d','--name',recovery,'--network','none','--memory','512m','--pids-limit','150','-e','POSTGRES_HOST_AUTH_METHOD=trust','-e','POSTGRES_USER=yance','-e','POSTGRES_DB='+database,'pgvector/pgvector:pg16'],stdout=sp.DEVNULL)
    # initdb briefly runs a Unix-socket-only temporary server. pg_isready can
    # report ready even before POSTGRES_DB exists. Require the final TCP server
    # and an actual SELECT in the requested database before restoring.
    for _ in range(90):
        if sp.run(['docker','exec',recovery,'psql','-X','-h','127.0.0.1','-U','yance','-d',database,'-Atqc','SELECT 1'],stdout=sp.DEVNULL,stderr=sp.DEVNULL).returncode == 0:
            break
        time.sleep(.5)
    else:
        raise RuntimeError('Recovery database failed to start')
    started = time.monotonic()
    with dump.open('rb') as source_file:
        restored_process = sp.run(['docker','exec','-i',recovery,'pg_restore','--exit-on-error','--single-transaction','--no-owner','--no-acl','-U','yance','-d',database],stdin=source_file,capture_output=True)
    if restored_process.returncode:
        # Diagnostic bodies may contain customer values: keep them root-only,
        # never include them in stdout, chat or repository evidence.
        (root/'restore-error.private').write_bytes(restored_process.stderr)
        raise RuntimeError('Isolated restore failed; root-only diagnostics saved')
    assert fingerprints(recovery,database,schema) == hashes, 'Restored fingerprints differ'
    restore_seconds = time.monotonic()-started
    plain_hash = hashlib.file_digest(dump.open('rb'),'sha256').hexdigest()
    passfile = root/'passphrase.tmp'; passfile.write_text(secrets.token_hex(48))
    cipher = root/'database.dump.enc'; wrapped = root/'encryption-key.oaep'
    run(['openssl','enc','-aes-256-cbc','-pbkdf2','-iter','250000','-salt','-in',str(dump),'-out',str(cipher),'-pass','file:'+str(passfile)])
    run(['openssl','pkeyutl','-encrypt','-pubin','-inkey','/tmp/yance-recovery-public.pem','-in',str(passfile),'-out',str(wrapped),'-pkeyopt','rsa_padding_mode:oaep','-pkeyopt','rsa_oaep_md:sha256'])
    process = sp.Popen(['openssl','enc','-d','-aes-256-cbc','-pbkdf2','-iter','250000','-in',str(cipher),'-pass','file:'+str(passfile)],stdout=sp.PIPE)
    assert hashlib.file_digest(process.stdout,'sha256').hexdigest() == plain_hash
    assert process.wait() == 0
    report = {'verified':True,'container':recovery,'database':database,'network':'none','table_count':len(hashes),'row_count':sum(v['rows'] for v in hashes.values()),'backup_seconds':round(backup_seconds,3),'restore_seconds':round(restore_seconds,3),'plain_sha256':plain_hash,'cipher_sha256':hashlib.file_digest(cipher.open('rb'),'sha256').hexdigest()}
    (root/'verification.json').write_text(json.dumps(report,indent=2))
    dump.unlink(); passfile.unlink()
    print(json.dumps(report))


if __name__ == '__main__':
    root = Path(sys.argv[2])
    assert str(root).startswith('/opt/yance/backups/sms-20261029-01/')
    if sys.argv[1] == 'backup':
        backup(root)
    elif sys.argv[1] == 'verify':
        verify(root, sys.argv[3], sys.argv[4])
    else:
        raise SystemExit('Unsupported action')
