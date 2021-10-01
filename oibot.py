#!/usr/bin/env python3
#
# OIBot - A single-file, easy-to-use XMPP chatbot for NWWS-OI
#
# Copyright 2021 Sanel Kukic
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software
# and associated documentation files (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge, publish, distribute,
# sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished
# to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions
# of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
#
#
# Import required dependencies
#
# slixmpp is used for XMPP management
# json is used to load the configuration file
# xml is used to parse XMPP message stanzas
# ssl is used to specify the TLS version used to connect via XMPP
# signal is used to handle SIGINT and other signals
# sys and os are used for minor housekeeping things
# datetime is used for some minor housekeeping things
# argparse is used to implement commandline arguments
# traceback is used to allow tracebacks to be printed to stdout
# requests is used to make POST requests to the Discord webhook
import json
import slixmpp
from xml.dom import minidom
import ssl
import signal
import sys
import datetime
from argparse import ArgumentParser
import traceback
import requests
import asyncio

# Event handler for SIGINT (user interrupt)
def sigint(sig, frame):
    print("\n\n[i] Disconnecting from NWWS-OI and exiting gracefully...")
    # NWWS specifications say that it is important to disconnect every time you are finished
    # using NWWS, as failing to do so could result in you not being able to log in again since you're already logged in
    xmpp.disconnect()
    sys.exit(0)

# Event handler for SIGTERM (graceful termination)
def sigterm(sig, frame):
    xmpp.disconnect()
    sys.exit(0)


# I would add a handler for SIGKILL but the point of SIGKILL is that you should not handle it
# and it should immediately kill the process, so I won't. I doubt that a handler for SIGKILL
# would even work to be honest lmfao

# Create new class that extends slixmpp.ClientXMPP
class OIBot(slixmpp.ClientXMPP):

    """
    A XMPP bot that reads and prints messages from NWWS-OI, and can send them to a Discord webhook.

    Developed by Sanel Kukic - https://sanelkukic.us.eu.org/projects/oibot
    """

    # Create constructor for this child class
    def __init__(self, jid, password, room, nick):
        # Call parent class's constructor
        super().__init__(jid, password)

        # For convenience purposes, let's assign the values of room and nick
        # to class-wide variables
        self.room = room
        self.nick = nick

        # Create some event handlers for XMPP events
        self.add_event_handler('session_start', self.start)
        self.add_event_handler('groupchat_message', self.message)
        self.add_event_handler('message', self.message)
        self.add_event_handler('connection_failed', self.connection_failed)
        self.add_event_handler('disconnected', self.disconnected)
        self.add_event_handler('connected', self.connected)
        self.add_event_handler('failed_auth', self.failed_auth)
        self.add_event_handler('session_end', self.session_end)
        self.add_event_handler('session_resumed', self.session_resumed)
        self.add_event_handler('socket_error', self.socket_error)
        self.add_event_handler('stream_error', self.stream_error)

    def connection_failed(self, event):
        print("[x] Connection failed")
        sys.exit(1)

    def disconnected(self, event):
        print("[x] Disconnected, reason: "+str(event))

    def connected(self, event):
        print("[i] Connected to XMPP server, starting session...")

    def failed_auth(self, event):
        print("[x] Invalid login credentials. Please check your configuration file and try again")
        sys.exit(1)

    def session_end(self, event):
        print("[x] Session has ended")

    def session_resumed(self, event):
        print("[i] Session has been resumed")

    def socket_error(self, event):
        print("[x] Socket error, details: \n"+str(event))
        xmpp.disconnect()
        sys.exit(1)

    def stream_error(self, event):
        print("[x] Stream error, details: \n"+str(event))
        xmpp.disconnect()
        sys.exit(1)

    # This asynchronous method will be called every time the session starts in XMPP
    async def start(self, event):
        print("[i] Session started. Sending presence, getting roster, and joining MUC...")
        # We are required to send a presence event upon connecting
        self.send_presence()
        # And to retrieve the roster in an asynchronous manner
        await self.get_roster()

        # Use XEP-0045 (Multi User Chat) to join a MUC chatroom
        # The chatroom's ID is stored in self.room and the nickname we will use
        # is stored in self.nick
        self.plugin['xep_0045'].join_muc(self.room, self.nick)

    # This method will be called whenever a message is received in XMPP
    async def message(self, message):
        # If the message is from a MUC
        if message['type'] == "groupchat":
            # Parse the message stanza XML
            xmldoc = minidom.parseString(str(message))
            # Find the "x" element in the message stanza
            itemlist = xmldoc.getElementsByTagName('x')

            # This "x" element contains the information from the NWS office that issued the message
            # So let's extract some basic attributes and store them in variables
            ttaaii = itemlist[0].attributes['ttaaii'].value.lower()
            cccc = itemlist[0].attributes['cccc'].value.lower()
            awipsid = itemlist[0].attributes['awipsid'].value.lower()
            id = itemlist[0].attributes['id'].value.lower()
            content = itemlist[0].firstChild.nodeValue

            # If the ID of the WFO that issued the message is in our preconfigured list of WFOs we want
            if cccc in config['wfo_offices'] or "every" in config['wfo_offices']:
                # Print the message to the console output
                print("\n\n==||== Incoming message from NWWS-OI ==||==")
                print("\t:: TTAAII = " + ttaaii)
                print("\t:: CCCC = " + cccc)
                print("\t:: AWIPSID = " + awipsid)
                print("\t:: ID = " + id)
                print("\t:: Body = "+message['body'])

                # Send the message to the configured Discord webhook
                print("\t\t[i] Sending message to Discord...")

                # Usually, we would have to save the message contents as a file and upload the file to Discord
                # because most NWWS messages are over Discord's character limit of 2,000 characters
                #
                # But, recently, the fine employees at Discord decided to increase the character limit for embed descriptions
                # meaning we should be able to fit most NWWS messages into the embed description with no need to upload a file
                #
                # There may still be that occasional message that will not fit, and in that case, it will not send via Discord
                # I don't think I am able to fix that myself, so oh well.
                #
                # You'll also notice that I specify the date and time it was issued as a field instead of using the embed's
                # timestamp property in the footer
                #
                # Reason I did that is because all embeds need to have at least 1 field in order to successfully send via Discord
                # so I might as well add this timestamp as a field.
                discord_post_body = {
                    'content': '**New message from NWWS-OI**',
                    'embeds': [
                        {
                            'title': message['body'],
                            'description': '```\n'+content+'\n```',
                            'color': 13035253,
                            'timestamp': datetime.datetime.utcnow().isoformat(),
                            'fields': [
                                {
                                    'name': 'Issued on',
                                    'value': '`'+datetime.datetime.utcnow().strftime("%m-%d-%Y_%H:%M:%S")+'`',
                                    'inline': True
                                },
                                {
                                    'name': 'TTAAII',
                                    'value': '`'+ttaaii+'`',
                                    'inline': True
                                },
                                {
                                    'name': 'CCCC',
                                    'value': '`'+cccc+'`',
                                    'inline': True
                                },
                                {
                                    'name': 'AWIPSID',
                                    'value': '`'+awipsid+'`',
                                    'inline': True
                                },
                                {
                                    'name': 'ID',
                                    'value': '`'+id+'`',
                                    'inline': True
                                }
                            ],
                            'footer': {
                                'text': 'nwws@nwws-oi.weather.gov/nwws'
                            }
                        }
                    ]
                }
                try:
                    # Send a POST request with application/json content-type to Discord
                    # and a JSON body.
                    r = requests.post(config['discord_webhook'], data=json.dumps(discord_post_body), headers={'content-type': 'application/json'})
                    # The r.ok property is true if the response HTTP status code is less than 400
                    # Discord returns a 201 on successful webhook POSTs, so if the webhook POST was successful this property should be True
                    if r.ok:
                        print("\t\t[i] Successfully sent to Discord")
                    else:
                        print("\t\t[x] Error sending to Discord! Details: "+r.text)
                except Exception as e:
                    # If we encounter an error, print the traceback to the console and just keep going.
                    print("\t\t[x] Error sending to Discord. Details:\n")
                    traceback.print_exc()

                # If we're on Windows and we have the toast notifications API enabled
                if sys.platform == "win32" and config['enable_win10_notifications'] is True:
                    toaster.show_toast("New message from NWWS-OI", content, duration=10)
                    print("\t\t[i] Successfully sent Windows 10 toast notification")

                print("==||== End Of Message ==||==")

        # If it is just a normal DM message, print the contents of it to the console.
        # The reason I added this is because anyone who has used NWWS-OI knows that every single time
        # you logon, you get a DM from a bot that warns you that you are accessing a U.S. federal government
        # computer system and that everything may be logged and that if you aren't authorized to access the system
        # you will be prosecuted.
        #
        # I wanted to display that message without having to hard-code it into my program, so I just decided to display
        # the message as you would receive it if you connected normally via XMPP
        #
        # This comes with the added benefit that if they do change the verbage of that warning or something in the future, I don't have
        # to do anything in my code.
        if message['type'] in ('normal', 'chat'):
            print("\n\n\n"+message['body']+"\n\n\n")

# Helper function that lets the user generate a template configuration file right from this script.
def gen_config():
    CONFIG_TEMPLATE = """{
  "username": "<INSERT YOUR NWWS-OI USERNAME HERE>",
  "password": "<INSERT YOUR NWWS-OI PASSWORD HERE>",
  "server": "nwws-oi.weather.gov",
  "port": 5222,
  "use_ssl": false,
  "resource": "nwws",
  "wfo_offices": [
    "<INSERT THE ID OF EACH WFO YOU WISH TO MONITOR HERE, OR TYPE THE WORD EVERY>"
  ],
  "discord_webhook": "<INSERT THE URL OF THE DISCORD WEBHOOK TO SEND MESSAGES TO>",
  "enable_win10_notifications": false
}"""
    try:
        f = open("./config.json", "w")
        f.write(CONFIG_TEMPLATE)
        f.close()
        print("[i] Successfully written configuration template to ./config.json")
        sys.exit(0)
    except Exception as e:
        print("[x] Failed to write configuration file template!")
        sys.exit(1)

def view_license():
    LICENSE_TXT = """
    Copyright 2021 Sanel Kukic

    Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
    """
    print(LICENSE_TXT)
    sys.exit(0)

def _asyncio_task_handler(task: asyncio.Task) -> None:
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print("[x] Exception encountered during asynchronous task = "+task+": \n")
        traceback.print_exc()

# This is a method to validate the configuration JSON file and ensure all fields
# that need to be there, are there and that proper value types (int, boolean, string, etc)
# are adhered to.
def validate_config(config):
    # First we check the username and password, and make sure they are strings and non-empty
    if not isinstance(config['username'], str):
        print("[x] Your username is not a string. Your username must be a string in the configuration file.")
        sys.exit(1)

    if config['username'] is '' or None:
        print("[x] Your username is empty. You must have a username and password from the National Weather Service to use this program. You can obtain a username and password at https://weather.gov/nwws")
        sys.exit(1)

    if not isinstance(config['password'], str):
        print("[x] Your password is not a string. Your password must be a string in the configuration file.")
        sys.exit(1)

    if config['password'] is '' or None:
        print("[x] Your password is empty. You must have a username and password from the National Weather Service to use this program. You can obtain a username and password at https://weather.gov/nwws")
        sys.exit(1)

    # Now we check the server and port fields to make sure they are of the correct type and not empty
    if not isinstance(config['server'], str):
        print("[x] The server you set in the configuration file is not a string. The server field must be a string.")
        sys.exit(1)

    if config['server'] == '' or None:
        print("[x] You did not set a server to connect to. Please enter the URL of the server to connect to in the configuration file.")
        sys.exit(1)

    if not isinstance(config['port'], int):
        print("[x] The port is not an integer. The port must be an integer, and not a string, in the configuration file.")
        sys.exit(1)

    if config['port'] == 0 or '' or None:
        print("[x] The port is invalid. You must set a valid port number in the configuration file to use this program.")
        sys.exit(1)

    # Now we check use_ssl and resource

    if not isinstance(config['use_ssl'], bool):
        print("[x] The use_ssl setting in the configuration file is not a boolean. It must be a boolean (true/false) and not a string.")
        sys.exit(1)

    if config['use_ssl'] is '' or 0 or None:
        print("[x] Invalid setting for use_ssl in the configuration file. It must either be true or false.")
        sys.exit(1)

    if not isinstance(config['resource'], str):
        print("[x] The resource setting in the configuration file is not a string. It must be a string.")
        sys.exit(1)

    if config['resource'] is '' or None:
        print("[x] Invalid setting for resource in the configuration file. Please set a valid XMPP resource.")
        sys.exit(1)

    # Now we check wfo_offices and discord_webhook
    if not isinstance(config['wfo_offices'], list):
        print("[x] The wfo_offices setting is not an array. It must be an array containing at least one element representing the CCCC of the WFO you wish to monitor on NWWS-OI.")
        sys.exit(1)

    if len(config['wfo_offices']) is 0:
        print("[x] You must have at least one WFO set in your wfo_offices configuration variable. If you wish to monitor all available WFOs on NWWS-OI, add the word 'every' to your wfo_offices configuration.")
        sys.exit(1)

    if not isinstance(config['discord_webhook'], str):
        print("[x] Your Discord webhook URL is not stored as a string. It must be a string.")
        sys.exit(1)

    if config['discord_webhook'] is '' or None:
        print("[x] Invalid Discord webhook URL. You must set a Discord webhook URL to send NWWS-OI messages to in order to use this program.")
        sys.exit(1)

    # And lastly, we check the Windows 10 notifications setting
    # Here we need to first check if we're on Windows 10
    if sys.platform == "win32":
        if not isinstance(config['enable_win10_notifications'], bool):
            print("[x] Windows 10 notifications setting is not a boolean. It must be set to a boolean of either true or false.")
            sys.exit(1)

        if config['enable_win10_notifications'] is None:
            print("[x] Invalid setting for Windows 10 notifications. It must be a boolean of either true or false.")
            sys.exit(1)

    # If we made it to this line, then we know that the program did not exit and the configuration is completely valid
    # so let's return the value True to signify that
    print("[i] Configuration file is valid")
    return True


# Everything after this line will run when we run the script directly without passing parameters.
if __name__ == '__main__':
    # Register SIGINT so that we can CTRL+C and exit gracefully
    signal.signal(signal.SIGINT, sigint)
    # Register SIGTERM
    signal.signal(signal.SIGTERM, sigterm)

    # Set up commandline argument parser
    parser = ArgumentParser(prog="oibot", description=OIBot.__doc__, epilog="""
    WARNING: This software is 100% open-source and available completely free for anyone to use at https://github.com/sanelk2004/oibot - If you paid for this software, you have been SCAMMED and you should report the fraud to your financial institution.

    Licensed under the terms of the MIT License.""")
    parser.add_argument("config", nargs="?", help="Absolute path to the configuration JSON file to use.")
    parser.add_argument("-g", "--gen-config", action="store_true", help="Generate a template configuration file in the current directory that you can fill in.")
    parser.add_argument("-l", "--license", action="store_true", help="View the text of the program's license.")
    parser.add_argument("-v", "--validate", action="store_true", help="Validate the given configuration file.")
    args = parser.parse_args()

    # If the user did not specify the path to a configuration file
    if args.gen_config:
        gen_config()
    elif args.license:
        view_license()
    elif args.validate:
        if args.config is None:
            print("[x] You must specify the configuration file to validate! Example:\noibot.py config.json --validate\n\n")
        else:
            try:
                v_config = json.load(open(args.config))
                validate_config(v_config)
            except Exception as e:
                print("[x] Failed to validate that configuration file!")
                sys.exit(1)
    elif args.config is None:
        # Show an error message and exit
        print("[x] You must specify the path to a JSON configuration file to use with OIBot!")
        sys.exit(1)
    else:
        # Load configuration file
        print("[i] Loading configuration file...")
        global config
        config = None
        try:
            config = json.load(open(args.config))
        except Exception as e:
            print("[x] Failed to load configuration file!")
            sys.exit(1)
        # Validate configuration file
        print("[i] Validating configuration file...")
        validate_config(config)
        # Attempt to connect to the XMPP server
        print("[i] Trying to connect using the following details: ")
        xmpp_jid = config['username'] + '@' + config['server']
        xmpp_room = 'nwws@conference.' + config['server'] + '/' + config['resource']
        # Print configuration details
        print("\t:: Username = "+config['username'])
        # Censor the password and print it
        censored_pw = '*' * len(config['password'])
        print("\t:: Password = "+censored_pw)
        print("\t:: Server = "+config['server'])
        print("\t:: Port = "+str(config['port']))
        print("\t:: Use SSL? "+str(config['use_ssl']))
        print("\t:: Resource = "+config['resource'])
        print("\t:: Jabber ID = "+xmpp_jid)
        print("\t:: Room ID = "+xmpp_room)

        # This is some hacky code to censor the token portion of the Discord webhook URL before I output
        # it to the console, just for additional security purposes
        discord_webhook_url = config['discord_webhook']
        discord_webhook_parts = discord_webhook_url.split('/')
        # Split the token URL into an array of strings based on the / character
        # The fifth element in the array is the token
        webhook_token = discord_webhook_parts[6]
        # Create a new string that is the same length as the real token, but this new string will consist of pure asterisk symbols
        censored_webhook_token = '*' * len(webhook_token)
        # Remove the token from the array
        discord_webhook_parts.pop(6)
        # Add the new "censored" token string to the array in the same place where the uncensored token was
        discord_webhook_parts.append(censored_webhook_token)
        # And combine the elements in the array to form a URL, then print that censored URL to the console
        new_webhook_url = "https://" + discord_webhook_parts[2] + "/" + discord_webhook_parts[3] + "/" + discord_webhook_parts[4] + "/" + discord_webhook_parts[5] + "/" + discord_webhook_parts[6]
        print("\t:: Discord webhook URL = "+new_webhook_url)

        # Print the list of WFOs that the user has configured to receive messages from
        configured_wfos = config['wfo_offices']
        wfo_list = ""
        for wfo in configured_wfos:
            wfo_list += wfo.upper() + ", "
        print("\t:: Configured WFO offices: "+wfo_list)

        # Check if we're on Windows 10 and if the user chose to enable the toast notifications feature
        if sys.platform == "win32":
            print("\t:: Enable Windows 10 Notifications API? "+str(config['enable_win10_notifications']) + "\n")
            if config['enable_win10_notifications'] is True:
                from win10toast import ToastNotifier
                # Create a global variable for the toast notifications API and initialize an instance of ToastNotifier
                global toaster
                toaster = ToastNotifier()

        # Keep in mind that this process does not actually change the value of config['discord_webhook'], this is purely
        # "cosmetic" because at no point did I perform an assignment operation on the value of config['discord_webhook'] here

        # The reason I made the xmpp variable global is so that I can use it in the SIGINT handler method above
        # to gracefully disconnect from XMPP and quit the program.
        global xmpp
        xmpp = OIBot(xmpp_jid, config['password'], xmpp_room, config['username'])
        # Register XEPs
        xmpp.register_plugin('xep_0045')
        xmpp.register_plugin('xep_0030')
        xmpp.register_plugin('xep_0004')
        xmpp.register_plugin('xep_0199')
        xmpp.register_plugin('xep_0078')
        xmpp.register_plugin('xep_0198')
        # Set the SSL version to use, NWWS requires at least TLSv2.3
        xmpp.ssl_version = ssl.PROTOCOL_SSLv23
        # And finally, attempt to connect
        xmpp.connect((config['server'], config['port']), config['use_ssl'])
        # Make the process blocking and synchronous
        xmpp.process(forever=True)
