import stat
import threading
from socket import socket, AF_INET, SOCK_STREAM

import boto3
import subprocess
from config import Config
import os
import mlflow
import hdfs

os.environ["AWS_ACCESS_KEY_ID"] = "minioadmin"
os.environ["AWS_SECRET_ACCESS_KEY"] = "minioadmin"
os.environ["MLFLOW_S3_ENDPOINT_URL"] = f"http://39.105.6.98:43099"

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
        return subp
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


def portscanner(already_used_ports, lock: threading.Lock, host='127.0.0.1', ports=range(40000, 41000)):
    with lock:
        for port in ports:
            if port not in already_used_ports:
                try:
                    s = socket(AF_INET, SOCK_STREAM)
                    s.connect((host, port))
                    s.close()
                except:
                    print(f"{port} open")
                    already_used_ports.append(port)
                    return port


def kill_port(port):
    command = '''kill -9 $(netstat -nlp | grep :''' + str(port) + '''| awk '{print $7}' | awk -F"/" '{ print $1 
        }') '''
    os.system(command)


def upload_model(model_path, model_name):
    print(1)
    mlflow.tracking.set_tracking_uri('http://39.105.6.98:43082')
    print(2)
    mlflow.log_artifacts(local_dir=model_path, artifact_path='model')
    print(3)
    artifact_uri = mlflow.get_artifact_uri()
    print("Artifact uri: {}".format(artifact_uri))
    mv = mlflow.register_model(artifact_uri, model_name)
    print("Name: {}".format(mv.name))
    print("Version: {}".format(mv.version))


# 根据文件地址创建文件夹
def create_dir(file_path):
    if '/' not in file_path:
        return
    dir_path = file_path[:file_path.rfind('/')]
    print(dir_path)
    if len(dir_path) > 0 and not os.path.exists(dir_path):
        os.makedirs(dir_path)


def download_dir_from_hdfs(client: hdfs.Client, hdfs_path, local_path):
    if not client.status(hdfs_path, strict=False):
        return
    if client.status(hdfs_path)['type'] == 'DIRECTORY':
        if not os.path.exists(local_path):
            os.makedirs(local_path)
        for file in client.list(hdfs_path):
            download_dir_from_hdfs(client, hdfs_path + '/' + file, local_path + '/' + file)
    else:
        if not os.path.exists(local_path):
            create_dir(local_path)
        client.download(hdfs_path, local_path)


if __name__ == '__main__':
    # path = r'C:/Users/wangyan/PycharmProjects/MLFlow/repos'
    # head = scan_dir(path)
    # print(str(head))
    # command = 'cd C:/Users/wangyan/PycharmProjects/MLFlow && cd ./temp/repos/rock/second_repo/5/second_repo && rm -rf .git &&cd C:/Users/wangyan/PycharmProjects/MLFlow && mlflow run ./temp/repos/rock/second_repo/5/second_repo'
    # os.system(command)
    create_dir('/model.yaml')
