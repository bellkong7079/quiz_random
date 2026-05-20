import json, sys, os
sys.stdout.reconfigure(encoding='utf-8')

base = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(base, 'sanup_questions.json'), encoding='utf-8') as f:
    qs = json.load(f)

qs_json = json.dumps(qs, ensure_ascii=False)
_bslash = chr(92)
qs_json = qs_json.replace('<', _bslash + 'u003c')

# Build the same html string as make_quiz.py
title = 'test'
html = '<!DOCTYPE html><script>\nconst AQ = ' + qs_json + ';\n</script>'

b = html.encode('utf-8')
raw_tag = b'</script'
esc_lt = b'\\u003c'  # 5C 75 30 30 33 63
print('html contains </script:', html.count('</script'))
print('html contains backslash+u003c:', html.count(chr(92) + 'u003c'))
print('bytes </script:', b.count(raw_tag))
print('bytes backslash+u003c:', b.count(esc_lt))

# Write to temp file and read back
tmp = os.path.join(base, 'tmp_test.html')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(html)
with open(tmp, 'rb') as f:
    b2 = f.read()
print('file bytes </script:', b2.count(raw_tag))
print('file bytes backslash+u003c:', b2.count(esc_lt))
os.remove(tmp)
