import os
import re
import json
import urllib.request

def retry_failed_download(failed_path: str, save_path: str):
    """
    重新尝试下载 failed_path 指定的 JSON 文件中记录的所有失败项，
    下载成功后从失败列表中移除，并对目标文件进行覆盖。
    """

    # 1. 加载失败列表
    if os.path.exists(failed_path):
        with open(failed_path, "r", encoding="utf-8") as f:
            try:
                failed_list = json.load(f)
            except json.JSONDecodeError:
                print(f"[WARN] 无法解析 {failed_path}，重置为空列表")
                failed_list = []
    else:
        print(f"[INFO] 失败列表文件 {failed_path} 不存在，退出重试")
        return

    if not failed_list:
        print("[INFO] 没有需要重试的下载项")
        return

    os.makedirs(save_path, exist_ok=True)

    succeeded = []
    still_failed = []

    # 2. 遍历每条失败记录，尝试下载
    for entry in failed_list:
        url = entry.get("url")
        ts  = entry.get("time_stamp", None)
        if not url or ts is None:
            continue

        # 去掉可能的 query 参数
        clean_url = re.sub(r'\?.*$', '', url)
        match = re.search(r'/([^/]+)$', clean_url)
        if not match:
            print(f"[WARN] 无法从 URL 提取文件名，跳过：{url}")
            still_failed.append(entry)
            continue

        file_name = match.group(1)
        file_path = os.path.join(save_path, file_name)

        print(f"[RETRY] 下载：{clean_url} → {file_path}")
        try:
            # 无论文件是否已存在，都覆盖下载
            urllib.request.urlretrieve(clean_url, file_path)
            # 恢复时间戳
            os.utime(file_path, (ts, ts))
            succeeded.append(entry)
            print(f"[OK]   下载并设置时间：{file_name}")
        except Exception as e:
            print(f"[ERR]  下载失败：{clean_url}，原因：{e}")
            still_failed.append(entry)

    # 3. 将仍然失败的写回 JSON
    with open(failed_path, "w", encoding="utf-8") as f:
        json.dump(still_failed, f, indent=4, ensure_ascii=False)

    print(f"\n重试完成：总 {len(failed_list)} 项，成功 {len(succeeded)}，失败 {len(still_failed)}")

if __name__ == "__main__":
    FAILED_JSON = "./opus/芙兰剔牙_Flantia/__failed_download.json"
    SAVE_DIR    = "./opus/芙兰剔牙_Flantia/"

    retry_failed_download(FAILED_JSON, SAVE_DIR)
