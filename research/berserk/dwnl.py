import asyncio
import json
import aiofiles
import time

from aiohttp import ClientSession
from bs4 import BeautifulSoup
from uuid import uuid4


url = 'https://berserk.ru/?route=lib/feed/cards'


async def make_request(session: ClientSession):
    try:
        resp = await session.request(method="GET", url=url, data=data)
    except Exception as ex:
        print(ex)
        return

    if resp.status == 200:
        image_name = f'{uuid4()}.jpg'
        path = f'async_images/{image_name}'

        async with aiofiles.open(path, 'wb') as f:
            await f.write(await resp.read())


def download_images():
    start = time.time()
    asyncio.run(bulk_request())
    print('{} s'.format(time.time() - start))


async def get_links(session, i):
    data = {
        "saveState": True,
        "state": {"results_per_page": 100, "sort": "name", "order": "ASC", "page": i}
    }
    async with session.post(url, data=json.dumps(data)) as resp:
        content = await resp.json()
    return content['rendered']


async def bulk_request(func, iterator):
    async with ClientSession() as session:
        tasks = []
        for i in iterator:
            tasks.append(
                func(session, i)
            )
        results = await asyncio.gather(*tasks)
        return results


def extract_links(content):
    soup = BeautifulSoup(content, features='html.parser')
    links = []
    for a in soup.find_all('a', href=True):
        links.append(a['href'])
    return links


def get_all_card_links(refresh=False):
    if not refresh:
        with open('/files/projects/DnDGame/research/berserk/links.txt', 'r') as f:
            all_links = f.readlines()
            all_links = list(map(lambda x: x[:-1], all_links))
            return all_links

    contents = asyncio.run(bulk_request(get_links, iterator=range(30)))
    all_links = []
    for cont in contents:
        if not cont:
            continue
        all_links.extend(extract_links(cont))
    with open('/files/projects/DnDGame/research/berserk/links.txt', 'w') as f:
        f.write('\n'.join(set(all_links)))
    return all_links


def drop_stop_symbols(text: str):
    return text.replace('"', '').replace('\n', '').replace('\r', '')

def parse_card_detail(content):
    try:
        soup = BeautifulSoup(content, features='html.parser')
        card = soup.find('section', {'class': 'card'})
        img = card.find('img')['src']
        descr = card.find('div', {'class': 'description'})
        title = descr.find('div', {'class': 'desc-title'})
        sub_title = str(list(title.children)[-1].text)
        title = title.h2.text
        text = descr.find_all('div', {'class': 'col-md-2'})[1]
        text = ''.join(map(lambda x: ' '.join(str(x).split()), text.children))
        text_add = descr.find('div', {'class': 'col-md-4'})
        text_add = ''.join(map(lambda x: ' '.join(str(x).split()), text_add.children))
    except Exception as err:
        print(err)
        img, title, text, text_add, sub_title = [''] * 5
    return {
        'img': drop_stop_symbols(img),
        'title': drop_stop_symbols(title),
        'attributes': drop_stop_symbols(text + '<br>' + text_add),
        'sub_title': drop_stop_symbols(sub_title),
    }



async def get_card_detail(session, link):
    async with session.get(link) as resp:
        content = await resp.content.read()
        return content.decode('utf-8')


def get_all_card_detail(card_links, refresh=False):
    contents = asyncio.run(bulk_request(get_card_detail, iterator=card_links))
    cards_info = []
    for cont in contents:
        cards_info.append(parse_card_detail(cont.encode('utf-8')))

    with open('/files/projects/DnDGame/research/berserk/cards_detail.csv', 'w') as f:
        f.write('"' + '";"'.join(cards_info[0].keys()) + '"\n')
        for card in cards_info:
            try:
                f.write('"' + '";"'.join(card.values()) + '"\n')
            except Exception as err:
                print(err)
                continue
    return cards_info


if __name__ == '__main__':
    links = get_all_card_links(refresh=False)
    card_detail = get_all_card_detail(links, refresh=False)
