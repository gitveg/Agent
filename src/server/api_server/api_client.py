import aiohttp
import asyncio
from typing import Optional
import logging
from aiohttp import ClientError
from asyncio import TimeoutError
import os
import sys

# 获取当前脚本的绝对路径
current_script_path = os.path.abspath(__file__)
# 将项目根目录添加到sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_script_path))))
sys.path.append(root_dir)

from src.configs.configs import DEFAULT_API_BASE, DEFAULT_API_KEY

class AsyncHTTPClient:
    def __init__(self, retries: int = 3, timeout: int = 10):
        self.retries = retries
        self.timeout = timeout
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()
    
    async def request(
        self, 
        method: str, 
        url: str, 
        **kwargs
    ) -> Optional[dict]:
        for attempt in range(self.retries):
            try:
                async with self.session.request(
                    method, 
                    url, 
                    timeout=self.timeout,
                    **kwargs
                ) as response:
                    if response.status in (200, 201):
                        content_type = response.headers.get('Content-Type', '')
                        
                        if 'application/json' in content_type:
                            return await response.json()
                        elif 'text/plain' in content_type:
                            return await response.text()  # 返回文本
                        else:
                            # 尝试智能处理
                            text = await response.text()
                            try:
                                # 尝试解析为JSON
                                import json
                                return json.loads(text)
                            except json.JSONDecodeError:
                                # 如果不是JSON，返回原文本
                                return text
                    
                    # 服务器错误时重试
                    if response.status >= 500:
                        if attempt < self.retries - 1:
                            await asyncio.sleep(2 ** attempt)
                            continue
                            
                    response.raise_for_status()
                    
            except (ClientError, TimeoutError) as e:
                if attempt < self.retries - 1:
                    logging.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                    await asyncio.sleep(2 ** attempt)
                else:
                    logging.error(f"All attempts failed for {url}: {str(e)}")
                    raise
        
        return None
    
async def test_document():
    async with AsyncHTTPClient(retries=3, timeout=10) as client:
        try:
            data = await client.request(
                'GET',
                'http://127.0.0.1:8777/api/docs'
            )
            print(data)
        except Exception as e:
            logging.error(f"Request failed: {str(e)}")

async def test_health_check():
    async with AsyncHTTPClient(retries=3, timeout=10) as client:
        try:
            data = await client.request(
                'GET',
                'http://127.0.0.1:8777/api/health_check'
            )
            print(data)
        except Exception as e:
            logging.error(f"Request failed: {str(e)}")

async def test_new_knowledge_base():
    async with AsyncHTTPClient(retries=3, timeout=10) as client:
        try:
            data = await client.request(
                'POST',
                'http://127.0.0.1:8777/api/qa_handler/new_knowledge_base',
                json={'user_id': 'abc1234', 'user_info': '5678', 'kb_name': 'zzh', },
                headers={'Content-Type': 'application/json'}
            )
            print(data)
        except Exception as e:
            logging.error(f"Request failed: {str(e)}")

async def test_upload_files(file_path: str):
    async with AsyncHTTPClient(retries=1, timeout=10000) as client:
        try:
            # 准备文件和表单数据
            form_data = aiohttp.FormData()
            f = open(file_path, 'rb')
            # 添加文件
            form_data.add_field('files',
                                f,
                                filename=os.path.basename(file_path),
                                content_type='application/octet-stream')
            
            # 添加其他字段
            form_data.add_field('user_id', 'abc1234')
            form_data.add_field('user_info', '5678')
            form_data.add_field('kb_id', 'KBbf9488a498cf4407a6abdf477208c3ed')
            form_data.add_field('mode', 'soft')

            # 发送请求
            data = await client.request(
                'POST',
                'http://127.0.0.1:8777/api/qa_handler/upload_files',
                data=form_data
            )
            print(data)
        except Exception as e:
            logging.error(f"Request failed: {str(e)}")
        finally:
            # 确保关闭所有打开的文件
            f.close()

async def test_local_doc_chat():
    async with AsyncHTTPClient(retries=3, timeout=30) as client:
        try:
            # 模拟请求参数
            payload = {
                "user_id": "abc1234",
                "max_token": 3000,
                "user_info": "5678",
                "kb_ids": ["KBbf9488a498cf4407a6abdf477208c3ed"],  # 替换为实际的知识库ID
                "question": "zzh是谁?",
                "history": [],
                "streaming": False,  # 设置为False以获取完整回答
                "rerank": True,
                "custom_prompt": None,
                "api_base": DEFAULT_API_BASE,  # 替换为实际API地址
                "api_key": DEFAULT_API_KEY,  # 替换为实际API密钥
                "api_context_length": 10000,
                "top_p": 0.99,
                "temperature": 0.7,
                "top_k": 5
            }

            # 发送POST请求
            response = await client.request(
                method="POST",
                url="http://127.0.0.1:8777/api/local_doc_qa/local_doc_chat",
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            # 打印返回结果
            print("Response from local_doc_chat:")
            print(response)

        except Exception as e:
            logging.error(f"Request to local_doc_chat failed: {str(e)}")

async def test_list_kbs():
    async with AsyncHTTPClient(retries=3, timeout=10) as client:
        try:
            payload = {
                "user_id": "abc1234",
                "user_info": "5678"
            }
            data = await client.request(
                'POST', # 根据 sanic_api.py 中的路由方法
                'http://127.0.0.1:8777/api/qa_handler/list_knowledge_base',
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            print("List Knowledge Bases Response:")
            print(data)
        except Exception as e:
            logging.error(f"Request to list_kbs failed: {str(e)}")
            
async def test_upload_faqs_json():
    async with AsyncHTTPClient(retries=3, timeout=20) as client:
        try:
            # 方法一：通过JSON发送FAQ数据
            payload = {
                "user_id": "abc1234",
                "user_info": "5678",
                "kb_id": "KBbf9488a498cf4407a6abdf477208c3ed",
                "chunk_size": 800,
                "faqs": [
                    {
                        "question": "什么是人工智能?",
                        "answer": "人工智能是计算机科学的一个分支，致力于创造能够模拟人类智能的系统和程序。"
                    },
                    {
                        "question": "机器学习的基本原理是什么?",
                        "answer": "机器学习是通过算法使计算机从数据中学习并做出预测或决策，而无需明确编程。它通常依赖于统计模型和大量数据。"
                    }
                ]
            }
            
            data = await client.request(
                'POST',
                'http://127.0.0.1:8777/api/local_doc_qa/upload_faqs',
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            print("Upload FAQs Response (JSON):")
            print(data)
            
            # 创建FormData对象
            form = aiohttp.FormData()
            form.add_field('user_id', 'abc1234')
            form.add_field('user_info', '5678')
            form.add_field('kb_id', 'KBbf9488a498cf4407a6abdf477208c3ed')
            form.add_field('chunk_size', '800')
            # 预先读取文件内容
            with open('./faqs.xlsx', 'rb') as f:
                file_data = f.read()
            form.add_field('files', 
                            file_data,
                            filename='faqs.xlsx',
                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            
            # 使用aiohttp.ClientSession直接发送请求
            async with aiohttp.ClientSession() as session:
                async with session.post('http://127.0.0.1:8777/api/local_doc_qa/upload_faqs', 
                                       data=form) as response:
                    file_response = await response.json()
                    print("\nUpload FAQs Response (File):")
                    print(file_response)
            
        except Exception as e:
            logging.error(f"Request to upload_faqs failed: {str(e)}")
            
            
async def test_upload_faqs_file():
    async with AsyncHTTPClient(retries=3, timeout=20) as client:
        try:
            
            # 创建FormData对象
            form = aiohttp.FormData()
            form.add_field('user_id', 'abc1234')
            form.add_field('user_info', '5678')
            form.add_field('kb_id', 'KBbf9488a498cf4407a6abdf477208c3ed')
            form.add_field('chunk_size', '800')
            # 预先读取文件内容
            with open('./faqs.xlsx', 'rb') as f:
                file_data = f.read()
            form.add_field('files', 
                            file_data,
                            filename='faqs.xlsx',
                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            
            # 使用aiohttp.ClientSession直接发送请求
            async with aiohttp.ClientSession() as session:
                async with session.post('http://127.0.0.1:8777/api/local_doc_qa/upload_faqs', 
                                       data=form) as response:
                    file_response = await response.json()
                    print("\nUpload FAQs Response (File):")
                    print(file_response)
            
        except Exception as e:
            logging.error(f"Request to upload_faqs failed: {str(e)}")

def run_test():    
    # asyncio.run(test_document())
    # asyncio.run(test_health_check())
    # asyncio.run(test_new_knowledge_base())
    # asyncio.run(test_upload_files('./这是一个测试文件2.txt'))
    asyncio.run(test_local_doc_chat())
    # asyncio.run(test_list_kbs())
    # asyncio.run(test_upload_faqs_json())
    # asyncio.run(test_upload_faqs_file())

# asyncio.run(test_upload_files('./这是一个测试文件.txt'))

if __name__ == "__main__":
    run_test()