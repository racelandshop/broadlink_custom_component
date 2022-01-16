# CUSTOM COMPONENT BROADLINK

This is a custom component to be used in conjuction with the broadlink [remote card](https://github.com/zroger49/broadllink-card). Currently only remotes are suported. 

Contrary to the "classic" broadlink integration, the remote is not registered in homeassistant (might be in the future)
The main point of this integration is to communicate with the broadlink custom_card through websockets. Feel free to use this code in your own project.

## Why?

Although great the classic broadlink integration does not allow to run discover (AFAIK)

## Features

- AutoDiscover
- Saves learned commands


## Configuration

To configure simply put this line in the configuration.yaml file: 


```
broadlink_custom_card:
```


