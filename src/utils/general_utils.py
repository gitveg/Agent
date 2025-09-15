from io import BytesIO
import time
from functools import wraps
from turtle import pd

import tiktoken  # 添加这行导入
from src.utils.log_handler import debug_logger, embed_logger, rerank_logger
from src.configs.configs import DEFAULT_MODEL_PATH, KB_SUFFIX, EMBED_MODEL_PATH, RERANK_MODEL_PATH
from sanic.request import Request
from sanic.exceptions import BadRequest
import logging
import traceback
import re
import mimetypes
import os
import chardet
import inspect
from transformers import AutoTokenizer


# 异步执行环境下的耗时统计装饰器
def get_time_async(func):
    @wraps(func)
    async def get_time_async_inner(*args, **kwargs):
        s_time = time.perf_counter()
        res = await func(*args, **kwargs)  # 注意这里使用 await 来调用异步函数
        e_time = time.perf_counter()
        if 'embed' in func.__name__:
            embed_logger.info('函数 {} 执行耗时: {:.2f} 秒'.format(func.__name__, e_time - s_time))
        elif 'rerank' in func.__name__:
            rerank_logger.info('函数 {} 执行耗时: {:.2f} 秒'.format(func.__name__, e_time - s_time))
        else:
            debug_logger.info('函数 {} 执行耗时: {:.2f} 毫秒'.format(func.__name__, (e_time - s_time) * 1000))
        return res

    return get_time_async_inner

# 同步执行环境下的耗时统计装饰器
def get_time(func):
    def get_time_inner(*arg, **kwargs):
        s_time = time.time()
        res = func(*arg, **kwargs)
        e_time = time.time()
        if 'embed' in func.__name__:
            embed_logger.info('函数 {} 执行耗时: {:.2f} 秒'.format(func.__name__, e_time - s_time))
        elif 'rerank' in func.__name__:
            rerank_logger.info('函数 {} 执行耗时: {:.2f} 秒'.format(func.__name__, e_time - s_time))
        else:
            debug_logger.info('函数 {} 执行耗时: {:.2f} 毫秒'.format(func.__name__, (e_time - s_time) * 1000))
        return res

    return get_time_inner

def safe_get(req: Request, attr: str, default=None):
    """
    安全地从请求中获取参数值
    
    参数：
    req: Request - Flask/FastAPI的请求对象
    attr: str - 要获取的参数名
    default: Any - 如果获取失败时返回的默认值
    """
    try:
        # 1. 检查表单数据（multipart/form-data 或 application/x-www-form-urlencoded）
        if attr in req.form:
            # Sanic中form数据是列表形式，取第一个值
            return req.form.getlist(attr)[0]
        # 2. 检查URL查询参数 (?key=value)
        if attr in req.args:
            return req.args[attr]
        # 3. 检查JSON数据体 (application/json)
        if attr in req.json:
            return req.json[attr]
    except BadRequest:
        logging.warning(f"missing {attr} in request")
    except Exception as e:
        logging.warning(f"get {attr} from request failed:")
        logging.warning(traceback.format_exc())
    return default

def deduplicate_documents(source_docs):
    unique_docs = set()
    deduplicated_docs = []
    for doc in source_docs:
        if doc.page_content not in unique_docs:
            unique_docs.add(doc.page_content)
            deduplicated_docs.append(doc)
    return deduplicated_docs

def validate_user_id(user_id):
    if len(user_id) > 64:
        return False
    # 定义正则表达式模式
    pattern = r'^[A-Za-z][A-Za-z0-9_]*$'
    # 检查是否匹配
    if isinstance(user_id, str) and re.match(pattern, user_id):
        return True
    else:
        return False

def get_invalid_user_id_msg(user_id):
    return "fail, Invalid user_id: {}. user_id 长度必须小于64，且必须只含有字母，数字和下划线且字母开头".format(user_id)

def simplify_filename(filename, max_length=40):
    if len(filename) <= max_length:
        # 如果文件名长度小于等于最大长度，直接返回原文件名
        return filename

    # 分离文件的基本名和扩展名
    name, extension = filename.rsplit('.', 1)
    extension = '.' + extension  # 将点添加回扩展名

    # 计算头部和尾部的保留长度
    part_length = (max_length - len(extension) - 1) // 2  # 减去扩展名长度和破折号的长度
    end_start = -part_length if part_length else None

    # 构建新的简化文件名
    simplified_name = f"{name[:part_length]}-{name[end_start:]}" if part_length else name[:max_length - 1]

    return f"{simplified_name}{extension}"

def truncate_filename(filename, max_length=200):
    # 获取文件名后缀
    file_ext = os.path.splitext(filename)[1]

    # 获取不带后缀的文件名
    file_name_no_ext = os.path.splitext(filename)[0]

    # 计算文件名长度，注意中文字符
    filename_length = len(filename.encode('utf-8'))

    # 如果文件名长度超过最大长度限制
    if filename_length > max_length:
        debug_logger.warning("文件名长度超过最大长度限制，将截取文件名")
        # 生成一个时间戳标记
        timestamp = str(int(time.time()))
        # 截取文件名
        while filename_length > max_length:
            file_name_no_ext = file_name_no_ext[:-4]
            new_filename = file_name_no_ext + "_" + timestamp + file_ext
            filename_length = len(new_filename.encode('utf-8'))
    else:
        new_filename = filename

    return new_filename

def check_and_transform_excel(binary_data):
    # 使用BytesIO读取二进制数据
    try:
        data_io = BytesIO(binary_data)
        df = pd.read_excel(data_io)
    except Exception as e:
        return f"读取文件时出错: {e}"

    # 检查列数
    if len(df.columns) != 2:
        return "格式错误：文件应该只有两列"

    # 检查列标题
    if df.columns[0] != "问题" or df.columns[1] != "答案":
        return "格式错误：第一列标题应为'问题'，第二列标题应为'答案'"

    # 检查每行长度
    for index, row in df.iterrows():
        question_len = len(row['问题'])
        answer_len = len(row['答案'])
        if question_len > 512 or answer_len > 2048:
            return f"行{index + 1}长度超出限制：问题长度={question_len}，答案长度={answer_len}"

    # 转换数据格式
    transformed_data = []
    for _, row in df.iterrows():
        transformed_data.append({"question": row['问题'], "answer": row['答案']})

    return transformed_data

def correct_kb_id(kb_id):
    if not kb_id:
        return kb_id
    # 如果kb_id末尾不是KB_SUFFIX,则加上
    if KB_SUFFIX not in kb_id:
        # 判断有FAQ的时候
        if kb_id.endswith('_FAQ'):  # KBc86eaa3f278f4ef9908780e8e558c6eb_FAQ
            return kb_id.split('_FAQ')[0] + KB_SUFFIX + '_FAQ'
        else:  # KBc86eaa3f278f4ef9908780e8e558c6eb
            return kb_id + KB_SUFFIX
    else:
        return kb_id

def check_user_id_and_user_info(user_id, user_info):
    if user_id is None or user_info is None:
        msg = "fail, user_id 或 user_info 为 None"
        return False, msg
    if not validate_user_id(user_id):
        msg = get_invalid_user_id_msg(user_id)
        return False, msg
    if not user_info.isdigit():
        msg = "fail, user_info 必须是纯数字"
        return False, msg
    return True, 'success'

def read_files_with_extensions():
    # 获取当前脚本文件的路径
    current_file = os.path.abspath(__file__)

    # 获取当前脚本文件所在的目录
    current_dir = os.path.dirname(current_file)

    # 获取项目根目录
    project_dir = os.path.dirname(os.path.dirname(current_dir))

    directory = project_dir + '/data'

    extensions = ['.md', '.txt', '.pdf', '.jpg', '.docx', '.xlsx', '.eml', '.csv', 'pptx', 'jpeg', 'png']

    files = []
    for root, dirs, files_list in os.walk(directory):
        for file in files_list:
            if file.endswith(tuple(extensions)):
                file_path = os.path.join(root, file)
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                    mime_type, _ = mimetypes.guess_type(file_path)
                    if mime_type is None:
                        mime_type = 'application/octet-stream'
                    # 模拟 req.files.getlist('files') 返回的对象
                    file_obj = type('FileStorage', (object,), {
                        'name': file,
                        'type': mime_type,
                        'body': file_content
                    })()
                    files.append(file_obj)
    return files

def check_filename(filename, max_length=200):

    # 计算文件名长度，注意中文字符
    filename_length = len(filename.encode('utf-8'))

    # 如果文件名长度超过最大长度限制
    if filename_length > max_length:
        debug_logger.warning("文件名长度超过最大长度限制，返回None")
        return None

    return filename
    
def cur_func_name():
    return inspect.currentframe().f_back.f_code.co_name

def clear_string(str):
    # 只保留中文、英文、数字
    str = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", str)
    return str

embedding_tokenizer = AutoTokenizer.from_pretrained(EMBED_MODEL_PATH)
rerank_tokenizer = AutoTokenizer.from_pretrained(RERANK_MODEL_PATH)
llm_tokenizer = AutoTokenizer.from_pretrained(DEFAULT_MODEL_PATH)

def num_tokens(text: str) -> int:
    """Return the number of tokens in a string."""
    return len(llm_tokenizer.encode(text))

def num_tokens_embed(text: str) -> int:
    """返回字符串的Token数量"""
    return len(embedding_tokenizer.encode(text, add_special_tokens=True))

def num_tokens_rerank(text: str) -> int:
    """Return the number of tokens in a string."""
    return len(rerank_tokenizer.encode(text, add_special_tokens=True))

def fast_estimate_file_char_count(file_path):
    """
    快速估算文件的字符数，如果超过max_chars则返回False，否则返回True
    """
    file_extension = os.path.splitext(file_path)[1].lower()
    # TODO:先支持纯文本文件，后续在支持更多
    try:
        if file_extension in ['.txt']:
            # 'rb' 表示以二进制模式读取
            with open(file_path, 'rb') as file:
                # 读取前1024字节
                raw = file.read(1024)
                # 使用chardet库检测文件编码
                encoding = chardet.detect(raw)['encoding']
            # 第二次打开计算字符数
            with open(file_path, 'r', encoding=encoding) as file:
                char_count = sum(len(line) for line in file)
        else:
            # 不支持的文件类型
            return None

        return char_count

    except Exception as e:
        print(f"Error processing file {file_path}: {str(e)}")
        return None

def my_print(str):
        # 获取调用栈
    frame = inspect.currentframe()
    # 上一层frame是调用当前函数的函数
    caller_frame = frame.f_back
    
    # 获取调用者信息
    caller_filename = caller_frame.f_code.co_filename
    caller_function = caller_frame.f_code.co_name
    caller_lineno = caller_frame.f_lineno
    
    # 清理frame引用以避免引用循环
    del frame

    print(f"I was called by {caller_function} in file {caller_filename} at line {caller_lineno}")
    print(str)

# 将图片引用地址转换为服务器所存图片引用地址
def replace_image_references(text, file_id):
    lines = text.split('\n')
    result = []

    # 匹配带标题的图片引用
    pattern_with_caption = r'^!\[figure\]\((.+\.jpg)\s+(.+)\)$'
    # 匹配不带标题的图片引用
    pattern_without_caption = r'^!\[figure\]\((.+\.jpg)\)$'

    for line in lines:
        if not line.startswith('![figure]'):
            result.append(line)
            continue

        match_with_caption = re.match(pattern_with_caption, line)
        match_without_caption = re.match(pattern_without_caption, line)
        if match_with_caption:
            image_path, caption = match_with_caption.groups()
            debug_logger.info(f"line: {line}, caption: {caption}")
            result.append(f"#### {caption}")
            result.append(f"![figure](/home/zzh/Agent/file_store/image_store/{file_id}/{image_path})")
        elif match_without_caption:
            image_path = match_without_caption.group(1)
            result.append(f"![figure](/home/zzh/Agent/file_store/image_store/{file_id}/{image_path})")
        else:
            result.append(line)

    return '\n'.join(result)
