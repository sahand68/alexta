from __future__ import print_function
from twilio.rest import TwilioRestClient

# Twilio account credentials
ACCOUNT_SID = "AC4dce8203c02091a26424866295da8211"
AUTH_TOKEN = "a1fa7d1b496046ba9a796109de7776a3"
TWILIO_NUMBER = "+19177468658"

# --------------- Main handler ------------------

def lambda_handler(event, context):
    """ 
    Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])

# --------------- Events ------------------

def on_session_started(session_started_request, session):
    """ Called when the session starts."""
    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they want."""
    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    # Dispatch to skill's launch
    return get_welcome_response()


def on_intent(intent_request, session):
    """Called when the user specifies an intent for this skill."""

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # Dispatch to skill's intent handlers
    if intent_name == "TextMessageIntent":
        return set_message_in_session(intent, session)
    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    else:
        raise ValueError("Invalid intent")


def on_session_ended(session_ended_request, session):
    """
    Called when the user ends the session.
    Is not called when the skill returns should_end_session=true.
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])


# --------------- Helpers that build all of the responses ----------------

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': title,
            'content': output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }

# --------------- Functions that control the skill's behavior ------------

def get_welcome_response():
    """ 
    If we wanted to initialize the session to have some attributes we could
    add those here.
    """

    session_attributes = {}
    card_title = "Welcome"
    speech_output = "You can send a text message to any number by saying, " \
                    "send a text to two zero one eight four nine three eight " \
                    "four eight saying Hi, how are you doing?."

    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = "Sorry I couldn't catch that. Please tell me what message " \
                    "you want to send by saying, send a text to two zero one " \
                    "eight four nine three eight four eight saying Hi, how are" \
                    "you doing?."
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def create_message_attributes(message):
    return {"textMessage": message}


def set_message_in_session(intent, session):
    """ 
    Sets the message in the session and uses the Twilio API to send a SMS to a user.
    """

    card_title = "Sending Text Message"
    session_attributes = {}

    if intent['slots']['Message']['value'] is not "": # if message is not empty
        message = intent['slots']['Message']['value']
        phone_number = intent['slots']['PhoneNumber']['value']
        session_attributes = create_message_attributes(message)
        send_and_display_message(intent)  # send the intended message
        speech_output = "Sent '" + message + "' to " + phone_number
        reprompt_text = "Sent '" + message + "' to " + phone_number
        should_end_session = True
    else:
        speech_output = "I was not able to send your message. " \
                        "Please try again. You can send a text message to " \
                        "any number by saying, send a text to two zero one " \
                        "eight four nine three eight four eight saying Hi, " \
                        "how are you doing?."
        reprompt_text = "I was not able to send your message. " \
                        "You can send a text message to any number by " \
                        "saying, send a text to two zero one eight four " \
                        "nine three eight four eight saying Hi, how are you doing?."
        should_end_session = False
    
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def send_and_display_message(intent):
    card_title = "Message Sent"

    try:
        slots = intent['slots']
        phone_number = slots['PhoneNumber']['value']
        text_message = slots['Message']['value']

        # send text
        if(send_text(phone_number, text_message)):
            speech_output = "Message sent."
            should_end_session = False
        else:
            speech_output = "Could not sent the message. Please try again."
            should_end_session = True
    except Exception:
        speech_output = "I did not understand the message. Please try again."
        should_end_session = True

    # Setting reprompt_text to None signifies that we do not want to reprompt
    # the user. If the user does not respond or says something that is not
    # understood, then the session will end.
    return build_response(None, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


def send_text(to_number, msg):
    try:
        client = TwilioRestClient(ACCOUNT_SID, AUTH_TOKEN)
        client.messages.create(to=to_number, from_=TWILIO_NUMBER, body=msg,)
        return True
    except Exception as error:
        print("Failed to send message: " + error.code)
        print("Message: " + error.msg)
        return False


def handle_session_end_request():
    """Called after the message has been sent."""
    card_title = "Text Messaging Session Ended"
    speech_output = "Thank you for using the text message app. " \
                    "Have a nice day! "
    should_end_session = True
    
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))