import sqlite3
import datetime
import json


def extract_body_attributed(attributed_body) -> str:
    if not attributed_body:
        return ""
    attributed_body = attributed_body.decode('utf-8', errors='replace')
    if "NSNumber" in str(attributed_body):
        attributed_body = str(attributed_body).split("NSNumber")[0]
        if "NSString" in attributed_body:
            attributed_body = str(attributed_body).split("NSString")[1]
            if "NSDictionary" in attributed_body:
                attributed_body = str(attributed_body).split("NSDictionary")[0]
                attributed_body = attributed_body[6:-12]
                body = attributed_body
                return body
    return ""

def read_messages(db_location,self_number='Me'):
    conn = sqlite3.connect(db_location)
    cursor = conn.cursor()
    query = """
    SELECT message.ROWID, message.date, message.text, message.attributedBody, handle.id, message.is_from_me, message.cache_roomnames
    FROM message
    LEFT JOIN handle ON message.handle_id = handle.ROWID
    """
    
    cursor.execute("SELECT room_name, display_name FROM chat")
    result_set = cursor.fetchall()
    mapping = {room_name: display_name for room_name, display_name in result_set}
    results = cursor.execute(query).fetchall()

    messages = []
    for result in results:
        rowid, date, text, attributed_body, handle_id, is_from_me, cache_roomname = result
        phone_number = handle_id if handle_id else self_number
        body = text if text else extract_body_attributed(attributed_body)
        date_string = '2001-01-01'
        mod_date = datetime.datetime.strptime(date_string, '%Y-%m-%d')
        unix_timestamp = int(mod_date.timestamp())*1000000000
        new_date = int((date+unix_timestamp)/1000000000)
        date = datetime.datetime.fromtimestamp(new_date).strftime("%Y-%m-%d %H:%M:%S")
        mapped_name = mapping.get(cache_roomname)
        messages.append(
            {"rowid": rowid, "date": date, "body": body, "phone_number": phone_number, "is_from_me": bool(is_from_me),
             "cache_roomname": cache_roomname, 'group_chat_name' : mapped_name})
    conn.close()
    return messages



with open("messages.json","w+") as file:
	file.write(json.dumps({"messages": read_messages("/Users/arnavjindal/Library/messages/chat.db", self_number='Me')}))
