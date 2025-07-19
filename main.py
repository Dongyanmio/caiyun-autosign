import hashlib
import requests
from loguru import logger
from config import config
import json
import schedule
import time
import os
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from typing import Optional, Union, List, Dict, Any
from dataclasses import dataclass
from enum import Enum


@dataclass
class AuthTokens:
    basic_token: str
    jwt_token: str = ""
    sso_token: str = ""


@dataclass
class UploadConfig:
    enabled: bool
    directory_id: str
    filename: str = "7"


@dataclass
class ShareConfig:
    enabled: bool
    filename: str


class AuthService:
    def __init__(self, auth_token: str, account: str):
        self.auth_token = auth_token
        self.account = str(account)
        self.tokens = AuthTokens(basic_token=auth_token)
        
    def fetch_sso_token(self) -> Union[str, List]:
        url = 'https://user-njs.yun.139.com/user/querySpecToken'
        host = 'user-njs.yun.139.com'
        data = {"phoneNumber": self.account, "toSourceId": "001003"}
            
        headers = {
            'Authorization': f"Basic {self.auth_token}",
            'Content-Type': 'application/json',
            'Accept': '*/*',
            'Host': host,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
        }
        
        resp = requests.post(url, headers=headers, data=json.dumps(data)).json()
        if resp['success']:
            self.tokens.sso_token = resp['data']['token']
            return self.tokens.sso_token
        return [False, resp['message']]

    def fetch_jwt_token(self) -> Union[bool, List]:
        sso_token = self.fetch_sso_token()
        logger.debug(f"use ssoToken: {sso_token}")
        
        if isinstance(sso_token, list):
            raise Exception(f"获取SSO Token失败: {sso_token[1]}")
            
        url = f"https://caiyun.feixin.10086.cn:7071/portal/auth/tyrzLogin.action?ssoToken={sso_token}"
        headers = self._get_base_headers()
        
        resp = requests.get(url, headers=headers).json()
        if resp['code'] != 0:
            return [False, resp['msg']]
            
        self.tokens.jwt_token = resp['result']['token']
        return True
    
    def _get_base_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Basic {self.auth_token}",
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
            'Content-Type': 'application/json',
            'Accept': '*/*',
            "jwtToken": self.tokens.jwt_token
        }
    
    def get_headers(self) -> Dict[str, str]:
        return self._get_base_headers()
    
    def get_cookies(self) -> Dict[str, str]:
        return {"jwtToken": self.tokens.jwt_token}


class BaseTask(ABC): 
    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service
        self.url = 'https://caiyun.feixin.10086.cn'
        
    @property
    def headers(self) -> Dict[str, str]:
        return self.auth_service.get_headers()
    
    @property
    def cookies(self) -> Dict[str, str]:
        return self.auth_service.get_cookies()
    
    @abstractmethod
    def execute(self) -> bool:
        pass


class SignInTask(BaseTask):
    
    def execute(self) -> bool:
        if not self._check_sign_status():
            return self._perform_sign()
        
        logger.success('今日已签到，不再进行签到操作')
        return True
    
    def _check_sign_status(self) -> bool:
        check_sign_url = f"{self.url}/market/signin/page/infoV2?client=mini"
        c_resp = requests.get(check_sign_url, headers=self.headers, cookies=self.cookies).json()
        
        if c_resp.get('msg') != 'success':
            logger.warning(f"检测签到状态失败，原因 {c_resp['msg']}")
            return False
            
        return c_resp.get('result').get('todaySignIn', False)
    
    def _perform_sign(self) -> bool:
        logger.info('今日未签到，正在开始签到')
        sign_url = f'{self.url}/market/manager/commonMarketconfig/getByMarketRuleName?marketName=sign_in_3'
        resp = requests.get(sign_url, headers=self.headers, cookies=self.cookies).json()
        
        if resp['msg'] == 'success':
            logger.success("签到成功")
            return True
        else:
            logger.error(f"签到失败，原因：{resp['msg']}")
            return False


class UploadTask(BaseTask):
    
    def __init__(self, auth_service: AuthService, upload_config: UploadConfig):
        super().__init__(auth_service)
        self.upload_config = upload_config
    
    def execute(self) -> bool:
        if not self.upload_config.enabled:
            logger.info('上传功能未开启，跳过')
            return True
            
        file_bytes = self._generate_file(7)  # 7MB
        return self._upload_file(file_bytes)
    
    def _generate_file(self, size_mb: int = 15) -> bytes:
        file_size = size_mb * 1024 * 1024
        return os.urandom(file_size)
    
    def _upload_file(self, file_bytes: bytes) -> bool:
        xml_data = self._build_upload_xml(file_bytes)
        headers = self._get_upload_headers()
        
        resp = requests.post(
            "https://ose.caiyun.feixin.10086.cn/richlifeApp/devapp/IUploadAndDownload",
            headers=headers,
            cookies=self.cookies,
            data=xml_data,
        )
        
        if resp.status_code != 200:
            logger.error(f"上传文件失败，返回结果{resp.content}")
            return False
            
        logger.success("上传文件成功")
        return True
    
    def _build_upload_xml(self, file_bytes: bytes) -> str:
        return f"""
        <pcUploadFileRequest>
            <ownerMSISDN>{self.auth_service.account}</ownerMSISDN>
            <fileCount>1</fileCount>
            <totalSize>{len(file_bytes)}</totalSize>
            <uploadContentList length="1">
            <uploadContentInfo>
                <contentName><![CDATA[{self.upload_config.filename}]]></contentName>
                <contentSize>{len(file_bytes)}</contentSize>
                <contentDesc></contentDesc>
                <contentTAGList></contentTAGList>
                <comlexFlag>0</comlexFlag>
                <comlexCID></comlexCID>
                <resCID length="0"></resCID>
                <digest>{hashlib.md5(file_bytes).hexdigest().upper()}</digest>
                <extInfo length="1">
                    <entry>
                        <key>modifyTime</key>
                        <vaule>{time.strftime('%Y%m%d%H%M%S')}</vaule>
                    </entry>
                </extInfo>
            </uploadContentInfo>
            </uploadContentList>
            <newCatalogName></newCatalogName>
            <parentCatalogID>{self.upload_config.directory_id}</parentCatalogID>
            <operation>0</operation>
            <path></path>
            <manualRename>2</manualRename>
        </pcUploadFileRequest>
        """
    
    def _get_upload_headers(self) -> Dict[str, str]:
        return {
            'x-huawei-uploadSrc': '1',
            'x-huawei-channelSrc': '10200153',
            'x-ClientOprType': '11',
            'Connection': 'keep-alive',
            'x-NetType': '6',
            'x-DeviceInfo': '||11|8.2.1.20241205|PC|V0lOLUVQSUxVNjE1TUlI|D1EA1E8B761492DFF34B18F05A5876E0|| Windows 10 (10.0)|1366X738|RW5nbGlzaA==|||',
            'x-MM-Source': '032',
            'x-SvcType': '1',
            'Authorization': f'Basic {self.auth_service.auth_token}',
            'X-Tingyun-Id': 'p35OnrDoP8k;c=2;r=1955442920;u=43ee994e8c3a6057970124db00b2442c::8B3D3F05462B6E4C',
            'Host': 'ose.caiyun.feixin.10086.cn',
            'User-Agent': 'Mozilla/5.0',
            'Content-Type': 'text/xml;UTF-8',
            'Accept': '*/*'
        }


class CloudStatusTask(BaseTask):
    
    def execute(self) -> bool:
        r = requests.get('https://caiyun.feixin.10086.cn/market/signin/page/receive', 
                        headers=self.headers, 
                        cookies=self.cookies).json()
        
        clouds = r["result"].get("receive", "")
        all_clouds = r["result"].get("total", "")
        logger.info(f'当前待领取云朵:{clouds}')
        logger.info(f'当前云朵数量:{all_clouds}')
        return True


class ShareTask(BaseTask):
    
    def __init__(self, auth_service: AuthService, share_config: ShareConfig, upload_config: UploadConfig):
        super().__init__(auth_service)
        self.share_config = share_config
        self.upload_config = upload_config
    
    def execute(self) -> bool:
        if not self.share_config.enabled:
            logger.info('分享功能未开启，跳过')
            return True
            
        file_list = self._get_file_list()
        if not file_list:
            return False
            
        share_file = self._find_target_file(file_list)
        if not share_file:
            logger.warning('没有找到目标文件可以分享')
            return False
            
        return self._create_share_link(share_file)
    
    def _get_file_list(self) -> Optional[Dict]:
        return self._get_file_list_type1()
    
    def _get_file_list_type1(self) -> Optional[Dict]:
        url = 'https://personal-kd-njs.yun.139.com/hcy/file/list'
        data = {
            "parentFileId": self.upload_config.directory_id,
            "pageInfo": {
                "pageSize": 40,
                "pageCursor": "0|[9-1-0,11-0-1][JzIwMjQtMDMtMDlUMTA6MzM6MTguNzEyWic=,J0ZzSVEweF9NVVVDVmNqQ1plaTJ0SFZxSjVadjNsbEZ5bCc=]"
            },
            "imageThumbnailStyleList": ["Big", "Small"],
            "orderDirection": "DESC",
            "orderBy": "updated_at"
        }
        
        headers = {
            "x-yun-op-type": "1",
            "x-yun-net-type": "1",
            "x-yun-module-type": "100",
            "x-yun-app-channel": "10214200",
            "x-yun-client-info": "1||8|5.10.1|microsoft|microsoft|306d1d1c-016c-4251-9ea6-951dca||windows 10 x64|||||",
            "x-tingyun": "c=M|4Nl_NnGbjwY",
            "authorization": f"Basic {self.auth_service.auth_token}",
            "x-yun-api-version": "v1",
            "xweb_xhr": "1",
            "x-yun-tid": "cb8a2b4b-8eb7-4b05-b1c1-e41020",
            "content-type": "application/json"
        }
        
        resp = requests.post(url=url, headers=headers, cookies=self.cookies, data=json.dumps(data))
        return resp.json()
    
    def _find_target_file(self, file_list: Dict) -> Optional[Dict]:
        content_list = file_list.get('data', {}).get('items', [])
        name_key = 'name'
            
        if not content_list:
            return None
            
        target_files = [item for item in content_list if self.share_config.filename in item[name_key]]
        return target_files[0] if target_files else None
    
    def _create_share_link(self, share_file: Dict) -> bool:
        share_data = self._build_share_data(share_file)
        
        resp_json = requests.post(
            url='https://yun.139.com/orchestration/personalCloud-rebuild/outlink/v1.0/getOutLink',
            headers=self.headers,
            cookies=self.cookies,
            data=json.dumps(share_data),
        ).json()
        
        if resp_json.get('success'):
            out_link = resp_json.get("data").get("getOutLinkRes").get("getOutLinkResSet")[0].get("linkUrl")
            logger.success(f'分享成功,url: {out_link}')
            return True
        else:
            logger.error(f'分享失败,原因: {resp_json.get("message")}')
            return False
    
    def _build_share_data(self, share_file: Dict) -> Dict:
        file_id = share_file.get('fileId')
        file_name = share_file.get('name')
            
        return {
            "getOutLinkReq": {
                "subLinkType": 0,
                "encrypt": 1,
                "coIDLst": [file_id],
                "caIDLst": [],
                "pubType": 1,
                "dedicatedName": file_name,
                "periodUnit": 1,
                "viewerLst": [],
                "extInfo": {
                    "isWatermark": 0,
                    "shareChannel": "3001"
                },
                "period": 1,
                "commonAccountInfo": {
                    "account": self.auth_service.account,
                    "accountType": 1
                }
            }
        }


class TaskScheduler:
    def __init__(self):
        self.tasks: List[BaseTask] = []
    
    def add_task(self, task: BaseTask) -> None:
        self.tasks.append(task)
    
    def execute_all(self) -> bool:
        success = True
        for task in self.tasks:
            try:
                if not task.execute():
                    success = False
            except Exception as e:
                logger.error(f"任务执行失败: {e}")
                success = False
        return success


class CaiYunService:
    def __init__(self, token: str, account: str):
        self.auth_token = token
        self.account = str(account)
        self.url = 'https://caiyun.feixin.10086.cn'
        self.auth_service = AuthService(token, account)
        self._init_configs()
        self._init_tasks()
    
    def _init_configs(self):
        self.upload_config = UploadConfig(
            enabled=bool(config.get('UPLOAD', False)),
            directory_id=str(config.get('DIR_ID', '')),
            filename=str(config.get('UPLOAD_FILENAME', '7'))
        )
        
        self.share_config = ShareConfig(
            enabled=bool(config.get('SHARE', False)),
            filename=str(config.get('SHARE_FILENAME', ''))
        )
    
    def _init_tasks(self):
        self.sign_task = SignInTask(self.auth_service)
        self.upload_task = UploadTask(self.auth_service, self.upload_config)
        self.share_task = ShareTask(self.auth_service, self.share_config, self.upload_config)
        self.cloud_task = CloudStatusTask(self.auth_service)
    
    
    @property
    def headers(self):
        return self.auth_service.get_headers()
    
    @property
    def cookies(self):
        return self.auth_service.get_cookies()



def job():
    auth_service = AuthService(
        auth_token=str(config.get('ACCOUNT_AUTH')),
        account=str(config.get('ACCOUNT_PHONE'))
    )
    upload_config = UploadConfig(
        enabled=bool(config.get('UPLOAD', False)),
        directory_id=str(config.get('DIR_ID', '')),
        filename='7'
    )
    
    share_config = ShareConfig(
        enabled=bool(config.get('SHARE', False)),
        filename=str(config.get('SHARE_FILENAME', ''))
    )
    scheduler = TaskScheduler()
    logger.info("获取jwtToken")
    if not auth_service.fetch_jwt_token():
        logger.error("获取JWT Token失败")
        return
    
    logger.info("开始签到")
    scheduler.add_task(SignInTask(auth_service))
    
    logger.info("开始上传大小为7M的文件")
    scheduler.add_task(UploadTask(auth_service, upload_config))
    
    logger.info("开始完成分享文件任务")
    scheduler.add_task(ShareTask(auth_service, share_config, upload_config))
    
    logger.info("检查待领取云朵")
    scheduler.add_task(CloudStatusTask(auth_service))
    if scheduler.execute_all():
        logger.success("任务执行完成")
    else:
        logger.warning("部分任务执行失败")


def main():
    '''
    schedule.every().day.at("08:00").do(job)
    schedule.every().day.at("20:00").do(job)
    logger.success("定时任务已创建，将在8:00和20:00执行一次")
    while True:
        schedule.run_pending()
        time.sleep(1)
    '''
    job()


if __name__ == '__main__':
    logger.info('程序启动')
    main()