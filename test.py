import re
import subprocess
import sys

import test2

#
#
# text = '<div class="layout-art review-features"><h3 class="layout-art-tit">Features</h3><h4>小标题</h4><p>普通段落...</p ></div><div class="layout-art review-tips"><h3 class="layout-art-tit">Tips</h3><h4>小标题</h4><p>普通段落...</p ></div><div class="layout-art review-pac"><h3 class="layout-art-tit">Pros &amp; Cons</h3><ul class="prco-pr"><li class="prco-pr-li">优点</li></ul><ul class="prco-pr"><li class="prco-co-li">缺点</li></ul></div><div class="layout-art review-faq"><h3 class="layout-art-tit">FAQ</h3></div><h4 class="review-faq-q">问题</h4><div class="review-faq-answer"><ul><li>无序列表子项</li><li>无序列表子项</li></ul></div><div class="layout-art review-增加大标题"><h3 class="layout-art-tit">增加大标题</h3><ol><li class="review-ol-li">有序列表子项</li><li class="review-ol-li">有序列表子项</li></ol></div></div>'
#
#
# pattern = re.compile("<li[\S\s]*class[\S\s]*=[\S\s]*layout-art-tit[\S\s]*>([\S\s]*?)<[\S\s]*/li[\S\s]*>")
# print(pattern.findall(text))

if __name__ == '__main__':
    p = subprocess.Popen('python test2.py', shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    print(type(p))
    p2 = subprocess.Popen()
    while True:
        line = input()
        p.stdin.write(bytes(line + '\n', 'utf-8'))
        p.stdin.flush()
        output = p.stdout.readline()
        sys.stdout.write(str(output, 'utf-8'))
        sys.stdout.flush()
