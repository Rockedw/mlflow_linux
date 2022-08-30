# -*- coding: utf-8 -*-
# coding=utf-8
import requests
from flask_cors import CORS
from transformers import AutoModelForQuestionAnswering, AutoTokenizer, pipeline
import csv
from fastapi import FastAPI
from typing import Optional
import json
import argparse
from flask import Flask, request

app = Flask(__name__)
CORS(app, resources=r'/*')

parser = argparse.ArgumentParser(
    description="you should add those parameter")
parser.add_argument('--config', type=str, help="The path of config file")
parser.add_argument('--input', type=str, help='Please input data which you want to predict', required=True)
arguments = parser.parse_args()

print(arguments.config)
with open(arguments.config, encoding='utf-8', mode='r') as f:
    conf = json.load(f)
f.close()
# model_path = models['model_path']
# print(model_path)
# print('hellow mlflow')


# model_path = arguments.model_path


model_names = [
    # 'hfl/chinese-pert-large',
    # 'hfl/chinese-pert-base',
    # 'hfl/chinese-roberta-wwm-ext-large',
    # 'hfl/chinese-roberta-wwm-ext',
    # 'hfl/chinese-bert-wwm-ext',
    # 'hfl/chinese-bert-wwm',
    # 'hfl/rbt3',
    # 'hfl/rbtl3',
    # 'uer/roberta-base-chinese-extractive-qa',
    'luhua/chinese_pretrain_mrc_roberta_wwm_ext_large',
    # 'luhua/chinese_pretrain_mrc_macbert_large',
    # 'wptoux/albert-chinese-large-qa',
    # 'yechen/question-answering-chinese',
    # 'liam168/qa-roberta-base-chinese-extractive'
]

# tokenizer = AutoTokenizer.from_pretrained(
#     "luhua/chinese_pretrain_mrc_roberta_wwm_ext_large")
#
# model = AutoModelForQuestionAnswering.from_pretrained(
#     "luhua/chinese_pretrain_mrc_roberta_wwm_ext_large")

# tokenizer = AutoTokenizer.from_pretrained(
#     model_path['mrc_roberta_wwm_ext_large'])

# model = AutoModelForQuestionAnswering.from_pretrained(
#    model_path['mrc_roberta_wwm_ext_large'])


tokenizer = AutoTokenizer.from_pretrained(conf['model'])

model = AutoModelForQuestionAnswering.from_pretrained(conf['model'])

port = conf['port']

QA = pipeline('question-answering', model=model, tokenizer=tokenizer, device=0)


def question_to_context(question, context):
    parent_dict = QA({'question': question, 'context': context})
    return parent_dict


@app.route('/' + conf['model'], methods=['POST'])
def test():
    context = "我叫小明，今年213213213岁"
    question = request.json('question')
    return question_to_context(question, context)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(conf['port']), debug=True)

