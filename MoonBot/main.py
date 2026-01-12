import logging
import asyncio
from MoonBot import config
from MoonBot.client import bot

# Logging Setup
logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.WARNING)

def main():
    print("MoonBot Controller Starting...")
    
    # Start the Bot
    bot.start(bot_token=config.API_TOKEN)
    
    print("Bot Connected! Loading Plugins...")

    # Load Plugins (Importing them registers the event handlers)
    import MoonBot.plugins.start
    import MoonBot.plugins.admin
    import MoonBot.plugins.login
    import MoonBot.plugins.manager
    import MoonBot.plugins.tools
    
    print("Plugins Loaded. Bot is Idle.")
    bot.run_until_disconnected()

if __name__ == '__main__':
    main()
