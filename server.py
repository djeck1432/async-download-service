import aiofiles
import asyncio
import os
import argparse
import logging
from aiohttp import web
from dotenv import load_dotenv
from aiohttp.web_exceptions import HTTPNotFound


def get_params_environment():
    load_dotenv()
    archives_path = os.getenv('ARCHIVES_PATH')
    response_delay = os.getenv('RESPONSE_DELAY')
    return archives_path,int(response_delay)

async def archivate(request):
    response = web.StreamResponse()
    archive_name = request.match_info.get('archive_hash')
    archives_path,response_delay = get_params_environment()
    if not os.path.exists(f'{archives_path}/{archive_name}'):
        raise HTTPNotFound(headers=None, reason=None,
             body=None, text='Ваша папка не найдена', content_type=None)

    response.headers['Content-Disposition'] = f'form-data; filename={archive_name}.zip'
    await response.prepare(request)
    cmd = f'zip -r  - {archive_name}'
    process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=archives_path,
        )
    chunk_b_size = 500 * 1024
    archive = b''
    try:
        while True:
            stdout_chunk = await process.stdout.read(chunk_b_size)
            await asyncio.sleep(response_delay)
            if stdout_chunk:
                archive += stdout_chunk
                await response.write(archive)
            else:
                logger.info('Archive downloaded success')
                break
    except asyncio.CancelledError:
        logger.warning('Download was interrupted')
        process.kill()
        await process.communicate()
    finally:
        return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()

    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Setting log output')
    parser.add_argument(
        '--logs',
        help='Switch on logging'
    )
    args = parser.parse_args()
    if args.logs == 'on':
        logger = logging.getLogger('archive')
        logging.basicConfig(
            format=u'%(levelname)-8s %(message)s', level=logging.INFO, filename=u'logs.log'
        )
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivate),
        web.get('/archive/7kna/', archivate),
    ])
    web.run_app(app)
