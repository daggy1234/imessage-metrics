import json
from datetime import datetime
from collections import Counter
import pandas as pd
import matplotlib

from typing import ItemsView
import matplotlib.pyplot as plt

with open("messages.json","r") as file:
	data = json.loads(file.read())


my_text = []
texting_times = []
people_i_text = []
people_text_me = []
group_chats = []
text_timing = []
sending = 0
recieving = 0

for item in data["messages"]:

	if item["is_from_me"]:
		text_timing.append(pd.Timestamp(item['date']).floor('min').time())
		
		sending += 1
		my_text.append(item["body"])
		if item["group_chat_name"] == "":
			people_i_text.append(item["phone_number"])
		else:
			group_chats.append(item["group_chat_name"])


	else:
		recieving += 1
		if item["group_chat_name"] == "":
			people_text_me.append(item["phone_number"])
		else:
			group_chats.append(item["group_chat_name"])

#TOp WORDS
top = Counter(my_text).most_common(20)
for i,itm in enumerate(top):
	print(f"{i}: {itm[0]}  - {itm[1]}")

#Top people I text
top = Counter(people_i_text).most_common(20)
for i,itm in enumerate(top):
	print(f"{i}: {itm[0]}  - {itm[1]}")

#Top people that text me
top = Counter(people_text_me).most_common(20)
for i,itm in enumerate(top):
	print(f"{i}: {itm[0]}  - {itm[1]}")

#Top GC by volume
top = Counter(group_chats).most_common(20)
for i,itm in enumerate(top):
	print(f"{i}: {itm[0]}  - {itm[1]}")



# ANANLYSIS
# Sent Vs Recieve
# Use sending vs recieving counters
# 

# get dictionary of times
top: ItemsView[datetime, int] = Counter(text_timing).items()
df = pd.DataFrame.from_dict(top)
df = df.rename(columns={0: "Time", 1: "Count"})
my_day = datetime.now().date()
df['Time'] = [datetime.combine(my_day, i) for i in df['Time']]
df = df.groupby(pd.Grouper(key='Time', freq='15T')).sum()
df.to_csv("out.csv")
# Ignore plotting just output CSV
plt.plot(df.index, df['Count'])
plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M'))
plt.gca().xaxis.set_major_locator(plt.matplotlib.dates.HourLocator(interval=1))
plt.savefig('text_time.png')
plt.show()
