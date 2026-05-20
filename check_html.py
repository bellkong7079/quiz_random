import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'c:\Users\jb733\OneDrive\바탕 화면\quiz\quiz_random\sanup_quiz.html', 'rb') as f:
    b = f.read()

raw_tag = b'</script'
esc_lt = b'\\u003c'          # bytes: 5C 75 30 30 33 63
esc_tag = b'\\u003c/script'  # escaped version

print('file size (bytes):', len(b))
print('raw </script count:', b.count(raw_tag))
print(r'< count:', b.count(esc_lt))
print(r'</script count:', b.count(esc_tag))

# Show context around first </script
idx = b.find(raw_tag)
if idx >= 0:
    print('first </script context:', b[max(0,idx-30):idx+40])
