"""Validated configuration, input records and private output contracts."""
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress, SecretStr, field_validator

class Contract(BaseModel):
    model_config=ConfigDict(extra='forbid',validate_assignment=True)

class RouterConfig(Contract):
    address: IPvAnyAddress
    certificate_sha256: str=Field(pattern=r'^[a-fA-F0-9]{64}$')
    token_file: Path
    username_file: Path|None=None
    password_file: Path|None=None

class Session(Contract):
    authorization: SecretStr
    cookie: SecretStr
    @field_validator('authorization','cookie')
    @classmethod
    def single_line(cls,value):
        raw=value.get_secret_value()
        if not raw or '\r' in raw or '\n' in raw:raise ValueError('invalid session header')
        return value

class RouterRecord(BaseModel):
    model_config=ConfigDict(extra='ignore')
    macAddress: str=Field(pattern=r'^(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$')
    @field_validator('macAddress')
    @classmethod
    def normalize_mac(cls,value):return value.lower()

class LanRecord(RouterRecord):
    hostName: str=Field(default='',max_length=100)
    ipv4Address: str=''
    ipv6Address: str=''

class WirelessRecord(RouterRecord):
    radio: str=Field(default='',max_length=20)

class Device(Contract):
    mac: str
    name: str
    addresses: list[str]
    type: str
    type_evidence: str
    private_mac: bool
    wifi_connected: bool=False
    radio: str|None=None
    dns_queries_24h: int=Field(ge=0)

class HistoryRecord(Contract):
    mac: str
    name: str
    type: str
    first_observed: int=Field(ge=0)
    last_observed: int=Field(ge=0)
    wifi_observations: int=Field(ge=0)

class Inventory(Contract):
    updated: int|None=None
    attempted: int|None=None
    state: Literal['available','unavailable']
    source: str='authenticated router polling'
    devices: list[Device]=Field(default_factory=list)
    history: list[HistoryRecord]=Field(default_factory=list)
    dns_available: bool=False
    error: str|None=None
    note: str='DHCP leases do not establish presence. Types are hostname hints. DNS uses current IP leases and can be misattributed after address reassignment.'

class Credentials(Contract):
    username: Literal['guest']
    password: SecretStr
    @field_validator('password')
    @classmethod
    def nonempty_password(cls,value):
        if not value.get_secret_value():raise ValueError('password is required')
        return value

class LoginResult(BaseModel):
    model_config=ConfigDict(extra='ignore')
    username: Literal['guest']
    token: SecretStr
    userType: Literal['GUEST']
