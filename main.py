import discord
import os
from urllib.parse import quote
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

client = discord.Client()

METACRITIC_BASE_URL = 'https://www.metacritic.com'

RECOGNIZED_CONSOLE_NAMES = {
    'game-boy',
    'gameboy-advance',
    'game-cube',
    'nintendo-64',
    'pc',
    'playstation',
    'playstation-2',
    'playstation-3',
    'playstation-4',
    'playstation-5',
    'switch',
    'xbox',
    'xbox-360',
    'xbox-one',
    'xbox-series-x'
}


class Message:
    def __init__(self, content):
        self.content = content


class Game:
    def __init__(self, name, url):
        self.name = name
        self.url = url

def fetch(url):
    user_agent = 'Mozilla/5.0'
    referrer = 'None'
    req = Request(url)
    req.add_header('User-Agent', user_agent)
    req.add_header('Referrer', referrer)
    return urlopen(req)

def fetch_games(console_name, game_name):
    game_name = quote(game_name.replace('/', ''))
    response = fetch(f'{METACRITIC_BASE_URL}/search/game/{game_name}/results')
    html_contents = response.read()
    soup = BeautifulSoup(html_contents, 'html.parser')
    products_html = soup.find_all("h3", {"class": "product_title"})

    def map_to_game(product_html):
        anchor = product_html.find("a")
        return Game(anchor.get_text().strip(), anchor["href"])

    return list(map(map_to_game, products_html))


def find_exact_match(games, game_name):
    if len(games) == 1:
        return games[0]

    for game in games:
        if game.name == game_name:
            return game

    return None


def get_proposals_message(games):
    if len(games) == 0:
        return "No games found :'("

    game_names = ',\n'.join([game.name for game in games])
    return f'Which one exactly?\n{game_names}'

def sanitize_rating(tag):
    if tag is None:
        return 'N/A'

    return tag.get_text()


def get_num_critic_and_user_reviews(game, soup):
    count_tags = soup.findAll('span', attrs={'class': 'count'})
    num_critic_reviews = 'N/A'
    num_user_reviews = 'N/A'
    for count_tag in count_tags:
        if num_critic_reviews != 'N/A' and num_user_reviews != 'N/A':
            break

        if num_critic_reviews == 'N/A':
            critic_review_anchor = count_tag.find('a', attrs={'href': f'{game.url}/critic-reviews'})
            if critic_review_anchor is not None:
                critic_review_count_span = critic_review_anchor.find('span')
                if critic_review_count_span is not None:
                    num_critic_reviews = critic_review_count_span.get_text().strip()

        if num_user_reviews == 'N/A':
            user_review_anchor = count_tag.find('a', attrs={'href': f'{game.url}/user-reviews'})
            if user_review_anchor is not None:
                num_user_reviews = user_review_anchor.get_text().strip().split(' ')[0]

    return num_critic_reviews, num_user_reviews


def fetch_game_details(game):
    response = fetch(f'{METACRITIC_BASE_URL}{game.url}')
    html_contents = response.read()
    soup = BeautifulSoup(html_contents, 'html.parser')
    metacritic_rating = sanitize_rating(soup.find(attrs={'itemprop': 'ratingValue'}))
    user_rating = sanitize_rating(soup.select_one('div.metascore_w.user.large'))
    num_critic_reviews, num_user_reviews = get_num_critic_and_user_reviews(game, soup)
    return f"""
Metacritic Rating: {metacritic_rating}
Number of Critic Reviews: {num_critic_reviews}
User Rating: {user_rating}
Number of User Reviews: {num_user_reviews}
"""


def sanitize_console_name(console_name):
    stripped_name = console_name.strip()
    if stripped_name not in RECOGNIZED_CONSOLE_NAMES:
        return None
    return stripped_name


def sanitize_game_name(game_name):
    return game_name.strip()


def get_message_to_send(raw_console_name, game_name):
    console_name = sanitize_console_name(raw_console_name)
    if (console_name is None):
        return f'Unrecognized console name ({raw_console_name}), recognized names {RECOGNIZED_CONSOLE_NAMES}'

    game_name = sanitize_game_name(game_name)
    games = fetch_games(console_name, game_name)
    exact_match = find_exact_match(games, game_name)
    if exact_match is None:
        return get_proposals_message(games)

    return fetch_game_details(exact_match)


def calculate_reply(message):
    try:
        command, console_name, game_name = message.content.split(' ', 2)
        return get_message_to_send(console_name, game_name)
    except:
        return """
        Will provide some metacritic info for the game.
        How to use:

        ex. !metabot <console> <name>

        Should an exact match not be found, we'll provide a list of options,
        run the command again with one of those options.
        """


def should_respond(message):
    if message.author == client.user:
        return False

    if message.content.startswith('!metabot'):
        return True


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))


@client.event
async def on_message(message):
    print('Received message {0}'.format(message))
    if not should_respond(message):
        return

    message_to_send = calculate_reply(message)
    return await message.channel.send(message_to_send)


if __name__ == '__main__':
    # message = Message('!metabot')
    # message_to_send = calculate_reply(message)
    # print(message_to_send)
    client.run(os.environ['TOKEN'])
