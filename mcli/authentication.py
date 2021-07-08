import json
import os
import uuid
import warnings
from dataclasses import asdict, dataclass
from enum import IntEnum, auto

import aiohttp

try:
    import keyring
except ImportError:
    keyring = None  # keyring is not available


class StoreStrategy(IntEnum):
    keyring = auto()
    memory = auto()
    disk = auto()
    none = auto()
    auto = auto()
    default = auto


@dataclass
class User:
    login: str
    name: str
    id: str


class Authentication:
    BASE_URL = 'https://authserver.mojang.com'
    SESSION_URL = 'https://sessionserver.mojang.com'
    SERVICE = 'mcli.session'

    def __init__(self, client_token: str = None, strategy: StoreStrategy = StoreStrategy.auto):
        if client_token is None:
            client_token = str(uuid.uuid4())

        if strategy == StoreStrategy.keyring and keyring is None:
            warnings.warn(
                "keyring module is not available, falling back to the default strategy. "
                "Install keyring module with `pip install keyring`.", Warning, stacklevel=2
            )
            strategy = StoreStrategy.default

        if strategy == StoreStrategy.auto:
            strategy = StoreStrategy.disk if keyring is None else StoreStrategy.keyring

        self.strategy: StoreStrategy = strategy
        self.client_token: str = client_token
        self.access_token: str = None
        self.user: User = None

    def load(self, login: str) -> bool:
        """Load saved tokens from the store strategy and return True if it has successfully loaded the data."""
        data = None
        if self.strategy == StoreStrategy.keyring:
            data = keyring.get_password(self.SERVICE, login)
        elif self.strategy == StoreStrategy.disk and os.path.isfile(f'{self.SERVICE}.json'):
            with open(f'{self.SERVICE}.json', 'r') as f:
                data = json.load(f).get(login)

        if isinstance(data, str):
            data = json.loads(data)

        if data is None or data == {} or not all(field in data for field in ('client', 'access', 'user')):
            return False

        self.client_token = data['client']
        self.access_token = data['access']
        self.user = User(**data['user'])

        return True

    def save(self):
        """Save the tokens and user data."""
        data = dict(client=self.client_token, access=self.access_token, user=asdict(self.user))

        if self.strategy == StoreStrategy.keyring:
            keyring.set_password(self.SERVICE, self.user.login, json.dumps(data))

        elif self.strategy == StoreStrategy.disk:
            data = {self.user.login: data}
            filename = f'{self.SERVICE}.json'

            if os.path.isfile(filename):
                with open(filename, 'r') as f:
                    try:
                        data = json.load(f)
                    except Exception:
                        pass

            with open(filename, 'w') as f:
                json.dump(data, f)

        elif self.strategy == StoreStrategy.none:
            self.client_token = None
            self.access_token = None
            self.user = None

    def clear(self, login: str):
        """Removes the saved tokens and user data."""
        if self.strategy == StoreStrategy.keyring:
            keyring.delete_password(self.SERVICE, login)

        elif self.strategy == StoreStrategy.disk:
            filename = f'{self.SERVICE}.json'

            if os.path.isfile(filename):
                with open(filename, 'r') as f:
                    try:
                        data = json.load(f)
                        data.pop(login)
                    except Exception:
                        pass

            with open(filename, 'w') as f:
                json.dump(data, f)

    async def authenticate(self, login: str, password: str, invalidate: bool = False, save: bool = True):
        """Authenticate to the mojang servers."""
        payload = {
            "agent": {
                "name": "Minecraft",
                "version": 1
            },
            "username": login,
            "password": password,
            "requestUser": True
        }

        if not invalidate:
            payload["clientToken"] = self.client_token

        async with aiohttp.ClientSession() as session:
            async with session.post(f'{self.BASE_URL}/authenticate', json=payload) as r:
                result = await r.json()
                if 'error' in result:
                    raise type(result['error'], (Exception,), {})(result['errorMessage'])

                self.user = User(login, **result['selectedProfile'])
                self.client_token = result['clientToken']
                self.access_token = result['accessToken']

                if save and self.strategy != StoreStrategy.none:
                    self.save()

    async def refresh(self, save: bool = True):
        """Refresh the access token to keep it valid longer."""
        if self.access_token is None or self.client_token is None:
            raise ValueError("Invalid access or client token.")

        payload = {
            "accessToken": self.access_token,
            "clientToken": self.client_token
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(f'{self.BASE_URL}/refresh', json=payload) as r:
                result = await r.json()
                if 'error' in result:
                    raise type(result['error'], (Exception,), {})(result['errorMessage'])

                self.user = User(self.user.login, **result['selectedProfile'])
                self.client_token = result['clientToken']
                self.access_token = result['accessToken']

                if save and self.strategy != StoreStrategy.none:
                    self.save()

    async def validate(self) -> bool:
        """Check if the access token is still valid. Return True upon success."""
        if self.access_token is None or self.client_token is None:
            raise ValueError("Invalid access or client token.")

        payload = {
            "accessToken": self.access_token,
            "clientToken": self.client_token
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(f'{self.BASE_URL}/validate', json=payload) as r:
                return r.status == 204

    async def invalidate(self) -> bool:
        """Invalidate the access token."""
        if self.access_token is None or self.client_token is None:
            raise ValueError("Invalid access or client token.")

        payload = {
            "accessToken": self.access_token,
            "clientToken": self.client_token
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(f'{self.BASE_URL}/invalidate', json=payload) as r:
                result = await r.text()

                if result != '':
                    result = json.loads(result)
                    raise type(result['error'], (Exception,), {})(result['errorMessage'])

    async def signout(self, login: str, password: str):
        """Invalidate any access token associated with this account."""
        payload = {
            "username": login,
            "password": password
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(f'{self.BASE_URL}/signout', json=payload) as r:
                result = await r.text()

                if result != '':
                    result = json.loads(result)
                    raise type(result['error'], (Exception,), {})(result['errorMessage'])

    async def join(self, serverid: str) -> bool:
        """Request to join a server. Return True upon success."""
        if self.access_token is None or self.user is None:
            raise ValueError("Invalid access token or user is not set.")

        payload = {
            "accessToken": self.access_token,
            "selectedProfile": self.user.id,
            "serverId": serverid
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(f'{self.SESSION_URL}/session/minecraft/join', json=payload) as r:
                return r.status == 204
