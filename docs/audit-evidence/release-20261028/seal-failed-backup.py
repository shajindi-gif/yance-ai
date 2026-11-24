"""Encrypt the failed attempt's retained dump after successful retry recovery.

Fixed root-only backup paths. No production DB writes or off-host data copy.
"""
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess as sp

os.umask(0o077)
root = Path('/opt/yance/backups/full-20261028-01/final')
retry = root.parent/'final-retry'
assert json.loads((retry/'verification.json').read_text())['verified']
dump = root/'database.dump'
assert dump.is_file() and not (root/'database.dump.enc').exists()
same_rows = json.loads((root/'private-fingerprints.json').read_text()) == json.loads((retry/'private-fingerprints.json').read_text())
plain_sha = hashlib.file_digest(dump.open('rb'),'sha256').hexdigest()
passfile = root/'passphrase.tmp'
passfile.write_text(secrets.token_hex(48))
cipher = root/'database.dump.enc'
sp.run(['openssl','enc','-aes-256-cbc','-pbkdf2','-iter','250000','-salt','-in',str(dump),'-out',str(cipher),'-pass','file:'+str(passfile)],check=True)
sp.run(['openssl','pkeyutl','-encrypt','-pubin','-inkey','/tmp/yance-recovery-public.pem','-in',str(passfile),'-out',str(root/'encryption-key.oaep'),'-pkeyopt','rsa_padding_mode:oaep','-pkeyopt','rsa_oaep_md:sha256'],check=True)
process=sp.Popen(['openssl','enc','-d','-aes-256-cbc','-pbkdf2','-iter','250000','-in',str(cipher),'-pass','file:'+str(passfile)],stdout=sp.PIPE)
assert hashlib.file_digest(process.stdout,'sha256').hexdigest()==plain_sha
assert process.wait()==0
report={'encrypted_roundtrip_verified':True,'original_restore_attempt_passed':False,'same_row_fingerprints_as_verified_retry':same_rows,'plain_sha256':plain_sha,'cipher_sha256':hashlib.file_digest(cipher.open('rb'),'sha256').hexdigest(),'private_plaintext_removed_after_cipher_verification':True}
(root/'sealing-verification.json').write_text(json.dumps(report,indent=2))
dump.unlink(); passfile.unlink()
print(json.dumps(report))
