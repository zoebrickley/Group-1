# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report, ModInterface
import pdb
from utils import * 
from openai import OpenAI

DEFAULT_MSGS = [
    {"role": "system", "content": "You are a content moderation system. Classify each input message based on its level of sextortion content from 0 to 5."},
    {"role": "system", "content": "Sextortion is a criminal act in which one person coerces another into sending sexually explicit photos. The perpetrator then extorts the victim, either for money in financially motivated sextortion or for additional photos, by threatening to release the photos publicly. The perpetrator of sextortion usually manipulates the victim into sending illicit photos by pretending to also be a teenager. We chose to focus on sextortion because it has profound psychological impacts on victims, making it critical to address through dedicated moderation efforts and user education."},
    {"role": "system", "content": "The classification scale ranges from 0 to 5, where: \n0: No sign of sextortion (completely benign messages).\n1-2: Minor threat of sextortion (warning message—Are you sure you’d like to send this message? before the user can send it).\n3-4: Sextortion present but not threatening (block from sending this message, send it to review).\n5: Clear harm and threat (temporarily suspend the user)."},
    {"role": "system", "content": "Examples:\n\nLevel 0: No sign of sextortion (Do nothing)\n- I just saved $100 on my last purchase with a discount code!\n- Hey, how are you doing today?\n- Can you help me with this project?\n- What's your favorite movie?\n- Let's catch up over coffee sometime!\n- My family and I went hiking this weekend. It was so much fun!\n- I visited my grandparents last weekend. It was great catching up with them.\n- We have a big family dinner every Sunday. It's my favorite part of the week.\n\nLevel 1: Mildly inappropriate or suggestive but no explicit threat (Warning message)\n- You have such a radiant smile. You could monetize that.\n- Your family must tell you how gorgeous you are. You should make money from it.\n- That dress looks amazing on you. You could be paid for that look.\n- You’re so photogenic. Do you share these pictures with your family?\n- You look really hot in that picture.\n- I bet you get a lot of attention from people.\n- You should send me more pics like that.\n- Why don't you show a bit more next time?\n\nLevel 2: Inappropriate, implying mild consequences but not explicit (Warning message)\n- Send me more pics, or I might show these to your family.\n- People would pay to see these photos. Send more.\n- If you don’t send a video, you might have to pay me.\n- Don’t make me regret trusting you. Your family wouldn’t like that.\n- Prove you care, or your family might hear about this.\n- If you don’t send more, your family might find out.\n- Your family wouldn’t want these pics to get out. Send more.\n- I need more pics to stay interested. Your family might want to know.\n- If you don’t send more, this might get costly.\n- You should really send me a video, or your family might find out.\n\nLevel 3: Explicitly suggestive, implying a demand with consequences (Block and review)\n- Send me what I want, or I’ll tell your family everything.\n- You better send me more, or your family will find out.\n- If you don’t send a video, I’ll tell your family about these photos.\n- Don’t make me ruin your reputation with your family.\n- Send more pics, or your family will see these.\n- You don’t want your family to know, do you? Send more.\n- If you don’t comply, your family will hear about this.\n- You better do what I say, or your family will know.\n- Send more, or your family will regret knowing you.\n- Don’t force me to tell your family. Send more pics.\n- Send me what I want, or else you'll regret it.\n- You better send me more or there will be serious consequences.\n- If you don't send a video, I'll make sure others see these.\n- Don't make me ruin your reputation online.\n\nLevel 4: Direct demand with implied consequences (Block and review)\n- Send me those pictures now, or I’ll ruin your family relationships.\n- You don’t want your family to see these, do you? Send more now.\n- If you don’t send more, I’ll tell your family everything.\n- Don’t think I won’t share these with your family. Send more.\n- Send what I want, or I’ll post these to your family.\n- You better do as I say, or your family will regret it.\n- If you don’t send a video, your family will see these.\n- I have your family’s contact info. Don’t test me.\n- Send more, or your family will be informed.\n- You don’t want to see what I’ll do. Send more now.\n- Send me those pictures now, or I'll ruin your life.\n- You don't want your family to see these, do you?\n- If you don't send more, I'll make sure everyone knows your secrets.\n- Don't think I won't share these with your friends.\n\nLevel 5: Clear harm and threat, explicit demand with severe consequences (Temporarily suspend user)\n- Send those explicit pics now, or I'll post these everywhere.\n- If you don't send a video, I'll make sure everyone knows your darkest secrets.\n- I have your address, don't test me. Send more now.\n- If you don't comply, I'll ruin your life and make sure everyone sees these.\n- Send those explicit pics now, or I’ll post these to your family.\n- If you don’t send a video, I’ll ruin your family relationships.\n- I have your family’s contact info. Send more now, or else.\n- If you don’t comply, I’ll tell your family everything.\n- Send what I want, or I’ll make sure you regret it financially.\n- You better do as I say, or your family will regret it.\n- If you don’t send more, I’ll destroy your family relationships.\n- Send more, or I’ll make sure your family sees these.\n- You don’t want to see what I’ll do. Send more now.\n- I’ll ruin your family’s reputation if you don’t comply."},
    {"role": "system", "content": "Instructions: Given the message, classify it by returning the appropriate number (0-5) that best matches the level of sextortion content. Your response should only contain one number, and nothing else."},
]


# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']


class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.mod_desk = {}
        self.submitted = {}
        self.user_flow = False
        self.mod_flow = False
        self.gpt = OpenAI(api_key='sk-proj-NylxEynoskZdhKvfablJT3BlbkFJRKadVwlSmYOC4uSi73Jm')

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')

        # Parse the group number out of the bot's name
        match = re.search('[gG]roup (\\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception("Group number not found in bot's name. Name format should be \"Group # Bot\".")

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel
        

    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs). 
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel. 
        '''
        # Ignore messages from the bot 
        if message.author.id == self.user.id:
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)

    async def handle_dm(self, message):
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        if message.content.startswith(Report.MOD_KEYWORD) and not self.user_flow:
            self.mod_flow = True 

        if not self.mod_flow:

            if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD):
                return

            # If we don't currently have an active report for this user, add one
            if author_id not in self.reports:
                self.reports[author_id] = Report(self)
                self.user_flow = True

        if self.user_flow:
    
            # Let the report class handle this message; forward all the messages it returns to uss
            responses = await self.reports[author_id].handle_message(message)
            for r in responses:
                await message.channel.send(r)

            # If the report is complete or cancelled, remove it from our map
            if self.reports[author_id].report_complete():
                if author_id not in self.submitted.keys():
                    self.submitted[author_id] = {1: self.reports[author_id]}
                else:
                    max_report_id = max(self.submitted[author_id].keys())
                    self.submitted[author_id][max_report_id + 1] = self.reports[author_id]
                self.user_flow = False
                self.reports.pop(author_id)

        elif self.mod_flow:

            if author_id not in self.mod_desk:
                self.mod_desk[author_id] = ModInterface(self)
            
            ModInterface.reports = self.submitted

            # Let the report class handle this message; forward all the messages it returns to uss
            responses = await self.mod_desk[author_id].handle_message(message)
            for r in responses:
                await message.channel.send(r)

            if self.mod_desk[author_id].is_complete():
                self.mod_flow = False
                self.mod_desk.pop(author_id)


    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        if not message.channel.name == f'group-{self.group_num}':
            return

        # Forward the message to the mod channel
        mod_channel = self.mod_channels[message.guild.id]
        await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')

        text_rating = self.eval_text(message.content)
        images_present = [file.content_type.startswith("image") for file in message.attachments]
        if any([images_present]):
            image_indices = [index for index, value in enumerate(images_present) if value]
            image_ratings = []
            for idx in image_indices:
                image_ratings.append(self.eval_img(message.attachements[idx].url))
            image_rating = max(image_ratings) 
        else: 
            image_rating = 0
        rating = max(text_rating, image_rating)

        await mod_channel.send(self.code_format(rating))

    
    def eval_text(self, message):
        ''''
        Send code to GPT-4 via API call, receive rating 0-5 and return as
        integer. 
        '''
        response = self.gpt.chat.completions.create(
            model="gpt-4",
            messages = DEFAULT_MSGS + [{"role": "user", "content": message}],
            max_tokens=300,
        )
        return int(response.choices[0].message.content)


    def eval_img(self, image_url):
        ''''
        Send image URL to GPT-4 via API call, receive rating 0-5 and return
        as integer. 
        '''
        messages = DEFAULT_MSGS + [{"role": "user", "content": f"[Image URL: {image_url}]"}]
        response = self.gpt.chat.completions.create(
            model="gpt-4",
            messages=messages,
            max_tokens=300,
        )
        return int(response.choices[0].message.content)
    

    def code_format(self, rating):
        if rating == 0:
            return "Your message has been evaluated and found to be safe."
        elif rating == 1 or rating == 2:
            return ("Warning: Your message has been flagged as potentially containing sextortion. "
                    "Please review your message again.")
        elif rating == 3 or rating == 4:
            return ("Your message has been flagged as containing sextortion. This message will be "
                    "blocked and your account will be reviewed.")
        elif rating == 5:
            return ("Your account has been temporarily suspended and your account will be reviewed.\n"
                    "If you want to appeal this decision, please submit a request.")
        else:
            return "Invalid rating. Please contact support."



client = ModBot()
client.run(discord_token)
