Crashed

2026-09-07 13:32 GMT+6
Get Help
Details
Build Logs
Deploy Logs
Network Logs
Filter and search logs


  File "/usr/local/lib/python3.11/site-packages/telethon/client/auth.py", line 22, in <lambda>
EOFError: EOF when reading a line
    phone: typing.Union[typing.Callable[[], str], str] = lambda: input('Please enter your phone (or bot token): '),
                                                                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    await client.start(bot_token=BOT_TOKEN)
  File "/usr/local/lib/python3.11/site-packages/telethon/client/auth.py", line 167, in _start
    value = phone()
            ^^^^^^^
  File "/usr/local/lib/python3.11/site-packages/telethon/client/auth.py", line 22, in <lambda>
2026-09-07 07:32:44,362 - INFO - Connecting to 149.154.167.51:443/TcpFull...
2026-09-07 07:32:44,449 - INFO - Connection to 149.154.167.51:443/TcpFull complete!
Please enter your phone (or bot token): Traceback (most recent call last):
  File "/app/main.py", line 152, in <module>
    asyncio.run(main())
  File "/usr/local/lib/python3.11/asyncio/runners.py", line 190, in run
    return runner.run(main)
           ^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    phone: typing.Union[typing.Callable[[], str], str] = lambda: input('Please enter your phone (or bot token): '),
  File "/usr/local/lib/python3.11/asyncio/base_events.py", line 654, in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
  File "/app/main.py", line 146, in main
EOFError: EOF when reading a line
2026-09-07 07:32:48,065 - INFO - Connecting to 149.154.167.51:443/TcpFull...
2026-09-07 07:32:48,154 - INFO - Connection to 149.154.167.51:443/TcpFull complete!
                                                                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Please enter your phone (or bot token): Traceback (most recent call last):
  File "/app/main.py", line 152, in <module>
    asyncio.run(main())
  File "/usr/local/lib/python3.11/asyncio/runners.py", line 190, in run
    return runner.run(main)
           ^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/asyncio/base_events.py", line 654, in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
  File "/app/main.py", line 146, in main
    await client.start(bot_token=BOT_TOKEN)
  File "/usr/local/lib/python3.11/site-packages/telethon/client/auth.py", line 167, in _start
    value = phone()
            ^^^^^^^
  File "/usr/local/lib/python3.11/site-packages/telethon/client/auth.py", line 22, in <lambda>
    phone: typing.Union[typing.Callable[[], str], str] = lambda: input('Please enter your phone (or bot token): '),
                                                                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
EOFError: EOF when reading a line
2026-09-07 07:32:52,032 - INFO - Connecting to 149.154.167.51:443/TcpFull...
2026-09-07 07:32:52,120 - INFO - Connection to 149.154.167.51:443/TcpFull complete!
Please enter your phone (or bot token): Traceback (most recent call last):
  File "/app/main.py", line 152, in <module>
    asyncio.run(main())
  File "/usr/local/lib/python3.11/asyncio/runners.py", line 190, in run
    return runner.run(main)
           ^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/asyncio/base_events.py", line 654, in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
  File "/app/main.py", line 146, in main
    await client.start(bot_token=BOT_TOKEN)
  File "/usr/local/lib/python3.11/site-packages/telethon/client/auth.py", line 167, in _start
    value = phone()
            ^^^^^^^
  File "/usr/local/lib/python3.11/site-packages/telethon/client/auth.py", line 22, in <lambda>
    phone: typing.Union[typing.Callable[[], str], str] = lambda: input('Please enter your phone (or bot token): '),
                                                                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
EOFError: EOF when reading a line
2026-09-07 07:32:55,433 - INFO - Connecting to 149.154.167.51:443/TcpFull...
2026-09-07 07:32:55,522 - INFO - Connection to 149.154.167.51:443/TcpFull complete!
Please enter your phone (or bot token): Traceback (most recent call last):
  File "/app/main.py", line 152, in <module>
    asyncio.run(main())
  File "/usr/local/lib/python3.11/asyncio/runners.py", line 190, in run
    return runner.run(main)
           ^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/asyncio/base_events.py", line 654, in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
  File "/app/main.py", line 146, in main
    await client.start(bot_token=BOT_TOKEN)
  File "/usr/local/lib/python3.11/site-packages/telethon/client/auth.py", line 167, in _start
    value = phone()
            ^^^^^^^
  File "/usr/local/lib/python3.11/site-packages/telethon/client/auth.py", line 22, in <lambda>
    phone: typing.Union[typing.Callable[[], str], str] = lambda: input('Please enter your phone (or bot token): '),
           ^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/asyncio/base_events.py", line 654, in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
  File "/app/main.py", line 146, in main
    await client.start(bot_token=BOT_TOKEN)
  File "/usr/local/lib/python3.11/site-packages/telethon/client/auth.py", line 167, in _start
    value = phone()
            ^^^^^^^
                                                                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
EOFError: EOF when reading a line
2026-09-07 07:32:58,776 - INFO - Connecting to 149.154.167.51:443/TcpFull...
2026-09-07 07:32:58,865 - INFO - Connection to 149.154.167.51:443/TcpFull complete!
Please enter your phone (or bot token): Traceback (most recent call last):
  File "/app/main.py", line 152, in <module>
    asyncio.run(main())
  File "/usr/local/lib/python3.11/asyncio/runners.py", line 190, in run
    return runner.run(main)
  File "/usr/local/lib/python3.11/site-packages/telethon/client/auth.py", line 22, in <lambda>
    phone: typing.Union[typing.Callable[[], str], str] = lambda: input('Please enter your phone (or bot token): '),
                                                                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
EOFError: EOF when reading a line
            ^^^^^^^
  File "/usr/local/lib/python3.11/site-packages/telethon/client/auth.py", line 22, in <lambda>
    phone: typing.Union[typing.Callable[[], str], str] = lambda: input('Please enter your phone (or bot token): '),
2026-09-07 07:33:02,290 - INFO - Connecting to 149.154.167.51:443/TcpFull...
2026-09-07 07:33:02,377 - INFO - Connection to 149.154.167.51:443/TcpFull complete!
Please enter your phone (or bot token): Traceback (most recent call last):
  File "/app/main.py", line 152, in <module>
    asyncio.run(main())
  File "/usr/local/lib/python3.11/asyncio/runners.py", line 190, in run
    return runner.run(main)
           ^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/asyncio/base_events.py", line 654, in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
  File "/app/main.py", line 146, in main
    await client.start(bot_token=BOT_TOKEN)
  File "/usr/local/lib/python3.11/site-packages/telethon/client/auth.py", line 167, in _start
    value = phone()
You reached the end of the range
2026-09-07 13:33
