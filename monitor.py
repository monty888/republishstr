import asyncio
import logging
import os
from poster import RouterService
from util import ConfigError


def get_args():
    pass


def clear_screen():
    # windows, test system os.system('cls')  # on windows
    # linux
    os.system('clear')

async def main(args):
    relay = 'ws://localhost:8081'
    my_router = RouterService(relays=relay,
                              preferred_peers=None,
                              enable_discovery=True)

    await my_router.start()

    while True:
        clear_screen()
        peers = my_router.republishers
        if not peers['preferred'] and not peers['discovered']:
            print('no peers!')
        else:
            if peers['preferred']:
                print('** Preferred peers **')
                for c_peer in peers['preferred']:
                    print(c_peer)

            if peers['discovered']:
                print('** Discovered peers **')
                for c_peer in peers['discovered']:
                    print(c_peer)
        await asyncio.sleep(1)

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    try:
        asyncio.run(main(get_args()))
    except ConfigError as ce:
        print(ce)