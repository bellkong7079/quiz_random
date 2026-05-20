import sys
sys.stdout.reconfigure(encoding='utf-8')

test = 'hello </script> world <b>bold</b>'
_bslash = chr(92)
result = test.replace('<', _bslash + 'u003c')
print('original:', repr(test))
print('result:  ', repr(result))
print('< count in result:', result.count('<'))
print('u003c count:', result.count(chr(92) + 'u003c'))
