import json

import requests


# 获取星云授权
def get_xingyun_auth():
    url = 'https://xingyun.taiwu.com/api/auth/login'
    headers = {
        'Encrypt-Key': 'i15yCqIfclg8NyEbxRzln+RW6eaD/PIZvd7yA/4flJd+EPRNJqu/OkIRJt0ZPCaOs05HZW36Ch2gCamKpqiN2Q==',
        'Clientid': 'e5cd7e4891bf95d1d19206ce24a7b32e',
        'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
        'Content-Type': 'application/json;charset=UTF-8',
        'Accept': '*/*',
        'Host': 'xingyun.taiwu.com',
        'Connection': 'keep-alive'
    }
    data = '"RnWJayCAJgXzSuLoG3YvPudLMfSRepG0Dfl2kXBzo7oq8rOMECVVNoHCtHPu9+x9ZfMVosxE46jKvYNAQkS7WCEceexb/TMAvp+JCDpaX2uepn/CA/RgI7oEEJGw0gY4fYe5BQN/MD0xjltCdR3V5bsWUaNnOwy5m9yQ8UA6MD+ePoKqI4W13qV+Z8T+BGP2Kc6DUzzxuD2ZgzTD5SOHRHYBtSWWqvkzlI+LxiYBae+jeTK3moGhmxIbQSOo6vsSEtAEZ5Km3H1V5dbqlMZciVw2d3PeFqltf7Ow6RchGb0="'

    response = requests.post(url, headers=headers, data=data)

    if response.status_code == 200:
        try:
            response_data = response.json()
            if response_data.get('code') == 200:
                return response_data['data']['access_token']
            else:
                return f"Error in response: {response_data.get('msg')}"
        except ValueError:
            return "Failed to parse JSON response"
    else:
        return f"Request failed with status code: {response.status_code}"


# 执行SQL
def execute_sql(sql, auth_str=None, db="ry-cloud"):
    if auth_str is None:
        auth_str = get_xingyun_auth()
    url = 'https://xingyunnew.taiwu.com/api/starcloud/tool/sql/run'
    headers = {
        'ClientId': 'e5cd7e4891bf95d1d19206ce24a7b32e',
        'Authorization': f"Bearer {auth_str}",
        'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
        'Content-Type': 'application/json',
        'Accept': '*/*',
        'Host': 'xingyunnew.taiwu.com',
        'Connection': 'keep-alive'
    }
    data = {
        "dataSource": db,
        "sql": sql
    }
    # data_json = json.dumps(data, ensure_ascii=False)

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        response_data = response.json()
        if response_data['code'] == 200:
            return response_data['data']
        else:
            print("Error in response: ", response_data['msg'])
            return None
    else:
        print("HTTP Error: ", response.status_code)
        return None


# 打印json格式结果
def print_json(data):
    """
    将对象格式化为JSON字符串并打印出来。

    Args:
        data (dict or list): 要格式化为JSON的对象

    Returns:
        None
    """
    # 使用 json.dumps 将对象格式化为 JSON 字符串
    json_str = json.dumps(data, ensure_ascii=False)
    print(json_str)
