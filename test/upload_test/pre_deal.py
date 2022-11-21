import argparse
import json


def parse_args():
    parser = argparse.ArgumentParser(
        description="you should add those parameter")
    parser.add_argument('--config', type=str, default="./config.json", help="The path of config file")
    parser.add_argument('--input', type=str, help='Please input data which you want to predict', required=True)
    arguments = parser.parse_args()
    return arguments


if __name__ == '__main__':
    arguments = parse_args()
    print(arguments.config)
    models = []
    with open(arguments.config, encoding='utf-8', mode='r') as f:
        models = json.load(f)
    model_path = models['model_path']
    print(model_path)
    print('hellow mlflow')
