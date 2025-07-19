# import yaml

# class Config:
#     def __init__(self, config_file):
#         self.config_file = config_file
#         print(f"Loading config from: {self.config_file}")
#         self.config = {}
#         self.load_config()

#     def get(self, key, default=None):
#         if not isinstance(key, str):
#             raise TypeError(f"The key must be a string, received key: {key}")
        
#         current = self.config
#         parts = key.split('.')
        
#         for part in parts:
#             if isinstance(current, dict) and part in current:
#                 current = current[part]
#             else:
#                 return default
#         return current

#     def set(self, key, value):
#         if not isinstance(key, str):
#             raise TypeError(f"The key must be a string, received key: {key}")
        
#         current = self.config
#         parts = key.split('.')
        
#         for part in parts[:-1]:
#             if part not in current:
#                 current[part] = {}
#             elif not isinstance(current[part], dict):
#                 current[part] = {}
#             current = current[part]
        
#         current[parts[-1]] = value
#         self.save_config()

#     def load_config(self):
#         try:
#             with open(self.config_file, 'r') as f:
#                 loaded = yaml.safe_load(f)
#                 self.config = loaded if loaded is not None else {}
#         except FileNotFoundError:
#             self.config = {}

#     def save_config(self):
#         with open(self.config_file, 'w') as f:
#             yaml.dump(self.config, f)

# config = Config('./config.yaml')

# # 账号类型 1 = 新个人云 0 = 个人云
# # 可参考 OpenList / AList 文档进行判断
# ACCOUNT_TYPE=
# # 移动云盘绑定的手机号
# PHONE_NUMBER=
# # 移动云盘 Authorization，可参考 OpenList / AList 文档抓包获取
# AUTHORIZATION=

# # 上传、分享文件时文件夹的 ID
# DIR_ID=
# # 是否开启分享功能
# SHARE=false
# # 分享的文件名，需放在 ID 为 DIR_ID 的目录下
# SHARE_FILENAME=
# # 是否开启上传功能
# UPLOAD=false


import os
from pathlib import Path
import dotenv

class Config():
    def __init__(self, config_file='config.yaml'):
        if os.path.exists('.env'):
            self.load_dotenv()

    def load_dotenv(self):
        dotenv.load_dotenv()

    def get(self, key, default=None):
        if not isinstance(key, str):
            raise TypeError(f"The key must be a string, received key: {key}")
        
        value = os.getenv(key)
        if value is None:
            return default
        
        # Convert to boolean if the value is 'true' or 'false'
        if value.lower() == 'true':
            return True
        elif value.lower() == 'false':
            return False
        
        return value
    
config = Config()