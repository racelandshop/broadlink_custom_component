# CUSTOM COMPONENT BROADLINK

This is a custom component to be used in conjuction with the broadlink [remote card](https://github.com/zroger49/broadllink-card). Currently only remotes are suported. 

Contrary to the "classic" broadlink integration, the remote is not registered in homeassistant (might be in the future)
The main point of this integration is to communicate with the broadlink custom_card through websockets. Feel free to use this code in your own project.

## Why?

Although great, the classic broadlink integration does not allow to run discover (AFAIK). The main goal of this integration is a solution that works out of the box without the need to configure anything 

## Features

- AutoDiscover
- Saves learned commands


## Configuration

To configure simply put this line in the configuration.yaml file: 
Also ensure the broadlink devices have been connected to your network

```
broadlink_custom_card:
```


Nao esquecer de dar contribuição ao techno broadlink 
