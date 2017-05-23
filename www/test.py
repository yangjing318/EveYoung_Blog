from www import orm
from www.models import User
import asyncio, sys

@asyncio.coroutine
def test(loop):
    yield from orm.create_pool(loop=loop, user='root', password='123456', db='EveYoung')

    u = User(id='1102',name='yangjing', email = '605943345@qq.com', passwd='123456', image='about-blank')
    yield from u.save()
    
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait([test(loop)]))
    print('test')
    print('success')
    loop.close()
    if loop.is_closed():
        sys.exit(0)


