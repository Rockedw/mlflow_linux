import stat
from socket import socket, AF_INET, SOCK_STREAM

import boto3
import os
import subprocess
from config import Config

bucket_name = Config.bucket_name
access_key = Config.access_key
secret_key = Config.secret_key
endpoint_url = Config.endpoint_url
git_url = Config.git_url


def rmtree(top):
    """
    递归删除文件夹
    :param top:
    :return:
    """
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            filename = os.path.join(root, name)
            os.chmod(filename, stat.S_IWUSR)
            os.remove(filename)
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(top)


def download_directory(download_path: str, save_path='/tmp/models/'):
    """
    从S3中下载模型到本地
    :param download_path:
    :param save_path:
    :return:
    """
    # bucket_name = 'models'
    print(save_path)
    print('download ' + download_path)
    download_path = download_path.replace('s3://models', '')
    print('download ' + download_path)
    resource = boto3.resource(
        's3',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        endpoint_url=endpoint_url
    )
    bucket = resource.Bucket(bucket_name)
    if os.path.exists(save_path + download_path):
        return save_path + download_path + '/model'
    for obj in bucket.objects.filter(Prefix=download_path):
        key = obj.key
        if '.git' not in key:
            if not os.path.exists(os.path.dirname(save_path + obj.key)):
                os.makedirs(os.path.dirname(save_path + obj.key))
            print(f'Downloading {key}')
            print(save_path + key)
            bucket.download_file(Key=key, Filename=save_path + key)
    return save_path + download_path + '/model'


def cmd(command):
    """
    执行bash或这cmd命令
    :param command:
    :return:
    """
    print(command)
    try:
        subp = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")
        # subp.wait()
        # print(subp.communicate()[1])
        # return subp.pid
    except Exception as e:
        print(str(e))
        # print(subp.communicate()[1])

    # if subp.poll() == 0:
    #     print(subp.communicate()[1])
    # else:
    #     print("失败")


def scan_dir(path, head: dict = None):
    if os.path.isdir(path):
        if head is None:
            head = {'is_dir': True, 'title': os.path.basename(path), 'key': path, 'children': []}
    else:
        return {'is_dir': False, 'title': os.path.basename(path), 'key': path, }
    for name in os.listdir(path):
        if name == '.git':
            pass
        elif os.path.isdir(path + os.sep + name):
            temp = {'is_dir': True, 'title': name, 'key': path + os.sep + name, 'children': []}
            scan_dir(path + os.sep + name, temp)
            head['children'].append(temp)
        else:
            temp = {'is_dir': False, 'title': name, 'key': path + os.sep + name}
            head['children'].append(temp)
    return head


def portscanner(host='127.0.0.1', ports=range(40000, 41000)):
    for port in ports:
        try:
            s = socket(AF_INET, SOCK_STREAM)
            s.connect((host, port))
            s.close()
        except:
            print(f"{port} open")
            return port


if __name__ == '__main__':
    # path = r'C:/Users/wangyan/PycharmProjects/MLFlow/repos'
    # head = scan_dir(path)
    # print(str(head))
    command = 'cd C:/Users/wangyan/PycharmProjects/MLFlow && cd ./temp/repos/rock/second_repo/5/second_repo && rm -rf .git &&cd C:/Users/wangyan/PycharmProjects/MLFlow && mlflow run ./temp/repos/rock/second_repo/5/second_repo'
    os.system(command)
