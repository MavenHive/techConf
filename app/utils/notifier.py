from datetime import datetime, timedelta
import json
import requests
import tweet_fetcher
from ..models.conference import Conference
from ..models.slackinfo import SlackInfo
from .. import app


def format_conference_data(conferences, user_id=None, page=0, per_page=3, notify_all=False):
    response = {}
    response['attachments'] = []
    if notify_all:
        response['response_type'] = 'in_channel'
    pretext = True
    # conferences = Conference.query.all()
    index = 0
    for conference in conferences:
        data = {}

        if index <= page * per_page:
            index += 1
            continue
        if index > (page + 1) * per_page:
            break
        index += 1

        data['title'] = conference.name
        data['text'] = 'Date : %s to %s\nLocation : %s\nDescription : %s' % (
            conference.start_date.date(), conference.end_date.date(), conference.location, conference.desc)
        data['title_link'] = conference.url
        data['color'] = '#36a64f'
        if pretext:
            if user_id:
                data['pretext'] = "*Hi <@" + user_id + ">! Some of the conferences I managed to find!*"
            else:
                data['pretext'] = "*Conferences in database*"
            data['mrkdwn_in'] = ['text', 'pretext']
            pretext = False
        response['attachments'].append(data)

    if len(response['attachments']) == 0:
        if user_id == None:
            return None
        data = {}
        data['color'] = '#e60000'
        data['pretext'] = "*Hi <@" + user_id + ">! Could not able to find any conferences for that region*"
        response['attachments'].append(data)
    return response


def send_notification(webhook_url, data):
    headers = {'content-type': 'application/json'}
    try:
        resp = requests.post(webhook_url, headers=headers, data=json.dumps(data))
        if resp.status_code != 200:
            print resp.text
            print "Something went wrong! Unable to send notifications to slack"
            return
    except:
        print "Connection error"
        return
    print "Data sent to ", webhook_url


def send_to_all_channels(data):
    channels = SlackInfo.query.all()
    for channel in channels:
        hours, minutes, seconds = app.config['SEND_SAME_TWEET_TIMER']
        if str(hash(str(data))) != channel.text_hash or datetime.now() - channel.last_sent_on > timedelta(hours=hours,
                                                                                                          minutes=minutes,
                                                                                                          seconds=seconds):
            print "Sending to : ", channel.channel_name
            send_notification(channel.incoming_webhook_url, data)
            channel.text_hash = str(hash(str(data)))
            channel.last_sent_on = datetime.now()
            channel.save()
        else:
            print "Message already sent to the channel"


def send_tweets():
    print "Sending tweets"
    tweet = tweet_fetcher.get_most_retweeted()
    response = {'attachments': []}
    data = {'pretext': '*Some trending news about conferences*', 'mrkdwn_in': ['text', 'pretext'],
            'title': 'Happening on twitter', 'text': tweet, 'color': '#36a64f'}
    response['attachments'].append(data)
    send_to_all_channels(response)


def notify_all():
    upcoming_conferences = Conference.fetch_upcoming_conferences(datetime.now().date())
    formatted_data = format_conference_data(upcoming_conferences)
    if formatted_data:
        # data = {'text' : "Time in my clock is :" + time.strftime('%X %x %Z')}
        send_to_all_channels(formatted_data)
