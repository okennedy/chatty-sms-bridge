import asyncio
from typing import Dict
from nio import AsyncClient, MatrixRoom, LoginResponse, JoinError, RoomResolveAliasError, RoomInviteError  # type: ignore[import]
import json
from socket import gethostname
import getpass
import sys
from os.path import expanduser
from messages import lookup_sms_messages

CONFIG_FILE = expanduser("~/.config/chatty-sms-bridge.json")

with open(CONFIG_FILE) as f:
  CONFIG = json.load(f)

ROOM_CACHE: Dict[str, MatrixRoom] = {}


async def main(messages) -> None:
  if "device-id" in CONFIG:
    print("Using existing credentials")
    client = AsyncClient("https://" + CONFIG["homeserver"])
    client.access_token = CONFIG["access-token"]
    client.user_id = CONFIG["user-id"]
    client.device_id = CONFIG["device-id"]

  else:
    print("Attempting to log in")
    client = AsyncClient("https://" + CONFIG["homeserver"], CONFIG["bot-user"])
    client.login(getpass.getpass(), device_name=gethostname())
    resp = await client.login(CONFIG["password"])

    if(isinstance(resp, LoginResponse)):
      with open(CONFIG_FILE, "w") as f:
        CONFIG["user-id"] = resp.user_id
        CONFIG["device-id"] = resp.device_id
        CONFIG["access-token"] = resp.access_token
        json.dump(CONFIG, f)
        print("Success!")
    else:
      print("homeserver = \"{}\"; user = \"{}\"".format(CONFIG["homeserver"], CONFIG["bot-user"]))
      print(f"Failed to log in: {resp}")
      sys.exit(1)

  async def get_room(alias):
    alias = "#{}:{}".format(alias, CONFIG["homeserver"])
    resp = await client.room_resolve_alias(alias)
    if isinstance(resp, RoomResolveAliasError):
      print("Unable to resolve: {}".format(alias))
      return None
    else:
      await client.sync()
      return client.rooms[resp.room_id]

  async def invite_if_needed(room):
    await client.sync()
    if CONFIG["recipient"] not in room.users:
      if CONFIG["recipient"] not in room.invited_users:
        resp = await client.room_invite(room.room_id, CONFIG["recipient"])
        if isinstance(resp, RoomInviteError):
          print("Unable to invite {} to bridge message room".format(CONFIG["recipient"]))
          sys.exit(1)
        else:
          print("Invited {} to bridge message room".format(CONFIG["recipient"]))
      else:
        print("{} is already invited to {}".format(CONFIG["recipient"], room.display_name))
    else:
      print("{} is already present in {}".format(CONFIG["recipient"], room.display_name))

  async def get_room_create_and_invite_if_needed(alias, user):
    if alias in ROOM_CACHE:
      return ROOM_CACHE[alias]
    room = await get_room(alias)
    if room is None:
      resp = await client.room_create(
        alias=alias,
        name=user,
        topic=""
      )
      if(isinstance(resp, JoinError)):
        print(f"Failed to join {alias} room: {resp}")
        sys.exit(1)
      else:
        room = await get_room(alias)
        assert(room is not None)
    await invite_if_needed(room)
    ROOM_CACHE[alias] = room
    return room

  # bridge_messages = get_room_create_and_invite_if_needed("sms-bridge")

  async def room_for_thread(thread):
    alias = "sms_{}".format(thread.replace("+", ""))
    return await get_room_create_and_invite_if_needed(alias, thread)

  for message in messages:
    room = await room_for_thread(message.thread_name)
    await client.room_send(
        # Watch out! If you join an old room you'll see lots of old messages
        room_id=room.room_id,
        message_type="m.room.message",
        content={
            "msgtype": "m.text",
            "body": "{}: {}".format(message.direction_symbol, message.text)
        }
    )
    print("Last ID now {}".format(message.id))
    CONFIG["last-id"] = message.id

  client.close()
#     await client.sync_forever(timeout=30000)  # milliseconds

if "last-id" in CONFIG:
  last_id = CONFIG["last-id"]
else:
  last_id = -1

last_id = 52200

messages = lookup_sms_messages(last_id)[:100]
if len(messages) > 0:
  asyncio.get_event_loop().run_until_complete(main(messages))

if "last-id" in CONFIG and CONFIG["last-id"] != last_id:
  with open(CONFIG_FILE, "w") as f:
    json.dump(CONFIG, f)
