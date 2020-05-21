import aiofiles
import asyncio
import os
import argparse
import logging
from aiohttp import web
from dotenv import load_dotenv
from aiohttp.web_exceptions import HTTPNotFound

logger = logging.getLogger('archive')

def get_environment_params():
    load_dotenv()
    parser = argparse.ArgumentParser(description='Setting log output')
    parser.add_argument(
        '--verbose',
        '-v',
        action='count',
        help='Switch on logging'
    )
    parser.add_argument(
        '--delay',
        help='Install response delay for server',
        type=int
    )
    parser.add_argument(
        '--log_name',
        help='Name of log file',
        default='logs'
    )
    parser.add_argument(
        '--folders_path',
        help='Write path to archives',
        type=str,
    )
    args = parser.parse_args()
    logging.basicConfig(
        format=u'%(levelname)-8s %(message)s', level=logging.INFO, filename=f'{args.log_name}.log'
    )
    return args.folders_path,args.delay

async def archivate(request):
    response = web.StreamResponse()
    archive_name = request.match_info.get('archive_hash')
    folders_path,response_delay = get_environment_params()
    # archive_path = os.path.join()
    if not os.path.exists(f'{folders_path}/{archive_name}'):
        raise HTTPNotFound(text='Ваша папка не найдена')
    response.headers['Content-Disposition'] = f'form-data; filename={archive_name}.zip'
    await response.prepare(request)
    cmd = f'zip -r  - {archive_name}'
    process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=folders_path,
        )
    chunk_b_size = 100 * 1024
    try:
        while True:
            stdout_chunk = await process.stdout.read(chunk_b_size)
            await asyncio.sleep(response_delay)
            if not stdout_chunk:
                logger.info('Archive downloaded success')
                break
            await response.write(stdout_chunk)

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

    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivate),
    ])
    web.run_app(app)
