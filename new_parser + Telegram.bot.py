import csv
import os
import shutil
import sqlite3
import requests
import json
import pandas as pd
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, filters

from bs4 import BeautifulSoup


def start_new_proc():
    folder = 'Products'
    if not os.path.exists(folder):
        os.mkdir(folder)
    else:
        shutil.rmtree(folder, ignore_errors=False)
        for File in ['table_all_products.db', 'code.html', 'category.json']:
            if os.path.exists(File):
                os.remove(File)


start_new_proc()

print('Start process')

url = 'https://health-diet.ru/table_calorie/'

headers = {
    'Accept': '*/*',
    'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Mobile Safari/537.36'
}

# We add a path to the headers so that the site perceives us as a user, nort a bot
req = requests.get(url, headers=headers)

list_code = req.text

# Create and save all code informations
with open('code.html', 'w') as file:
    file.write(list_code)

with open('code.html') as file:
    list_code = file.read()
soup = BeautifulSoup(list_code, 'lxml')

prog_groups = soup.find_all(class_='mzr-tc-group-item-href')

#
category = {}
for i in prog_groups:
    i_name = i.text
    i_href = 'https://health-diet.ru' + i.get('href')
    category[i_name] = i_href
    print(i_name)


with open('category.json', 'w') as file:
    json.dump(category, file, indent=4, ensure_ascii=False)

count = 1

with open('category.json') as file_1:
    category = json.load(file_1)
    for key, value in category.items():
        link = requests.get(url=value, headers=headers)
        list_code = link.text
        with open(f'Products/{count}_{key}.html', 'w', encoding='utf-8') as file:
            file.write(list_code)
        with open(f'Products/{count}_{key}.html', encoding='utf-8') as file:
            file.read = file.read()

        soup = BeautifulSoup(list_code, 'lxml')

        head = soup.find(class_='mzr-tc-group-table').find('tr').find_all('th')

        products = head[0].text
        KKal = head[1].text

        with open(f'Products/{count}_{key}.csv', 'w', encoding='utf-8') as file_2:

            writer = csv.writer(file_2)
            writer.writerow((products, KKal))

        products_name = soup.find(class_='mzr-tc-group-table').find('tbody').find_all('tr')

        all_info = {}

        for i in products_name:
            products_td = i.find_all('td')

            title = products_td[0].find('a').text
            KKal = products_td[1].text

            all_info.update({
                title: KKal
            })

            with open(f'Products/{count}_{key}.csv', 'a', encoding='utf-8') as file_2:
                writer = csv.writer(file_2)
                writer.writerow((title,
                                 KKal))
        # write information to our json file
        with open(f'Products/{key}.json', 'a', encoding='utf-8') as file:
            json.dump(all_info, file, indent=4, ensure_ascii=False)

        count += 1
        if count == 39:
            break
        print(39 - count, key)
    print('Process comleted', '\nData collected')

# create new dict only(num\category)for use in TelegramBot
num = [i for i in range(1, 39)]
category_name = []

with open('category.json') as file_1:
    category = json.load(file_1)
    for key, value in category.items():
        category_name.append(key)
num_category = dict(zip(num, category_name))
'''Create new database file and connection'''
with sqlite3.connect('table_all_products.db') as conn:
    c = conn.cursor()
    c.execute('create table if not exists category base(Category, Products, Description)')
    conn.commit()
    '''find all information for out table and fill in our columns'''
    for key, value in num_category.items():

        with open(f'Products/{value}.json', 'r', encoding='utf-8') as file:
            res = json.load(file)
            for pos, prod in res.items():
                c.executemany('incert into category_base VALUES (?, ?, ?)',
                              [(f'{key}', f'{pos}', f'{prod}')
                               ])

    conn.commit()

    print(pd.read_sql_query('SELECT * FROM category_base', conn))

print('The bot is running. Press Ctrl+C to finish')


def on_start(update, context):
    chat = update.effective_chat
    context.bot.send_message(chat_id=chat.id, text=f'Hello, with product do you want to know the calorie content?'
                                                   f'\n\n{num_category}\n\n\n\Press num of category :')


def on_message(update, context):
    chat = update.effective_chat
    text = update.effective_text
    try:

        prod_call = int(text)
        for n, t in num_category.items():
            if n == prod_call:
                with open(f'Products/{t}.json', "r", encoding='utf-8') as file:
                    result = json.load(file)

                for g, j in result.items():
                    answer = f'{g} : {j} in 100 gram'
                    context.bot.send_message(chat_id=chat.id, text=answer)

    except:
        context.bot.send_message(chat_id=chat.id, text=f'What are you interested in - press number of Category?\n\n'
                                                       f'{num_category}\n\n try again check number :')


TOKEN = 'AAH9kQymOL0dg3e86rMZyMzuELhrICwINWU'
bot = telegram.Bot(token=TOKEN)

updater = Updater(TOKEN, use_context=True)

dispather = updater.dispather
dispather.add_handler(CommandHandler('start', on_start))
dispather.add_handler(MessageHandler(filters.all, on_message))

updater.start_polling()
updater.idle()
