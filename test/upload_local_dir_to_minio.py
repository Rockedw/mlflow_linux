import os
import mlflow

os.environ["AWS_ACCESS_KEY_ID"] = "minioadmin"
os.environ["AWS_SECRET_ACCESS_KEY"] = "minioadmin"
os.environ["MLFLOW_S3_ENDPOINT_URL"] = f"http://39.105.6.98:43099"


def transform(model_path):
    pass


def upload_model(model_path,model_name):
    try:
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
        return 'success'
    except Exception as e:
        print(e)
        return 'fail'


if __name__ == "__main__":
    # with open('s3://models/0/3de4bc5ed26348229ce9bd8a19472817/artifacts/model/conda.yaml') as f:
    #     print(f.readline())


    # upload(model_path)
