import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
from telegram.ext import Updater, CommandHandler
import Parse
import DB
import json
from collections import Counter
import os
import statistics

TOKEN = "579989274:AAEzwSK5zi_HASYfDrzDn1rV3RCfa8OEbYg"
URL = 'https://www.rbc.ru/story/'
INTERVAL = 3600  # in seconds => every 60 min
NUMBER_CHARACTERISTIC_WORDS = 5
NUMBER_NEWEST_DOCS = 5
SIGMA_KOF = 3
LOW_KOW = 0.05
UP_KOF = 2


def start(bot, update):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')


def help(bot, update):
    """Send a message when the command /help is issued."""
    text = '''
    new_docs <N> - показать N самых свежих новостей
new_topics <N> - показать N самых свежих тем
topic <topic_name> - показать описание темы и заголовки 5 самых свежих новостей в этой теме
doc <doc_title> - показать текст документа с заданным заголовком
words <topic_name> - показать 5 слов, лучше всего характеризующих тему
describe_doc <doc_title> - вывести статистику по документу
describe_topic <topic_name> - вывести статистику по теме
'''
    update.message.reply_text(text)


def update_news(bot, job):
    topics = Parse.parse_topics(URL)
    for t in topics:
        Parse.parse_one_doc_to_set_topic_time(t)
    topics = DB.remain_need_to_update_topics(topics)
    topics = Parse.parse_docs(topics)
    DB.update_DB(topics)


def new_docs(bot, update, args):
    """show n newest docs"""
    amount = int(args[0])
    res = DB.select_newest_docs(amount)
    for d in res:
        update.message.reply_text(str(d.time) + ' ' + d.name + '\n' + d.link)


def new_topics(bot, update, args):
    """show n newest topics"""
    amount = int(args[0])
    res = DB.select_newest_topics(amount)
    for t in res:
        update.message.reply_text(str(t.time) + ' ' + t.name + '\n' + t.link)


def topic(bot, update, args):
    """show descrp of topic and NUMBER_NEWEST_DOCS newest docs of topic"""
    topic_name = ' '.join(args)
    tpc = DB.select_topic(topic_name)
    text = [tpc.description + '\n']
    i = 0
    while i < NUMBER_NEWEST_DOCS and i < len(tpc.documents):
        text.append(tpc.documents[i].name + '\n'
                    + tpc.documents[i].link + '\n')
        i += 1
    update.message.reply_text('\n'.join(text))


def doc(bot, update, args):
    """show text of doc"""
    doc_name = ' '.join(args)
    dc = DB.select_doc(doc_name)
    update.message.reply_text(dc.paragraphs)


def send_photo_to_chat(update, bot, name, kind_of_pic):
    filename = str(kind_of_pic) + '_pic' + str(name) + '.png'
    bot.send_photo(chat_id=update.message.chat.id, photo=open(filename, 'rb'))
    path = os.path.join(os.path.abspath(os.path.dirname(__file__)), filename)
    os.remove(path)


def create_and_show_graphics(update, bot, name, data_dict, kind_of_graphic):
    mean = statistics.mean(data_dict.values())
    sigma = statistics.stdev(data_dict.values())

    for_graphic = Counter()
    for key in data_dict:
        if (mean - SIGMA_KOF*sigma) <= data_dict[key] <= (mean + SIGMA_KOF*sigma) \
                and kind_of_graphic == 'len':
            for_graphic[key] = data_dict[key]
        else:
            if (LOW_KOW*mean) <= data_dict[key] <= (UP_KOF*mean):
                for_graphic[key] = data_dict[key]

    plt.bar([int(i) for i in for_graphic],
            list(for_graphic.values()),
            align='center')

    ax = plt.axes()
    ax.set_ylabel('Количество повторений')

    if kind_of_graphic == 'len':
        plt.title('Распределение длин слов')
        ax.set_xlabel('Длина слова')
    else:  # freq
        plt.title('Распределение частот слов')
        ax.set_xlabel('Повторившееся x раз слова')

    plt.savefig(str(kind_of_graphic) + '_pic' + str(name) + '.png')
    plt.close()
    send_photo_to_chat(update, bot, name, str(kind_of_graphic))


def describe_doc(bot, update, args):
    """show doc's statistics"""
    doc_name = ' '.join(args)
    dc = DB.select_doc(doc_name)
    len_stat = json.loads(dc.len_word_frequency)
    freq_stat = json.loads(dc.freq_word_frequency)

    create_and_show_graphics(update, bot, doc_name, len_stat, 'len')
    create_and_show_graphics(update, bot, doc_name, freq_stat, 'freq')


def describe_topic(bot, update, args):
    """show topic's statistics"""
    topic_name = ' '.join(args)
    tc = DB.select_topic(topic_name)
    text = ['Количество документов в теме: ' + str(len(tc.documents))]

    avg_len_doc = 0
    for dc in tc.documents:
        avg_len_doc += len(dc.paragraphs)
    avg_len_doc /= len(tc.documents)
    text.append('Средняя длина документа: ' + str(avg_len_doc))
    update.message.reply_text('\n'.join(text))

    len_stat = json.loads(tc.len_word_frequency)
    freq_stat = json.loads(tc.freq_word_frequency)

    create_and_show_graphics(update, bot, topic_name, len_stat, 'len')
    create_and_show_graphics(update, bot, topic_name, freq_stat, 'freq')


def words(bot, update, args):
    """show NUMBER_CHARACTERISTIC_WORDS most relevant words for topic"""
    topic_name = ' '.join(args)
    tpc = DB.select_topic(topic_name)

    lst_of_tags = []
    for dc in tpc.documents:
        lst_of_tags += [tag.name for tag in dc.tags]
    tpc_tags = Counter(lst_of_tags)
    sorted_tags = sorted(tpc_tags, key=lambda x: tpc_tags[x], reverse=True)

    text = []
    i = 0
    while i < NUMBER_CHARACTERISTIC_WORDS and i < len(sorted_tags):
        text.append(sorted_tags[i])
        i += 1

    update.message.reply_text('\n'.join(text))


def add_handler(dispatcher, handler_name, handler_func):
    dispatcher.add_handler(CommandHandler(handler_name,
                                          handler_func,
                                          pass_args=True))


def main():
    """Start the bot."""
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(TOKEN)

    if not updater.job_queue.get_jobs_by_name('update_news'):
         updater.job_queue.run_repeating(update_news,
                                         interval=INTERVAL,
                                         first=0)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))

    handler_names = ["new_docs", "new_topics", "topic", "doc",
                     "words", "describe_doc", "describe_topic"]
    handler_funcs = [new_docs, new_topics, topic, doc,
                     words, describe_doc, describe_topic]

    for i in range(len(handler_names)):
        add_handler(dp, handler_names[i], handler_funcs[i])

    # Start the Bot
    updater.start_polling()

    updater.idle()


main()
