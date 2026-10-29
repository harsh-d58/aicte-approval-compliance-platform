# Update timeouts
for filepath in ['backend/app/accounts.py', 'backend/app/database.py', 'backend/app/transactions.py']:
    with open(filepath, 'r', encoding='utf-8') as f:
        c = f.read()
    c = c.replace('statement_timeout=3000', 'statement_timeout=30000')
    c = c.replace('statement_timeout=5000', 'statement_timeout=30000')
    c = c.replace('connect_timeout=8', 'connect_timeout=15')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(c)
    print(f"Updated timeouts in {filepath}")
