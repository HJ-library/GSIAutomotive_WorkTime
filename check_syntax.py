import sys
import re

with open('web/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

# Remove strings first to avoid matching // inside strings
text = re.sub(r'".*?"', '""', text)
text = re.sub(r"'.*?'", "''", text)
text = re.sub(r'`.*?`', '``', text, flags=re.DOTALL)

# Remove comments
text = re.sub(r'//.*', '', text)
text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)

print('Left { :', text.count('{'))
print('Right } :', text.count('}'))
print('Left ( :', text.count('('))
print('Right ) :', text.count(')'))

stack = []
for i, char in enumerate(text):
    if char in '{[(':
        stack.append((char, i))
    elif char in '}])':
        if not stack:
            print(f'Unmatched {char} at index {i}')
            sys.exit(1)
        top, idx = stack.pop()
        if (char == '}' and top != '{') or (char == ']' and top != '[') or (char == ')' and top != '('):
            print(f'Mismatched {top} and {char} at index {i}')
            print('Context:')
            print(text[max(0, i-50):i+50])
            stack.append((top, idx)) # Put the original back to try to resync

print('Remaining in stack:', len(stack))
print('Remaining in stack:', len(stack))
if stack:
    for char, idx in stack:
        print(f"Unclosed {char} at index {idx}")
        print(text[max(0, idx-30):idx+30])
