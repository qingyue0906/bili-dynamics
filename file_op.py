import json

def w2json(json_file_name: str, json_dict, mode: str = 'w'):
    with open(json_file_name, mode, encoding='utf-8') as f:
        json.dump(json_dict, f, indent=4, ensure_ascii=False)

def w2file(file_name: str, msg: str, mode: str = 'w'):
    with open(file_name, mode, encoding='utf-8') as f:
        f.write(msg)

def rjson(json_file_name: str):
    try:
        with open(json_file_name, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(e)
        return None