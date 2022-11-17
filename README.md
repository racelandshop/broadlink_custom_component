# CUSTOM COMPONENT BROADLINK

This is a custom component to be used in conjuction with the broadlink [remote card](https://github.com/zroger49/broadllink-card). Currently only remotes are suported.

Contrary to the "classic" broadlink integration, the remote is not registered in homeassistant (might be in the future)
The main point of this integration is to communicate with the broadlink custom_card through websockets. Feel free to use this code in your own project.

## Why?

Although great, the classic broadlink integration does not allow to run discover (AFAIK). The main goal of this integration is a solution that works out of the box without the need to configure anything (other than the custom_card and custom_component)

## Features

- AutoDiscover
- Saves learned commands in the backend

## Configuration

To configure simply put this line in the configuration.yaml file. Alternatively, this integration can also be configured through the config flow:
Also ensure the broadlink devices have been connected to your network

```
broadlink_custom_card:
```

### Send services 
To send a command to broadlink entity you can use the service `broadlink_custom_card.send_command`

```
service: broadlink_custom_card.send_command
data:
  button_name: PowerOff
target:
  entity_id: remote.foo
```

## Acknowledgements

Some code was inspired by the official broadlink integration in homeassistant (https://github.com/home-assistant/core/tree/dev/homeassistant/components/broadlink)
