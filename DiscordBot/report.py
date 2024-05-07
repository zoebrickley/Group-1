from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    STATE1 = auto()
    STATE2 = auto()
    STATE3 = auto()
    STATE4 = auto()
    STATE5 = auto()
    STATE6 = auto()
    STATE7 = auto()
    STATE8 = auto()
    STATE9 = auto()
    STATE10 = auto()
    REPORT_COMPLETE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.data = {}
        self.sextortion = False
    
    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        
        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]
        
        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.STATE1
            return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
                    "Please select the reason for reporting this content:\n" + \
                    "- Spam\n- Offensive content\n- Harassment\n- Imminent danger\n- I'm not sure"]
        
        if self.state == State.STATE1:
            msg = message.content.lower().strip()
            if msg in ["spam", "offensive content", "harassment", "imminent danger"]:
                self.data["abuse type"] = msg
                self.state = State.STATE2
                request = f"Please select the type of {msg}:\n"
                if msg == "spam":
                    return [request + \
                            "- Fraud\n- Impersonation\n- Solicitation\n- I'm not sure"]
                if msg == "offensive content":
                    return [request + \
                            "- Hate Speech\n- Copyright\n- Violence\n- Sexually explicit content\n- I'm not sure"]
                if msg == "harassment":
                    return [request + \
                            "- Bullying\n- Hate speech\n- Unwanted sexual content\n- Blackmail\n- I'm not sure"]
                if msg == "imminent danger":
                    return [request + \
                            "- Credible threat against you or a loved one\n- Suicidal ideation or self harm\n- I'm not sure"]
            if msg in ["i'm not sure", "im not sure", "not sure", "don't know", "dont know"]:
                self.data["abuse type"] = "N/A"
                self.state = State.STATE3
                return ["Do you want to block this user to prevent them from contacting you?"]
            else:
                return ["Sorry, I can't seem to parse your input. Please try again or say `cancel` to cancel."]
        
        if self.state == State.STATE2:
            msg = message.content.lower().strip()
            if self.data["abuse type"] == "spam" and \
            msg in ["fraud", "impersonation", "solicitation"]: 
                self.data["abuse subtype"] = msg
                if msg == "solicitation":
                    self.sextortion = True
            elif self.data["abuse type"] == "offensive content" and \
            msg in ["hate speech", "hatespeech", "copyright", "sexually explicit content", "sexual content"]:
                self.data["abuse subtype"] = msg
                if msg in ["sexually explicit content", "sexual content"]:
                    self.sextortion = True
            elif self.data["abuse type"] == "harassment" and \
            msg in ["bullying", "hate speech", "hatespeech", "unwanted sexual content", "sexual content", "blackmail"]:
                self.data["abuse subtype"] = msg
                if msg in ["unwanted sexual content", "sexual content", "blackmail"]:
                    self.sextortion = True
            elif self.data["abuse type"] == "imminent danger" and \
            any([trigger in msg for trigger in ["credible threat", "threat", "suicidal", "suicide", "self harm", "self-harm"]]):
                self.sextortion = True
                if "threat" in msg:
                    self.data["abuse subtype"] = "credible threat"
                else:
                    self.data["abuse subtype"] = "suicide/self-harm"
            elif msg in ["i'm not sure", "im not sure", "not sure", "don't know", "dont know"]:
                self.data["abuse subtype"] = "N/A"
            else:
                return ["Sorry, I can't seem to parse your input. Please try again or say `cancel` to cancel."]
            self.state = State.STATE3
            return ["Do you want to block this user to prevent them from contacting you?"]
        
        if self.state == State.STATE3:
            msg = message.content.lower().strip()
            if msg in ["yes", "y"]:
                self.data["block"] = True
            elif msg in ["no", "n"]:
                self.data["block"] = False
            else:
                return ["Sorry, I can't seem to parse your input. Please try again or say `cancel` to cancel."]
            if self.sextortion:
                self.state = State.STATE4
                return ["Are you a minor?"]
            else:
                self.state = State.REPORT_COMPLETE 
                return ["Thank you for reporting. Our moderation team will investigate the issue " + \
                        "and determine the appropriate action"]

        if self.state == State.STATE4:
            msg = message.content.lower().strip()
            if msg in ["yes", "y"]:
                self.data["minor"] = True
            elif msg in ["no", "n"]:
                self.data["minor"] = False
            else:
                return ["Sorry, I can't seem to parse your input. Please try again or say `cancel` to cancel."]
            self.state = State.STATE5
            return ["Do you feel an imminent threat of danger?"]

        if self.state == State.STATE5:
            msg = message.content.lower().strip()
            if msg.startswith("yes") or msg == "y":
                if self.data["abuse type"] == "imminent danger":
                    self.state = State.STATE7
                    return ["Thank you for reaching out. " + \
                            "Would you like us to notify the authorities for your safety?"]
                else:
                    self.state = State.STATE6
                    return ["Please select the type of danger:\n" + \
                            "- Credible threat against you or a loved one\n- Suicidal ideation or self harm\n- I'm not sure"]
            elif msg.startswith("no") or "msg" == "n":
                self.data["report to authorities"] = False # initializing for future use
                self.state = State.STATE8
                return ["Have you sent any sexually explicit content?"]
            else:
                return ["Sorry, I can't seem to parse your input. Please try again or say `cancel` to cancel."]

        if self.state == State.STATE6:
            msg = message.content.lower().strip()
            if any([trigger in msg for trigger in ["credible threat", "threat", "suicidal", "suicide", "self harm", "self-harm"]]):
                if "threat" in msg:
                    self.data["danger"] = "credible threat"
                else:
                    self.data["danger"] = "suicide/self-harm"
                self.state = State.STATE7
                return ["Thank you for reaching out. Would you like us to notify the authorities for your safety?"]
            elif msg in ["i'm not sure", "im not sure", "not sure", "don't know", "dont know"]:
                self.data["danger"] = "N/A"
                self.state = State.STATE7
                return ["Thank you for reaching out. Would you like us to notify the authorities for your safety?"]
            else: 
                return ["Sorry, I can't seem to parse your input. Please try again or say `cancel` to cancel."]

        if self.state == State.STATE7:
            msg = message.content.lower().strip()
            if msg in ["yes", "y"]:
                self.data["report to authorities"] = True
            elif msg in ["no", "n"]:
                self.data["report to authorities"] = False
            else:
                return ["Sorry, I can't seem to parse your input. Please try again or say `cancel` to cancel."]
            self.state = State.STATE8
            return ["Have you sent any sexually explicit content?"]

        if self.state == State.STATE8:
            msg = message.content.lower().strip()
            if msg in ["yes", "y"]:
                self.data["sent sexual content"] = True
                self.state = State.STATE9
                return ["Have you been blackmailed and/or told to send money or more explicit content?"]
            elif msg in ["no", "n"]:
                self.data["sent sexual content"] = False
                self.state = State.REPORT_COMPLETE
                return ["Thank you for reporting. Our moderation team will investigate the issue and determine " + \
                        "the appropriate action. In addition, here are resources related to sextortion and " + \
                        "the suicide prevention hotline. You are not alone."]
            else:
                return ["Sorry, I can't seem to parse your input. Please try again or say `cancel` to cancel."]

        if self.state == State.STATE9:
            msg = message.content.lower().strip()
            if msg.startswith("yes") or msg == "y":
                self.state = State.STATE10 
                return ["Please describe."]
            elif msg.startswith("no") or msg == "n":
                self.state = State.REPORT_COMPLETE
                return ["Thank you for reporting. Our moderation team will investigate the issue and determine " + \
                        "the appropriate action. In addition, here are resources related to sextortion and " + \
                        "the suicide prevention hotline. You are not alone."]
            else:
                return ["Sorry, I can't seem to parse your input. Please try again or say `cancel` to cancel."]

        if self.state == State.STATE10:
            self.data["further sextortion details"] = message.content
            self.state = State.REPORT_COMPLETE
            if self.data["minor"]:
                self.data["report to authorities"] = True 
            if self.data["report to authorities"]:
                return ["Thank you for reaching out. Our content moderation team will be reaching out to " + \
                        "authorities to guarantee your safety. We will also determine if the user should " + \
                        "be banned. In addition, here are resources related to sextortion and the suicide " + \
                        "prevention hotline. You are not alone." ]
            else:
                return ["Thank you for reaching out. Our moderation team will determine if the user should " + \
                        "be banned. Here are resources related to sextortion and the suicide prevention hotline. You are not alone."]

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

