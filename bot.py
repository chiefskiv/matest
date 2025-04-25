from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from web3 import Web3
from datetime import datetime, timedelta
from collections import defaultdict
from hexbytes import HexBytes
from web3.middleware import geth_poa_middleware

# 🎯 Настройки
BOT_TOKEN = "8091288421:AAFGzQnglUcH7uSIFx5EO0THsfkHnS8ANCo"
TARGET_ADDRESS = Web3.to_checksum_address("0xcC0CfC5C95831EFaaaf2c141257cD46573EADEb5")
USDT_ADDRESS = Web3.to_checksum_address("0xc2132d05d31c914a87c6611c10748aeb04b58e8f")
RPC_URL = "https://polygon-mainnet.infura.io/v3/b0affbfb7d4f4c29929e4996faac0b3c"

web3 = Web3(Web3.HTTPProvider(RPC_URL))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

TRANSFER_TOPIC = web3.keccak(text="Transfer(address,address,uint256)")
TOPIC_TO = HexBytes('0x' + TARGET_ADDRESS[2:].rjust(64, '0'))

# 📦 Команда /stat
async def stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.utcnow()
    start = now - timedelta(hours=1)

    def find_block_by_time(target_time):
        latest = web3.eth.block_number
        low, high = 0, latest
        while low <= high:
            mid = (low + high) // 2
            block = web3.eth.get_block(mid)
            block_time = datetime.utcfromtimestamp(block.timestamp)
            if block_time < target_time:
                low = mid + 1
            else:
                high = mid - 1
        return low

    from_block = find_block_by_time(start)
    to_block = find_block_by_time(now)

    logs = web3.eth.get_logs({
        "fromBlock": from_block,
        "toBlock": to_block,
        "address": USDT_ADDRESS,
        "topics": [TRANSFER_TOPIC, None, TOPIC_TO]
    })

    senders = defaultdict(float)
    for log in logs:
        sender = "0x" + log["topics"][1].hex()[-40:]
        amount = int.from_bytes(log["data"], byteorder='big') / 1e6
        senders[sender] += amount

    if not senders:
        await update.message.reply_text("⛔ Нет транзакций за последний час.")
    else:
        response = "📊 USDT за последний час:\n"
        for sender, total in sorted(senders.items(), key=lambda x: x[1], reverse=True):
            response += f"{sender} — {total:.2f} USDT\n"
        await update.message.reply_text(response)

# ▶️ Запуск бота
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("stat", stat))
    print("✅ Бот запущен...")
    app.run_polling()
