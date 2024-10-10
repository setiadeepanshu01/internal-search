#!/bin/bash

# Start ngrok tunnel for port 3000
ngrok http 3000 &

# Start ngrok tunnel for port 3001
ngrok http 3001 &

