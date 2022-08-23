class Config:
    SQLALCHEMY_BINDS = {
        'mlflow': 'mysql://root:wangyan123@localhost:3306/mlflow',
        'gitea': 'mysql://root:wangyan123@localhost:3306/gitea'
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    SQLALCHEMY_COMMIT_TEARDOWN = True
    SQLALCHEMY_ECHO = True
    bucket_name = 'models'
    access_key = 'minioadmin'
    secret_key = 'minioadmin'
    endpoint_url = 'http://169.254.123.5:9001'  # minio server地址
    git_url = 'http://169.254.123.6:3000'  # gitea地址
