# oibot

An XMPP chat bot that connects to [NWWS-OI](https://weather.gov/nwws) and can forward messages to a Discord webhook.

I made this because I looked around the internet and couldn't find a single free-to-use or open-source XMPP client that was able to parse the contents of NWWS-OI messages and display them. There used to be clients that worked but they no longer work so I tasked myself with making my own client.

Inspired by [jbuitt/nwws-python-client](https://github.com/jbuitt/nwws-python-client).

## How does it work?
Using [slixmpp](https://slixmpp.readthedocs.io), it connects to the NWWS-OI XMPP server and listens for messages from WFOs.

You can configure which WFOs you want to trigger the script in the configuration file, detailed below. Or, you can have it go off for every single message posted on NWWS-OI (not recommended in a production environment but useful for testing the script)

Completely contained in one single Python file, too.

## How do I use it?
For starters, you need to have credentials to access NWWS-OI. You can obtain these credentials on the [National Weather Service's webpage](https://weather.gov/nwws)

Once you have obtained your credentials, you need to create a `.json` file that looks like the following. A blank, example configuration file is included with the Python script and in this repository.
```json
{
  "username": "<INSERT YOUR NWWS-OI USERNAME HERE>",
  "password": "<INSERT YOUR NWWS-OI PASSWORD HERE>",
  "server": "nwws-oi.weather.gov",
  "port": 5222,
  "use_ssl": false,
  "resource": "nwws",
  "wfo_offices": [
    "<SPECIFY THE ID OF EACH WFO THAT YOU WANT TO RECEIVE MESSAGES FROM>"
  ],
  "discord_webhook": "<INSERT THE URL OF YOUR DISCORD WEBHOOK HERE>",
  "enable_win10_notifications": false
}
```

**If you wish to receive messages from all WFOs, put the word "all" in your `wfo_offices` configuration, such that it looks like this:**
```json
"wfo_offices": [
    "every"
]
```

Now, simply fill in the fields that have a placeholder in them, save the file, and run the following commands in your terminal:
```bash
$ pip install -r requirements.txt
$ python oibot.py <path to your config file here>
```

You can also run the script with the `-g` or `--gen-config` argument to generate a template configuration file akin to the one displayed above.

Once you've done that, you should see the program start up, print some basic information, and if all goes well you should see the federal government warning message that everyone who logs in to NWWS-OI sees:
```
**WARNING**WARNING**WARNING**WARNING**WARNING**WARNING**WARNING**WARNING**

This is a United States Federal Government computer system, which may be
accessed and used only for official Government business by authorized
personnel.  Unauthorized access or use of this computer system may
subject violators to criminal, civil, and/or administrative action.

All information on this computer system may be intercepted, recorded,
read, copied, and disclosed by and to authorized personnel for official
purposes, including criminal investigations. Access or use of this
computer system by any person whether authorized or unauthorized,
CONSTITUTES CONSENT to these terms.

**WARNING**WARNING**WARNING**WARNING**WARNING**WARNING**WARNING**WARNING**
```

Once you see this message, you know you're connected. All you have to do now is sit back and wait. Based on your configuration, the program will send messages to the Discord webhook you specified.

### Enabling toast notifications on Windows 10
If you are running this script on Windows 10, you can install an additional package and change a setting in your configuration file to enable toast notifications every time a new message is posted to NWWS-OI. To do this, follow these steps.

1. Run `pip install -r requirements-windows.txt` in your terminal.
2. Open your configuration file and change the value for `enable_win10_notifications` from `false` to `true`, then save your configuration file.
3. Run the program and specify the path to your configuration file!

It really is that easy :D

## Is this free to use? Do I need to buy a license?
Yes, and no. This is completely free-to-use by anyone who is authorized to access NWWS-OI. You do not need to pay me a single penny to use this, however, I would greatly appreciate it if you [sponsor me on GitHub](https://github.com/sponsors/sanelk2004) or [bought me a coffee](https://cash.app/$3reetop).

If you paid to obtain access to this software, you have been SCAMMED and you should contact your financial institution to report the fraud as soon as possible. You may also want to [report the fraud to the Federal Trade Commission](https://reportfraud.ftc.gov) and/or file a report with your local police department. If you believe your identity has been stolen, visit the [Federal Trade Commission's Identity Theft](https://identitytheft.gov) website to file a report.

## License
This program is licensed under the terms and conditions of the MIT License. The full text of the license can be found in the [LICENSE.txt](./LICENSE.txt) file.
