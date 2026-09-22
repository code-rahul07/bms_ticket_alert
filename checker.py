
import json
import os
import requests
from bs4 import BeautifulSoup

URL="https://in.bookmyshow.com/movies/hyderabad/the-paradise/buytickets/ET00518274/20260924?etCodes=*&language=telugu&refEventCode=ET00518274"

TOKEN=os.environ["TELEGRAM_BOT_TOKEN"]
CHAT=os.environ["TELEGRAM_CHAT_ID"]

def send(msg):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id":CHAT,"text":msg}
    )

def load():
    with open("last_seen.json") as f:
        return json.load(f)

def save(data):
    with open("last_seen.json","w") as f:
        json.dump(data,f)

html=requests.get(URL,headers={"User-Agent":"Mozilla/5.0"}).text
soup=BeautifulSoup(html,"html.parser")

text=soup.get_text(" ",strip=True)

matches=[]

# very simple parser
# if BookMyShow changes layout this is easy to update.

import re

times=re.findall(r"([0-9]{1,2}:[0-9]{2}\s?(?:AM|PM))",text,re.I)

for t in times:
    x=t.upper().replace(" ","")

    if "AM" in x:
        hour=int(x.split(":")[0])

        # before 8 AM
        if hour<8:
            matches.append(("24 Sep",t))

# 23 Sept page text
if "23 Sep" in text or "23 September" in text:
    matches.append(("23 Sep","Available"))

state=load()

new=[]

for m in matches:
    key=f"{m[0]}-{m[1]}"
    if key not in state["shows"]:
        state["shows"].append(key)
        new.append(m)

if new:

    msg="🎟 Paradise Ticket Alert\n\n"

    for d,t in new:
        msg+=f"{d} • {t}\n"

    msg+="\nOpen BookMyShow now."

    send(msg)

save(state)
