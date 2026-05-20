import json, sys, os
sys.stdout.reconfigure(encoding='utf-8')

base = os.path.dirname(os.path.abspath(__file__))
json_file = os.path.join(base, 'sanup_questions.json')

with open(json_file, encoding='utf-8') as f:
    qs = json.load(f)

qs_json = json.dumps(qs, ensure_ascii=False)
print('Before replace: < count =', qs_json.count('<'))
print('Sample with <:', [q for q in qs if '<' in q.get('q','')][0]['q'][:80] if any('<' in q.get('q','') for q in qs) else 'none')

_bslash = chr(92)
qs_json2 = qs_json.replace('<', _bslash + 'u003c')
print('After replace:  < count =', qs_json2.count('<'))
print('After replace: \\u003c count =', qs_json2.count(chr(92) + 'u003c'))
print('chr(92) =', repr(chr(92)))
print('replacement string =', repr(_bslash + 'u003c'))
