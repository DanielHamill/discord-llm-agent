import requests, time

def benchmark(model, prompt, runs=3):
    times = []
    for _ in range(runs):
        start = time.time()
        r = requests.post("http://localhost:11434/api/generate", json={
            "model": model,
            "prompt": prompt,
            "stream": False
        })
        elapsed = time.time() - start
        data = r.json()
        times.append({
            "time_s": round(elapsed, 2),
            "tokens": data.get("eval_count", 0),
            "tok_per_sec": round(data.get("eval_count", 0) / elapsed, 1)
        })
    return times

results = benchmark("llama3.2", "Explain recursion in one paragraph.")
for i, r in enumerate(results):
    print(f"Run {i+1}: {r['tok_per_sec']} tok/s | {r['time_s']}s | {r['tokens']} tokens")