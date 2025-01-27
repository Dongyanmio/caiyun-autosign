# caiyun-autosign
## 📖 介绍
基于 Python 的中国移动云盘自动签到程序

## 📚 使用方法
### 1. 安装环境
确保已安装 Python 和 pip。如果未安装，请参考 [Python 官方文档](https://www.python.org/downloads/) 进行安装。

### 2. 安装依赖库
在终端中执行以下命令，安装所需的 Python 库：
```bash
pip install requests loguru PyYAML
```
### 3. 获取 Authorization
按照 [AList 官方文档](https://alist.nn.ci/zh/guide/drivers/139.html#%E6%96%B0%E4%B8%AA%E4%BA%BA%E4%BA%91) 中 `新个人云` 部分的方法，获取 `Authorization`。

### 4. 配置 config.yaml

- 将 `config.yaml.example` 文件复制一份，并重命名为 `config.yaml`。
- 打开 `config.yaml` 文件，在 `139yun` 下的 `token` 字段中填入上一步获取的 `Authorization`。
- 同时在 `139yun` 下的 `phone` 字段中填入需要签到用户的手机号。

### 5. 运行脚本
在终端中执行以下命令，运行脚本：
```bash
python ./main.py
```
