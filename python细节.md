```python
@staticmethod
静态方法, 不强制要求传递参数

@classmethod
类方法, 不需要实例化, 不需要self参数, 但第一个参数需要是表示自身类的cls参数, 可以用来调用类的属性, 类的方法, 实例化对象等

### 类特殊方法

class Test():
    def __init__():
    	pass
    
    def __enter__():
        '''使用with语句创建示例时会自动运行此方法'''
        pass
    
    ‘’‘
    with Test() as t:
        pass
    ’‘’
    
    def __exit__():
        '''使用with语句创建实例, 在结束时自动调用该方法'''
        pass
    
    def __str__():
        '''可print(实例)'''
        return ‘我是Test类’
    
    def __setattr__, __getattr__, __getattribute__, __delattr__:
        '''对属性进行操作'''
        pass
    
    def __call__():
        '''能让把实例化对象直接当做函数来调用'''
        print(1)    
    '''
    a = Test()
    in: a()
    out: 1
    '''
    
    def __contains__, __len__():
        '''类作为容器'''
        pass

# HDFStore`	
with pd.HDFStore('iv_hv.h5') as store:
    c = store.keys()

'''matplotlib
':'  点虚线
'-'  实线
'--' 破折线
'-.' 点划线

添加水平垂直线
plt.axhline(y=0,ls=":",c="yellow") 水平直线
plt.axvline(x=4,ls="-",c="green")  垂直直线
'''

```

![img](https://pic4.zhimg.com/v2-c84b6a01a16b94af53a56e8f49d9c497_r.jpg)

## 自动发邮件

```python
import smtplib
from smtplib import SMTP_SSL
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.mime.application import MIMEApplication  # 用于添加附件


host_server = 'smtp.qq.com'  # qq邮箱smtp服务器
sender_qq = '359582058@qq.com'  # 发件人邮箱
pwd = 'bglhxfrujynobhda'qq
pwd = 'EGGZASTFLHVGCBRU'163
receiver = '13918949838@163.com'
mail_title = 'Python自动发送邮件'  # 邮件标题

# 邮件正文内容
mail_content = "您好"

msg = MIMEMultipart()
msg["Subject"] = Header(mail_title, 'utf-8')
msg["From"] = sender_qq
msg["To"] = Header("测试邮箱", "utf-8")

msg.attach(MIMEText(mail_content, 'html'))
attachment = MIMEApplication(open('复权.xlsx', 'rb').read())
attachment["Content-Type"] = 'application/octet-stream'
# 给附件重命名
basename = "复权.xlsx"
attachment.add_header('Content-Disposition', 'attachment',
                      filename=('utf-8', '', basename))  # 注意：此处basename要转换为gbk编码，否则中文会有乱码。
msg.attach(attachment)


try:
    smtp = SMTP_SSL(host_server)  # ssl登录连接到邮件服务器
    smtp.set_debuglevel(1)  # 0是关闭，1是开启debug
    smtp.ehlo(host_server)  # 跟服务器打招呼，告诉它我们准备连接，最好加上这行代码
    smtp.login(sender_qq, pwd)
    smtp.sendmail(sender_qq, receiver, msg.as_string())
    smtp.quit()
    print("邮件发送成功")
except smtplib.SMTPException:
    print("无法发送邮件")
```



## Tkinter

