import requests
import json
import time
import random
from datetime import datetime, timedelta

# 生成 100 条模拟日志
print("📤 生成 100 条模拟日志...")
logs = []
base_time = datetime(2024, 7, 25, 10, 0, 0)
for i in range(100):
    # 随机生成不同级别的日志
    level = random.choices(["INFO", "WARNING", "ERROR", "CRITICAL"], weights=[60, 25, 12, 3])[0]
    response_time = random.randint(10, 800) if level == "INFO" else random.randint(500, 5000)
    bytes_out = random.randint(0, 2048)
    timestamp = (base_time + timedelta(seconds=i * 30)).isoformat() + "Z"
    
    logs.append({
        "raw_log": f"timestamp={timestamp} level={level} response_time={response_time} bytes_out={bytes_out}",
        "service": random.choice(["auth_service", "db_service", "api_gateway", "frontend"]),
        "source": "system",
        "format_type": "key_value"
    })

print(f"✅ 已生成 {len(logs)} 条日志")

# 1. 注入数据
print("📤 发送数据到系统...")
data = {"logs": logs}
resp1 = requests.post("http://localhost:8000/api/v1/stream/multi-source", json=data)
print(f"注入状态码: {resp1.status_code}")
if resp1.status_code != 200:
    print(f"注入失败: {resp1.text}")
    exit()

# 2. 触发训练（必须带请求体）
print("🧠 触发模型训练...")
train_data = {"logs": logs}  # 复用日志
resp2 = requests.post("http://localhost:8000/api/v1/train", json=train_data)
print(f"训练状态码: {resp2.status_code}")
print(f"训练响应: {resp2.text}")

# 3. 等待 10 秒，确保训练完成
print("⏳ 等待 10 秒...")
time.sleep(10)

# 4. 查看指标
print("📊 查看系统指标...")
resp3 = requests.get("http://localhost:8000/api/v1/metrics")
metrics = resp3.json()
print(json.dumps(metrics, indent=2))

# 5. 查看是否有异常
print("🔍 查看异常列表...")
resp4 = requests.get("http://localhost:8000/api/v1/anomalies")
try:
    anomalies = resp4.json()
    print(f"异常数量: {len(anomalies)}")
    if anomalies:
        print(json.dumps(anomalies[:5], indent=2))  # 只显示前 5 条
except:
    print("无法解析异常列表:", resp4.text)

if metrics.get("last_trained"):
    print("\n🎉 恭喜！模型训练成功！时间:", metrics["last_trained"])
else:
    print("\n❌ 训练仍未完成，请查看 Uvicorn 终端的日志。")