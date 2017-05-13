import praw
import sqlite3
from datetime import datetime
import pytz

import thirdegree_praw_login as t  # testing purposes


class Zombie(object):
    def __init__(self):
        self.reddit = t.login()
        """
        self.reddit = praw.Reddit(client_id="",
                                  client_secret="",
                                  user_agent="Zombie Attack by u/thirdegree",
                                  username="",
                                  password="",)
        """

        self.conn = sqlite3.connect('zombies.db')
        with self.conn:
            self.conn.execute("CREATE TABLE IF NOT EXISTS zombies (seen date, banned boolean, thingid text, author text)")

        self.subreddit = self.reddit.subreddit("Zombies_Attack")
        self.keywords = None
        self.mods = None

    @property
    def wiki(self):  # works
        if not self.keywords:  # if it's just starting up
            self.keywords = self.subreddit.wiki['keywords'].content_md.split(',')
            self.keywords = list(map(str.lower, self.keywords))
        elif datetime.today().weekday() == 0:  # if it's monday
            self.keywords = self.subreddit.wiki['keywords'].content_md.split(',')
            self.keywords = list(map(str.lower, self.keywords))
        return self.keywords

    @property
    def is_active(self):  # works
        return (datetime.now().replace(tzinfo=pytz.timezone('US/Pacific')).hour > 19 or
                datetime.now().replace(tzinfo=pytz.timezone('US/Pacific')).hour < 7)  # after 7pm or before 7am

    def unban_banned(self):  # works
        with self.conn as conn:
            # select users banned a day or more ago
            c = conn.execute("SELECT author FROM zombies WHERE banned=1 AND date(seen) < date('now', '-1 day')")
            names = c.fetchall()
        for n in names:
            # Unban them
            self.subreddit.banned.remove(n[0])
            with self.conn as conn:
                # tell the database you've unbanned them
                conn.execute("UPDATE zombies SET banned=0 WHERE author=?", n)

    def mark(self, thing, ban=False):  # works
        author = thing.author.name
        now = datetime.now().replace(tzinfo=pytz.timezone('US/Pacific'))
        with self.conn as conn:
            conn.execute("INSERT INTO zombies (seen, banned, thingid, author) VALUES (?, ?, ?, ?)",
                         (now, ban, thing.fullname, author))

    def is_seen(self, thing):  # works
        with self.conn as conn:
            c = conn.execute("SELECT 1 FROM zombies WHERE thingid=? LIMIT 1", (thing.fullname,))
            fetched = c.fetchone()
        return bool(fetched)

    def ban(self, thing):  # works
        if not thing.author:
            return
        self.subreddit.banned.add(thing.author)

    def by_mod(self, thing):
        if not self.mods:
            self.mods = list(self.subreddit.moderator())
        return thing.author in self.mods

    def check_thing(self, thing):  # works
        if self.by_mod(thing):  # so that it won't try to ban mods
            self.mark(thing)
        elif self.is_active:
            if isinstance(thing, praw.models.Submission):  # if it's a submission
                tocheck = thing.selftext + " " + thing.title  # check the body and the title
            else:
                tocheck = thing.body  # if it's a comment, check the body

            if any(i in tocheck.lower() for i in self.wiki):  # if any of the keywords match a word in the body
                self.ban(thing)
                self.mark(thing, True)
            else:
                self.mark(thing)
        else:
            self.mark(thing)

    def scan_subbie(self):  # works
        self.unban_banned()
        for post in self.subreddit.new():
            if self.is_seen(post):
                continue
            else:
                self.check_thing(post)
        for comment in self.subreddit.comment():
            if self.is_seen(comment):
                continue
            else:
                self.check_thing(comment)

    def main(self):  # works
        while True:
            try:
                self.scan_subbie()
            except Exception:
                continue


if __name__ == '__main__':
    z = Zombie()
    z.main()
