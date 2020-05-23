import aiofiles
import asyncio
import os
import argparse
import logging
from aiohttp import web
from aiohttp.web_exceptions import HTTPNotFound

logger = logging.getLogger('archive')


async def archivate(request):
    response = web.StreamResponse()
    archive_hash = request.match_info['archive_hash']
    archive_path = os.path.join(app.folders_path,archive_hash)
    if not os.path.exists(archive_path):
        raise HTTPNotFound(text='Ваша папка не найдена')
    response.headers['Content-Disposition'] = f'form-data; filename={archive_hash}.zip'
    await response.prepare(request)
    cmd = ['zip','-r','-',archive_hash]
    cwd = app.folders_path
    process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    chunk_b_size = 100 * 1024
    try:
        while True:
            stdout_chunk = await process.stdout.read(chunk_b_size)
            await asyncio.sleep(app.response_delay)
            if not stdout_chunk:
                logger.info('Archive uploaded successfully')
                break
            await response.write(stdout_chunk)

    except asyncio.CancelledError:
        logger.info('Download was interrupted')
        raise
    finally:
        process.kill()
        await process.communicate()
        return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()

    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
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
        '--log_path',
        help='Path to log file',
        default='logs.log'
    )
    parser.add_argument(
        '--folders_path',
        help='Write path to archives',
        type=str,
    )
    args = parser.parse_args()

    logging.basicConfig(
        format=u'%(levelname)-8s %(message)s', level=args.verbose, filename=args.log_path,
    )

    app = web.Application()
    app.response_delay = args.delay
    app.folders_path = args.folders_path
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivate),
    ])
    web.run_app(app)
