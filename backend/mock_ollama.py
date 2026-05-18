from flask import Flask, jsonify, request
import time
import logging

# Disable Flask default logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)
@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json
    model = data.get('model')
    if model != 'gemma4:31b':
        return jsonify({"error": "Model not found"}), 404
    time.sleep(2)
    return jsonify({
        "model": "gemma4:31b",
        "response": "## 会议纪要\n\n**时间:** 2026-05-18\n\n### 核心决策\n1. 确定采用 Flask + 独立单页面的架构，以保证最高离线兼容性。\n2. 前端UI完美适配深色主题模式，交互体验顺滑。\n\n### Action Items\n- [ ] 开发人员继续完善项目架构\n- [ ] 收集用户真实音频进行最终验证",
        "done": True
    })
if __name__ == '__main__':
    app.run(port=11434)
