// Staff-looking names and throwaway mailboxes are refused at sign-up and rename (the owner's rule, 2026-11-04).
import test from 'node:test';
import assert from 'node:assert/strict';
import {reservedName, disposableEmail, nameKey} from './src/reserved-names.js';

test('names that pass for staff are reserved, however they are spelled', () => {
  for (const n of ['admin', 'Admin', 'ADMIN', 'admin1', 'admin_2026', 'real_admin', 'xAdmin', '4dm1n', 'a.d.m.i.n', 'Ａｄｍｉｎ',
    'administrator', 'SiteAdministrator', 'haslalab', 'HaslaLab_official', 'haslaedu', '관리자', '관리자입니다', '운영자', '하슬라랩 운영진',
    '운영팀', '공식계정', 'moderator', 'root', 'System', 'staff', 'support', 'official', 'owner', 'mod', 'hasla', '하슬라', '공식', '어드민', 'webmaster'])
    assert.equal(reservedName(n), true, n);
});
test('ordinary names, including ones with those letters inside a word, pass', () => {
  for (const n of ['badminton', 'Badminton_King', 'kim', '김철수', 'physics_lover', 'rooted', 'systemic', 'modern', 'staffing', 'supporter',
    'owner_kim', 'mail_owner', 'hasla_fan', '하슬라팬', '공식암기', '관리', 'user123', 'Lee n'].filter(n => !['owner_kim', '관리'].includes(n)))
    assert.equal(reservedName(n), false, n);
  assert.equal(reservedName('관리'), true, 'a whole word is reserved');
  assert.equal(reservedName('owner_kim'), false, 'a whole-name word is only reserved as the whole name');
  assert.equal(reservedName(''), false);
  assert.equal(nameKey('Ad_m1n 2026'), 'admino', 'digits that look like letters are read as letters; the rest are dropped');
});
test('throwaway mailboxes are refused, with their subdomains; ordinary providers and look-alikes pass', () => {
  for (const e of ['cegaroj972@drtall.com', 'x@mailinator.com', 'x@YOPMAIL.com', 'x@sub.guerrillamail.com', 'x@10minutemail.com', 'x@temp-mail.org', 'x@mail.tm', 'x@sharklasers.com'])
    assert.equal(disposableEmail(e), true, e);
  for (const e of ['kim@gmail.com', 'kim@naver.com', 'kim@kaist.ac.kr', 'kim@notmailinator.com', 'kim@mail.tm.example.org', 'not-an-address'])
    assert.equal(disposableEmail(e), false, e);
  assert.equal(disposableEmail('x@newthrowaway.io', {DISPOSABLE_EMAIL_DOMAINS: 'newthrowaway.io, other.example'}), true, 'the environment can add domains');
});
