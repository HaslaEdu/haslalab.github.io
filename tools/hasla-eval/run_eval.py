"""Hasla AI reasoning-model selection: runs the three events against one model and writes what it produced.

  event 1 (make):  write an original olympiad problem, solution and marking scheme on a given topic (gen_topics.json)
  event 2 (grade): mark audited answer sheets from the site's server and write short feedback (grade_cases.json,
                   exported by the Worker's bench stage tune-grade-export); scored here against the audit's marks
  event 3 (solve): solve IPhO 2025 / APhO 2023 / IPhO 2026 theory tasks (tasks/<id>/problem.md); graded afterwards
                   against tasks/<id>/key.md

Every call is streamed and the model's thinking is held to a budget: when the think reaches the budget it is cut,
«</think>» is written for it and a second call writes only the answer from the thinking so far (budget forcing, as
community/src/qwq-reason.js does for QwQ). Time, tokens and the answer of every call are written to --out.

  python run_eval.py --name p1 --kind openai --base-url https://<pod>-8000.proxy.runpod.net/v1 --model PRIME-RL/P1-30B-A3B \
      --events 1,2,3 --budget 16000 --out results/p1.json
  python run_eval.py --name gemma4 --kind workers-ai --model @cf/google/gemma-4-26b-a4b-it --events 1,2,3 --out ...
"""
import argparse
import concurrent.futures as cf
import glob
import json
import os
import re
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
E = os.environ


def chat_stream(url, headers, body, budget=None, timeout=1800):
    """one streamed chat completion; returns (text, reasoning, finish, usage, pieces, cut). With `budget`, reading stops
    once the thinking (reasoning_content, or text before «</think>») passes that many pieces."""
    text, reasoning, finish, usage, pieces, cut = '', '', None, None, 0, False
    with requests.post(url, headers=headers, json={**body, 'stream': True, 'stream_options': {'include_usage': True}},
                       stream=True, timeout=timeout) as r:
        if r.status_code >= 400:
            raise RuntimeError(f'{r.status_code} {r.text[:300]}')
        for raw in r.iter_lines(decode_unicode=True):
            if not raw or not raw.startswith('data:'):
                continue
            data = raw[5:].strip()
            if data == '[DONE]':
                break
            try:
                j = json.loads(data)
            except ValueError:
                continue
            if j.get('usage'):
                usage = j['usage']
            ch = (j.get('choices') or [{}])[0]
            d = ch.get('delta') or {}
            if ch.get('finish_reason'):
                finish = ch['finish_reason']
            piece_r = d.get('reasoning_content') or d.get('reasoning') or ''
            piece_t = d.get('content') or (j.get('response') if isinstance(j.get('response'), str) else '') or ''
            if piece_r or piece_t:
                pieces += 1
            reasoning += piece_r
            text += piece_t
            # still thinking: the think has not closed («</think>» inline) and, for a model with a reasoning field, no
            # answer text has started yet
            thinking = '</think>' not in text and not (reasoning and text.strip())
            if budget and pieces >= budget and thinking:
                cut = True
                break
    return text, reasoning, finish, usage, pieces, cut


def split_think(text, reasoning, cut):
    """(thinking, answer) from a reply that carries its thinking in a field of its own or inline before «</think>»;
    a reply cut in its thinking has no answer yet, and a model that does not think answers in plain text"""
    if '</think>' in text:
        k = text.index('</think>')
        return (reasoning + text[:k]).replace('<think>', '').strip(), text[k + 8:].strip()
    if cut:
        return (reasoning + text).replace('<think>', '').strip(), ''
    return reasoning.strip(), text.strip()


class Model:
    def __init__(self, a):
        self.a = a
        if a.kind == 'workers-ai':
            tok = E.get('CLOUDFLARE_AI_TOKEN') or E.get('CLOUDFLARE_API_TOKEN')
            acct = E.get('CLOUDFLARE_ACCOUNT_ID') or requests.get('https://api.cloudflare.com/client/v4/accounts',
                headers={'Authorization': f'Bearer {tok}'}, timeout=60).json()['result'][0]['id']
            self.url = f'https://api.cloudflare.com/client/v4/accounts/{acct}/ai/v1/chat/completions'
            self.headers = {'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json'}
        else:
            self.url = a.base_url.rstrip('/') + '/chat/completions'
            key = E.get(a.api_key_env) if a.api_key_env else 'x'
            self.headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
        self.sampling = json.loads(a.sampling) if a.sampling else {'temperature': 0.6, 'top_p': 0.95}

    def ask(self, system, user, budget, answer_tokens):
        t0 = time.time()
        msgs = ([{'role': 'system', 'content': system}] if system else []) + [{'role': 'user', 'content': user}]
        body = {'model': self.a.model, 'messages': msgs, 'max_tokens': budget + answer_tokens, **self.sampling}
        if self.a.effort:
            body['reasoning_effort'] = self.a.effort
        if self.a.template_kwargs:
            body['chat_template_kwargs'] = json.loads(self.a.template_kwargs)
        text, reasoning, finish, usage, pieces, cut = chat_stream(self.url, self.headers, body, budget=None if self.a.no_think or self.a.kind == 'workers-ai' else budget)
        think, answer = split_think(text, reasoning, cut)
        forced, usage2 = False, None
        if (cut or not answer) and self.a.kind == 'openai':
            # budget forcing: the thinking so far, closed, and only the answer written from it
            forced = True
            cont = msgs + [{'role': 'assistant', 'content': '<think>\n' + think + '\n</think>\n\n'}]
            t2, r2, _, usage2, _, _ = chat_stream(self.url, self.headers, {'model': self.a.model, 'messages': cont,
                'max_tokens': answer_tokens, 'continue_final_message': True, 'add_generation_prompt': False, **self.sampling})
            answer = (r2 + t2).strip()
        u = lambda x, k: (x or {}).get(k) or 0
        return {'ms': int((time.time() - t0) * 1000), 'thinking_pieces': pieces, 'forced': forced, 'finish': finish,
                'in_tokens': u(usage, 'prompt_tokens') + u(usage2, 'prompt_tokens'),
                # a stream cut in its thinking ends before the usage line: its pieces are counted instead
                'out_tokens': max(u(usage, 'completion_tokens'), pieces) + u(usage2, 'completion_tokens'),
                'thinking_head': think[:1500], 'thinking_tail': think[-1500:], 'thinking_chars': len(think), 'answer': answer}


MAKE_SYSTEM = ('You are an expert author of physics and mathematics olympiad problems. Write original problems, '
               'not copies or near-copies of known ones, and make sure every problem is well posed and solvable.')
MAKE_USER = """Write one original {domain} olympiad problem on the topic below, at {level} level.

Topic: {topic}

Answer in English with these sections exactly:
## Problem
(the full statement, with parts numbered (a), (b), … and all data needed)
## Solution
(a complete solution for every part)
## Marking scheme
(10 points in total, split by part and step)
## Final answers
(one line per part)"""

SOLVE_SYSTEM = ('You are solving an international physics olympiad theory problem. Work carefully, check units and '
                'limiting cases, and state every final answer clearly.')
SOLVE_USER = """{problem}

Answer every part in order. For each part write a short derivation and then a line «Final answer (<part id>): …».
Parts marked [GRAPH/FIGURE-DEPENDENT] that need a drawing: describe the drawing in words."""

GRADE_TAIL = ('\n\nAfter thinking, write the marks one per line «<item id> <points awarded>» for every scheme item, '
              'then a line «FEEDBACK:» followed by 3 to 5 short sentences in Korean on the main errors and how to fix them.')


def marks_of(text):
    out = {}
    for line in text.split('\n'):
        m = re.match(r'^\s*(?:[-*•]\s*)?`?([A-Za-z0-9][\w.\/-]*)`?\s*[:=]?\s+(-?\d*\.?\d+)\s*(?:/\s*\d*\.?\d+)?\s*$', line)
        if m and re.search(r'[A-Za-z.]', m.group(1)):
            out.setdefault(m.group(1), float(m.group(2)))
    return out


def jobs(a):
    ev = set(a.events.split(','))
    if '1' in ev:
        for t in json.load(open(os.path.join(HERE, 'gen_topics.json'))):
            yield '1', t['id'], MAKE_SYSTEM, MAKE_USER.format(**t), {'topic': t}
    if '2' in ev and os.path.exists(os.path.join(HERE, 'grade_cases.json')):
        g = json.load(open(os.path.join(HERE, 'grade_cases.json')))
        for c in g['cases']:
            yield '2', f'{c["exam"]}-{c["task"]}-s{c["session"]}', g['system'], c['input'] + GRADE_TAIL, {'items': c['items']}
    if '3' in ev:
        for p in sorted(glob.glob(os.path.join(HERE, 'tasks', '*', 'problem.md'))):
            tid = os.path.basename(os.path.dirname(p))
            if a.tasks and tid not in a.tasks.split(','):
                continue
            yield '3', tid, SOLVE_SYSTEM, SOLVE_USER.format(problem=open(p, encoding='utf-8').read()), {}


def score2(answer, items):
    got = marks_of(answer)
    mis = over = under = missing = 0
    for it in items:
        if it['got'] is None:
            continue
        if it['id'] not in got:
            missing += 1
            continue
        d = got[it['id']] - it['got']
        if abs(d) > 0.005:
            mis += 1
            over += d > 0
            under += d < 0
    fb = answer.split('FEEDBACK:', 1)[1].strip() if 'FEEDBACK:' in answer else ''
    return {'items': len(items), 'mis': mis, 'over': over, 'under': under, 'missing': missing, 'feedback': fb[:2000]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', required=True)
    ap.add_argument('--kind', choices=['openai', 'workers-ai'], default='openai')
    ap.add_argument('--base-url')
    ap.add_argument('--api-key-env')
    ap.add_argument('--model', required=True)
    ap.add_argument('--events', default='1,2,3')
    ap.add_argument('--tasks', default='')
    ap.add_argument('--budget', type=int, default=16000)
    ap.add_argument('--answer-tokens', type=int, default=6000)
    ap.add_argument('--effort', default='')
    ap.add_argument('--no-think', action='store_true', help='a model without a thinking phase (Gemma): no budget cut')
    ap.add_argument('--template-kwargs', default='')
    ap.add_argument('--sampling', default='')
    ap.add_argument('--concurrency', type=int, default=8)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    m, rows, t0 = Model(a), [], time.time()

    def run(job):
        event, jid, system, user, extra = job
        try:
            r = m.ask(system, user, a.budget, a.answer_tokens)
        except Exception as e:  # one failed call costs only itself
            r = {'error': str(e)[:400]}
        r.update({'event': event, 'id': jid})
        if event == '2' and 'answer' in r:
            r['grading'] = score2(r['answer'], extra['items'])
        print(f'{a.name} e{event} {jid}: {r.get("ms")} ms, out {r.get("out_tokens")}, forced {r.get("forced")}, '
              f'{r.get("grading", {}).get("mis", "")} {r.get("error", "")[:120]}', flush=True)
        return r

    with cf.ThreadPoolExecutor(a.concurrency) as ex:
        rows = list(ex.map(run, list(jobs(a))))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump({'name': a.name, 'model': a.model, 'kind': a.kind, 'budget': a.budget, 'events': a.events,
               'wall_s': round(time.time() - t0), 'rows': rows}, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
