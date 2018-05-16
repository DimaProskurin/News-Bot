import urllib.request
import re
import html
from datetime import datetime

AMOUNT_OF_TOPICS_TO_PARSE = 50
AMOUNT_OF_DOCS_TO_PARSE = 50


class Topic:
    def __init__(self, _name, _link, _description):
        self.name = _name
        self.link = _link
        self.description = _description
        self.time = None
        self.docs = []


class Document:
    def __init__(self, _name, _link, _time):
        self.name = _name
        self.link = _link
        self.time = _time
        self.paragraphs = []
        self.tags = []


def date_convert(s):
    if s.__contains__(','):
        '''Вынужденные меры, так как на сервере не хочет менять locale'''
        months_rus = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн',
                      'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']

        months_en = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
                     'jul', 'aug', 'sep', 'oct', 'nov', 'dec']

        for i in range(len(months_rus)):
            s = s.replace(months_rus[i], months_en[i])

        try:
            date = datetime.strptime(s, "%d %b, %H:%M")
            return date.replace(year=2018)
        except ValueError:
            # значит, не 2018 года
            return datetime.strptime(s, "%d %b %Y, %H:%M")
    else:
        # если дата сегодняшняя, то есть только время
        date = datetime.strptime(s, "%H:%M")
        return datetime.today().replace(
            hour=date.hour, minute=date.minute, second=0, microsecond=0)


def get_blocks(html_ans, kind_of):  # topics or docs
    if kind_of == 'topics':
        reg_exp = r'<div class="item item_story js-story-item">(.*?)</div>'
    else:  # docs
        reg_exp = r'<div class="item item_story-single js-story-item">(.*?)</div>'

    blocks = re.findall(reg_exp, html_ans, re.DOTALL)
    return blocks


def get_topic_link(block):
    link = re.findall(
        r'<a href="(.*)" class="item__link no-injects">',
        block, re.DOTALL)[0]
    return link


def get_doc_link(block):
    link = re.findall(
        r'<a href="(.*)" class="item__link no-injects js-yandex-counter">',
        block, re.DOTALL)[0]
    return link


def get_name(block):
    name = re.findall(
        r'<span class="item__title">(.*?)</span>',
        block, re.DOTALL)[0]
    return name


def get_topic_description(block):
    topic_description = re.findall(
        r'<span class="item__text">(.*?)</span>',
        block, re.DOTALL)[0].strip()
    return topic_description


def get_doc_time(block):
    doc_time = re.findall(
        r'<span class="item__info">(.*?)</span>',
        block, re.DOTALL)[0]
    return doc_time


def get_paragraphs(html_ans):
    paragraphs = re.findall(r'<p>(.*?)</p>', html_ans, re.DOTALL)
    paragraphs = [
        html.unescape(re.sub(r'(\<(/?[^>]+)>)', '', item)).strip()
        for item in paragraphs]
    paragraphs = [' '.join(item.split()) for item in paragraphs]
    return paragraphs


def get_tags(html_ans):
    tags = re.findall(
        r'class="article__tags__link">(.*?)</a>',
        html_ans, re.DOTALL)
    return tags


def get_info(blocks, kind_of):  # docs or topics
    output = []
    for block in blocks:
        name = get_name(block)

        if kind_of == 'topics':
            link = get_topic_link(block)
            topic_description = get_topic_description(block)
            topic = Topic(name, link, topic_description)
            output.append(topic)
            if len(output) >= AMOUNT_OF_TOPICS_TO_PARSE:
                break
        else:  # docs
            link = get_doc_link(block)
            doc_time = get_doc_time(block)
            doc = Document(name, link, date_convert(doc_time))
            output.append(doc)
            if len(output) >= AMOUNT_OF_DOCS_TO_PARSE:
                break

    if kind_of == 'topics':
        return output[:-1]  # так как "герои РБК"
    else:
        return output


def parse_topics(url):
    response = urllib.request.urlopen(url)
    html_ans = response.read().decode('utf-8')
    blocks_topics = get_blocks(html_ans, 'topics')
    return get_info(blocks_topics, 'topics')


def parse_docs(topics):
    for tpc in topics:
        response = urllib.request.urlopen(tpc.link)
        html_ans = response.read().decode('utf-8')
        blocks_docs = get_blocks(html_ans, 'docs')
        docs = get_info(blocks_docs, 'docs')

        for doc in docs:
            response = urllib.request.urlopen(doc.link)
            html_ans = response.read().decode('utf-8')

            paragraphs = get_paragraphs(html_ans)
            tags = get_tags(html_ans)
            doc.paragraphs = paragraphs
            doc.tags = tags

        tpc.docs = docs
        tpc.time = tpc.docs[0].time

    return topics


def parse_one_doc_to_set_topic_time(topic):
    response = urllib.request.urlopen(topic.link)
    html_ans = response.read().decode('utf-8')

    blocks_docs = get_blocks(html_ans, 'docs')
    block = blocks_docs[0]
    doc_time = get_doc_time(block)
    topic.time = date_convert(doc_time)
