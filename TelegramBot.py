import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from telegram.ext import Updater, CommandHandler
import Parse
import DB
import json
from collections import Counter
import os
import statistics

TOKEN = "<token>"
URL = 'https://www.rbc.ru/story/'
INTERVAL = 3600  # in seconds => every 60 min
NUMBER_CHARACTERISTIC_WORDS = 5
NUMBER_NEWEST_DOCS = 5
SIGMA_KOF = 3
LOW_KOW = 0.05
UP_KOF = 2
UP_BOARD_FOR_OUTPUT = 50
NEW_DOCS_DEFAULT = 3
NEW_TOPICS_DEFAULT = 3


def start(bot, update):
    """
    Отправляет приветствие
    :param bot:
    :param update:
    :return: void
    """
    update.message.reply_text('Hi!')


def help(bot, update):
    """
    Отправляет то, что умеет бот по команде /help
    :param bot:
    :param update:
    :return: void
    """
    text = '''
    new_docs <число N> - показать N самых свежих новостей
    
new_topics <число N> - показать N самых свежих тем

topic <название темы> - показать описание темы и заголовки 5 самых свежих новостей в этой теме

doc <название документа> - показать текст документа с заданным названием

words <название темы> - показать 5 слов, лучше всего характеризующих тему

describe_doc <название документа> - вывести статистику по документу

describe_topic <название темы> - вывести статистику по теме
'''
    update.message.reply_text(text)


def update_news(bot, job):
    """
    Обновление новостей в БД
    :param bot:
    :param job:
    :return: void
    """
    topics = Parse.parse_topics(URL)
    for t in topics:
        Parse.parse_one_doc_to_set_topic_time(t)
    topics = DB.remain_need_to_update_topics(topics)
    topics = Parse.parse_docs(topics)
    DB.update_DB(topics)


def new_docs(bot, update, args):
    """
    Отправляет новейшие документы
    :param bot:
    :param update:
    :param args: количество документов
    :return: void
    """

    try:
        try:
            amount = int(args[0])
        except IndexError:
            amount = NEW_DOCS_DEFAULT
        if amount < 0 or amount > UP_BOARD_FOR_OUTPUT:
            raise ValueError

        res = DB.select_newest_docs(amount)
        for d in res:
            update.message.reply_text(str(d.time) + ' ' + d.name + '\n' + d.link)
    except ValueError:
        update.message.reply_text("Неправильный аргумент")


def new_topics(bot, update, args):
    """
    Отправляет новейшие темы
    :param bot:
    :param update:
    :param args: количество тем
    :return: void
    """
    try:
        try:
            amount = int(args[0])
        except IndexError:
            amount = NEW_TOPICS_DEFAULT
        if amount < 0 or amount > UP_BOARD_FOR_OUTPUT:
            raise ValueError

        res = DB.select_newest_topics(amount)
        for t in res:
            update.message.reply_text(str(t.time) + ' ' + t.name + '\n' + t.link)
    except ValueError:
        update.message.reply_text("Неправильный аргумент")


def topic(bot, update, args):
    """
    Отправляет описание темы и несколько новейших документов из неё
    :param bot:
    :param update:
    :param args: название темы
    :return: void
    """
    topic_name = ' '.join(args)
    tpc = DB.select_topic(topic_name)
    if tpc is not None:
        text = [tpc.description + '\n']
        i = 0
        while i < NUMBER_NEWEST_DOCS and i < len(tpc.documents):
            text.append(tpc.documents[i].name + '\n'
                        + tpc.documents[i].link + '\n')
            i += 1
        update.message.reply_text('\n'.join(text))
    else:
        update.message.reply_text("Нет такой темы")


def doc(bot, update, args):
    """
    Отправляет текст документа
    :param bot:
    :param update:
    :param args: название документа
    :return: void
    """
    doc_name = ' '.join(args)
    dc = DB.select_doc(doc_name)
    if dc is not None:
        update.message.reply_text(dc.paragraphs)
    else:
        update.message.reply_text("Нет такого документа")


def send_photo_to_chat(update, bot, name, kind_of_pic):
    """
    Отправляет фото в чат и затем удаляет его из системы
    :param update:
    :param bot:
    :param name: название фото
    :param kind_of_pic: 'freq' or 'len' добавка к названию
    :return: void
    """
    filename = str(kind_of_pic) + '_pic' + str(name) + '.png'
    bot.send_photo(chat_id=update.message.chat.id, photo=open(filename, 'rb'))
    path = os.path.join(os.path.abspath(os.path.dirname(__file__)), filename)
    os.remove(path)


def create_and_show_graphics(update, bot, name, data_dict, kind_of_graphic):
    """
    Создаёт и отправляет графики в чат
    :param update:
    :param bot:
    :param name: название графиков
    :param data_dict: данные для графиков в виде словаря
    :param kind_of_graphic: 'freq' or 'len' вид данных по которым
    будет строиться график
    :return: void
    """
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

    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.savefig(str(kind_of_graphic) + '_pic' + str(name) + '.png')
    plt.close()
    send_photo_to_chat(update, bot, name, str(kind_of_graphic))


def describe_doc(bot, update, args):
    """
    Отправляет статистику по документу
    :param bot:
    :param update:
    :param args: название документа
    :return: void
    """
    doc_name = ' '.join(args)
    dc = DB.select_doc(doc_name)
    if dc is not None:
        len_stat = json.loads(dc.len_word_frequency)
        freq_stat = json.loads(dc.freq_word_frequency)

        create_and_show_graphics(update, bot, doc_name, len_stat, 'len')
        create_and_show_graphics(update, bot, doc_name, freq_stat, 'freq')
    else:
        update.message.reply_text("Нет такого документа")


def describe_topic(bot, update, args):
    """
    Отправляет статистику по теме
    :param bot:
    :param update:
    :param args: название темы
    :return: void
    """
    topic_name = ' '.join(args)
    tc = DB.select_topic(topic_name)
    if tc is not None:
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
    else:
        update.message.reply_text("Нет такой темы")


def check_for_added_data(prepared_lst, new_s):
    """
    Проверить, есть ли в готовых тегах уже такой же
    или очень похожий
    :param prepared_lst: список готовых тегов
    :param new_s: новый тег
    :return: bool
    """
    for s in prepared_lst:
        if new_s.lower() in s.lower() or s.lower() in new_s.lower():
            return True
    return False


def words(bot, update, args):
    """
    Выводит несколько релевантных слов по теме
    :param bot:
    :param update:
    :param args: название темы
    :return: void
    """
    topic_name = ' '.join(args)
    tpc = DB.select_topic(topic_name)
    if tpc is not None:
        lst_of_tags = []
        for dc in tpc.documents:
            lst_of_tags += [tag.name for tag in dc.tags]
        tpc_tags = Counter(lst_of_tags)
        sorted_tags = sorted(tpc_tags, key=lambda x: tpc_tags[x], reverse=True)

        text = []
        i = 0
        while len(text) < NUMBER_CHARACTERISTIC_WORDS and i < len(sorted_tags):
            if not check_for_added_data(text, sorted_tags[i]):
                text.append(sorted_tags[i])
            i += 1

        update.message.reply_text('\n'.join(text))
    else:
        update.message.reply_text("Нет такой темы")


def add_handler(dispatcher, handler_name, handler_func):
    """
    Устанавливает хэндлеры для команд
    :param dispatcher:
    :param handler_name: название команды
    :param handler_func: функция её исполняющую
    :return: void
    """
    dispatcher.add_handler(CommandHandler(handler_name,
                                          handler_func,
                                          pass_args=True))


def main():
    updater = Updater(TOKEN)

    if not updater.job_queue.get_jobs_by_name('update_news'):
         updater.job_queue.run_repeating(update_news,
                                         interval=INTERVAL,
                                         first=0)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))

    handler_names = ["new_docs", "new_topics", "topic", "doc",
                     "words", "describe_doc", "describe_topic"]
    handler_funcs = [new_docs, new_topics, topic, doc,
                     words, describe_doc, describe_topic]

    for i in range(len(handler_names)):
        add_handler(dp, handler_names[i], handler_funcs[i])

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
