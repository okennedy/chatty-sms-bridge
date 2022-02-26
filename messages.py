from sqlalchemy import create_engine  # type: ignore[import]
from sqlalchemy import Table, Column, MetaData, Integer, String
from sqlalchemy import and_
from sqlalchemy.sql import select  # type: ignore[import]

metadata = MetaData()

Accounts = Table('accounts', metadata, 
                 Column('id', Integer), 
                 Column('user_id', Integer), 
                 Column('password', String),
                 Column('enabled', Integer), 
                 Column('protocol', Integer))

Users = Table('users', metadata,
              Column('id', Integer),
              Column('username', String),
              Column('alias', String),
              Column('avatar_id', Integer),
              Column('type', Integer))

Messages = Table('messages', metadata,
                 Column('id', Integer),
                 Column('uid', String), 
                 Column('thread_id', Integer),
                 Column('sender_id', Integer), 
                 Column('user_alias', String), 
                 Column('body', String), 
                 Column('body_type', Integer),
                 Column('direction', Integer),
                 Column('time', Integer), 
                 Column('status', Integer), 
                 Column('encrypted', Integer),
                 Column('preview_id', Integer))

Threads = Table('threads', metadata,
                Column('id', Integer),
                Column('name', String), 
                Column('alias', String), 
                Column('avatar_id', Integer), 
                Column('account_id', Integer), 
                Column('type', Integer), 
                Column('encrypted', Integer), 
                Column('last_read_id', Integer), 
                Column('visibility', Integer))

chatty_engine = create_engine('sqlite:////home/mobian/.purple/chatty/db/chatty-history.db')
chatty_connection = chatty_engine.connect()


class Message:
    def __init__(self, row):
        self.id           = row[0]  # noqa: E221
        self.thread_id    = row[1]  # noqa: E221
        self.thread_name  = row[2]  # noqa: E221
        self.thread_alias = row[3]  # noqa: E221
        self.sender       = row[4]  # noqa: E221
        self.text         = row[5]  # noqa: E221
        self.direction    = row[6]  # noqa: E221

    @property
    def direction_symbol(self):
        return "←" if self.direction < 0 else "→"

    def __repr__(self):
        return "{} [{}; {}] {} {}".format(self.sender, self.thread_name, self.thread_id,
          self.direction_symbol, self.text)


def lookup_sms_messages(since=-1):
    query = (
      select(Messages.c.id, 
             Threads.c.id,
             Threads.c.name,
             Users.c.alias, 
             Threads.c.alias, 
             Messages.c.body,
             Messages.c.direction,
             Accounts.c.id)
      .where(and_(
            Messages.c.id > since,
            Threads.c.account_id == Accounts.c.id,
            Messages.c.sender_id == Users.c.id,
            Messages.c.thread_id == Threads.c.id,
            Accounts.c.protocol == 1,
      ))
      .order_by(Messages.c.id)
    )
    return [
        Message(row)
        for row in chatty_connection.execute(query)
    ]


# for message in lookup_sms_messages():
#    print(message)
