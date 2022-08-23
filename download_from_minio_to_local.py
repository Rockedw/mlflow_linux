import os

import boto3


def download_directory(
        bucket_name,
        path,
        access_key,
        secret_key,
        endpoint_url,
):
    resource = boto3.resource(
        's3',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        endpoint_url=endpoint_url

    )

    bucket = resource.Bucket(bucket_name)
    save_path = 'C://temp/'
    for obj in bucket.objects.filter(Prefix=path):
        key = obj.key
        if '.git' not in key:
            if not os.path.exists(os.path.dirname(save_path + obj.key)):
                os.makedirs(os.path.dirname(save_path + obj.key))
            print(f'Downloading {key}')
            print('./data/' + key)
            bucket.download_file(Key=key, Filename=save_path + key)
    return save_path + path

# if __name__ == '__main__':
#     path = '0/36fce13f7d444ecb86791a82c6e538e2/artifacts/model'
#     # path = '3/ddc7779843a9495b9ad96e0bca7a6b28/artifacts/iris_rf'
#     download_directory(bucket_name='models', path=path, access_key='minioadmin', secret_key='minioadmin',
#                        endpoint_url='http://39.105.6.98:43098')
# mlflow.projects.run(uri=path + '/model', env_manager='conda')
# mlflow.projects.SubmittedRun
# project_uri = "https://github.com/mlflow/mlflow-example"
# params = {"alpha": 0.5, "l1_ratio": 0.01}

# Run MLflow project and create a reproducible conda environment
# on a local host
# mlflow.run(project_uri, parameters=params)
