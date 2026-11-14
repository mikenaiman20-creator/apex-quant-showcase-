import time
import chromadb

time.sleep(5)
try:
    client = chromadb.HttpClient(host='chromadb', port=8000)
    col = client.get_or_create_collection('alpha_strategy_trials')
    if col.count() == 0:
        col.add(
            ids=['trial_001', 'trial_002'],
            documents=[
                'CPCV Mean Reversion SPY 15m | DSR: 1.84 | PBO: 0.12',
                'Momentum Breakout QQQ 1h | DSR: 2.11 | PBO: 0.08'
            ],
            metadatas=[
                {'asset': 'SPY', 'status': 'PASSED'},
                {'asset': 'QQQ', 'status': 'PASSED'}
            ]
        )
    print("ChromaDB alpha_strategy_trials collection initialized.")
except Exception as e:
    print(f"ChromaDB init error: {e}")

while True:
    time.sleep(3600)
