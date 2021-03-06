import argparse
import csv
import json
import re
from collections import Counter
from opencc import OpenCC
import jieba
import pandas as pd


def add_arguments(parser):
    """Build ArgumentParser."""
    parser.register("type", "bool", lambda v: v.lower() == "true")

    parser.add_argument("--data_file", type=str, default=None, required=True, help="data file to process")
    parser.add_argument("--output_file", type=str, default=None, required=True, help="data file to process")
    parser.add_argument("--vocab_file", type=str, default=None,
                        help="vocab file, needed when data file is training file")
    parser.add_argument("--vocab_size", type=int, default=50000, help='vocab size')
    parser.add_argument("--embedding", type='bool', nargs="?", const=True, default=False,
                        help='whether process embedding file')


def replace_dish(content):
    return re.sub("【.{5,20}】", "<dish>", content)


def normalize_num(words):
    '''Normalize numbers
    for example: 123 -> 100,  3934 -> 3000
    '''
    tokens = []
    for w in words:
        try:
            ww = w
            num = int(float(ww))
            if len(ww) < 2:
                tokens.append(ww)
            else:
                num = int(ww[0]) * (10 ** (len(str(num)) - 1))
                tokens.append(str(num))
        except:
            tokens.append(w)
    return tokens


def tokenize(content):
    content = content.replace("\u0006", '').replace("\u0005", '').replace("\u0007", '')
    tokens = []
    content = content.lower()
    # 去除重复字符
    content = re.sub('~+', '~', content)
    content = re.sub('～+', '～', content)
    content = re.sub('(\n)+', '\n', content)
    for para in content.split('\n'):
        para_tokens = []
        words = list(jieba.cut(para))
        words = normalize_num(words)
        para_tokens.extend(words)
        para_tokens.append('<para>')
        tokens.append(' '.join(para_tokens))
    content = " ".join(tokens)
    content = re.sub('\s+', ' ', content)
    content = re.sub('(<para> )+', '<para> ', content)
    content = re.sub('(- )+', '- ', content)
    content = re.sub('(= )+', '= ', content)
    content = re.sub('(\. )+', '. ', content).strip()
    content = replace_dish(content)
    if content.endswith("<para>"):
        content = content[:-7]
    return content


def create_vocab(data, vocab_file, vocab_size):
    print("# Start to create vocab ...")
    words = Counter()
    for item in data:
        words.update(item['content'].split())
    special_tokens = ['<unk>', '<sos>', '<eos>']
    with open(vocab_file, 'w',encoding='utf-8') as f:
        for w in special_tokens:
            f.write(w + '\n')
        for w, _ in words.most_common(vocab_size - len(special_tokens)):
            f.write(w + '\n')
    print("# Created vocab file {0} with vocab size {1}".format(vocab_file, vocab_size))


def is_CN_char(ch):
    return ch >= u'\u4e00' and ch <= u'\u9fa5'


def cut(string):
    return list(jieba.cut(string))


def get_stopwords(filename = "D:/senior/aiCourse/dataSource/stop_word.txt"):
    stopwords_dic = open(filename, encoding= 'utf-8')
    stopwords = stopwords_dic.readlines()
    stopwords = [w.strip() for w in stopwords]
    stopwords_dic.close()
    return stopwords


def convert2simple(word):
    openCC = OpenCC('tw2sp')
    return openCC.convert(word)


def clean_sentence(sentence):
    stopwords = get_stopwords()
    sentence = ''.join(filter(is_CN_char,sentence))
    sentence = convert2simple(sentence)
    words = [w for w in cut(sentence) if len(w)>0 and w not in stopwords]
    words = ' '.join(words)
    return words


def process_data(output_file, data_file):
    data = []
    with open(output_file, 'w',encoding='utf-8') as f:
        with open(data_file, encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            stopwords = get_stopwords()
            for i, item in enumerate(reader):
                content = tokenize(item['content'].strip()[1:-1])
                item['content'] = clean_sentence(content)
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
                data.append(item)
                if (i + 1) % 10000 == 0:
                    print("# processed -- %d --" % (i + 1))
    return data


def process_embedding(embedding_file, vocab_file, out_embedding_file):
    words = set([line.strip() for line in open(vocab_file,encoding='utf-8')])
    with open(out_embedding_file, 'w',encoding='utf-8') as f:
        for line in open(embedding_file,encoding='utf-8'):
            tokens = line.split()
            # skip the first line
            if len(tokens) == 2:
                continue
            word = tokens[0].lower()
            if word in words:
                f.write(word + ' ' + ' '.join(tokens[1:]) + '\n')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    flags, unparsed = parser.parse_known_args()
    if flags.embedding:
        process_embedding(flags.data_file, flags.vocab_file, flags.output_file)
    else:
        if 'train' in flags.data_file:
            if flags.vocab_file is None:
                raise ValueError("Must provided a vocab file to save vocab")
            data = process_data(flags.output_file, flags.data_file)
            create_vocab(data, flags.vocab_file, flags.vocab_size)
        else:
            process_data(flags.output_file, flags.data_file)