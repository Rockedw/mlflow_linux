# class Config:
#     SQLALCHEMY_BINDS = {
#         'mlflow': 'mysql://root:wangyan123@localhost:3306/mlflow',
#         'gitea': 'mysql://root:wangyan123@localhost:3306/gitea'
#     }
#     SQLALCHEMY_TRACK_MODIFICATIONS = True
#     SQLALCHEMY_COMMIT_TEARDOWN = True
#     SQLALCHEMY_ECHO = True
#     bucket_name = 'models'
#     access_key = 'minioadmin'
#     secret_key = 'minioadmin'
#     endpoint_url = 'http://169.254.123.2:9001/'  # minio server地址
#     git_url = 'http://169.254.123.3:3000/'  # gitea地址

# class Config:
#     SQLALCHEMY_BINDS = {
#         'mlflow': 'mysql://root:wangyan123@39.105.6.98:43307/mlflow',
#         'gitea': 'mysql://root:wangyan123@39.105.6.98:43307/gitea'
#     }
#     SQLALCHEMY_TRACK_MODIFICATIONS = True
#     SQLALCHEMY_COMMIT_TEARDOWN = True
#     SQLALCHEMY_ECHO = True
#     bucket_name = 'models'
#     access_key = 'minioadmin'
#     secret_key = 'minioadmin'
#     endpoint_url = 'http://39.105.6.98:43099/'  # minio server地址
#     git_url = 'http://39.105.6.98:43000/'  # gitea地址
#     UPLOAD_FOLDER = r'./upload'
#     HDFS_URL = 'http://172.31.129.149:50070'

# 爬虫用的配置
# class Config:
#     SQLALCHEMY_BINDS = {
#        'mlflow': 'mysql://root:wangyan123@localhost:3306/mlflow',
# #         'gitea': 'mysql://root:wangyan123@localhost:3306/gitea'
#     }
#     SQLALCHEMY_TRACK_MODIFICATIONS = True
#     SQLALCHEMY_COMMIT_TEARDOWN = True
#     SQLALCHEMY_ECHO = True
#     bucket_name = 'models'
#     access_key = 'minioadmin'
#     secret_key = 'minioadmin'
#     endpoint_url = 'http://39.105.6.98:43099/'  # minio server地址
#     git_url = 'http://172.17.0.4:3000/'  # gitea地址
#     UPLOAD_FOLDER = r'./upload'
#     HDFS_URL = 'http://172.31.129.149:50070'


# 本地用
class Config:
    SQLALCHEMY_BINDS = {
        'mlflow': 'mysql://root:wangyan123@8.130.105.10:59036/mlflow',
        'gitea': 'mysql://root:wangyan123@8.130.105.10:59036/gitea'
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    SQLALCHEMY_COMMIT_TEARDOWN = True
    SQLALCHEMY_ECHO = True
    bucket_name = 'models'
    access_key = 'minioadmin'
    secret_key = 'minioadmin'
    endpoint_url = 'http://39.105.6.98:43099/'  # minio server地址
    git_url = 'http://8.130.105.10:59030/'  # gitea地址
    UPLOAD_FOLDER = r'./upload'
    HDFS_URL = 'http://172.31.129.149:50070'
