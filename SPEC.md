This project is to create a minimal ai agent in the openclaw sense, following some concepts used in picoclaw.

The project is intended to be used on Raspberry Pi devices, mainly 4 and 5 level devices using arm64 OS.

The project should be written in python where possible, although some parts may be other languages.

The device should use python webhooks to connect to llm ai providers.

Initially, the project should be written to connect to openrouter.ai, requiring an openrouter api key, and a selection list of popular models available in openrouter.

There should be a vector database with embeddings. This could be a ChromeDB database. The vector database should run on using a python script.

The project should allow connecting to a calendar and email service using the default Raspberry Pi services which come with a full desktop install of Raspberry Pi 4 and 5.

There should be a skills list. Skills should include instructions on how to write a prompt, how to write a skill.md, how to store information in the vector database and embed it.

The project should be designed to use local python and cron for as many actions as possible to cut down on ai costs.

The project should allow gateway connection through Telegram app, and WhatsApp.

A user should be able to start the project by adding an openrouter api key, selecting a preferred openrouter model from a list of popular models, and a Telegram token.

There should be a terminal agent interface.

The project should be designed to minimize the number of ai calls, in order to reduce cost.

The project should be a low amount of code with fast startup.

An example of a similar project would be picoclaw.
