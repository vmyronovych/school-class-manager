#!/usr/bin/env python3
"""HTTPS end-to-end check on school-server using disposable accounts; no secrets printed."""
import http.cookiejar
import json
import os
import re
from pathlib import Path
import secrets
import shutil
import socket
import sqlite3
import ssl
import subprocess
import tempfile
import urllib.request
import urllib.error
import urllib.parse
from samba import ldb, gensec
from samba.auth import system_session
from samba.credentials import Credentials, MUST_USE_KERBEROS
from samba.param import LoadParm
from samba.samdb import SamDB

assert os.geteuid()==0 and socket.gethostname()=='school-server'
os.umask(0o077)
lp=LoadParm();lp.load_default()
db=SamDB(url='/var/lib/samba/private/sam.ldb',session_info=system_session(),lp=lp)
token=secrets.token_hex(4)
teacher='checkteacher'+token
student='checkpupil'+token
teacher_password='Aa1!'+secrets.token_urlsafe(22)
created=[]
context=ssl.create_default_context(cafile='/etc/scm-panel/lab-ca.crt')
base='https://192.168.1.176:8443'
def client():
 return urllib.request.build_opener(urllib.request.HTTPSHandler(context=context),urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def call(opener,path,data=None,csrf=True,binary=False):
 headers={}
 if data is not None:
  if csrf:
   status,result=call(opener,'/api/auth/csrf')
   assert status==200,'CSRF fetch failed'
   headers['X-CSRF-TOKEN']=result['token']
  headers['Content-Type']='application/json'
 req=urllib.request.Request(base+path,headers=headers,data=None if data is None else json.dumps(data).encode())
 try:
  response=opener.open(req,timeout=40)
 except urllib.error.HTTPError as e:
  response=e
 with response:
  payload=response.read()
  return response.status,(payload if binary else json.loads(payload)) if payload else None

def check_password(login,password):
 creds=Credentials();creds.guess(lp);creds.set_username(login);creds.set_password(password)
 creds.set_domain('SCHOOL');creds.set_realm('SCHOOL.TEST');creds.set_kerberos_state(MUST_USE_KERBEROS)
 creds.set_gensec_features(creds.get_gensec_features()|gensec.FEATURE_SEAL)
 try:
  connection=SamDB(url='ldap://school-server.school.test',credentials=creds,lp=lp)
  connection.search(base='',scope=ldb.SCOPE_BASE,attrs=['defaultNamingContext'])
  return True
 except ldb.LdbError:return False

def check_pupil_password(password):
 # A usability contract, checked on actual create/reset responses.
 assert len(password)==7, 'Pupil password does not match the domain minimum'
 assert re.fullmatch(r'[BCDFGHKMNPRSTVWZ][aeiou][bcdfghkmnprstvwz][aeiou][2-9]{3}',password), 'Pupil password is not easy to transcribe'

try:
 # Directory spelling differs from the lower-case login submitted by the API.
 db.newuser(teacher.upper(),teacher_password);created.append(teacher)
 db.add_remove_group_members('vchyteli',[teacher],add_members_operation=True)
 web=client()
 assert call(web,'/api/students')[0]==401,'Anonymous read allowed'
 assert call(web,'/api/auth/login',{'login':teacher,'password':teacher_password},False)[0]==400,'CSRF missing was accepted'
 status,session=call(web,'/api/auth/login',{'login':teacher,'password':teacher_password})
 assert status==200 and session['role']=='Teacher','Teacher login failed: '+str(status)+' '+str(session.get('code'))
 assert session['login']==teacher,'Session login was not canonicalized'
 assert call(web,'/api/me')[0]==200,'Mixed-case directory name broke the session'
 status,rows=call(web,'/api/students')
 assert status==200 and {'student1','student2'}<={r['login'] for r in rows},'Real pupil list missing'
 assert call(web,'/api/students/administrator/reset-password',{})[0]==403,'Administrator reset allowed'
 status,result=call(web,'/api/students',{'login':student,'givenName':'Перевірка','surname':'Панелі'})
 assert status==200,'Pupil creation failed: '+str(result.get('code'))
 created.append(student);old_password=result['password']
 check_pupil_password(old_password)
 assert check_password(student,old_password),'Created password does not authenticate'
 # Real teacher access to only the disposable pupil's home, with hostile paths.
 home=Path('/srv/school/home')/student
 owner=home.stat()
 nested=home/'Урок 1';nested.mkdir();os.chown(nested,owner.st_uid,owner.st_gid)
 work=nested/'Робота #1.txt';content='Учнівська робота\n'.encode();work.write_bytes(content);os.chown(work,owner.st_uid,owner.st_gid)
 endpoint='/api/students/'+student
 def file_url(action,path=''):
  return endpoint+'/'+action+'?'+urllib.parse.urlencode({'path':path})
 assert call(client(),file_url('files'))[0]==401,'Anonymous file list allowed'
 assert call(client(),file_url('download','Урок 1/Робота #1.txt'),binary=True)[0]==401,'Anonymous download allowed'
 status,entries=call(web,file_url('files'))
 assert status==200 and any(e['name']=='Урок 1' and e['directory'] for e in entries),'Teacher cannot list pupil home'
 status,entries=call(web,file_url('files','Урок 1'))
 assert status==200 and entries[0]['name']==work.name and entries[0]['size']==len(content),'Nested file metadata wrong'
 assert call(web,file_url('download','Урок 1/Робота #1.txt'),binary=True)==(200,content),'Teacher download differs from pupil file'
 assert call(web,'/api/students/administrator/files')[0]==403,'Administrator home exposed'
 for invalid in ['../student1','/etc/passwd','Урок 1/../../student1','Урок 1\\..\\student1']:
  assert call(web,file_url('files',invalid))[0]==400,'Traversal list accepted'
  assert call(web,file_url('download',invalid),binary=True)[0]==400,'Traversal download accepted'
 with tempfile.TemporaryDirectory(prefix='scm-file-canary-') as temporary:
  canary=Path(temporary)/'canary.txt';canary.write_text('Disposable outside-home canary')
  (home/'link.txt').symlink_to(canary)
  (home/'linked-folder').symlink_to(temporary,target_is_directory=True)
  os.link(canary,home/'hardlink.txt')
  os.mkfifo(home/'pipe')
  large=home/'large.bin'
  with large.open('wb') as stream:stream.truncate(20*1024*1024+1)
  os.chown(large,owner.st_uid,owner.st_gid)
  status,entries=call(web,file_url('files'))
  assert status==200 and not {'link.txt','linked-folder','hardlink.txt','pipe'} & {e['name'] for e in entries},'Unsafe entries exposed'
  for unsafe in ['link.txt','linked-folder/canary.txt','hardlink.txt','pipe']:
   assert call(web,file_url('download',unsafe),binary=True)[0]==403,'Unsafe file downloaded'
  assert call(web,file_url('files','linked-folder'))[0]==403,'Symlink folder opened'
  assert call(web,file_url('download','large.bin'),binary=True)[0]==413,'Oversized file accepted'
  assert call(web,file_url('download','missing.txt'),binary=True)[0]==404,'Missing file status wrong'
 assert call(web,'/api/students',{'login':student,'givenName':'Duplicate','surname':'Check'})[0]==409,'Duplicate not rejected'
 status,result=call(web,'/api/students/'+student+'/reset-password',{})
 assert status==200,'Reset failed'
 password=result['password']
 check_pupil_password(password)
 assert check_password(student,password),'New password failed'
 assert not check_password(student,old_password),'Old password still accepted'
 assert call(client(),'/api/auth/login',{'login':student,'password':password})[0]==403,'Pupil entered teacher panel'
 path=Path('/srv/school/home')/student
 assert path.is_dir() and path.stat().st_mode&0o777==0o700,'Private folder mode wrong'
 with tempfile.TemporaryDirectory(prefix='scm-panel-smoke-') as directory:
  folder=Path(directory);auth=folder/'auth';auth.write_text('username = '+student+'\npassword = '+password+'\ndomain = SCHOOL\n')
  source=folder/'source.txt';source.write_text('Panel pupil H: check\n')
  returned=folder/'returned.txt';remote='.smoke-'+token+'.txt'
  own=subprocess.run(['smbclient','//192.168.1.176/pupils','-A',str(auth),'-c',f'put {source} {remote}; get {remote} {returned}; del {remote}'],capture_output=True)
  assert own.returncode==0 and returned.read_bytes()==source.read_bytes(),'New pupil SMB roundtrip failed'
  ca=folder/'lab-ca.cer'
  fetched=subprocess.run(['smbclient','//192.168.1.176/netlogon','-A',str(auth),'-c',f'get school-lab-ca.cer {ca}'],capture_output=True)
  assert fetched.returncode==0 and ca.is_file(),'Domain CA download failed'
  peer=subprocess.run(['smbclient','//192.168.1.176/student1','-A',str(auth),'-c','ls'],capture_output=True)
  assert peer.returncode!=0 and b'NT_STATUS_ACCESS_DENIED' in peer.stdout+peer.stderr,'Peer share not denied'
 db.add_remove_group_members('vchyteli',[teacher],add_members_operation=False)
 assert call(web,'/api/students')[0]==403,'Revoked teacher session retained access'
 assert call(web,file_url('files'))[0]==403,'Revoked teacher can list files'
 assert call(web,file_url('download','Урок 1/Робота #1.txt'),binary=True)[0]==403,'Revoked teacher can download files'
 with sqlite3.connect('/var/lib/scm-directory/journal.sqlite3') as journal:
  events=journal.execute('SELECT action,result FROM events WHERE actor=?',(teacher,)).fetchall()
 assert ('create','Succeeded') in events and ('reset','Succeeded') in events,'Audit missing'
 print('PANEL_SMOKE_OK: HTTPS, CSRF, teacher login, pupils, create/reset, password rejection, pupil denial, H: SMB isolation, teacher files/download, traversal/symlink/hardlink/FIFO/size protections, live role revocation, audit.')
finally:
 # Delete only the disposable identities created by this invocation.
 for login in reversed(created):
  db.deleteuser(login)
  path=Path('/srv/school/home')/login
  if path.exists():shutil.rmtree(path)
 print('DISPOSABLE_PANEL_ACCOUNTS_REMOVED')
