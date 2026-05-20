import json, sys, os
sys.stdout.reconfigure(encoding='utf-8')

# Check exact line 30-31 behavior from make_quiz.py
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'make_quiz.py'), encoding='utf-8') as f:
    lines = f.readlines()
print("Lines 28-32 of make_quiz.py:")
for i, l in enumerate(lines[27:33], start=28):
    print(f"  {i}: {repr(l)}")

# Simulate the actual replacement
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sanup_questions.json'), encoding='utf-8') as f:
    qs = json.load(f)
qs_json = json.dumps(qs, ensure_ascii=False)
before = qs_json.count('<')
_bslash = chr(92)
qs_json = qs_json.replace('<', _bslash + 'u003c')
after_raw = qs_json.count('<')
after_esc = qs_json.count(chr(92) + 'u003c')
print(f"\nBefore replace: {before} < chars")
print(f"After replace: {after_raw} < chars, {after_esc} \\u003c sequences")
print(f"__file__ = {__file__}")
print(f"CWD = {os.getcwd()}")
