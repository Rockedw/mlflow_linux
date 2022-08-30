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
#     endpoint_url = 'http://169.254.123.2:9001'  # minio server地址
#     git_url = 'http://169.254.123.3:3000'  # gitea地址

class Config:
    SQLALCHEMY_BINDS = {
        'mlflow': 'mysql://root:wangyan123@39.105.6.98:43307/mlflow',
        'gitea': 'mysql://root:wangyan123@39.105.6.98:43307/gitea'
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    SQLALCHEMY_COMMIT_TEARDOWN = True
    SQLALCHEMY_ECHO = True
    bucket_name = 'models'
    access_key = 'minioadmin'
    secret_key = 'minioadmin'
    endpoint_url = 'http://39.105.6.98:43099/'  # minio server地址
    git_url = 'http://39.105.6.98:43000/'  # gitea地址
