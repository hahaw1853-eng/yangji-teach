#[pin:false]
#[disable:false]
#[public:true]
#[rule: ^(自动签到|签到测试)$]
#[version: 1.0]
#[price: 0.00]
#[cron: 0 9 * * *]
#[title: 自动签到]
#[author: kimi]
#[admin: false]
#[icon: https://img.cdn1.vip/i/6a8e00f74bda3_1787691255.webp]
#[description: 每天自动给指定机器人发送签到消息。<br>指令:自动签到、签到测试<br>定时:每天9:00自动执行]
#[param: {"required":true,"key":"dd_AutoSign.target_qq","bool":false,"placeholder":"4010292593","name":"目标QQ","desc":"接收签到消息的机器人QQ号"}]
#[param: {"required":false,"key":"dd_AutoSign.content","bool":false,"placeholder":"签到","name":"签到内容","desc":"发送的签到消息内容"}]

import middleware

TARGET_QQ = middleware.bucketGet(bucket='dd_AutoSign', key='target_qq') or '4010292593'
CONTENT = middleware.bucketGet(bucket='dd_AutoSign', key='content') or '签到'

senderID = middleware.getSenderID()
sender = middleware.Sender(senderID)
message = sender.getMessage()

def do_sign() -> bool:
    """执行签到发送"""
    try:
        target = middleware.Sender(TARGET_QQ)
        target.reply(CONTENT)
        print(f"[{__import__('datetime').datetime.now().strftime('%H:%M:%S')}] 已发送签到给 {TARGET_QQ}")
        return True
    except Exception as e:
        print(f"发送签到失败: {e}")
        return False

def main():
    if message == "签到测试":
        if do_sign():
            sender.reply(
                "✅ 签到测试成功\n"
                f"📱 目标：{TARGET_QQ}\n"
                f"📝 内容：{CONTENT}"
            )
        else:
            sender.reply(
                "❌ 签到测试失败\n"
                "请检查目标QQ是否正确"
            )
    else:
        # cron 定时触发
        do_sign()

main()
