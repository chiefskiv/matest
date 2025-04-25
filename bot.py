from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from web3 import Web3
from datetime import datetime, timedelta
from collections import defaultdict
from web3.middleware import geth_poa_middleware
import requests

# 🔐 ВСТАВЬ СВОЙ ТОКЕН НИЖЕ
BOT_TOKEN = "7454626704:AAFgK-2fqDiofX6jDlk8fjKUmNzAawMAZp8"
TARGET_ADDRESS = Web3.to_checksum_address("0xcC0CfC5C95831EFaaaf2c141257cD46573EADEb5")
USDT_ADDRESS = Web3.to_checksum_address("0xc2132d05d31c914a87c6611c10748aeb04b58e8f")
RPC_URL = "https://polygon-mainnet.infura.io/v3/b0affbfb7d4f4c29929e4996faac0b3c"

web3 = Web3(Web3.HTTPProvider(RPC_URL))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

TRANSFER_TOPIC = web3.keccak(text="Transfer(address,address,uint256)").hex()
TOPIC_TO = "0x" + TARGET_ADDRESS[2:].lower().rjust(64, '0')

def reset_telegram_updates():
    print("⚙️ Сбрасываем getUpdates у Telegram...")
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        requests.get(url, timeout=5)
        print("✅ Сброс завершён.")
    except Exception as e:
        print(f"⚠️ Ошибка сброса: {e}")

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

    try:
        logs = web3.eth.get_logs({
            "fromBlock": from_block,
            "toBlock": to_block,
            "address": USDT_ADDRESS,
            "topics": [TRANSFER_TOPIC, None, TOPIC_TO]
        })
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка запроса логов: {e}")
        return

    senders = defaultdict(float)
    for log in logs:
        sender = "0x" + log["topics"][1].hex()[-40:]
        amount = int.from_bytes(bytes.fromhex(log["data"][2:]), byteorder='big') / 1e6
        senders[sender] += amount

    if not senders:
        await update.message.reply_text("⛔ Нет переводов USDT за последний час.")
    else:
        result = "📊 USDT за последний час:\n"
        for sender, total in sorted(senders.items(), key=lambda x: x[1], reverse=True):
            result += f"{sender} — {total:.2f} USDT\n"
        await update.message.reply_text(result)

if __name__ == "__main__":
    reset_telegram_updates()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("stat", stat))
    print("✅ Бот запущен и ждёт команду /stat...")
    app.run_polling()
