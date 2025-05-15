import json

async def load_history(redis_client , session_id) : 

    # ! ----------------------------only for dev----------------------------

    # with open('assets/history/chat.json') as chat_file : history = json.load(chat_file)

    # if session_id in history : return history[session_id]
    # else : return []

    # ! --------------------------------------------------------

    messages = redis_client.get(session_id)
    if messages : return json.loads(messages)
    return []

async def save_history(redis_client , row , session_id) : 

    # ! ----------------------------only for Dev----------------------------

    # with open('assets/history/chat.json') as chat_file : history = json.load(chat_file)

    # history[session_id] = row 

    # with open('assets/history/chat.json' , 'w') as chat_file : json.dump(history , chat_file)

    # ! --------------------------------------------------------

    redis_client.set(session_id , json.dumps(row))