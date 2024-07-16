from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer
from c3papplication.conf.springConfig import springConfig
import json
from jproperties import Properties

configs = springConfig().fetch_config()
    
chatbot_greetings=(configs.get("chatbot_greetings")).strip()
chatbot_productinfo=(configs.get("chatbot_productinfo")).strip()   

conversationSettings=[
    chatbot_greetings,
    chatbot_productinfo
    ]

def initialize():
    global bot
    global trainer
    
    bot=ChatBot("C3PBOT")
    trainer=ListTrainer(bot)
   
def loadConversation():
    conversations=[]
    
    for settingFile in conversationSettings:
        with open(settingFile,'r',encoding="utf-8") as file:
            configuredConversation=json.load(file)
            conversations.append(configuredConversation["conversations"])
            file.close()      
    return conversations;      
 
def trainBot(conversations): 
    global trainer
    
    for conversation in conversations:
        for messageResponse in conversation: 
            message=  messageResponse["message"]
            response=  messageResponse["response"]
            print("message:", message,"response:",response)
            for messages in message:
                trainer.train([messages,response])

def train():
    initialize()
    conversations=loadConversation()
    if conversations:
        trainBot(conversations)
            
# if __name__ == "__main__":
#     initialize()
#     conversations=loadConversation()
#     if conversations:
#         trainBot(conversations)
            