# Rasa Custom Channel Connector - WhatsApp

##  Overview
This repository contains a custom channel connector for Rasa Open Source that enables you to connect your Rasa chatbot to WhatsApp, one of the most popular messaging platforms worldwide. With this custom connector, you can interact with your Rasa chatbot through WhatsApp, providing a seamless conversational experience to your users.

## Features
- **WhatsApp Integration**: Connect your Rasa chatbot to WhatsApp and leverage its vast user base.
- **Two-way Messaging**: Send and receive messages between your Rasa bot and WhatsApp users.
- **Interactive Conversations**: Engage users in interactive conversations via WhatsApp.
- **Message Attachments**: Share images, files, and other attachments with your chatbot.
- **Configurable**: Easily configure the connector to work with your WhatsApp account.

## Prerequisites
Before you get started, make sure you have the following prerequisites in place:

- A WhatsApp Business Account: You need a WhatsApp Business Account to connect your chatbot to WhatsApp. Follow WhatsApp's guidelines to set up an account.

## Installation
To use this custom WhatsApp channel connector with your Rasa chatbot, follow these steps:

1. Clone this repository to your local machine:
```
git clone https://github.com/maharanasarkar/rasa-whatsapp_connector.git
```
Make sure git is installed locally on your PC.

2. Configure the connector by editing the `config.yml` file. You'll need to provide your WhatsApp Business Account details, including your phone number and authentication credentials.
3. Integrate the connector into your Rasa chatbot's configuration by including it in your `endpoints.yml` file:
```
custom_whatsapp_connector.CustomWhatsAppInput:
  webhook_url: "http://localhost:5056/webhook"
```
Replace the webhook_url with the appropriate endpoint where your WhatsApp connector is running.
4. Run your Rasa chatbot and start communicating with it through WhatsApp.
## Usage
Once your Rasa chatbot is connected to WhatsApp, users can initiate conversations with your bot on WhatsApp. Your bot can respond to user messages and engage in interactive dialogues.

Please note that WhatsApp's policies and terms of service apply when using this connector. Ensure your bot complies with WhatsApp's guidelines.

## Contributing

We welcome contributions from the community to enhance and maintain this custom WhatsApp channel connector for Rasa Open Source. If you'd like to contribute, please follow these steps:

- Fork this repository to your own GitHub account.
- Create a new branch with a descriptive name for your feature or bug fix.
- Make your changes and test them thoroughly.
- Create a pull request (PR) to merge your changes into the main branch of this repository.
- Include clear documentation and explanations of the changes made in your PR.

## Contact
If you have any questions or need assistance, please feel free to open an issue in this repository.

Enjoy connecting your Rasa chatbot to WhatsApp and building conversational experiences! 
