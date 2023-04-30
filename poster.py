import asyncio
import logging
from monstr.client.client import ClientPool
from monstr.event.event import Event
from monstr.encrypt import Keys
from util import ConfigError


def get_args():
    pass


async def main(args):
    relay = 'ws://localhost:8081'

    def do_post(msg: str, keys: Keys=None):
        if keys is None:
            keys = Keys()

        n_evt = Event(kind=Event.KIND_REPUBLISH,
                      content=msg,
                      pub_key=keys.public_key_hex())
        n_evt.sign(keys.private_key_hex())
        cp.publish(n_evt)

    async with ClientPool(clients=relay) as cp:
        do_post('this is a test post to be republished!!!')
        await asyncio.sleep(0.5)


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    try:
        asyncio.run(main(get_args()))
    except ConfigError as ce:
        print(ce)