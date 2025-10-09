import os
from openai import OpenAI
client = OpenAI(
    base_url='https://api.siliconflow.cn/v1',
    api_key=os.environ.get("API_KEY")
)
model="deepseek-ai/DeepSeek-R1"
def generate_no_stream_response(msg):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": msg}
        ],
        stream=False  # 设置为True以启用流式响应
    )
    print(response.choices[0].message.content)

def generate_stream_response(msg):
    # 发送带有流式输出的请求
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": msg}
        ],
        stream=True  # 启用流式输出
    )

    # 逐步接收并处理响应
    for chunk in response:
        if not chunk.choices:
            continue
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
        if chunk.choices[0].delta.reasoning_content:
            print(chunk.choices[0].delta.reasoning_content, end="", flush=True)
            
if __name__ == "__main__":
    print("=== Non-Streaming Response ===")
    generate_no_stream_response("你是谁？")
    print("\n\n=== Streaming Response ===")
    generate_stream_response("我是谁？")