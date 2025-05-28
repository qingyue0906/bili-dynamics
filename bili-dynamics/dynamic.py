import json
import os
import re
import time
import urllib.request

from bilibili_api import user, sync
from bilibili_api.user import User

from file_op import *

async def get_dynamics(u: User, sleep_time: float = 1.0, stop_value: int = 0) -> list:
    """
    :param u: User实例
    :param sleep_time: 每页爬取时的间隔时间，防止爬取过快导致Ban IP
    :param stop_value: 爬到<=指定的动态ID以后停止爬取
    :return: 返回一个列表
    """
    # 用于记录下一次起点
    offset = ""

    # 用于存储所有动态
    dynamics = []

    # 无限循环，直到 has_more != 1
    while True:
        # 获取该页动态
        page = await u.get_dynamics_new(offset)

        dynamics.extend(page["items"])

        if page["has_more"] != 1:
            # 如果没有更多动态，跳出循环
            break

        '''
        # 我晕了，完全搞不懂啊
        if [dy_id for dy_id in page["items"] if int(dy_id['id_str']) <= stop_value]:
            duplicate = [a for i in dynamics if (a := i) and int(a['id_str']) <= stop_value] 
            print(duplicate)
            dynamics = [x for x in dynamics if x not in duplicate]
            break
        '''
        # 先判断 page["items"] 中是否有 id_str 小于等于 stop_value 的
        if any(int(item['id_str']) <= stop_value for item in page["items"]):
            # 过滤出所有符合条件的 dynamics 项
            duplicate = [item for item in dynamics if int(item['id_str']) <= stop_value]
            # 移除 duplicate 中的项
            dynamics = [item for item in dynamics if int(item['id_str']) > stop_value]
            # print(dynamics)
            break


        # 设置 offset，用于下一轮循环
        offset = page["offset"]

        time.sleep(sleep_time)

    # 打印动态数量
    print(f"遍历 {len(dynamics)} 条动态")

    return dynamics

def parse_dynamic(dynamic: dict) -> dict|None:
    if dynamic['type'] != 'DYNAMIC_TYPE_DRAW': # DYNAMIC_TYPE_DRAW 为图文
        return None

    try:
        major = dynamic['modules']['module_dynamic']['major']
        opus_data = major.get('opus', {})
        author = dynamic['modules']['module_author']

        pictures = [p['url'] for p in opus_data.get('pics', [])]
        item = {
            "title": opus_data.get('title'),
            "description": opus_data.get('summary', {}).get('text'),
            "pictures": pictures
        }

        # 时间戳转换
        formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(author.get('pub_ts')))
        return {
            "dynamic_id": dynamic.get('id_str'),
            "time": formatted_time,
            "type": dynamic['type'],
            "item": item
        }
    except KeyError as e:
        print(f"字段缺失: {e}")
        return None

def get_download_queue(dynamic: dict) -> list|None:
    if dynamic['type'] != 'DYNAMIC_TYPE_DRAW': # DYNAMIC_TYPE_DRAW 为图文
        return None

    try:
        major = dynamic['modules']['module_dynamic']['major']
        opus_data = major.get('opus', {})
        author = dynamic['modules']['module_author']

        pictures = [p['url'] for p in opus_data.get('pics', [])]
        time_stamp = author.get('pub_ts')
        download_queue = []
        for url in pictures:
            url_and_timestamp = {
                "url": url,
                "time_stamp": time_stamp
            }
            download_queue.append(url_and_timestamp)
        return download_queue

    except KeyError as e:
        print(f"字段缺失: {e}")
        return None

def save_failed_list(save_path, failed_list):
    # 加载旧数据
    if os.path.exists(save_path):
        with open(save_path, "r", encoding="utf-8") as f:
            try:
                old_failed = json.load(f)
            except json.JSONDecodeError:
                old_failed = []
    else:
        old_failed = []

    # 合并新旧列表
    combined = old_failed + failed_list

    # 去重（以 url 为唯一键，保留时间戳较新的记录）
    url_to_data = {}
    for item in combined:
        url = item.get("url")
        ts = item.get("time_stamp", 0)
        if url:
            # 如果已存在，则保留时间戳更大的
            if url not in url_to_data or ts > url_to_data[url]["time_stamp"]:
                url_to_data[url] = item

    # 生成去重后的列表
    unique_failed_list = list(url_to_data.values())

    # 写入去重后的文件
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(unique_failed_list, f, indent=4, ensure_ascii=False)

    print(f"存在下载失败记录，共 {len(unique_failed_list)} 项。")


def download_pictures(download_queue: list, save_path: str, failed_download_path: str):
    failed_list = []
    for download in download_queue:
        url = download.get('url')
        time_stamp = download.get('time_stamp')
        url = re.sub(r'\?.*', '', url)

        print(f"Downloading: {url}")
        try:
            match = re.search(r'/([^/]+)$', url)
            file_name = match.group(1)
            file_path = os.path.join(save_path, file_name)
            urllib.request.urlretrieve(url, file_path)
            os.utime(file_path, (time_stamp, time_stamp))

        except Exception as e:
            print(f"Failed to download {url}: {e}")
            failed_data = {
                "url": url,
                "time_stamp": time_stamp
            }
            failed_list.append(failed_data)

    if failed_list:
        save_failed_list(failed_download_path, failed_list)

def get_opus(user_name: str, user_id: int, save_dir: str = "./opus"):
    path = os.getcwd()
    save_path = os.path.join(path, save_dir, user_name) # 图片保存路径
    info_path = os.path.join(save_path, '__info.json') # 图
    failed_download_path = os.path.join(save_path, '__failed_download.json') # 错误下载列表保存路径
    os.makedirs(save_path, exist_ok=True) # 创建输出文件夹

    u = user.User(user_id)

    info = rjson(info_path)
    stop_value = int(info[0].get('dynamic_id')) if info else 0
    # print(stop_value)
    # 获取动态
    dynamics = sync(get_dynamics(u, 1.0, stop_value))
    # 解析图文内容
    opus = [post for i in dynamics if (post := parse_dynamic(i))]
    opus.sort(key=lambda x: int(x["dynamic_id"]), reverse=True) # 排序
    print(f"筛选出 {len(opus)} 条图文动态")
    # 保存或追加 info
    if info:
        info[:0] = opus # 插在最前面
    else:
        info = opus
    # 保存info
    w2json(info_path, info)


    # 提取url和时间戳
    download_queue = [
        item
        for i in dynamics
        for item in (get_download_queue(i) or [])
    ]
    # 下载图片
    download_pictures(download_queue, save_path, failed_download_path)

def demo():
    u = user.User(660303135)
    dynamics = sync(get_dynamics(u, 1.0, 999643944421687328))

    # 解析图文内容
    opus = [post for i in dynamics if (post := parse_dynamic(i))]
    print(f"共有 {len(opus)} 条图文")
    with open("data_.json", "w", encoding="utf-8") as f:
        json.dump(opus, f, indent=4, ensure_ascii=False)

    # 提取url和时间戳
    download_queue = [
        item
        for i in dynamics
        for item in (get_download_queue(i) or [])
    ]
    with open("download_queue.json", "w", encoding="utf-8") as f:
        json.dump(download_queue, f, indent=4, ensure_ascii=False)

    download_pictures(download_queue, "./opus")

if __name__ == '__main__':
    get_opus("清风残影Sid", 16590804)
