import os
import sys
import datetime

from dynamic import *
from re_download import *

class DualOutput:
    """
    自定义输出流，允许同时输出到文件和标准输出。
    """
    def __init__(self, file, stream=sys.stdout):
        self.file = file
        self.stream = stream

    def write(self, message):
        self.file.write(message)  # 写入文件
        self.stream.write(message)  # 输出到控制台

    def flush(self):
        self.file.flush()
        self.stream.flush()

def save_log(func, *args, **kwargs):
    """
    将指定函数的 print 输出保存到以当前时间命名的 txt 文件中。

    :param func: 要执行的函数
    :param args: 传递给函数的参数
    :param kwargs: 传递给函数的关键字参数
    :return: 输出文件的路径
    """
    # 根据当前时间生成文件名
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    path = os.getcwd()
    log_path = os.path.join(path, "log")
    os.makedirs(log_path, exist_ok=True)
    output_file = os.path.join(log_path, f"{timestamp}.txt")

    # 打开文件并使用 DualOutput
    with open(output_file, "w", encoding="utf-8") as f:
        dual_output = DualOutput(f)
        original_stdout = sys.stdout
        try:
            sys.stdout = dual_output  # 重定向到 DualOutput
            func(*args, **kwargs)  # 调用目标函数
        finally:
            sys.stdout = original_stdout  # 恢复原始标准输出

    print(f"日志已保存到 {output_file}")
    return output_file

def batch_dynamics(mode='download', sleep_time:float=1.0):
    with open('./user_list.txt', "r", encoding="utf-8") as file:
        for line in file:
            time.sleep(sleep_time)
            line = line.strip() # 去掉行末的换行符并确保非空行
            if line:
                uname, uid = line.split(":")
                uid = int(uid)

                print(f'{uname} ({uid})')
                if mode == 'download':
                    get_opus(user_name = uname, user_id = uid, save_dir = "./opus")
                elif mode == 're_download':
                    save_dir = os.path.join(os.getcwd(), f"./opus/{uname}")
                    failed_json = os.path.join(save_dir, '__failed_download.json')
                    retry_failed_download(failed_json, save_dir)
                print('')

    print("运行完成")

if __name__ == '__main__':
    save_log(batch_dynamics, mode='re_download')