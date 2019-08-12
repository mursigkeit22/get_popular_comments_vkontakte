import time
import requests
import smtplib, ssl
from yaml import load
from datetime import timedelta

with open('config.yaml', 'r') as f:
    config = load(f)
token = config['access_token']  # your token
group_id = config['group_id']  # vkontakte group ID
password = config['mail_password']

period = 7  # number of days you need comments for
current_machine_time = time.time()
day_delta = timedelta(days=period)
day_delta_seconds = day_delta.total_seconds()
stop_machine = current_machine_time - day_delta_seconds


def get_inner_comments(post_id, comment_id):
    url = 'https://api.vk.com/method/wall.getComments'
    params = {
        'owner_id': group_id,
        'post_id': post_id,
        'need_likes': 1,
        'comment_id': comment_id,
        'access_token': token,
        'v': 5.92}
    info = requests.get(url, params=params).json()['response']['items']
    return info


# create dictionary with comments info
def many_comments_for_one_post(comments_dict, post_id):
    url = 'https://api.vk.com/method/wall.getComments'
    count = 100
    offset = 0
    flag = True
    while flag:
        params = {
            'owner_id': group_id,
            'post_id': post_id,
            'need_likes': 1,
            'preview_length': 0,
            'count': count,
            'offset': offset,
            'access_token': token,
            'v': 5.92}
        data = requests.get(url, params=params).json()['response']['items']
        if len(data) == 0:
            flag = False
        for item in data:
            if 'deleted' in item:
                continue
            id_com = item['id']
            comments_dict[id_com] = [item['likes']['count'], post_id, 0]
            if item['thread']['count'] > 0:
                data_lev1 = get_inner_comments(post_id, id_com)
                for el in data_lev1:
                    id_com_lev1 = el['id']
                    comments_dict[id_com_lev1] = [el['likes']['count'], post_id, id_com]
        offset += count
    return comments_dict  # { ID comment: [likes count, ID post, ID thread]}


def get_post_id(post_count, post_dict, last_post):
    for record in post_count:
        if record['date'] < stop_machine:
            break
        post_id = record['id']
        post_dict[post_id] = record['date']
        last_post = (time.ctime(record['date']), post_id)
    return post_dict, last_post


comments_dict = {}
last_post = ()
post_number = 0
count = 100
offset = 0
flag = True
flag_pinned = True  # get rid of first post
while flag:  # while posts are not too old
    params = {
        'owner_id': group_id,
        'filter': 'owner',
        'count': count,
        'offset': offset,
        'access_token': token,
        'v': 5.92}
    offset += count
    if flag_pinned:
        post_count = requests.get('https://api.vk.com/method/wall.get', params=params).json()['response']['items'][1:]
        flag_pinned = False
    else:
        post_count = requests.get('https://api.vk.com/method/wall.get', params=params).json()['response']['items']
    if post_count[0]['date'] < stop_machine:
        flag = False
        break

    for post_id in get_post_id(post_count, {}, last_post)[0]:
        post_number += 1
        many_comments_for_one_post(comments_dict, post_id)
    last_post = get_post_id(post_count, {}, last_post)[1]  # the earliest post
mes1 = '20 most popular comments for the last ' + str(period) + " days"
mes2 = 'Number of posts: ' + str(post_number)
mes3 = 'Number of comments: ' + str(len(comments_dict))
mes4 = 'The earliest post (date, id): ' + str(last_post)
popular_comments = sorted(comments_dict.items(), key=lambda x: x[1], reverse=True)[
                   0:21]  # change number of comments you need here

links = []
for el in popular_comments:
    thread = el[1][-1]
    post_id = el[1][-2]
    comment_id = el[0]
    temp_link = ''
    if el[1][-1] != 0:
        temp_link = 'https://vk.com/wall-98492689_' + str(post_id) + '?reply=' + str(comment_id) + '&thread=' + str(
            thread)
    else:
        temp_link = 'https://vk.com/wall-98492689_' + str(post_id) + '?reply=' + str(comment_id)
    links.append(temp_link)
links = '\n'.join(links)
print(links)

port = 465  # For SSL
smtp_server = "smtp.gmail.com"
sender_email = ""  # Enter your address
receiver_email = [""]  # Enter receiver address
password = password
message = """\
Subject: the most popular comments""" + '\n' + \
          mes1 + '\n' + mes2 + '\n' + mes3 + '\n' + mes4 + '\n' + str(links)

context = ssl.create_default_context()
with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
    server.login(sender_email, password)
    server.sendmail(sender_email, receiver_email, message)
